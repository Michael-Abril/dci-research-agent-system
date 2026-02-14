"""
Dependency injection for the DCI Research Agent API.

Manages singleton instances of system components (orchestrator, database, etc.)
shared across API requests via FastAPI's dependency injection system.
"""

from __future__ import annotations

from config.settings import get_config
from src.llm.client import LLMClient
from src.retrieval.pageindex_retriever import PageIndexRetriever
from src.retrieval.index_manager import IndexManager
from src.agents.router import QueryRouter
from src.agents.domain_agents import DomainAgentFactory
from src.agents.synthesizer import ResponseSynthesizer
from src.agents.orchestrator import AgentOrchestrator
from src.persistence.database import DatabaseManager


class SystemComponents:
    """Container for all system components, initialized once at startup."""

    def __init__(self) -> None:
        self.config = get_config()
        self.database: DatabaseManager | None = None
        self.llm_client: LLMClient | None = None
        self.retriever: PageIndexRetriever | None = None
        self.orchestrator: AgentOrchestrator | None = None
        self.index_manager: IndexManager | None = None
        self.mode_info: dict = {}

    async def initialize(self) -> None:
        """Initialize all system components."""
        config = self.config

        # Database
        self.database = DatabaseManager(config.paths.database_path)
        await self.database.initialize()

        # LLM
        has_openai = bool(config.llm.openai_api_key)
        has_anthropic = bool(config.llm.anthropic_api_key)

        self.llm_client = LLMClient(
            openai_api_key=config.llm.openai_api_key,
            anthropic_api_key=config.llm.anthropic_api_key,
        )

        # Retrieval
        self.retriever = PageIndexRetriever(
            indexes_dir=config.paths.indexes_dir,
            documents_dir=config.paths.documents_dir,
            llm_client=self.llm_client,
            model=config.llm.pageindex_model,
        )

        # Agents
        router = QueryRouter(llm_client=self.llm_client, model=config.llm.router_model)
        agent_factory = DomainAgentFactory(
            llm_client=self.llm_client, model=config.llm.agent_model
        )
        synthesizer = ResponseSynthesizer(
            llm_client=self.llm_client, model=config.llm.synthesizer_model
        )

        # Orchestrator
        self.orchestrator = AgentOrchestrator(
            retriever=self.retriever,
            router=router,
            agent_factory=agent_factory,
            synthesizer=synthesizer,
            database=self.database,
        )

        # Index manager
        self.index_manager = IndexManager(
            documents_dir=config.paths.documents_dir,
            indexes_dir=config.paths.indexes_dir,
            llm_client=self.llm_client,
        )

        # Mode info
        num_indexes = sum(
            len(docs) for docs in self.index_manager.list_indexes().values()
        )
        self.mode_info = {
            "has_openai": has_openai,
            "has_anthropic": has_anthropic,
            "num_indexes": num_indexes,
            "mode": "full" if (has_openai and has_anthropic) else (
                "partial" if (has_openai or has_anthropic) else "local"
            ),
        }

    async def shutdown(self) -> None:
        """Clean up resources."""
        if self.llm_client:
            await self.llm_client.close()
        if self.database:
            await self.database.close()


# Singleton instance
_components: SystemComponents | None = None


def get_components() -> SystemComponents:
    """Get the global system components instance."""
    if _components is None:
        raise RuntimeError("System not initialized. Call initialize_components() first.")
    return _components


async def initialize_components() -> SystemComponents:
    """Initialize and return global system components."""
    global _components
    _components = SystemComponents()
    await _components.initialize()
    return _components


async def shutdown_components() -> None:
    """Shut down global system components."""
    global _components
    if _components:
        await _components.shutdown()
        _components = None
