"""Simple demo of just the query analyzer without retrieval."""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.modules.query_analyzer.ollama_analyzer import OllamaQueryAnalyzer
from src.modules.query_analyzer.models import QueryAnalyzerConfig, RelevanceConfig
from src.modules.query_analyzer.relevance_checker import ContextualRelevanceChecker
from src.modules.embeddings.factory import EmbedderFactory

def demo_query_analysis():
    """Demo just the query analysis features."""
    print("🔬 Query Analyzer Demo")
    print("=" * 50)
    
    # Create analyzer
    config = QueryAnalyzerConfig(
        model_name="llama3.2",
        temperature=0.0,
        enable_query_expansion=True,
        enable_decomposition=True,
        enable_step_back=True,
        enable_clarification=True,
        max_expanded_queries=5,
        max_decomposed_questions=8,
        max_clarifying_questions=3
    )
    
    # Add relevance checking
    relevance_config = RelevanceConfig(
        enabled=True,
        rejection_mode="soft"
    )
    
    analyzer = OllamaQueryAnalyzer(config, relevance_config)
    
    # Set up relevance checker with embedder
    embedder = EmbedderFactory.create("clip")
    relevance_checker = ContextualRelevanceChecker(relevance_config, embedder)
    analyzer.set_relevance_checker(relevance_checker)
    
    # Test queries - mix of relevant and potentially irrelevant
    test_queries = [
        "How does a jet engine compressor work?",
        "Compare turbofan and turbojet engines",
        "What are the best practices for database optimization?",
        "Debug memory leak in Python application",
        "What's the weather forecast?",  # Irrelevant query
        "Tell me a joke"  # Irrelevant query
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n📝 Query {i}/{len(test_queries)}: '{query}'")
        print("─" * 60)
        
        try:
            intent = analyzer.analyze(query)
            
            # Show relevance information if available
            if intent.relevance_info:
                relevance = intent.relevance_info
                status = "✅ Relevant" if relevance.is_relevant else "❌ Out of Context"
                print(f"📊 Relevance: {status} (confidence: {relevance.confidence:.2%})")
                if not relevance.is_relevant and relevance.suggestions:
                    print(f"💡 Suggestions:")
                    for suggestion in relevance.suggestions:
                        print(f"   - {suggestion}")
            
            print(f"🏷️  Query Type: {intent.query_type}")
            print(f"🔍 Entities: {intent.entities}")
            print(f"💭 Semantic Intent: {intent.semantic_intent}")
            print(f"⏰ Time Filter: {intent.time_filter}")
            
            if intent.expanded_queries:
                print(f"\n🔄 Expanded Queries ({len(intent.expanded_queries)}):")
                for j, eq in enumerate(intent.expanded_queries, 1):
                    print(f"   {j}. {eq}")
            
            if intent.decomposed_questions:
                print(f"\n🧩 Decomposed Questions ({len(intent.decomposed_questions)}):")
                for j, dq in enumerate(intent.decomposed_questions, 1):
                    print(f"   {j}. {dq}")
            
            if intent.step_back_questions:
                print(f"\n🔙 Step-back Questions ({len(intent.step_back_questions)}):")
                for j, sq in enumerate(intent.step_back_questions, 1):
                    print(f"   {j}. {sq}")
            
            if intent.clarifying_questions:
                print(f"\n❓ Clarifying Questions ({len(intent.clarifying_questions)}):")
                for j, cq in enumerate(intent.clarifying_questions, 1):
                    print(f"   {j}. {cq}")
            
        except Exception as e:
            print(f"❌ Error analyzing query: {e}")
            import traceback
            traceback.print_exc()
        
        # Auto-continue for demo
        if i < len(test_queries):
            print("\n" + "="*60)

def demo_relevance_checking():
    """Demo relevance checking functionality."""
    print("\n\n🎯 Relevance Checking Demo")
    print("=" * 50)
    
    # Create analyzer with relevance checking
    config = QueryAnalyzerConfig(
        model_name="llama3.2",
        enable_query_expansion=False,  # Disable for cleaner output
        enable_decomposition=False,
        enable_step_back=False,
        enable_clarification=False
    )
    
    relevance_config = RelevanceConfig(
        enabled=True,
        rejection_mode="soft",
        high_confidence_threshold=0.8,
        low_confidence_threshold=0.3
    )
    
    analyzer = OllamaQueryAnalyzer(config, relevance_config)
    embedder = EmbedderFactory.create("clip")
    relevance_checker = ContextualRelevanceChecker(relevance_config, embedder)
    analyzer.set_relevance_checker(relevance_checker)
    
    # Test various queries
    relevance_test_queries = [
        ("How to replace brake pads?", "Technical automotive"),
        ("What is the torque spec for head bolts?", "Technical specification"),
        ("What's your favorite movie?", "Off-topic"),
        ("Recipe for chocolate cake", "Off-topic"),
        ("Diagnose P0301 error code", "Technical diagnostic"),
        ("How does this work?", "Vague/ambiguous")
    ]
    
    print("\nTesting relevance detection:\n")
    
    for query, category in relevance_test_queries:
        print(f"Query: \"{query}\" ({category})")
        intent = analyzer.analyze(query)
        
        if intent.relevance_info:
            relevance = intent.relevance_info
            status = "✅ RELEVANT" if relevance.is_relevant else "❌ IRRELEVANT"
            print(f"  {status} - Confidence: {relevance.confidence:.2%}")
            print(f"  Explanation: {relevance.explanation}")
        print()

def demo_feature_configuration():
    """Demo different feature configurations."""
    print("\n\n🔧 Feature Configuration Demo")
    print("=" * 50)
    
    # Minimal configuration
    print("\n🚀 Minimal Configuration (fast):")
    minimal_config = QueryAnalyzerConfig(
        model_name="llama3.2",
        enable_query_expansion=False,
        enable_decomposition=False,
        enable_step_back=False,
        enable_clarification=False
    )
    
    minimal_analyzer = OllamaQueryAnalyzer(minimal_config)
    query = "How to optimize database performance?"
    
    intent = minimal_analyzer.analyze(query)
    print(f"Query Type: {intent.query_type}")
    print(f"Semantic Intent: {intent.semantic_intent}")
    print(f"Features: Basic analysis only")
    
    # Full configuration
    print("\n🎯 Full Configuration (comprehensive):")
    full_config = QueryAnalyzerConfig(
        model_name="llama3.2",
        enable_query_expansion=True,
        enable_decomposition=True,
        enable_step_back=True,
        enable_clarification=True,
        max_expanded_queries=3,
        max_decomposed_questions=5
    )
    
    full_analyzer = OllamaQueryAnalyzer(full_config)
    intent = full_analyzer.analyze(query)
    
    print(f"Query Type: {intent.query_type}")
    print(f"Semantic Intent: {intent.semantic_intent}")
    print(f"Expanded Queries: {len(intent.expanded_queries)}")
    print(f"Decomposed Questions: {len(intent.decomposed_questions)}")
    print(f"Step-back Questions: {len(intent.step_back_questions)}")
    print(f"Clarifying Questions: {len(intent.clarifying_questions)}")

if __name__ == "__main__":
    try:
        demo_query_analysis()
        demo_relevance_checking()
        demo_feature_configuration()
        print("\n✅ Demo complete!")
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()