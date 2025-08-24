"""Example usage of contextual relevance checking in query analysis."""

import os
from pathlib import Path

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.modules.query_analyzer.ollama_analyzer import OllamaQueryAnalyzer
from src.modules.query_analyzer.relevance_checker import ContextualRelevanceChecker
from src.modules.query_analyzer.models import QueryAnalyzerConfig, RelevanceConfig
from src.modules.embeddings.factory import EmbedderFactory


def demonstrate_relevance_checking():
    """Demonstrate contextual relevance checking with various queries."""
    
    print("=" * 80)
    print("Contextual Relevance Checking Demonstration")
    print("=" * 80)
    
    # Create configurations
    analyzer_config = QueryAnalyzerConfig(
        model_name="llama3.2",
        temperature=0.0,
        enable_query_expansion=True,
        enable_decomposition=False,  # Disable for cleaner output
        enable_step_back=False,
        enable_clarification=False
    )
    
    relevance_config = RelevanceConfig(
        enabled=True,
        min_domain_terms=1,
        high_confidence_threshold=0.8,
        low_confidence_threshold=0.3,
        enable_semantic_validation=True,
        rejection_mode="soft"  # Can be "hard", "soft", or "score"
    )
    
    # Create embedder for semantic validation
    embedder = EmbedderFactory.create("clip")
    
    # Create analyzer and relevance checker
    analyzer = OllamaQueryAnalyzer(analyzer_config, relevance_config)
    relevance_checker = ContextualRelevanceChecker(relevance_config, embedder)
    analyzer.set_relevance_checker(relevance_checker)
    
    # Test queries - mix of relevant and irrelevant
    test_queries = [
        # Clearly relevant technical queries
        "How do I replace the brake pads on a 2020 Honda Civic?",
        "What is the torque specification for cylinder head bolts?",
        "Diagnose P0301 misfire code on cylinder 1",
        
        # Edge cases - might be relevant
        "How does this system work?",
        "Fix the problem with my car",
        "Where can I find more information?",
        
        # Clearly irrelevant queries
        "What's the weather forecast for tomorrow?",
        "Tell me a joke about cars",
        "How do I post on Instagram?",
        "Recipe for chocolate cake"
    ]
    
    print("\nTesting various queries for relevance:\n")
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: \"{query}\"")
        print(f"{'='*60}")
        
        # Analyze the query
        intent = analyzer.analyze(query)
        
        # Display relevance information
        if intent.relevance_info:
            relevance = intent.relevance_info
            status = "✅ RELEVANT" if relevance.is_relevant else "❌ OUT OF CONTEXT"
            
            print(f"\nRelevance Check Results:")
            print(f"  Status: {status}")
            print(f"  Confidence: {relevance.confidence:.2%}")
            print(f"  Stage: {relevance.stage}")
            print(f"  Explanation: {relevance.explanation}")
            
            if relevance.domain_matches:
                print(f"  Domain matches: {', '.join(relevance.domain_matches[:5])}")
            
            if relevance.suggestions:
                print(f"\n  💡 Suggestions to improve your query:")
                for suggestion in relevance.suggestions:
                    print(f"     - {suggestion}")
        
        # Show analysis results only for relevant queries
        if intent.query_type != "out_of_context":
            print(f"\nQuery Analysis:")
            print(f"  Type: {intent.query_type}")
            print(f"  Intent: {intent.semantic_intent}")
            if intent.entities:
                print(f"  Entities: {intent.entities}")
            if intent.expanded_queries:
                print(f"  Expanded queries: {intent.expanded_queries[:3]}")


def demonstrate_rejection_modes():
    """Demonstrate different rejection modes for handling irrelevant queries."""
    
    print("\n" + "=" * 80)
    print("Rejection Mode Demonstration")
    print("=" * 80)
    
    irrelevant_query = "What's your favorite movie?"
    
    # Test different rejection modes
    rejection_modes = ["hard", "soft", "score"]
    
    for mode in rejection_modes:
        print(f"\n\n--- Testing with rejection_mode = '{mode}' ---")
        
        # Create config with specific rejection mode
        relevance_config = RelevanceConfig(
            enabled=True,
            rejection_mode=mode
        )
        
        # Create analyzer
        analyzer_config = QueryAnalyzerConfig(
            enable_query_expansion=False,
            enable_decomposition=False,
            enable_step_back=False,
            enable_clarification=False
        )
        
        analyzer = OllamaQueryAnalyzer(analyzer_config, relevance_config)
        relevance_checker = ContextualRelevanceChecker(relevance_config)
        analyzer.set_relevance_checker(relevance_checker)
        
        # Analyze query
        intent = analyzer.analyze(irrelevant_query)
        
        print(f"Query: \"{irrelevant_query}\"")
        
        if intent.relevance_info:
            print(f"Relevance: {'Relevant' if intent.relevance_info.is_relevant else 'Not relevant'}")
            print(f"Confidence: {intent.relevance_info.confidence:.2%}")
        
        print(f"Query type returned: {intent.query_type}")
        print(f"Semantic intent: {intent.semantic_intent}")
        
        if mode == "hard" and intent.query_type == "out_of_context":
            print("→ Query was rejected and minimal processing was done")
        elif mode == "soft":
            print("→ Query was processed despite being irrelevant")
        elif mode == "score":
            print("→ Query was processed and relevance score was provided")


def demonstrate_with_enhanced_retriever():
    """Demonstrate relevance checking in the retrieval pipeline."""
    
    print("\n" + "=" * 80)
    print("Enhanced Retriever with Relevance Checking")
    print("=" * 80)
    
    try:
        from src.modules.query_analyzer.enhanced_retriever import EnhancedRetriever
        from src.modules.storage_manager.factory import create_storage_manager
    except ImportError as e:
        print(f"Error importing modules: {e}")
        return
    
    # Create components
    storage_config = {
        "type": "chroma",
        "collection_name": "test_collection",
        "persist_directory": "./chroma_db"
    }
    
    embedder = EmbedderFactory.create("clip")
    storage_manager = create_storage_manager(storage_config)
    
    # Create analyzer with relevance checking
    relevance_config = RelevanceConfig(
        enabled=True,
        rejection_mode="soft"  # Show warnings but still search
    )
    
    analyzer_config = QueryAnalyzerConfig(
        model_name="llama3.2",
        temperature=0.0
    )
    analyzer = OllamaQueryAnalyzer(analyzer_config, relevance_config)
    relevance_checker = ContextualRelevanceChecker(relevance_config, embedder)
    analyzer.set_relevance_checker(relevance_checker)
    
    # Create retriever
    retriever = EnhancedRetriever(
        storage_manager=storage_manager,
        embedder=embedder,
        query_analyzer=analyzer,
        relevance_config=relevance_config
    )
    
    # Test queries
    test_queries = [
        "How to change engine oil?",  # Relevant
        "What's the best pizza recipe?"  # Irrelevant
    ]
    
    print("\nTesting retrieval with relevance checking:\n")
    
    for query in test_queries:
        print(f"\nQuery: \"{query}\"")
        print("-" * 40)
        
        # Retrieve with relevance checking
        results = retriever.retrieve(query, limit=3)
        
        if results:
            print(f"Found {len(results)} results")
        else:
            print("No results returned")


if __name__ == "__main__":
    # Check if Ollama is available
    try:
        from langchain_ollama import ChatOllama
        
        # Test if llama3.2 model is available
        test_llm = ChatOllama(model="llama3.2")
        test_response = test_llm.invoke("test")
        
        # Run demonstrations
        demonstrate_relevance_checking()
        demonstrate_rejection_modes()
        
        # Only run retriever demo if storage exists
        if Path("./chroma_db").exists():
            demonstrate_with_enhanced_retriever()
        else:
            print("\n⚠️  Skipping retriever demonstration (no chroma_db found)")
            
    except ImportError:
        print("Error: langchain-ollama not installed")
        print("Install with: pip install langchain-ollama")
    except Exception as e:
        print(f"Error: Could not connect to Ollama or model not available")
        print(f"Make sure Ollama is running and llama3.2 model is installed")
        print(f"Error details: {e}")
        
        # Show example output instead
        print("\n" + "="*60)
        print("Example Output (when Ollama is available):")
        print("="*60)
        print("""
Query: "How do I replace the brake pads?"
Relevance Check Results:
  Status: ✅ RELEVANT
  Confidence: 85.3%
  Stage: pre-filter
  Domain matches: brake, replace, pad

Query: "What's the weather forecast?"  
Relevance Check Results:
  Status: ❌ OUT OF CONTEXT
  Confidence: 12.1%
  Stage: pre-filter
  Suggestions:
    - Try including specific component names
    - Mention the specific system you're asking about
""")