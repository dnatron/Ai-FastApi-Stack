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

# Inicializace FastAPI aplikace
app = FastAPI(title="FastAPI Ollama Chat App")

# Připojení statických souborů (CSS, JS, atd.)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Nastavení šablon Jinja2
templates = Jinja2Templates(directory="templates")

# Přidání vlastního filtru do Jinja2 prostředí pro formátování časových značek
def strftime_filter(timestamp, format_str):
    return datetime.datetime.fromtimestamp(timestamp).strftime(format_str)

templates.env.filters["strftime"] = strftime_filter

# Inicializace Ollama klienta pro komunikaci s LLM modely
ollama_client = OllamaClient(base_url="http://localhost:11434")

# Výchozí model, který bude použit, pokud uživatel nevybere jiný
DEFAULT_MODEL = "llama3.2:1b"

# Definice datového modelu pro zprávy
class Message(BaseModel):
    role: str  # 'user' (uživatel) nebo 'assistant' (asistent)
    content: str  # obsah zprávy
    timestamp: Optional[float] = None  # časová značka
    model: Optional[str] = None  # použitý LLM model

# Úložiště historie chatu v paměti (v reálné aplikaci by bylo vhodné použít databázi)
chat_history: List[Message] = []

# Dependency pro získání Ollama klienta a kontrolu dostupnosti služby
async def get_ollama_client():
    try:
        # Kontrola, zda je Ollama dostupná
        is_available = await ollama_client.check_model_availability(DEFAULT_MODEL)
        if not is_available:
            raise HTTPException(status_code=503, detail=f"Ollama služba nebo model {DEFAULT_MODEL} není dostupný")
        return ollama_client
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Chyba při připojení k Ollama: {str(e)}")

# Událost při vypnutí aplikace - zajistí korektní uzavření spojení
@app.on_event("shutdown")
async def shutdown_event():
    await ollama_client.close()

# Hlavní stránka aplikace
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # Získání dostupných modelů
    try:
        models = await ollama_client.list_available_models()
    except Exception:
        # Pokud se nepodaří získat seznam modelů, použije se výchozí model
        models = [{"name": DEFAULT_MODEL}]
    
    # Vykreslení šablony s daty
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

# Endpoint pro odeslání zprávy (bez streamování)
@app.post("/send-message", response_class=HTMLResponse)
async def send_message(
    request: Request,
    message: str = Form(...),  # Text zprávy od uživatele
    model: str = Form(DEFAULT_MODEL),  # Vybraný model
    client: OllamaClient = Depends(get_ollama_client)  # Ollama klient
):
    # Přidání zprávy uživatele do historie
    user_message = Message(role="user", content=message, timestamp=time.time())
    chat_history.append(user_message)
    
    try:
        # Získání odpovědi z Ollama
        response = await client.generate(
            prompt=message,
            model=model,
            system="You are a helpful AI assistant. Provide clear and concise responses.",
            temperature=0.7  # Parametr ovlivňující kreativitu odpovědí (vyšší = kreativnější)
        )
        
        # Přidání odpovědi asistenta do historie
        assistant_message = Message(
            role="assistant", 
            content=response.get("response", "Omlouvám se, nepodařilo se vygenerovat odpověď."),
            timestamp=time.time(),
            model=model
        )
        chat_history.append(assistant_message)
        
        # Vrácení pouze nových zpráv pro HTMX k vložení do DOM
        return templates.TemplateResponse(
            "partials/messages.html", 
            {"request": request, "messages": [user_message, assistant_message]}
        )
    except Exception as e:
        # Zpracování chyb
        error_message = Message(
            role="system", 
            content=f"Chyba: {str(e)}",
            timestamp=time.time()
        )
        chat_history.append(error_message)
        return templates.TemplateResponse(
            "partials/messages.html", 
            {"request": request, "messages": [user_message, error_message]}
        )

# Endpoint pro odeslání zprávy se streamováním odpovědi (postupné zobrazování)
@app.post("/send-message-stream")
async def send_message_stream(
    request: Request,
    message: str = Form(...),
    model: str = Form(DEFAULT_MODEL),
    client: OllamaClient = Depends(get_ollama_client)
):
    # Přidání zprávy uživatele do historie
    user_message = Message(role="user", content=message, timestamp=time.time())
    chat_history.append(user_message)
    
    # Vytvoření zástupného místa pro zprávu asistenta
    assistant_message = Message(role="assistant", content="", timestamp=time.time(), model=model)
    chat_history.append(assistant_message)
    
    # Generátor událostí pro SSE (Server-Sent Events)
    async def event_generator():
        try:
            # Počáteční událost se zprávou uživatele
            yield {
                "event": "user_message",
                "data": templates.TemplateResponse(
                    "partials/message.html", 
                    {"request": request, "message": user_message}
                ).body.decode()
            }
            
            # Začátek kontejneru pro zprávu asistenta
            yield {
                "event": "assistant_start",
                "data": templates.TemplateResponse(
                    "partials/message_start.html", 
                    {"request": request, "message_id": len(chat_history) - 1, "model": model}
                ).body.decode()
            }
            
            # Streamování odpovědi z Ollama (token po tokenu)
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
                await asyncio.sleep(0.01)  # Malé zpoždění pro plynulejší streamování
                
            # Konečná událost signalizující dokončení
            yield {
                "event": "done",
                "data": "Message complete"
            }
            
        except Exception as e:
            # Zpracování chyb
            error_message = f"Chyba: {str(e)}"
            yield {
                "event": "error",
                "data": error_message
            }
            # Aktualizace zprávy asistenta s chybou
            assistant_message.content = error_message
    
    # Vrácení EventSourceResponse pro SSE
    return EventSourceResponse(event_generator())

# Endpoint pro vymazání historie chatu
@app.get("/clear-chat", response_class=HTMLResponse)
async def clear_chat(request: Request):
    # Vymazání historie chatu
    chat_history.clear()
    return templates.TemplateResponse(
        "partials/chat_container.html", 
        {"request": request, "messages": chat_history}
    )

# Endpoint pro získání seznamu dostupných modelů
@app.get("/models", response_class=HTMLResponse)
async def list_models(request: Request):
    try:
        models = await ollama_client.list_available_models()
        return templates.TemplateResponse(
            "partials/model_selector.html",
            {"request": request, "models": models, "default_model": DEFAULT_MODEL}
        )
    except Exception as e:
        return HTMLResponse(f"<div class='alert alert-danger'>Chyba při načítání modelů: {str(e)}</div>")

# Demonstrační endpoint pro ukázku funkčnosti HTMX
@app.get("/htmx-demo", response_class=HTMLResponse)
async def htmx_demo(request: Request):
    # Simulace zpoždění pro zobrazení načítacího indikátoru
    time.sleep(1)
    
    # Vrácení HTML obsahu, který bude vložen pomocí HTMX
    return """
    <div class="alert alert-success">
        <h4 class="alert-heading">HTMX funguje!</h4>
        <p>Tento obsah byl načten dynamicky pomocí HTMX bez kompletního obnovení stránky.</p>
        <hr>
        <p class="mb-0">Aktuální čas je: {}</p>
    </div>
    """.format(time.strftime("%H:%M:%S"))

# Spuštění aplikace při přímém spuštění tohoto souboru
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)  # reload=True umožňuje automatické restartování při změnách kódu
