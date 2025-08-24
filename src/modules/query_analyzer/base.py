"""Base abstractions for query analysis components."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional

from ..storage_manager.base import SearchResult

if TYPE_CHECKING:
    from .models import RelevanceResult


@dataclass
class QueryIntent:
    """Structured representation of query intent."""

    query_type: str
    semantic_intent: str
    final_query: Optional[str] = None
    entities: List[str] = field(default_factory=list)
    time_filter: Optional[str] = None
    expanded_queries: List[str] = field(default_factory=list)
    decomposed_questions: List[str] = field(default_factory=list)
    step_back_questions: List[str] = field(default_factory=list)
    clarifying_questions: List[str] = field(default_factory=list)
    clarified_query: Optional[str] = None  # Rephrased query with additional context
    relevance_info: Optional["RelevanceResult"] = None  # Relevance check result


@dataclass
class AnalysisResult:
    """Result of query analysis including retrieval information."""

    query: str
    intent: QueryIntent
    retrieval_queries: List[str]
    hypothetical_document: Optional[str] = None


class BaseQueryAnalyzer(ABC):
    """Abstract base class for query analyzers."""

    @abstractmethod
    def analyze(self, query: str) -> QueryIntent:
        """Analyze a query and return structured intent."""
        pass

    def get_retrieval_queries(self, query: str) -> List[str]:
        """
        Get optimized queries for retrieval based on analysis.
        This method can be optionally implemented by subclasses.
        By default, it returns the original query.
        """
        return [query]

    def analyze_with_context(
        self, query: str, context: Optional[str] = None
    ) -> QueryIntent:
        """
        Analyze a query with optional conversation context.

        Args:
            query: The query to analyze
            context: Optional conversation context

        Returns:
            QueryIntent with analysis results
        """
        # Default implementation ignores context
        return self.analyze(query)

    def check_relevance(self, query: str) -> Optional["RelevanceResult"]:
        """
        Check if query is contextually relevant to the domain.

        Args:
            query: The query to check

        Returns:
            RelevanceResult if relevance checking is enabled, None otherwise
        """
        # Default implementation returns None (no relevance checking)
        return None


class BaseHyDEGenerator(ABC):
    """Abstract base class for HyDE (Hypothetical Document Embeddings) generators."""

    @abstractmethod
    def generate(self, query: str) -> str:
        """Generate a hypothetical document that would answer the query."""
        pass


class BaseEnhancedRetriever(ABC):
    """Abstract base class for enhanced retrievers using query analysis."""

    @abstractmethod
    def retrieve(
        self,
        query: str,
        limit: int = 5,
        use_hyde: bool = False,
        use_query_expansion: bool = True,
        **kwargs,
    ) -> List[SearchResult]:
        """
        Retrieve documents using query analysis.

        Args:
            query: The search query
            limit: Maximum number of results to return
            use_hyde: Whether to use HyDE for retrieval
            use_query_expansion: Whether to expand the query
            **kwargs: Additional arguments for retrieval

        Returns:
            List of search results
        """
        pass

    @abstractmethod
    def retrieve_with_analysis(
        self, query: str, limit: int = 5, **kwargs
    ) -> Dict[str, any]:
        """
        Retrieve documents and return analysis details.

        Args:
            query: The search query
            limit: Maximum number of results to return
            **kwargs: Additional arguments for retrieval

        Returns:
            Dictionary containing query analysis and search results
        """
        pass
