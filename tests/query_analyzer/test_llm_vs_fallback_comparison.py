"""Compare LLM-based vs fallback rule-based task-action-target evaluation."""

from src.modules.query_analyzer.relevance_checker import ContextualRelevanceChecker
from src.modules.query_analyzer.models import RelevanceConfig


def test_llm_vs_fallback_comparison():
    """Compare LLM-based evaluation with fallback rule-based evaluation."""
    
    # Test queries that demonstrate the difference
    test_queries = [
        "remove the oil filter",
        "the engine is making noise", 
        "check engine oil level",
        "adjust carburetor mixture",
        "what's wrong with my car",
        "cook dinner"
    ]
    
    print("LLM vs Fallback Comparison")
    print("=" * 50)
    
    for query in test_queries:
        print(f"\nQuery: \"{query}\"")
        print("-" * 40)
        
        # Test with fallback (no LLM)
        config_fallback = RelevanceConfig(evaluation_mode="task_action_target")
        checker_fallback = ContextualRelevanceChecker(config_fallback)
        result_fallback = checker_fallback.check_relevance(query)
        
        print(f"FALLBACK (Rule-based):")
        print(f"  Relevant: {result_fallback.is_relevant} | Confidence: {result_fallback.confidence}")
        print(f"  Explanation: {result_fallback.explanation}")
        print(f"  Domain matches: {result_fallback.domain_matches}")
        
        # Test with LLM (if available)
        try:
            from langchain_ollama import ChatOllama
            
            llm = ChatOllama(model="llama3.2", temperature=0.0)
            config_llm = RelevanceConfig(evaluation_mode="task_action_target")
            checker_llm = ContextualRelevanceChecker(config_llm, llm_provider=llm)
            result_llm = checker_llm.check_relevance(query)
            
            print(f"LLM (Ollama):")
            print(f"  Relevant: {result_llm.is_relevant} | Confidence: {result_llm.confidence}")
            print(f"  Explanation: {result_llm.explanation[:100]}...")
            print(f"  Domain matches: {result_llm.domain_matches}")
            
            # Compare results
            if result_fallback.is_relevant != result_llm.is_relevant:
                print(f"  ⚠️  DIFFERENCE: Relevance assessment differs!")
            elif abs(result_fallback.confidence - result_llm.confidence) > 0.2:
                print(f"  ℹ️  DIFFERENCE: Confidence differs significantly")
            else:
                print(f"  ✓ Similar results")
                
        except ImportError:
            print(f"LLM (Ollama): Not available (langchain_ollama not installed)")
        except Exception as e:
            print(f"LLM (Ollama): Error - {e}")


def test_edge_cases():
    """Test edge cases that might differ between LLM and fallback."""
    
    edge_cases = [
        "My car won't start",           # Natural language problem description
        "Service the transmission",     # Implied action
        "Brake pad replacement guide",  # Procedural query
        "Engine diagnostic codes",      # Technical information request
        "Oil change procedure",         # Procedure without explicit action
    ]
    
    print("\n\nEdge Cases Comparison")
    print("=" * 30)
    
    for query in edge_cases:
        print(f"\nQuery: \"{query}\"")
        
        # Fallback evaluation
        config = RelevanceConfig(evaluation_mode="task_action_target")
        checker = ContextualRelevanceChecker(config)
        result = checker.check_relevance(query)
        
        print(f"Fallback: {result.is_relevant} (conf: {result.confidence})")
        if result.suggestions:
            print(f"  Suggestions: {result.suggestions[0]}")


if __name__ == "__main__":
    test_llm_vs_fallback_comparison()
    test_edge_cases()