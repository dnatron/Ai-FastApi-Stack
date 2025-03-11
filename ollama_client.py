import httpx
import json
from typing import AsyncGenerator, Dict, Any, Optional

class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=60.0)
        
    async def generate(self, 
                      prompt: str, 
                      model: str = "llama2:latest", 
                      system: Optional[str] = None,
                      temperature: float = 0.7,
                      max_tokens: int = 2000) -> Dict[str, Any]:
        """
        Generate a response from Ollama without streaming.
        """
        # Ensure model name is correct
        if not await self.check_model_availability(model):
            raise Exception(f"Model '{model}' is not available. Please check the model name or pull the model first.")
            
        payload = {
            "model": model,
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if system:
            payload["system"] = system
            
        try:
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=60.0
            )
            response.raise_for_status()
            
            # Parse the response - Ollama may return multiple JSON objects
            # We need to get the last complete one with "done": true
            response_text = response.text
            lines = response_text.strip().split('\n')
            
            # Get the last line which should contain the completed response
            last_response = None
            full_response_text = ""
            
            for line in lines:
                if line.strip():
                    try:
                        json_response = json.loads(line)
                        if "response" in json_response:
                            full_response_text += json_response["response"]
                        if json_response.get("done", False):
                            last_response = json_response
                    except json.JSONDecodeError:
                        continue
            
            # If we found a complete response, return it
            if last_response:
                return {"response": full_response_text}
            
            # If we didn't find a complete response but collected some text
            if full_response_text:
                return {"response": full_response_text}
                
            # Fallback to returning the raw response
            return {"response": "Could not parse response from Ollama API"}
            
        except httpx.HTTPStatusError as e:
            # Try to get more detailed error information from the response
            error_detail = "Unknown error"
            try:
                error_json = e.response.json()
                error_detail = error_json.get("error", str(e))
            except json.JSONDecodeError:
                error_detail = str(e)
                
            raise Exception(f"Ollama API error: {error_detail}")
        except httpx.HTTPError as e:
            raise Exception(f"Failed to generate response: {str(e)}")
    
    async def generate_stream(self, 
                             prompt: str, 
                             model: str = "llama2",
                             system: Optional[str] = None,
                             temperature: float = 0.7,
                             max_tokens: int = 2000) -> AsyncGenerator[str, None]:
        """
        Stream a response from Ollama.
        """
        payload = {
            "model": model,
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }
        
        if system:
            payload["system"] = system
            
        async with self.client.stream(
            "POST",
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=60.0
        ) as response:
            response.raise_for_status()
            
            async for chunk in response.aiter_text():
                if chunk.strip():
                    try:
                        data = json.loads(chunk)
                        if "response" in data:
                            yield data["response"]
                    except json.JSONDecodeError:
                        continue
    
    async def check_model_availability(self, model: str = "llama2:latest") -> bool:
        """
        Check if the specified model is available in Ollama.
        """
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            models = response.json().get("models", [])
            
            # Check for exact match first
            if any(m["name"] == model for m in models):
                return True
                
            # If no exact match, check if the model name is a prefix of any available model
            model_prefix = model.split(':')[0]
            return any(m["name"].startswith(model_prefix) for m in models)
        except (httpx.HTTPError, KeyError):
            return False
    
    async def list_available_models(self) -> list:
        """
        List all available models in Ollama.
        """
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            return response.json().get("models", [])
        except (httpx.HTTPError, KeyError):
            return []
    
    async def close(self):
        """
        Close the HTTP client.
        """
        await self.client.aclose()
