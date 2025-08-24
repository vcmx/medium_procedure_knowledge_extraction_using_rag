"""
A simple worker agent that wraps the MultimodalChromaRAGQueryEngine.
"""

import logging
from typing import Dict

from src.modules.query_answering.rag_with_chroma import MultimodalChromaRAGQueryEngine

logger = logging.getLogger(__name__)


class SimpleRAGAgent:
    """
    A RAG agent that executes a query against the multimodal RAG engine.
    """

    def __init__(self, rag_engine: MultimodalChromaRAGQueryEngine):
        """
        Initializes the agent with a RAG query engine.

        Args:
            rag_engine: An instance of the RAG query engine.
        """
        self.rag_engine = rag_engine

    def process(self, query: str, **kwargs) -> Dict:
        """
        Processes a query using the RAG engine.

        Args:
            query: The query to be executed.
            **kwargs: Additional parameters for the RAG query engine,
                      such as n_results, experience_years, etc.

        Returns:
            A dictionary containing the answer and sources from the RAG engine.
        """
        logger.info(f"RAG agent processing query: '{query}' with args: {kwargs}")
        try:
            result = self.rag_engine.query(query=query, **kwargs)
            return result
        except Exception as e:
            logger.error(f"Error querying RAG engine: {e}", exc_info=True)
            return {
                "answer": "I encountered an error while searching the documents.",
                "sources": [],
                "relevant_images": [],
            }
