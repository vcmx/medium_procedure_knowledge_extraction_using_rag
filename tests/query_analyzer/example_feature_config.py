"""Example demonstrating feature configuration in OllamaQueryAnalyzer."""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.modules.query_analyzer.ollama_analyzer import OllamaQueryAnalyzer
from src.modules.query_analyzer.models import QueryAnalyzerConfig


def demo_full_features():
    """Demonstrate analyzer with all features enabled (default)."""
    print("=== Full Features Demo ===\n")
    
    # Default config has all features enabled
    analyzer = OllamaQueryAnalyzer()
    
    query = "How does machine learning affect software development practices in 2024?"
    intent = analyzer.analyze(query)
    
    print(f"Query: {query}\n")
    print(f"✅ Query Type: {intent.query_type}")
    print(f"✅ Entities: {intent.entities}")
    print(f"✅ Time Filter: {intent.time_filter}")
    print(f"✅ Semantic Intent: {intent.semantic_intent}")
    print(f"✅ Expanded Queries: {len(intent.expanded_queries)} generated")
    print(f"✅ Decomposed Questions: {len(intent.decomposed_questions or [])} generated")
    print(f"✅ Step-back Questions: {len(intent.step_back_questions or [])} generated")
    print(f"✅ Clarifying Questions: {len(intent.clarifying_questions or [])} generated")


def demo_minimal_features():
    """Demonstrate analyzer with minimal features for performance."""
    print("\n\n=== Minimal Features Demo ===\n")
    
    config = QueryAnalyzerConfig(
        model_name="llama3.2",
        enable_query_expansion=False,
        enable_decomposition=False,
        enable_step_back=False,
        enable_clarification=False,
        enable_entity_extraction=False,
        enable_time_filter=False
    )
    
    analyzer = OllamaQueryAnalyzer(config)
    
    query = "How does machine learning affect software development practices in 2024?"
    intent = analyzer.analyze(query)
    
    print(f"Query: {query}\n")
    print(f"✅ Query Type: {intent.query_type}")
    print(f"❌ Entities: {intent.entities} (disabled)")
    print(f"❌ Time Filter: {intent.time_filter} (disabled)")
    print(f"✅ Semantic Intent: {intent.semantic_intent}")
    print(f"❌ Expanded Queries: {len(intent.expanded_queries)} (disabled)")
    print(f"❌ Decomposed Questions: {len(intent.decomposed_questions or [])} (disabled)")
    print(f"❌ Step-back Questions: {len(intent.step_back_questions or [])} (disabled)")
    print(f"❌ Clarifying Questions: {len(intent.clarifying_questions or [])} (disabled)")


def demo_custom_features():
    """Demonstrate analyzer with custom feature selection."""
    print("\n\n=== Custom Features Demo ===\n")
    
    # Enable only specific features
    config = QueryAnalyzerConfig(
        model_name="llama3.2",
        
        # Enable only query expansion and clarification
        enable_query_expansion=True,
        enable_decomposition=False,
        enable_step_back=False,
        enable_clarification=True,
        enable_entity_extraction=True,
        enable_time_filter=False,
        
        # Custom limits
        max_expanded_queries=3,
        max_clarifying_questions=2
    )
    
    analyzer = OllamaQueryAnalyzer(config)
    
    query = "How to fix performance issues?"
    intent = analyzer.analyze(query)
    
    print(f"Query: {query}\n")
    print(f"✅ Query Type: {intent.query_type}")
    print(f"✅ Entities: {intent.entities}")
    print(f"❌ Time Filter: {intent.time_filter} (disabled)")
    print(f"✅ Semantic Intent: {intent.semantic_intent}")
    print(f"✅ Expanded Queries (max 3):")
    for i, eq in enumerate(intent.expanded_queries, 1):
        print(f"   {i}. {eq}")
    print(f"❌ Decomposed Questions: Disabled")
    print(f"❌ Step-back Questions: Disabled")
    print(f"✅ Clarifying Questions (max 2):")
    for i, cq in enumerate(intent.clarifying_questions or [], 1):
        print(f"   {i}. {cq}")


def demo_performance_comparison():
    """Compare performance with different feature sets."""
    print("\n\n=== Performance Comparison Demo ===\n")
    
    import time
    
    query = "What are the best practices for implementing microservices architecture?"
    
    # Full features
    full_config = QueryAnalyzerConfig()
    full_analyzer = OllamaQueryAnalyzer(full_config)
    
    start = time.time()
    full_intent = full_analyzer.analyze(query)
    full_time = time.time() - start
    
    # Minimal features
    min_config = QueryAnalyzerConfig(
        enable_query_expansion=False,
        enable_decomposition=False,
        enable_step_back=False,
        enable_clarification=False,
        enable_entity_extraction=False,
        enable_time_filter=False
    )
    min_analyzer = OllamaQueryAnalyzer(min_config)
    
    start = time.time()
    min_intent = min_analyzer.analyze(query)
    min_time = time.time() - start
    
    print(f"Query: {query}\n")
    print(f"Full Features Analysis:")
    print(f"  - Time: {full_time:.2f}s")
    print(f"  - Features extracted: {sum([
        1,  # query_type
        1,  # semantic_intent
        len(full_intent.entities) > 0,
        full_intent.time_filter is not None,
        len(full_intent.expanded_queries) > 0,
        len(full_intent.decomposed_questions or []) > 0,
        len(full_intent.step_back_questions or []) > 0,
        len(full_intent.clarifying_questions or []) > 0
    ])}")
    
    print(f"\nMinimal Features Analysis:")
    print(f"  - Time: {min_time:.2f}s")
    print(f"  - Features extracted: 2 (query_type, semantic_intent)")
    print(f"  - Speed improvement: {(full_time - min_time) / full_time * 100:.1f}%")


def demo_clarification_with_config():
    """Demonstrate clarification with custom configuration."""
    print("\n\n=== Clarification with Custom Config Demo ===\n")
    
    config = QueryAnalyzerConfig(
        enable_clarification=True,
        max_clarifying_questions=2,  # Limit to 2 questions
        
        # Disable other features for focused demo
        enable_decomposition=False,
        enable_step_back=False
    )
    
    analyzer = OllamaQueryAnalyzer(config)
    
    # Mock response collector
    def auto_responder(question: str) -> str:
        if "system" in question.lower():
            return "E-commerce website"
        elif "specific" in question.lower():
            return "Checkout page loading time"
        return ""
    
    query = "How to improve performance?"
    
    # Analyze with clarification
    intent = analyzer.analyze_with_clarification(
        query,
        response_collector=auto_responder,
        auto_clarify=True
    )
    
    print(f"Original Query: {query}")
    print(f"Clarifying Questions (max 2): {intent.clarifying_questions}")
    print(f"Clarified Query: {intent.clarified_query}")


if __name__ == "__main__":
    print("🔧 Query Analyzer Feature Configuration Demo\n")
    
    try:
        demo_full_features()
        demo_minimal_features()
        demo_custom_features()
        demo_performance_comparison()
        demo_clarification_with_config()
        
    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()