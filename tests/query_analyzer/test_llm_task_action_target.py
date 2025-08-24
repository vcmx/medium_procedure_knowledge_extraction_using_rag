"""Test LLM-based task-action-target evaluation mode."""

from src.modules.query_analyzer.relevance_checker import ContextualRelevanceChecker
from src.modules.query_analyzer.models import RelevanceConfig


def test_llm_task_action_target():
    """Test LLM-based task-action-target evaluation."""
    
    # Try to import Ollama dependencies
    try:
        from langchain_ollama import ChatOllama
    except ImportError:
        print("Ollama dependencies not available. Skipping LLM test.")
        return
    
    # Create LLM provider
    llm = ChatOllama(
        model="llama3.2",
        temperature=0.0
    )
    
    # Configure for LLM-based task-action-target mode
    config = RelevanceConfig(
        evaluation_mode="task_action_target",
        enabled=True
    )
    
    # Create relevance checker with LLM provider
    checker = ContextualRelevanceChecker(config, llm_provider=llm)
    
    # Test queries
    test_queries = [
        "remove the oil filter",
        "replace brake pads",
        "the engine is making noise",
        "tighten the bolts",
        "what's the weather today",
        "cook dinner",
        "install new spark plugs"
    ]
    
    print("LLM-Based Task-Action-Target Evaluation")
    print("=" * 50)
    print()
    
    for query in test_queries:
        print(f"Query: \"{query}\"")
        
        try:
            result = checker.check_relevance(query)
            
            print(f"├─ Relevant: {'✓' if result.is_relevant else '✗'} (confidence: {result.confidence})")
            print(f"├─ Stage: {result.stage}")
            
            # Show what was found
            actions = [m.split(':')[1] for m in result.domain_matches if m.startswith('action:')]
            targets = [m.split(':')[1] for m in result.domain_matches if m.startswith('target:')]
            
            if actions:
                print(f"├─ Actions found: {', '.join(actions)}")
            if targets:
                print(f"├─ Targets found: {', '.join(targets)}")
            
            print(f"├─ Explanation: {result.explanation}")
            
            if result.suggestions:
                print(f"└─ Suggestions:")
                for suggestion in result.suggestions:
                    print(f"   • {suggestion}")
            else:
                print(f"└─ No suggestions needed")
                
        except Exception as e:
            print(f"├─ Error: {e}")
            print(f"└─ This might indicate LLM is not available")
        
        print()


def test_fallback_mode():
    """Test fallback to rule-based when no LLM is provided."""
    
    config = RelevanceConfig(
        evaluation_mode="task_action_target",
        enabled=True
    )
    
    # Create checker without LLM provider
    checker = ContextualRelevanceChecker(config)
    
    print("\nFallback Mode (No LLM)")
    print("=" * 30)
    
    query = "remove the oil filter"
    result = checker.check_relevance(query)
    
    print(f"Query: \"{query}\"")
    print(f"Relevant: {result.is_relevant}")
    print(f"Confidence: {result.confidence}")
    print(f"Stage: {result.stage}")
    print(f"Explanation: {result.explanation}")


if __name__ == "__main__":
    test_llm_task_action_target()
    test_fallback_mode()