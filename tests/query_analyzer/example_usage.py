"""Example usage of the query analyzer module with existing components."""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.modules.embeddings.factory import EmbedderFactory
from src.modules.storage_manager.factory import StorageManagerFactory
from src.modules.query_analyzer.factory import (
    QueryAnalyzerFactory,
    HyDEGeneratorFactory,
    EnhancedRetrieverFactory
)
from src.modules.query_analyzer.models import RetrievalConfig


def example_basic_usage():
    """Basic usage example with existing components."""
    print("=== Basic Query Analysis Example ===\n")
    
    # Create existing components
    embedder = EmbedderFactory.create(implementation="clip")
    storage_manager = StorageManagerFactory.create(
        implementation="chroma",
        collection_name="query_analyzer_demo"  # Use different collection name
    )
    
    # Create query analyzer (Ollama-based)
    query_analyzer = QueryAnalyzerFactory.create(
        implementation="ollama",
        model_name="llama3.2",
        temperature=0.0
    )
    
    # Create HyDE generator (optional)
    hyde_generator = HyDEGeneratorFactory.create(
        implementation="ollama",
        model_name="llama3.2",
        temperature=0.7
    )
    
    # Create enhanced retriever
    retriever = EnhancedRetrieverFactory.create(
        storage_manager=storage_manager,
        embedder=embedder,
        query_analyzer=query_analyzer,
        hyde_generator=hyde_generator
    )
    
    # Perform enhanced retrieval
    query = "How does the compressor section of a jet engine work?"
    results = retriever.retrieve(
        query=query,
        limit=5,
        use_hyde=True,
        use_query_expansion=True
    )
    
    print(f"Found {len(results)} results:")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. Score: {result.score:.3f}")
        print(f"   Title: {result.metadata.title}")
        print(f"   Page: {result.metadata.page_number}")
        print(f"   Content: {result.content[:150]}...")


def example_with_config():
    """Example using configuration objects."""
    print("\n\n=== Configuration-based Example ===\n")
    
    # Create components
    embedder = EmbedderFactory.create(implementation="siglip")
    storage_manager = StorageManagerFactory.create(
        implementation="chroma",
        collection_name="query_analyzer_config_demo"  # Use different collection name
    )
    
    # Create enhanced retriever with default Ollama components
    retriever = EnhancedRetrieverFactory.create(
        storage_manager=storage_manager,
        embedder=embedder,
        analyzer_implementation="ollama",
        hyde_implementation="ollama"
    )
    
    # Use retrieval config
    config = RetrievalConfig(
        limit=10,
        use_hyde=True,
        use_query_expansion=True,
        filter_metadata={"document_type": "manual"}
    )
    
    query = "Compare turbofan and turbojet engines"
    results = retriever.retrieve_with_config(query, config)
    
    print(f"Retrieved {len(results)} documents with config")


def example_analysis_only():
    """Example showing just query analysis without retrieval."""
    print("\n\n=== Query Analysis Only Example ===\n")
    
    # Create just the query analyzer
    analyzer = QueryAnalyzerFactory.create(
        implementation="ollama",
        model_name="llama3.2"
    )
    
    queries = [
        "What is the efficiency of modern jet engines?",
        "How do jet engines compare to rocket engines?",
        "List all the components of a turbofan engine",
        "Explain the thermodynamic cycle in jet propulsion"
    ]
    
    for query in queries:
        print(f"\nAnalyzing: '{query}'")
        intent = analyzer.analyze(query)
        print(f"  Type: {intent.query_type}")
        print(f"  Entities: {intent.entities}")
        print(f"  Semantic intent: {intent.semantic_intent}")
        
        # Get expanded queries
        expanded = analyzer.get_retrieval_queries(query)
        print(f"  Expanded to {len(expanded)} queries")


def example_with_analysis_details():
    """Example showing full analysis details."""
    print("\n\n=== Detailed Analysis Example ===\n")
    
    # Create components
    embedder = EmbedderFactory.create(implementation="clip")
    storage_manager = StorageManagerFactory.create(
        implementation="chroma",
        collection_name="query_analyzer_config_demo"  # Use different collection name
    )
    
    # Create enhanced retriever
    retriever = EnhancedRetrieverFactory.create(
        storage_manager=storage_manager,
        embedder=embedder,
        analyzer_implementation="ollama",
        hyde_implementation="ollama"
    )
    
    # Get detailed analysis results
    query = "What are the advantages of high-bypass turbofan engines?"
    analysis_result = retriever.retrieve_with_analysis(
        query=query,
        limit=5,
        use_hyde=True
    )
    
    print(f"Query: {analysis_result['query']}")
    print(f"\nIntent Analysis:")
    print(f"  Type: {analysis_result['intent']['query_type']}")
    print(f"  Entities: {analysis_result['intent']['entities']}")
    print(f"  Semantic intent: {analysis_result['intent']['semantic_intent']}")
    print(f"\nRetrieval Queries ({len(analysis_result['retrieval_queries'])}):")
    for i, q in enumerate(analysis_result['retrieval_queries'], 1):
        print(f"  {i}. {q}")
    if analysis_result['hypothetical_document']:
        print(f"\nHyDE Document: {analysis_result['hypothetical_document'][:200]}...")
    print(f"\nFound {len(analysis_result['results'])} results")


if __name__ == "__main__":
    # Check if Ollama dependencies are available
    try:
        import langchain_ollama
        print("Ollama dependencies are installed. Running examples...\n")
        
        # Run examples
        example_basic_usage()
        example_with_config()
        example_analysis_only()
        example_with_analysis_details()
        
    except ImportError:
        print("Ollama dependencies not installed.")
        print("To use query analysis with Ollama, install with:")
        print("  pip install langchain-ollama")
        print("\nThe module can still be used with other LLM providers.")