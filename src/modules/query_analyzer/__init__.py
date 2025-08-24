"""Query Analysis module for enhanced retrieval."""

from .base import (
    BaseQueryAnalyzer,
    BaseHyDEGenerator,
    BaseEnhancedRetriever,
    QueryIntent,
    AnalysisResult
)

from .models import (
    RetrievalConfig,
    QueryAnalyzerConfig,
    HyDEConfig,
    QueryType
)

from .factory import (
    QueryAnalyzerFactory,
    HyDEGeneratorFactory,
    EnhancedRetrieverFactory
)

from .enhanced_retriever import EnhancedRetriever
from .conversational_workflow import ConversationalWorkflow

# Optional imports (only available if dependencies are installed)
try:
    from .ollama_analyzer import OllamaQueryAnalyzer
    from .hyde_generator import OllamaHyDEGenerator
    _OLLAMA_AVAILABLE = True
except ImportError:
    _OLLAMA_AVAILABLE = False

__all__ = [
    # Base classes
    "BaseQueryAnalyzer",
    "BaseHyDEGenerator", 
    "BaseEnhancedRetriever",
    "QueryIntent",
    "AnalysisResult",
    
    # Models
    "RetrievalConfig",
    "QueryAnalyzerConfig",
    "HyDEConfig",
    "QueryType",
    
    # Factories
    "QueryAnalyzerFactory",
    "HyDEGeneratorFactory",
    "EnhancedRetrieverFactory",
    
    # Implementations
    "EnhancedRetriever",
    "ConversationalWorkflow",
]

# Add optional implementations to exports if available
if _OLLAMA_AVAILABLE:
    __all__.extend([
        "OllamaQueryAnalyzer",
        "OllamaHyDEGenerator",
    ])