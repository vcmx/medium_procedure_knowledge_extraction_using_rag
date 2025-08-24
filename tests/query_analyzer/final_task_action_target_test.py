"""Final comprehensive test of task-action-target evaluation modes."""

from src.modules.query_analyzer.relevance_checker import ContextualRelevanceChecker
from src.modules.query_analyzer.models import RelevanceConfig


def test_comprehensive():
    """Comprehensive test of both LLM and fallback modes."""
    
    test_cases = [
        {
            "query": "remove the oil filter",
            "expected_relevant": True,
            "description": "Clear action + target"
        },
        {
            "query": "the engine",
            "expected_relevant": False,
            "description": "Target only, missing action"
        },
        {
            "query": "tighten",
            "expected_relevant": False,
            "description": "Action only, missing target"
        },
        {
            "query": "cook dinner",
            "expected_relevant": False,
            "description": "Non-technical query"
        },
        {
            "query": "install new brake pads",
            "expected_relevant": True,
            "description": "Complex technical task"
        }
    ]
    
    print("Comprehensive Task-Action-Target Test")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        query = test_case["query"]
        expected = test_case["expected_relevant"]
        description = test_case["description"]
        
        print(f"\nTest {i}: {description}")
        print(f"Query: \"{query}\"")
        print("-" * 30)
        
        # Test fallback mode
        config_fallback = RelevanceConfig(evaluation_mode="task_action_target")
        checker_fallback = ContextualRelevanceChecker(config_fallback)
        result_fallback = checker_fallback.check_relevance(query)
        
        fallback_pass = result_fallback.is_relevant == expected
        print(f"FALLBACK: {'✓' if fallback_pass else '✗'} (Relevant: {result_fallback.is_relevant}, Expected: {expected})")
        print(f"  Confidence: {result_fallback.confidence}")
        print(f"  Matches: {result_fallback.domain_matches}")
        
        # Test LLM mode (if available)
        try:
            from langchain_ollama import ChatOllama
            
            llm = ChatOllama(model="llama3.2", temperature=0.0)
            config_llm = RelevanceConfig(evaluation_mode="task_action_target")
            checker_llm = ContextualRelevanceChecker(config_llm, llm_provider=llm)
            result_llm = checker_llm.check_relevance(query)
            
            llm_pass = result_llm.is_relevant == expected
            print(f"LLM:      {'✓' if llm_pass else '✗'} (Relevant: {result_llm.is_relevant}, Expected: {expected})")
            print(f"  Confidence: {result_llm.confidence}")
            print(f"  Matches: {result_llm.domain_matches}")
            
            # Overall test result
            if fallback_pass and llm_pass:
                print(f"  RESULT: ✓ PASS - Both modes agree with expected result")
            elif fallback_pass or llm_pass:
                print(f"  RESULT: ⚠ PARTIAL - One mode disagrees")
            else:
                print(f"  RESULT: ✗ FAIL - Both modes disagree with expected result")
                
        except ImportError:
            print(f"LLM:      SKIPPED (Ollama not available)")
            print(f"  RESULT: {'✓ PASS' if fallback_pass else '✗ FAIL'} - Fallback only")
        except Exception as e:
            print(f"LLM:      ERROR ({e})")
            print(f"  RESULT: {'✓ PASS' if fallback_pass else '✗ FAIL'} - Fallback only")


def test_mode_switching():
    """Test switching between two-stage and task-action-target modes."""
    
    print("\n\nMode Switching Test")
    print("=" * 30)
    
    query = "remove the oil filter"
    
    # Two-stage mode
    config_two_stage = RelevanceConfig(evaluation_mode="two_stage")
    checker_two_stage = ContextualRelevanceChecker(config_two_stage)
    result_two_stage = checker_two_stage.check_relevance(query)
    
    # Task-action-target mode (fallback)
    config_task_action = RelevanceConfig(evaluation_mode="task_action_target")
    checker_task_action = ContextualRelevanceChecker(config_task_action)
    result_task_action = checker_task_action.check_relevance(query)
    
    print(f"Query: \"{query}\"")
    print(f"Two-stage mode:        Stage: {result_two_stage.stage}, Relevant: {result_two_stage.is_relevant}")
    print(f"Task-action-target:    Stage: {result_task_action.stage}, Relevant: {result_task_action.is_relevant}")
    
    # Verify stages are different
    if result_two_stage.stage != result_task_action.stage:
        print("✓ PASS - Different stages confirm mode switching works")
    else:
        print("✗ FAIL - Stages should be different")


if __name__ == "__main__":
    test_comprehensive()
    test_mode_switching()