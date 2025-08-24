"""Test the task-action-target evaluation mode."""

from src.modules.query_analyzer.relevance_checker import ContextualRelevanceChecker
from src.modules.query_analyzer.models import RelevanceConfig


def test_task_action_target_mode():
    """Test the task-action-target evaluation mode."""
    
    # Create config with task-action-target mode
    config = RelevanceConfig(
        evaluation_mode="task_action_target",
        enabled=True
    )
    
    # Create relevance checker
    checker = ContextualRelevanceChecker(config)
    
    # Test cases from the technical_tasks_evaluate.txt examples
    test_cases = [
        {
            "query": "remove the oil filter",
            "expected_relevant": True,
            "expected_confidence": 1.0,
            "expected_has_action": True,
            "expected_has_target": True
        },
        {
            "query": "the engine",
            "expected_relevant": False,
            "expected_confidence": 0.3,
            "expected_has_action": False,
            "expected_has_target": True
        },
        {
            "query": "cook the egg",
            "expected_relevant": False,
            "expected_confidence": 0.0,
            "expected_has_action": False,
            "expected_has_target": False
        },
        {
            "query": "tighten the bolts",
            "expected_relevant": True,
            "expected_confidence": 1.0,
            "expected_has_action": True,
            "expected_has_target": True
        },
        {
            "query": "inspect",
            "expected_relevant": False,
            "expected_confidence": 0.5,
            "expected_has_action": True,
            "expected_has_target": False
        }
    ]
    
    print("Testing task-action-target evaluation mode:\n")
    
    for test in test_cases:
        result = checker.check_relevance(test["query"])
        
        print(f"Query: '{test['query']}'")
        print(f"  Is Relevant: {result.is_relevant} (expected: {test['expected_relevant']})")
        print(f"  Confidence: {result.confidence} (expected: {test['expected_confidence']})")
        print(f"  Stage: {result.stage}")
        print(f"  Explanation: {result.explanation}")
        print(f"  Domain Matches: {result.domain_matches}")
        if result.suggestions:
            print(f"  Suggestions: {result.suggestions}")
        
        # Verify results
        assert result.is_relevant == test["expected_relevant"], f"Relevance mismatch for '{test['query']}'"
        assert result.confidence == test["expected_confidence"], f"Confidence mismatch for '{test['query']}'"
        assert result.stage == "task-action-target", f"Stage should be 'task-action-target'"
        
        # Check domain matches
        has_action = any(match.startswith("action:") for match in result.domain_matches)
        has_target = any(match.startswith("target:") for match in result.domain_matches)
        assert has_action == test["expected_has_action"], f"Action presence mismatch for '{test['query']}'"
        assert has_target == test["expected_has_target"], f"Target presence mismatch for '{test['query']}'"
        
        print()
    
    print("\n✓ All tests passed!")


def test_mode_switching():
    """Test switching between evaluation modes."""
    
    # Test two-stage mode
    config_two_stage = RelevanceConfig(
        evaluation_mode="two_stage",
        enabled=True
    )
    checker_two_stage = ContextualRelevanceChecker(config_two_stage)
    
    result_two_stage = checker_two_stage.check_relevance("remove the oil filter")
    print(f"\nTwo-stage mode result:")
    print(f"  Stage: {result_two_stage.stage}")
    print(f"  Explanation: {result_two_stage.explanation}")
    
    # Test task-action-target mode
    config_task_action = RelevanceConfig(
        evaluation_mode="task_action_target",
        enabled=True
    )
    checker_task_action = ContextualRelevanceChecker(config_task_action)
    
    result_task_action = checker_task_action.check_relevance("remove the oil filter")
    print(f"\nTask-action-target mode result:")
    print(f"  Stage: {result_task_action.stage}")
    print(f"  Explanation: {result_task_action.explanation}")
    
    # Verify different stages
    assert result_two_stage.stage == "pre-filter", "Two-stage mode should use 'pre-filter' stage"
    assert result_task_action.stage == "task-action-target", "Task-action mode should use 'task-action-target' stage"
    
    print("\n✓ Mode switching test passed!")


if __name__ == "__main__":
    test_task_action_target_mode()
    test_mode_switching()