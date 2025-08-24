"""Test OllamaQueryAnalyzer with updated relevance checker."""

from src.modules.query_analyzer.factory import QueryAnalyzerFactory
from src.modules.query_analyzer.relevance_checker import ContextualRelevanceChecker
from src.modules.query_analyzer.models import QueryAnalyzerConfig, RelevanceConfig


def test_analyzer_with_relevance():
    """Test query analyzer with relevance checking integration."""
    print("Testing Query Analyzer with Relevance Checker")
    print("=" * 50)
    
    # Test 1: Two-stage relevance mode
    print("\nTest 1: Two-Stage Relevance Mode")
    print("-" * 30)
    
    relevance_config = RelevanceConfig(
        enabled=True,
        evaluation_mode="two_stage",
        rejection_mode="soft"
    )
    
    analyzer = QueryAnalyzerFactory.create(
        implementation="ollama",
        relevance_config=relevance_config
    )
    
    # Test relevant query
    query1 = "How to replace brake pads?"
    print(f"\nQuery: '{query1}'")
    intent1 = analyzer.analyze(query1)
    print(f"Query type: {intent1.query_type}")
    print(f"Semantic intent: {intent1.semantic_intent}")
    if hasattr(intent1, 'relevance_info') and intent1.relevance_info:
        print(f"Relevance: {intent1.relevance_info.is_relevant} (confidence: {intent1.relevance_info.confidence})")
    
    # Test irrelevant query
    query2 = "What's the weather today?"
    print(f"\nQuery: '{query2}'")
    intent2 = analyzer.analyze(query2)
    print(f"Query type: {intent2.query_type}")
    if hasattr(intent2, 'relevance_info') and intent2.relevance_info:
        print(f"Relevance: {intent2.relevance_info.is_relevant} (confidence: {intent2.relevance_info.confidence})")
        if intent2.relevance_info.suggestions:
            print(f"Suggestions: {intent2.relevance_info.suggestions[0]}")


def test_analyzer_with_task_action_target():
    """Test query analyzer with task-action-target mode."""
    print("\n\nTest 2: Task-Action-Target Mode")
    print("-" * 30)
    
    # Create LLM provider for task-action-target mode
    try:
        from langchain_ollama import ChatOllama
        llm = ChatOllama(model="llama3.2", temperature=0.0)
        llm_available = True
    except ImportError:
        print("Warning: Ollama not available, will use fallback mode")
        llm = None
        llm_available = False
    
    relevance_config = RelevanceConfig(
        enabled=True,
        evaluation_mode="task_action_target",
        rejection_mode="soft"
    )
    
    # Create relevance checker with LLM
    relevance_checker = ContextualRelevanceChecker(relevance_config, llm_provider=llm)
    
    # Create analyzer
    analyzer = QueryAnalyzerFactory.create(
        implementation="ollama",
        relevance_config=relevance_config
    )
    
    # Set relevance checker with LLM
    analyzer.set_relevance_checker(relevance_checker)
    
    test_queries = [
        "remove the oil filter",
        "the engine is making noise",
        "tighten the bolts"
    ]
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        try:
            intent = analyzer.analyze(query)
            print(f"Query type: {intent.query_type}")
            
            if hasattr(intent, 'relevance_info') and intent.relevance_info:
                rel_info = intent.relevance_info
                print(f"Relevance: {rel_info.is_relevant} (confidence: {rel_info.confidence})")
                print(f"Stage: {rel_info.stage}")
                print(f"Mode: {'LLM' if llm_available else 'Fallback'}")
                
                if rel_info.domain_matches:
                    actions = [m for m in rel_info.domain_matches if m.startswith('action:')]
                    targets = [m for m in rel_info.domain_matches if m.startswith('target:')]
                    if actions:
                        print(f"Actions: {', '.join(a.split(':')[1] for a in actions)}")
                    if targets:
                        print(f"Targets: {', '.join(t.split(':')[1] for t in targets)}")
                
                if not rel_info.is_relevant and rel_info.suggestions:
                    print(f"Suggestion: {rel_info.suggestions[0]}")
                    
        except Exception as e:
            print(f"Error: {e}")


def test_rejection_modes():
    """Test different rejection modes."""
    print("\n\nTest 3: Rejection Modes")
    print("-" * 30)
    
    rejection_modes = ["soft", "hard", "score"]
    irrelevant_query = "What's the weather today?"
    
    for mode in rejection_modes:
        print(f"\nRejection mode: {mode}")
        
        relevance_config = RelevanceConfig(
            enabled=True,
            evaluation_mode="two_stage",
            rejection_mode=mode
        )
        
        analyzer = QueryAnalyzerFactory.create(
            implementation="ollama",
            relevance_config=relevance_config
        )
        
        try:
            intent = analyzer.analyze(irrelevant_query)
            print(f"Query type: {intent.query_type}")
            
            if mode == "hard" and intent.query_type == "out_of_context":
                print("✓ Hard mode: Query marked as out_of_context")
            elif mode == "soft":
                print("✓ Soft mode: Query processed with warning")
            elif mode == "score":
                print("✓ Score mode: Query processed with relevance info")
                
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    test_analyzer_with_relevance()
    test_analyzer_with_task_action_target()
    test_rejection_modes()