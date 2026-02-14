"""Ollama client for clawlite."""

import json
from dataclasses import dataclass
from typing import Optional

import httpx


@dataclass
class ChatMessage:
    """A chat message."""
    role: str  # "system", "user", or "assistant"
    content: str


@dataclass
class ChatResponse:
    """Response from Ollama chat."""
    content: str
    done: bool
    model: str
    total_duration_ms: Optional[int] = None
    load_duration_ms: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    eval_count: Optional[int] = None


class OllamaClient:
    """Client for Ollama REST API."""
    
    def __init__(
        self,
        model: str = "llama3.1:8b-instruct",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.1,
        timeout: float = 120.0,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout)
    
    def chat(self, messages: list[ChatMessage]) -> ChatResponse:
        """Send chat messages to Ollama.
        
        Args:
            messages: List of chat messages
            
        Returns:
            ChatResponse with the assistant's reply
        """
        payload = {
            "model": self.model,
            "messages": [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ],
            "stream": False,
            "options": {
                "temperature": self.temperature,
            },
        }
        
        response = self.client.post(
            f"{self.base_url}/api/chat",
            json=payload,
        )
        response.raise_for_status()
        
        data = response.json()
        
        return ChatResponse(
            content=data["message"]["content"],
            done=data.get("done", True),
            model=data.get("model", self.model),
            total_duration_ms=data.get("total_duration", 0) // 1_000_000 if data.get("total_duration") else None,
            load_duration_ms=data.get("load_duration", 0) // 1_000_000 if data.get("load_duration") else None,
            prompt_eval_count=data.get("prompt_eval_count"),
            eval_count=data.get("eval_count"),
        )
    
    def is_healthy(self) -> bool:
        """Check if Ollama server is reachable."""
        try:
            response = self.client.get(f"{self.base_url}/api/tags", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False
    
    def close(self):
        """Close the HTTP client."""
        self.client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()
