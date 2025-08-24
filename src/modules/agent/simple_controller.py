"""
Controller for the simplified supervisor-worker agent system.
"""

import logging
from typing import Any, AsyncGenerator, Dict

from src.modules.agent.simple_supervisor_agent import SimpleSupervisorAgent
from src.modules.query_answering.rag_with_chroma import MultimodalChromaRAGQueryEngine

logger = logging.getLogger(__name__)


class SimpleAgentController:
    """
    Manages the lifecycle and interaction with the SimpleSupervisorAgent.
    """

    def __init__(self, rag_path: str, rag_embedder_impl: str, model_name: str):
        """
        Initializes the controller and the underlying supervisor agent.
        """
        logger.info("Initializing SimpleAgentController...")
        try:
            rag_engine = MultimodalChromaRAGQueryEngine(
                persist_directory=rag_path,
                embedder_impl=rag_embedder_impl,
            )
            self.supervisor = SimpleSupervisorAgent(
                rag_engine=rag_engine, model_name=model_name
            )
            logger.info("SimpleAgentController initialized successfully.")
        except Exception as e:
            logger.error(
                f"Failed to initialize SimpleAgentController: {e}", exc_info=True
            )
            raise

    async def process_query(
        self, query: str, **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Starts the agent workflow for a given user query.

        Args:
            query: The user's query.
            **kwargs: Additional parameters for the RAG query.

        Returns:
            An async generator that yields the output of each agent step.
        """
        logger.info(f"Controller processing query: '{query}'")
        async for step in self.supervisor.process_query(query, **kwargs):
            yield step

    async def resume_with_clarification(
        self, action: str, selected_manual: str, **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Resumes the agent workflow with the user's clarification.

        Args:
            action: The action extracted from the initial query.
            selected_manual: The manual selected by the user.
            **kwargs: Additional parameters for the RAG query.

        Returns:
            An async generator that yields the output of the remaining agent steps.
        """
        logger.info(
            f"Controller resuming with manual: '{selected_manual}' for action: '{action}'"
        )
        async for step in self.supervisor.resume_with_clarification(
            action=action, selected_manual=selected_manual, **kwargs
        ):
            yield step
