"""
Tests for config/settings.py and config/constants.py.

Validates that settings load correctly and all domain/agent constants
are complete and consistent.
"""

import pytest

from config.settings import Settings, settings, InferenceSettings, PathSettings, AppSettings
from config.constants import DOMAINS, AGENT_ROSTER, PROVIDER_MODEL_MAP, GRAPH_SCHEMA


class TestSettingsLoads:
    """Test that the global settings object loads correctly."""

    def test_settings_loads(self):
        assert isinstance(settings, Settings)
        assert isinstance(settings.inference, InferenceSettings)
        assert isinstance(settings.paths, PathSettings)
        assert isinstance(settings.app, AppSettings)

    def test_settings_paths_exist(self):
        assert settings.paths.base_dir.exists()
        # data_dir and sub-dirs may not exist yet, but the base should

    def test_settings_app_defaults(self):
        assert settings.app.vector_top_k > 0
        assert settings.app.graph_max_hops > 0
        assert settings.app.bm25_top_k > 0
        assert settings.app.agent_temperature >= 0
        assert settings.app.agent_max_tokens > 0
        assert settings.app.max_self_correction_rounds > 0

    def test_settings_inference_priority(self):
        # Should have at least one provider in priority
        assert len(settings.inference.priority) >= 1
        # Default includes groq, together, fireworks, ollama
        assert "ollama" in settings.inference.priority

    def test_settings_inference_models(self):
        assert settings.inference.router_model
        assert settings.inference.domain_model
        assert settings.inference.math_model
        assert settings.inference.code_model
        assert settings.inference.synthesis_model
        assert settings.inference.critique_model


class TestDomainsAllHaveKeywords:
    """Test domain definitions in constants.py."""

    def test_domains_all_have_keywords(self):
        expected_domains = {"cbdc", "privacy", "stablecoins", "bitcoin", "payment_tokens"}
        assert set(DOMAINS.keys()) == expected_domains

        for domain_key, domain_info in DOMAINS.items():
            assert "label" in domain_info, f"Domain {domain_key} missing 'label'"
            assert "description" in domain_info, f"Domain {domain_key} missing 'description'"
            assert "keywords" in domain_info, f"Domain {domain_key} missing 'keywords'"
            assert len(domain_info["keywords"]) >= 3, (
                f"Domain {domain_key} has too few keywords ({len(domain_info['keywords'])})"
            )

    def test_keywords_are_lowercase(self):
        for domain_key, domain_info in DOMAINS.items():
            for kw in domain_info["keywords"]:
                assert kw == kw.lower(), (
                    f"Keyword '{kw}' in domain '{domain_key}' should be lowercase"
                )


class TestAgentRosterComplete:
    """Test agent roster in constants.py."""

    def test_agent_roster_complete(self):
        expected_agents = {
            "router", "cbdc", "privacy", "stablecoins", "bitcoin",
            "payment_tokens", "math_crypto", "code", "synthesis", "critique",
        }
        assert set(AGENT_ROSTER.keys()) == expected_agents

    def test_agent_roster_structure(self):
        for agent_key, agent_info in AGENT_ROSTER.items():
            assert "label" in agent_info, f"Agent {agent_key} missing 'label'"
            assert "model_key" in agent_info, f"Agent {agent_key} missing 'model_key'"
            assert "description" in agent_info, f"Agent {agent_key} missing 'description'"

    def test_agent_model_keys_valid(self):
        """Every agent's model_key should be an attribute of InferenceSettings."""
        valid_model_keys = {
            "router_model", "domain_model", "math_model",
            "code_model", "synthesis_model", "critique_model",
        }
        for agent_key, agent_info in AGENT_ROSTER.items():
            assert agent_info["model_key"] in valid_model_keys, (
                f"Agent {agent_key} has invalid model_key '{agent_info['model_key']}'"
            )

    def test_every_domain_has_agent(self):
        """Every domain in DOMAINS should have a corresponding agent in AGENT_ROSTER."""
        for domain_key in DOMAINS:
            assert domain_key in AGENT_ROSTER, (
                f"Domain '{domain_key}' has no corresponding agent in AGENT_ROSTER"
            )


class TestProviderModelMap:
    """Test PROVIDER_MODEL_MAP in constants.py."""

    def test_provider_model_map_covers_all_models(self):
        # Collect all internal model names referenced by agents
        internal_models = set()
        for agent_key, agent_info in AGENT_ROSTER.items():
            model_key = agent_info["model_key"]
            model_name = getattr(settings.inference, model_key)
            internal_models.add(model_name)

        # Every provider should map all internal models
        for provider, mapping in PROVIDER_MODEL_MAP.items():
            for model in internal_models:
                assert model in mapping, (
                    f"Provider '{provider}' missing mapping for model '{model}'"
                )

    def test_provider_model_map_has_required_providers(self):
        expected_providers = {"groq", "together", "fireworks", "ollama"}
        assert set(PROVIDER_MODEL_MAP.keys()) == expected_providers

    def test_provider_model_map_values_are_strings(self):
        for provider, mapping in PROVIDER_MODEL_MAP.items():
            for internal_model, provider_model in mapping.items():
                assert isinstance(internal_model, str)
                assert isinstance(provider_model, str)
                assert len(provider_model) > 0


class TestGraphSchema:
    """Test GRAPH_SCHEMA in constants.py."""

    def test_graph_schema_node_types(self):
        assert "node_types" in GRAPH_SCHEMA
        expected_types = {"Paper", "Author", "Concept", "Method", "Result", "Institution", "Section"}
        assert set(GRAPH_SCHEMA["node_types"].keys()) == expected_types

    def test_graph_schema_relationship_types(self):
        assert "relationship_types" in GRAPH_SCHEMA
        assert len(GRAPH_SCHEMA["relationship_types"]) >= 10
        # Each relationship should be a tuple of (source_type, relation, target_type)
        for rel in GRAPH_SCHEMA["relationship_types"]:
            assert len(rel) == 3
            assert isinstance(rel[0], str)
            assert isinstance(rel[1], str)
            assert isinstance(rel[2], str)
