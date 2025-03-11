from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sse_starlette.sse import EventSourceResponse
import time
import asyncio
from typing import List, Optional
from pydantic import BaseModel
from ollama_client import OllamaClient
import datetime

# Initialize FastAPI app
app = FastAPI(title="FastAPI Ollama Chat App")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")

# Add custom filters to Jinja2 environment
def strftime_filter(timestamp, format_str):
    return datetime.datetime.fromtimestamp(timestamp).strftime(format_str)

templates.env.filters["strftime"] = strftime_filter

# Initialize Ollama client
ollama_client = OllamaClient(base_url="http://localhost:11434")

# Default model to use
DEFAULT_MODEL = "llama3.2:1b"

# Define message model
class Message(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: Optional[float] = None
    model: Optional[str] = None

# In-memory chat history storage (in a real app, you'd use a database)
chat_history: List[Message] = []

# Dependency to get Ollama client
async def get_ollama_client():
    try:
        # Check if Ollama is available
        is_available = await ollama_client.check_model_availability(DEFAULT_MODEL)
        if not is_available:
            raise HTTPException(status_code=503, detail=f"Ollama service or model {DEFAULT_MODEL} not available")
        return ollama_client
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Error connecting to Ollama: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    await ollama_client.close()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # Get available models
    try:
        models = await ollama_client.list_available_models()
    except Exception:
        models = [{"name": DEFAULT_MODEL}]
    
    return templates.TemplateResponse(
        "index.html", 
        {
            "request": request, 
            "title": "Ollama Chat App", 
            "messages": chat_history,
            "models": models,
            "default_model": DEFAULT_MODEL
        }
    )

@app.post("/send-message", response_class=HTMLResponse)
async def send_message(
    request: Request,
    message: str = Form(...),
    model: str = Form(DEFAULT_MODEL),
    client: OllamaClient = Depends(get_ollama_client)
):
    # Add user message to history
    user_message = Message(role="user", content=message, timestamp=time.time())
    chat_history.append(user_message)
    
    try:
        # Get response from Ollama
        response = await client.generate(
            prompt=message,
            model=model,
            system="You are a helpful AI assistant. Provide clear and concise responses.",
            temperature=0.7
        )
        
        # Add assistant response to history
        assistant_message = Message(
            role="assistant", 
            content=response.get("response", "Sorry, I couldn't generate a response."),
            timestamp=time.time(),
            model=model
        )
        chat_history.append(assistant_message)
        
        # Return only the new messages for HTMX to insert
        return templates.TemplateResponse(
            "partials/messages.html", 
            {"request": request, "messages": [user_message, assistant_message]}
        )
    except Exception as e:
        # Handle errors
        error_message = Message(
            role="system", 
            content=f"Error: {str(e)}",
            timestamp=time.time()
        )
        chat_history.append(error_message)
        return templates.TemplateResponse(
            "partials/messages.html", 
            {"request": request, "messages": [user_message, error_message]}
        )

@app.post("/send-message-stream")
async def send_message_stream(
    request: Request,
    message: str = Form(...),
    model: str = Form(DEFAULT_MODEL),
    client: OllamaClient = Depends(get_ollama_client)
):
    # Add user message to history
    user_message = Message(role="user", content=message, timestamp=time.time())
    chat_history.append(user_message)
    
    # Create a placeholder for the assistant's message
    assistant_message = Message(role="assistant", content="", timestamp=time.time(), model=model)
    chat_history.append(assistant_message)
    
    async def event_generator():
        try:
            # Initial message with user input
            yield {
                "event": "user_message",
                "data": templates.TemplateResponse(
                    "partials/message.html", 
                    {"request": request, "message": user_message}
                ).body.decode()
            }
            
            # Start the assistant message container
            yield {
                "event": "assistant_start",
                "data": templates.TemplateResponse(
                    "partials/message_start.html", 
                    {"request": request, "message_id": len(chat_history) - 1, "model": model}
                ).body.decode()
            }
            
            # Stream the response from Ollama
            full_response = ""
            async for token in client.generate_stream(
                prompt=message,
                model=model,
                system="You are a helpful AI assistant. Provide clear and concise responses.",
                temperature=0.7
            ):
                full_response += token
                assistant_message.content = full_response
                yield {
                    "event": "token",
                    "data": token
                }
                await asyncio.sleep(0.01)  # Small delay for smoother streaming
                
            # Final event to signal completion
            yield {
                "event": "done",
                "data": "Message complete"
            }
            
        except Exception as e:
            # Handle errors
            error_message = f"Error: {str(e)}"
            yield {
                "event": "error",
                "data": error_message
            }
            # Update the assistant message with the error
            assistant_message.content = error_message
    
    return EventSourceResponse(event_generator())

@app.get("/clear-chat", response_class=HTMLResponse)
async def clear_chat(request: Request):
    # Clear chat history
    chat_history.clear()
    return templates.TemplateResponse(
        "partials/chat_container.html", 
        {"request": request, "messages": chat_history}
    )

@app.get("/models", response_class=HTMLResponse)
async def list_models(request: Request):
    try:
        models = await ollama_client.list_available_models()
        return templates.TemplateResponse(
            "partials/model_selector.html",
            {"request": request, "models": models, "default_model": DEFAULT_MODEL}
        )
    except Exception as e:
        return HTMLResponse(f"<div class='alert alert-danger'>Error listing models: {str(e)}</div>")

@app.get("/htmx-demo", response_class=HTMLResponse)
async def htmx_demo(request: Request):
    # Simulate a delay to show the loading spinner
    time.sleep(1)
    
    # Return HTML content that will be injected by HTMX
    return """
    <div class="alert alert-success">
        <h4 class="alert-heading">HTMX Works!</h4>
        <p>This content was loaded dynamically using HTMX without a full page reload.</p>
        <hr>
        <p class="mb-0">The current time is: {}</p>
    </div>
    """.format(time.strftime("%H:%M:%S"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
