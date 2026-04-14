"""Ollama API client with JSON mode support."""

import httpx
import json
from typing import Optional


class OllamaClient:
    """Client for Ollama API with JSON format enforcement."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "gemma4:e4b",
    ):
        self.base_url = base_url
        self.model = model

    def generate(
        self,
        prompt: str,
        system: str = "",
        format: str = "json",
        temperature: float = 0.1,
        max_tokens: int = 800,
    ) -> dict:
        """
        Generate response from Ollama with JSON format.

        Args:
            prompt: User prompt/message
            system: System prompt
            format: Output format ("json" enforces structured output)
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate

        Returns:
            Parsed JSON response from the model

        Raises:
            httpx.HTTPError: If API request fails
            json.JSONDecodeError: If response is not valid JSON
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": format,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        if system:
            payload["system"] = system

        try:
            response = httpx.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=180.0,
            )
            response.raise_for_status()

            result = response.json()
            output_text = result["response"]

            # Parse JSON from response
            return json.loads(output_text)

        except httpx.HTTPError as e:
            raise ConnectionError(f"Failed to connect to Ollama: {e}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response from model: {e}\nResponse: {output_text[:500]}")

    def check_health(self) -> bool:
        """Check if Ollama is running and model is available."""
        try:
            response = httpx.get(f"{self.base_url}/api/tags", timeout=5.0)
            response.raise_for_status()

            models = response.json().get("models", [])
            model_names = [m["name"] for m in models]

            return self.model in model_names
        except Exception:
            return False
