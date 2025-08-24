#!/usr/bin/env python3
"""Test integration between conversation features and updated relevance checker."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from src.modules.query_analyzer.ollama_analyzer import OllamaQueryAnalyzer
from src.modules.query_analyzer.relevance_checker import ContextualRelevanceChecker
from src.modules.query_analyzer.models import RelevanceConfig, QueryAnalyzerConfig


def test_ollama_analyzer_integration():
    """Test that OllamaQueryAnalyzer integrates properly with updated relevance checker."""
    print("🧪 Testing OllamaQueryAnalyzer integration with updated relevance checker...")
    
    # Test queries
    test_cases = [
        {
            "query": "How does diesel engine fuel injection work?",
            "expected_relevant": True,
            "description": "Technical query"
        },
        {
            "query": "What's for dinner tonight?",
            "expected_relevant": False,
            "description": "Irrelevant query"
        },
        {
            "query": "Fix braking system noise",
            "expected_relevant": True,
            "description": "Technical action query"
        }
    ]
    
    print("\n" + "="*60)
    print("Testing TWO-STAGE relevance mode")
    print("="*60)
    
    # Create analyzer with two-stage relevance checking
    relevance_config_two_stage = RelevanceConfig(
        enabled=True,
        evaluation_mode="two_stage",
        rejection_mode="hard"
    )
    
    try:
        analyzer_two_stage = OllamaQueryAnalyzer(
            config=QueryAnalyzerConfig(),
            relevance_config=relevance_config_two_stage
        )
        
        # Create and set relevance checker
        relevance_checker = ContextualRelevanceChecker(relevance_config_two_stage)
        analyzer_two_stage.set_relevance_checker(relevance_checker)
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n--- Test {i}: {test_case['description']} ---")
            print(f"Query: '{test_case['query']}'")
            
            try:
                # Analyze query
                intent = analyzer_two_stage.analyze(test_case["query"])
                
                print(f"✅ Analysis completed")
                print(f"   Query type: {intent.query_type}")
                print(f"   Semantic intent: {intent.semantic_intent}")
                
                # Check relevance info
                if intent.relevance_info:
                    print(f"   Relevance: {'✅ Relevant' if intent.relevance_info.is_relevant else '❌ Irrelevant'}")
                    print(f"   Confidence: {intent.relevance_info.confidence:.2f}")
                    print(f"   Stage: {intent.relevance_info.stage}")
                    print(f"   Explanation: {intent.relevance_info.explanation}")
                    
                    # Verify expectation
                    is_relevant = intent.relevance_info.is_relevant
                    status = "✅" if is_relevant == test_case["expected_relevant"] else "⚠️"
                    print(f"   {status} Relevance matches expectation: {is_relevant}")
                else:
                    print(f"   ⚠️  No relevance info available")
                    
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
        
    except Exception as e:
        print(f"❌ Failed to test two-stage mode: {str(e)}")
    
    print("\n" + "="*60)
    print("Testing TASK-ACTION-TARGET relevance mode")
    print("="*60)
    
    # Create analyzer with task-action-target relevance checking
    relevance_config_tat = RelevanceConfig(
        enabled=True,
        evaluation_mode="task_action_target",
        rejection_mode="hard"
    )
    
    try:
        analyzer_tat = OllamaQueryAnalyzer(
            config=QueryAnalyzerConfig(),
            relevance_config=relevance_config_tat
        )
        
        # Create and set relevance checker
        relevance_checker = ContextualRelevanceChecker(relevance_config_tat)
        analyzer_tat.set_relevance_checker(relevance_checker)
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n--- Test {i}: {test_case['description']} ---")
            print(f"Query: '{test_case['query']}'")
            
            try:
                # Analyze query
                intent = analyzer_tat.analyze(test_case["query"])
                
                print(f"✅ Analysis completed")
                print(f"   Query type: {intent.query_type}")
                print(f"   Semantic intent: {intent.semantic_intent}")
                
                # Check relevance info
                if intent.relevance_info:
                    print(f"   Relevance: {'✅ Relevant' if intent.relevance_info.is_relevant else '❌ Irrelevant'}")
                    print(f"   Confidence: {intent.relevance_info.confidence:.2f}")
                    print(f"   Stage: {intent.relevance_info.stage}")
                    print(f"   Explanation: {intent.relevance_info.explanation}")
                    
                    # Verify expectation
                    is_relevant = intent.relevance_info.is_relevant
                    status = "✅" if is_relevant == test_case["expected_relevant"] else "⚠️"
                    print(f"   {status} Relevance matches expectation: {is_relevant}")
                else:
                    print(f"   ⚠️  No relevance info available")
                    
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
        
    except Exception as e:
        print(f"❌ Failed to test task-action-target mode: {str(e)}")
    
    print("\n✅ Integration testing completed!")


def test_relevance_checker_standalone():
    """Test the relevance checker in standalone mode."""
    print("\n🔧 Testing ContextualRelevanceChecker standalone...")
    
    # Test both modes
    configs = [
        ("two_stage", RelevanceConfig(evaluation_mode="two_stage")),
        ("task_action_target", RelevanceConfig(evaluation_mode="task_action_target"))
    ]
    
    test_query = "How do I repair diesel engine fuel pump?"
    
    for mode_name, config in configs:
        print(f"\n--- Testing {mode_name} mode ---")
        
        try:
            checker = ContextualRelevanceChecker(config)
            result = checker.check_relevance(test_query)
            
            print(f"✅ {mode_name} check completed")
            print(f"   Relevant: {result.is_relevant}")
            print(f"   Confidence: {result.confidence:.2f}")
            print(f"   Stage: {result.stage}")
            print(f"   Explanation: {result.explanation}")
            
        except Exception as e:
            print(f"   ❌ {mode_name} failed: {str(e)}")


if __name__ == "__main__":
    test_ollama_analyzer_integration()
    test_relevance_checker_standalone()