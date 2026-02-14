"""
LLM client abstraction layer.

Provides a unified interface for OpenAI and Anthropic model calls,
allowing the system to route different components to different providers.
"""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI
from anthropic import Anthropic

from src.utils.logging import setup_logging

logger = setup_logging("llm.client")


class LLMClient:
    """Unified LLM client supporting OpenAI and Anthropic models.

    Routes requests to the appropriate provider based on model name.
    OpenAI models start with 'gpt-'; Anthropic models start with 'claude-'.
    """

    def __init__(
        self,
        openai_api_key: str = "",
        anthropic_api_key: str = "",
    ):
        self._openai: OpenAI | None = None
        self._anthropic: Anthropic | None = None

        if openai_api_key:
            self._openai = OpenAI(api_key=openai_api_key)
        if anthropic_api_key:
            self._anthropic = Anthropic(api_key=anthropic_api_key)

    def _is_anthropic(self, model: str) -> bool:
        return model.startswith("claude")

    async def complete(
        self,
        prompt: str,
        system_prompt: str = "",
        model: str = "gpt-4o",
        temperature: float = 0.1,
        max_tokens: int = 4096,
        response_format: str | None = None,
    ) -> str:
        """Generate a completion from the appropriate LLM provider.

        Args:
            prompt: User message / prompt.
            system_prompt: System message for context.
            model: Model identifier (determines provider routing).
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in response.
            response_format: If "json", request JSON output.

        Returns:
            Generated text response.
        """
        if self._is_anthropic(model):
            return await self._complete_anthropic(
                prompt, system_prompt, model, temperature, max_tokens
            )
        return await self._complete_openai(
            prompt, system_prompt, model, temperature, max_tokens, response_format
        )

    async def _complete_openai(
        self,
        prompt: str,
        system_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
        response_format: str | None,
    ) -> str:
        if not self._openai:
            raise RuntimeError("OpenAI client not initialized. Provide OPENAI_API_KEY.")

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}

        logger.debug("OpenAI request: model=%s, tokens=%d", model, max_tokens)
        response = self._openai.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or ""
        logger.debug("OpenAI response: %d chars", len(content))
        return content

    async def _complete_anthropic(
        self,
        prompt: str,
        system_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        if not self._anthropic:
            raise RuntimeError(
                "Anthropic client not initialized. Provide ANTHROPIC_API_KEY."
            )

        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        logger.debug("Anthropic request: model=%s, tokens=%d", model, max_tokens)
        response = self._anthropic.messages.create(**kwargs)
        content = response.content[0].text
        logger.debug("Anthropic response: %d chars", len(content))
        return content

    async def complete_json(
        self,
        prompt: str,
        system_prompt: str = "",
        model: str = "gpt-4o",
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Generate a completion and parse the result as JSON.

        Uses JSON mode for OpenAI models. For Anthropic, instructs the model
        to respond in JSON and extracts it from the response.
        """
        from src.utils.helpers import extract_json_from_response

        if self._is_anthropic(model):
            suffix = "\n\nRespond with valid JSON only. No other text."
            raw = await self.complete(
                prompt + suffix, system_prompt, model, temperature, max_tokens
            )
        else:
            raw = await self.complete(
                prompt, system_prompt, model, temperature, max_tokens, "json"
            )

        return extract_json_from_response(raw)
