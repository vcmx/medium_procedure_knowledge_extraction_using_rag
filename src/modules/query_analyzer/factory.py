"""Factory for creating query analysis components."""

from typing import Dict, Optional, Type

from ..embeddings.base import BaseEmbedder
from ..storage_manager.base import BaseStorageManager
from .base import BaseEnhancedRetriever, BaseHyDEGenerator, BaseQueryAnalyzer
from .enhanced_retriever import EnhancedRetriever
from .hyde_generator import OllamaHyDEGenerator, OpenRouterHyDEGenerator
from .models import HyDEConfig, QueryAnalyzerConfig, RelevanceConfig
from .ollama_analyzer import OllamaQueryAnalyzer
from .openrouter_analyzer import OpenRouterQueryAnalyzer
from .relevance_checker import ContextualRelevanceChecker


class QueryAnalyzerFactory:
    """Factory for creating query analyzers."""

    _analyzers: Dict[str, Type[BaseQueryAnalyzer]] = {
        "ollama": OllamaQueryAnalyzer,
        "openrouter": OpenRouterQueryAnalyzer,
    }

    @classmethod
    def create(
        cls,
        implementation: str = "ollama",
        config: Optional[QueryAnalyzerConfig] = None,
        relevance_config: Optional[RelevanceConfig] = None,
        embedder: Optional[BaseEmbedder] = None,
        model_name: str = None,
        **kwargs,
    ) -> BaseQueryAnalyzer:
        """
        Create a query analyzer instance.

        Args:
            implementation: Name of the analyzer to use
            config: Configuration for the analyzer
            relevance_config: Configuration for relevance checking
            embedder: Embedder for semantic validation (required if relevance checking enabled)
            model_name: The name of the model to use, overriding config defaults.
            **kwargs: Additional arguments to pass to the analyzer constructor

        Returns:
            An instance of the specified query analyzer

        Raises:
            ValueError: If the specified implementation is not supported
        """
        analyzer_class = cls._analyzers.get(implementation.lower())
        if analyzer_class is None:
            raise ValueError(
                f"Unknown query analyzer implementation: {implementation}. "
                f"Supported implementations: {list(cls._analyzers.keys())}"
            )

        # Use provided config or create default
        if config is None:
            config = QueryAnalyzerConfig(provider=implementation, **kwargs)

        # Override model name if provided
        if model_name:
            config.model_name = model_name

        # Create analyzer instance
        analyzer = analyzer_class(config=config)

        # For implementations that still support it, set up relevance checking
        if (
            implementation != "openrouter"
            and relevance_config
            and relevance_config.enabled
        ):
            relevance_checker = ContextualRelevanceChecker(relevance_config, embedder)
            if hasattr(analyzer, "set_relevance_checker"):
                analyzer.set_relevance_checker(relevance_checker)

        return analyzer

    @classmethod
    def register_analyzer(
        cls, name: str, analyzer_class: Type[BaseQueryAnalyzer]
    ) -> None:
        """
        Register a new query analyzer implementation.

        Args:
            name: Name to register the analyzer under
            analyzer_class: The analyzer class to register
        """
        if not issubclass(analyzer_class, BaseQueryAnalyzer):
            raise ValueError("Analyzer class must inherit from BaseQueryAnalyzer")
        cls._analyzers[name.lower()] = analyzer_class


class HyDEGeneratorFactory:
    """Factory for creating HyDE generators."""

    _generators: Dict[str, Type[BaseHyDEGenerator]] = {
        "ollama": OllamaHyDEGenerator,
        "openrouter": OpenRouterHyDEGenerator,
    }

    @classmethod
    def create(
        cls,
        implementation: str = "ollama",
        config: Optional[HyDEConfig] = None,
        **kwargs,
    ) -> BaseHyDEGenerator:
        """
        Create a HyDE generator instance.

        Args:
            implementation: Name of the generator to use
            config: Configuration for the generator
            **kwargs: Additional arguments to pass to the generator constructor

        Returns:
            An instance of the specified HyDE generator

        Raises:
            ValueError: If the specified implementation is not supported
        """
        generator_class = cls._generators.get(implementation.lower())
        if generator_class is None:
            raise ValueError(
                f"Unknown HyDE generator implementation: {implementation}. "
                f"Supported implementations: {list(cls._generators.keys())}"
            )

        # Use provided config or create default
        if config is None:
            config = HyDEConfig(provider=implementation, **kwargs)

        return generator_class(config=config)

    @classmethod
    def register_generator(
        cls, name: str, generator_class: Type[BaseHyDEGenerator]
    ) -> None:
        """
        Register a new HyDE generator implementation.

        Args:
            name: Name to register the generator under
            generator_class: The generator class to register
        """
        if not issubclass(generator_class, BaseHyDEGenerator):
            raise ValueError("Generator class must inherit from BaseHyDEGenerator")
        cls._generators[name.lower()] = generator_class


class EnhancedRetrieverFactory:
    """Factory for creating enhanced retrievers."""

    @classmethod
    def create(
        cls,
        storage_manager: BaseStorageManager,
        embedder: BaseEmbedder,
        query_analyzer: Optional[BaseQueryAnalyzer] = None,
        hyde_generator: Optional[BaseHyDEGenerator] = None,
        analyzer_implementation: str = "ollama",
        hyde_implementation: Optional[str] = None,
        **kwargs,
    ) -> BaseEnhancedRetriever:
        """
        Create an enhanced retriever instance.

        Args:
            storage_manager: Storage manager for vector operations
            embedder: Embedder for generating query embeddings
            query_analyzer: Optional pre-configured query analyzer
            hyde_generator: Optional pre-configured HyDE generator
            analyzer_implementation: Implementation to use if creating analyzer
            hyde_implementation: Implementation to use if creating HyDE generator
            **kwargs: Additional arguments

        Returns:
            An instance of the enhanced retriever
        """
        # Create query analyzer if not provided
        if query_analyzer is None:
            query_analyzer = QueryAnalyzerFactory.create(
                implementation=analyzer_implementation, **kwargs
            )

        # Create HyDE generator if requested
        if hyde_implementation is not None and hyde_generator is None:
            hyde_generator = HyDEGeneratorFactory.create(
                implementation=hyde_implementation, **kwargs
            )

        # Extract relevance config if provided in kwargs
        relevance_config = kwargs.pop("relevance_config", None)

        return EnhancedRetriever(
            storage_manager=storage_manager,
            embedder=embedder,
            query_analyzer=query_analyzer,
            hyde_generator=hyde_generator,
            relevance_config=relevance_config,
        )
