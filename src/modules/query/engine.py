import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from llama_index.core.llms import LLM

from src.modules.query_answering.rag_with_chroma import MultimodalChromaRAGQueryEngine

load_dotenv(override=True)


class QueryEngine:
    """A query engine for the multimodal RAG system."""

    def __init__(
        self,
        persist_directory: str = "./rag_storage",
        embedder_impl: str = "clip",
        embedder_kwargs: Optional[Dict[str, Any]] = None,
        llm: Optional[LLM] = None,
    ):
        """
        Initializes the query engine.

        Args:
            persist_directory (str): The directory where the RAG data is stored.
            embedder_impl (str): The embedder implementation to use.
            embedder_kwargs (Optional[Dict[str, Any]]): Kwargs for the embedder.
            llm (Optional[LLM]): An optional pre-configured llama-index LLM object.
        """
        if not os.path.isdir(persist_directory):
            raise FileNotFoundError(
                f"RAG storage directory not found at: {persist_directory}"
            )

        self.engine = MultimodalChromaRAGQueryEngine(
            persist_directory=persist_directory,
            embedder_impl=embedder_impl,
            embedding_kwargs=embedder_kwargs,
            llm=llm,
        )

    def update_llm(self, llm: LLM):
        """Updates the LLM in the query engine."""
        self.engine.update_llm(llm)

    def query(
        self,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
        experience_years: int = 0,
        use_mmr: bool = True,
        llm_model: Optional[str] = None,
        fusion_method: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Queries the RAG system.

        Args:
            query (str): The query string.
            n_results (int): The number of results to retrieve.
            filter_metadata (Optional[Dict[str, Any]]): Metadata to filter by.
            experience_years (int): The user's experience level in years.
            use_mmr (bool): Whether to use MMR for result diversity.
            llm_model (Optional[str]): The LLM model to use for the query.
            fusion_method (Optional[str]): The fusion method to use ('rrf' or 'interleave').

        Returns:
            Dict[str, Any]: A dictionary containing the answer, sources, and relevant images.
        """
        return self.engine.query(
            query=query,
            n_results=n_results,
            filter_metadata=filter_metadata,
            experience_years=experience_years,
            use_mmr=use_mmr,
            llm_model=llm_model,
            fusion_method=fusion_method,
        )
