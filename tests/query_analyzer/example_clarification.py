"""Example usage of the clarifying questions feature in OllamaQueryAnalyzer."""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.modules.query_analyzer.ollama_analyzer import OllamaQueryAnalyzer
from src.modules.query_analyzer.models import QueryAnalyzerConfig


def demo_basic_clarification():
    """Demonstrate basic clarification with standard input."""
    print("=== Basic Clarification Demo ===\n")
    
    # Initialize analyzer
    analyzer = OllamaQueryAnalyzer(QueryAnalyzerConfig(model_name="llama3.2"))
    
    # Example ambiguous queries
    queries = [
        "How to fix the error?",
        "Why is it slow?",
        "What's the best approach?",
        "How do I optimize this?"
    ]
    
    for query in queries:
        print(f"\n{'='*60}")
        print(f"Original Query: {query}")
        print('='*60)
        
        # Get clarification interactively
        result = analyzer.clarify_interactively(query)
        
        print(f"\n📝 Summary:")
        print(f"  - Original: {result['original_query']}")
        print(f"  - Clarified: {result['clarified_query']}")
        print(f"  - Questions asked: {len(result['clarifying_questions'])}")
        

def demo_programmatic_clarification():
    """Demonstrate clarification with programmatic responses."""
    print("\n\n=== Programmatic Clarification Demo ===\n")
    
    # Initialize analyzer
    analyzer = OllamaQueryAnalyzer(QueryAnalyzerConfig(model_name="llama3.2"))
    
    # Define a custom response collector
    def mock_response_collector(question: str) -> str:
        """Mock responses for demonstration."""
        responses = {
            "error": "TypeError: cannot concatenate str and int",
            "language": "Python 3.9",
            "system": "Django web application",
            "application": "Our e-commerce checkout process",
            "trying": "Process user payment",
            "performance": "Page load takes 15 seconds instead of 2 seconds",
            "approach": "Building a recommendation engine",
            "optimize": "Database queries for user analytics"
        }
        
        # Match keywords in question to provide relevant response
        question_lower = question.lower()
        for keyword, response in responses.items():
            if keyword in question_lower:
                print(f"   [Auto-response]: {response}")
                return response
        
        return "Not specified"
    
    # Test with programmatic responses
    query = "How to fix the error in my application?"
    
    print(f"Query: {query}\n")
    result = analyzer.clarify_interactively(query, response_collector=mock_response_collector)
    
    print(f"\n📝 Clarification Result:")
    print(f"  Original: {result['original_query']}")
    print(f"  Clarified: {result['clarified_query']}")
    

def demo_analyze_with_clarification():
    """Demonstrate the full analyze_with_clarification workflow."""
    print("\n\n=== Analyze with Clarification Demo ===\n")
    
    # Initialize analyzer
    analyzer = OllamaQueryAnalyzer(QueryAnalyzerConfig(model_name="llama3.2"))
    
    # Mock response collector for automation
    def auto_responder(question: str) -> str:
        if "error" in question.lower():
            return "Connection timeout error"
        elif "database" in question.lower():
            return "PostgreSQL 14"
        elif "frequency" in question.lower():
            return "Every morning around 9 AM"
        elif "changes" in question.lower():
            return "Upgraded to new server last week"
        return ""
    
    # Analyze with automatic clarification
    query = "Why is the database connection failing?"
    
    print(f"Analyzing: {query}\n")
    intent = analyzer.analyze_with_clarification(
        query, 
        response_collector=auto_responder,
        auto_clarify=True
    )
    
    print(f"\n📊 Full Analysis Results:")
    print(f"  Query Type: {intent.query_type}")
    print(f"  Entities: {intent.entities}")
    print(f"  Semantic Intent: {intent.semantic_intent}")
    print(f"  Clarified Query: {intent.clarified_query or 'N/A'}")
    print(f"\n  Expanded Queries ({len(intent.expanded_queries)}):")
    for i, eq in enumerate(intent.expanded_queries[:3], 1):
        print(f"    {i}. {eq}")
    

def demo_no_clarification_needed():
    """Demonstrate behavior when clarification is not needed."""
    print("\n\n=== No Clarification Needed Demo ===\n")
    
    # Initialize analyzer
    analyzer = OllamaQueryAnalyzer(QueryAnalyzerConfig(model_name="llama3.2"))
    
    # Very specific query that shouldn't need clarification
    query = "How to implement quicksort algorithm in Python 3.9 with type hints for a list of integers?"
    
    print(f"Query: {query}\n")
    result = analyzer.clarify_interactively(query)
    
    if not result['clarifying_questions']:
        print("✅ Query is specific enough - no clarification needed!")
    else:
        print(f"❓ {len(result['clarifying_questions'])} clarifying questions generated")


if __name__ == "__main__":
    print("🚀 Ollama Query Analyzer - Clarification Feature Demo\n")
    
    # Run demos
    try:
        # Comment out interactive demo if running in non-interactive environment
        # demo_basic_clarification()
        
        demo_programmatic_clarification()
        demo_analyze_with_clarification()
        demo_no_clarification_needed()
        
    except KeyboardInterrupt:
        print("\n\n❌ Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error during demo: {e}")