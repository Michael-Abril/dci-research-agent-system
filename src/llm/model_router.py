"""
Model Router — finds the best available inference provider for a given model.

Tries providers in priority order (configured in settings) and falls back
gracefully.  This is the single entry point every agent uses to get an
LLM client + resolved model name.
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple

from config.settings import settings
from config.constants import PROVIDER_MODEL_MAP
from src.llm.client import LLMClient

logger = logging.getLogger(__name__)

# Cache instantiated clients so we don't re-create them per request.
_client_cache: dict[str, LLMClient] = {}


class ModelRouter:
    """Resolve an internal model name to (LLMClient, provider_model_id)."""

    @staticmethod
    def get_client(internal_model: str) -> Tuple[LLMClient, str]:
        """
        Return an (LLMClient, resolved_model_name) tuple for the first
        provider that (a) has an API key configured and (b) has a mapping
        for the requested model.

        Raises RuntimeError if no provider is available.
        """
        for provider in settings.inference.priority:
            # Check if the provider has credentials
            if not ModelRouter._provider_available(provider):
                continue

            # Check if the provider supports this model
            mapping = PROVIDER_MODEL_MAP.get(provider, {})
            if internal_model not in mapping and provider != "ollama":
                continue

            client = ModelRouter._get_or_create_client(provider)
            resolved = mapping.get(internal_model, internal_model)
            logger.debug("Routing %s → %s/%s", internal_model, provider, resolved)
            return client, resolved

        raise RuntimeError(
            f"No inference provider available for model '{internal_model}'. "
            f"Configure at least one provider in .env (GROQ_API_KEY, "
            f"TOGETHER_API_KEY, FIREWORKS_API_KEY, or OLLAMA_BASE_URL)."
        )

    # ── Internal helpers ────────────────────────────────────────────

    @staticmethod
    def _provider_available(provider: str) -> bool:
        if provider == "groq":
            return bool(settings.inference.groq_api_key)
        if provider == "together":
            return bool(settings.inference.together_api_key)
        if provider == "fireworks":
            return bool(settings.inference.fireworks_api_key)
        if provider == "ollama":
            return True  # Ollama is always "available" (may fail at call time)
        return False

    @staticmethod
    def _get_or_create_client(provider: str) -> LLMClient:
        if provider not in _client_cache:
            _client_cache[provider] = LLMClient(provider=provider)
        return _client_cache[provider]
