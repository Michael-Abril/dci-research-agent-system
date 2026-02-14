"""
LLM client abstraction layer.

Provides a unified async interface for OpenAI and Anthropic model calls,
with automatic retry logic via tenacity and proper async I/O.
Routes requests to the appropriate provider based on model name.
"""

from __future__ import annotations

import json
from typing import Any

from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from src.utils.logging import setup_logging

logger = setup_logging("llm.client")


# Retry configuration: 3 attempts with exponential backoff (1s, 2s, 4s)
_RETRY_KWARGS = {
    "stop": stop_after_attempt(3),
    "wait": wait_exponential(multiplier=1, min=1, max=10),
    "before_sleep": before_sleep_log(logger, log_level=20),  # INFO level
    "reraise": True,
}


class LLMClient:
    """Unified async LLM client supporting OpenAI and Anthropic models.

    Routes requests to the appropriate provider based on model name.
    OpenAI models start with 'gpt-'; Anthropic models start with 'claude-'.

    All I/O is truly async — uses AsyncOpenAI and AsyncAnthropic clients
    with tenacity retry decorators for resilience against transient failures.
    """

    def __init__(
        self,
        openai_api_key: str = "",
        anthropic_api_key: str = "",
    ):
        self._openai: AsyncOpenAI | None = None
        self._anthropic: AsyncAnthropic | None = None
        self._usage_log: list[dict[str, Any]] = []

        if openai_api_key:
            self._openai = AsyncOpenAI(api_key=openai_api_key)
        if anthropic_api_key:
            self._anthropic = AsyncAnthropic(api_key=anthropic_api_key)

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

    @retry(**_RETRY_KWARGS)
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
        response = await self._openai.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or ""

        # Track usage
        usage = response.usage
        if usage:
            self._usage_log.append({
                "provider": "openai",
                "model": model,
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
            })
            logger.debug(
                "OpenAI usage: %d prompt + %d completion = %d total tokens",
                usage.prompt_tokens, usage.completion_tokens, usage.total_tokens,
            )

        logger.debug("OpenAI response: %d chars", len(content))
        return content

    @retry(**_RETRY_KWARGS)
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
        response = await self._anthropic.messages.create(**kwargs)
        content = response.content[0].text

        # Track usage
        usage = response.usage
        if usage:
            self._usage_log.append({
                "provider": "anthropic",
                "model": model,
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
            })
            logger.debug(
                "Anthropic usage: %d input + %d output tokens",
                usage.input_tokens, usage.output_tokens,
            )

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

    def get_usage_summary(self) -> dict[str, Any]:
        """Return a summary of token usage across all calls."""
        if not self._usage_log:
            return {"total_calls": 0}

        openai_calls = [u for u in self._usage_log if u["provider"] == "openai"]
        anthropic_calls = [u for u in self._usage_log if u["provider"] == "anthropic"]

        return {
            "total_calls": len(self._usage_log),
            "openai": {
                "calls": len(openai_calls),
                "total_tokens": sum(u.get("total_tokens", 0) for u in openai_calls),
            },
            "anthropic": {
                "calls": len(anthropic_calls),
                "input_tokens": sum(u.get("input_tokens", 0) for u in anthropic_calls),
                "output_tokens": sum(u.get("output_tokens", 0) for u in anthropic_calls),
            },
        }

    async def close(self) -> None:
        """Close underlying HTTP connections for clean shutdown."""
        if self._openai:
            await self._openai.close()
        if self._anthropic:
            await self._anthropic.close()
