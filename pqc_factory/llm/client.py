"""Nebius Token Factory / OpenAI-compatible LLM client."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential


class LLMClient:
    """Thin wrapper around the OpenAI-compatible Nebius Token Factory API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("NEBIUS_API_KEY", "dummy-key-for-local")
        self.base_url = base_url or os.getenv(
            "NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/"
        )
        self.default_model = default_model or os.getenv(
            "SPECIALIST_MODEL", "nvidia/Nemotron-3-Super-120b-a12b"
        )
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self.total_tokens = 0

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> str:
        """Send a chat completion request and return the assistant content."""
        response = self.client.chat.completions.create(
            model=model or self.default_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        if response.usage:
            self.total_tokens += response.usage.total_tokens or 0
        return response.choices[0].message.content or ""

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """Force JSON-style responses when possible."""
        return self.chat(messages, model=model, **kwargs)
