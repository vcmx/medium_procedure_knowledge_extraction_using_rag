"""Data models and configurations for query analysis."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class RelevanceResult:
    """Result of contextual relevance checking."""
    
    is_relevant: bool
    confidence: float  # 0.0 to 1.0
    stage: str  # "pre-filter" or "semantic"
    explanation: str
    domain_matches: List[str]  # Matched domain terms/patterns
    suggestions: Optional[List[str]] = None  # Alternative queries if irrelevant


@dataclass
class RelevanceConfig:
    """Configuration for contextual relevance checking."""
    
    # Pre-filter settings
    min_domain_terms: int = 1
    domain_vocabulary_path: str = "./config/domain_vocabulary.json"
    domain_patterns_path: str = "./config/domain_patterns.json"
    
    # Confidence thresholds
    high_confidence_threshold: float = 0.8
    low_confidence_threshold: float = 0.3
    
    # Semantic validation settings
    enable_semantic_validation: bool = True
    semantic_threshold: float = 0.5
    representative_embeddings_path: str = "./config/representative_embeddings.pkl"
    
    # Response behavior
    rejection_mode: str = "soft"  # "hard", "soft", "score"
    
    # Evaluation mode
    evaluation_mode: str = "two_stage"  # "two_stage" or "task_action_target"
    
    # Task-action-target evaluation settings
    task_action_prompt_path: str = "./config/technical_tasks_evaluate.txt"
    task_action_model_name: str = "llama3.2"  # LLM model for task-action-target mode
    task_action_temperature: float = 0.0  # Temperature for deterministic output
    
    # Feature flags
    enabled: bool = True


@dataclass
class RetrievalConfig:
    """Configuration for retrieval operations."""
    
    limit: int = 5
    use_hyde: bool = False
    use_query_expansion: bool = True
    rerank: bool = False
    filter_metadata: Optional[Dict[str, any]] = None
    
    
@dataclass 
class QueryAnalyzerConfig:
    """Configuration for query analyzer."""
    
    model_name: str = "llama3.2"
    temperature: float = 0.0
    provider: str = "ollama"  # "ollama" or "openrouter"
    
    # OpenRouter specific configs
    openrouter_api_key: Optional[str] = None
    openrouter_model: Optional[str] = None
    
    # Feature flags
    enable_query_expansion: bool = True  # Generate alternative query phrasings
    enable_decomposition: bool = True    # Break down complex queries into sub-questions
    enable_step_back: bool = True        # Generate more generic questions
    enable_clarification: bool = True    # Generate clarifying questions
    enable_entity_extraction: bool = True # Extract entities from queries
    enable_time_filter: bool = True      # Detect time-based constraints
    
    # Feature-specific settings
    max_expanded_queries: int = 5        # Maximum number of expanded queries
    max_decomposed_questions: int = 10   # Maximum number of sub-questions
    max_step_back_questions: int = 4     # Maximum number of step-back questions
    max_clarifying_questions: int = 4    # Maximum number of clarifying questions
    
    
@dataclass
class HyDEConfig:
    """Configuration for HyDE generator."""
    
    model_name: str = "llama3.2" 
    temperature: float = 0.7
    provider: str = "ollama"
    max_length: int = 200
    
    

@dataclass
class QueryType:
    """Constants for query types."""
    
    FACTUAL: str = "factual"
    COMPARISON: str = "comparison"
    AGGREGATION: str = "aggregation"
    EXPLANATION: str = "explanation"
    
    @classmethod
    def all_types(cls) -> List[str]:
        """Get all query types."""
        return [cls.FACTUAL, cls.COMPARISON, cls.AGGREGATION, cls.EXPLANATION]
    
    @classmethod
    def is_valid(cls, query_type: str) -> bool:
        """Check if a query type is valid."""
        return query_type in cls.all_types()