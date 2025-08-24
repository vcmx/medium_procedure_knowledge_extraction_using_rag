"""Example usage of task-action-target evaluation mode."""

from src.modules.query_analyzer.relevance_checker import ContextualRelevanceChecker
from src.modules.query_analyzer.models import RelevanceConfig


def main():
    """Demonstrate task-action-target evaluation mode."""
    
    # Configure for task-action-target mode
    config = RelevanceConfig(
        evaluation_mode="task_action_target",
        enabled=True
    )
    
    # Create relevance checker
    checker = ContextualRelevanceChecker(config)
    
    # Example queries
    queries = [
        "remove the oil filter",
        "replace brake pads on front wheels",
        "the engine is making noise",
        "how to adjust valve clearance",
        "tighten",
        "spark plug",
        "what's the weather today",
        "cook dinner",
        "install new transmission fluid pump"
    ]
    
    print("Task-Action-Target Evaluation Mode Demo")
    print("=" * 50)
    print()
    
    for query in queries:
        result = checker.check_relevance(query)
        
        print(f"Query: \"{query}\"")
        print(f"├─ Relevant: {'✓' if result.is_relevant else '✗'} (confidence: {result.confidence:.1f})")
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
        
        print()
    
    # Compare with two-stage mode
    print("\nComparison with Two-Stage Mode")
    print("=" * 50)
    print()
    
    config_two_stage = RelevanceConfig(
        evaluation_mode="two_stage",
        enabled=True
    )
    checker_two_stage = ContextualRelevanceChecker(config_two_stage)
    
    test_query = "adjust the carburetor mixture"
    
    # Task-action-target result
    result_task = checker.check_relevance(test_query)
    print(f"Query: \"{test_query}\"")
    print("\nTask-Action-Target Mode:")
    print(f"  Stage: {result_task.stage}")
    print(f"  Relevant: {result_task.is_relevant} (confidence: {result_task.confidence})")
    print(f"  Explanation: {result_task.explanation}")
    
    # Two-stage result
    result_two = checker_two_stage.check_relevance(test_query)
    print("\nTwo-Stage Mode:")
    print(f"  Stage: {result_two.stage}")
    print(f"  Relevant: {result_two.is_relevant} (confidence: {result_two.confidence:.2f})")
    print(f"  Explanation: {result_two.explanation}")


if __name__ == "__main__":
    main()