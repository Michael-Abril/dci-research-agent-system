"""
Unified LLM client that speaks to any OpenAI-compatible API.

Supports Groq, Together AI, Fireworks AI, and Ollama — all of which
expose an OpenAI-compatible chat completions endpoint.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator, Dict, List, Optional

import httpx
from openai import AsyncOpenAI

from config.settings import settings
from config.constants import PROVIDER_ENDPOINTS, PROVIDER_MODEL_MAP

logger = logging.getLogger(__name__)


class LLMClient:
    """Thin wrapper around AsyncOpenAI pointed at any compatible endpoint."""

    def __init__(
        self,
        provider: str,
        api_key: str = "",
        base_url: str = "",
    ):
        self.provider = provider

        if not base_url:
            if provider == "ollama":
                base_url = settings.inference.ollama_base_url + "/v1"
            else:
                base_url = PROVIDER_ENDPOINTS.get(provider, "")

        if not api_key:
            api_key = self._resolve_api_key(provider)

        self._client = AsyncOpenAI(
            api_key=api_key or "ollama",  # Ollama doesn't need a real key
            base_url=base_url,
            http_client=httpx.AsyncClient(timeout=120.0),
        )

    # ── Public API ──────────────────────────────────────────────────

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> str:
        """Send a chat completion request and return the full response text."""
        resolved_model = self._resolve_model(model)
        try:
            response = await self._client.chat.completions.create(
                model=resolved_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error("LLM call failed [%s/%s]: %s", self.provider, resolved_model, e)
            raise

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        """Stream a chat completion, yielding text chunks."""
        resolved_model = self._resolve_model(model)
        try:
            stream = await self._client.chat.completions.create(
                model=resolved_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as e:
            logger.error("LLM stream failed [%s/%s]: %s", self.provider, resolved_model, e)
            raise

    # ── Internal helpers ────────────────────────────────────────────

    def _resolve_model(self, internal_name: str) -> str:
        """Map an internal model name to the provider-specific model ID."""
        mapping = PROVIDER_MODEL_MAP.get(self.provider, {})
        return mapping.get(internal_name, internal_name)

    @staticmethod
    def _resolve_api_key(provider: str) -> str:
        key_map = {
            "groq": settings.inference.groq_api_key,
            "together": settings.inference.together_api_key,
            "fireworks": settings.inference.fireworks_api_key,
            "ollama": "ollama",
        }
        return key_map.get(provider, "")
