#!/usr/bin/env python3
"""
Focused test for Query Analyzer Agent integration.

Tests the wrapper's ability to integrate the existing 5-step conversational 
workflow with the LangGraph agent system.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.modules.agent.query_analyzer_agent import QueryAnalyzerAgent
from src.modules.agent.base import AgentState
from langchain_core.messages import HumanMessage
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_query_analyzer_integration():
    """Test query analyzer integration with agent system."""
    
    print("🧪 Testing Query Analyzer Agent Integration")
    print("=" * 60)
    
    # Initialize agent
    qa_agent = QueryAnalyzerAgent(analyzer_type="ollama")
    
    # Test scenarios
    scenarios = [
        {
            "name": "Technical Query - Should Pass Relevance",
            "query": "How do I check engine oil level?",
            "user_level": "NOVICE",
            "expect_relevant": True
        },
        {
            "name": "Vague Query - Should Trigger Clarification", 
            "query": "How do I fix this?",
            "user_level": "NOVICE",
            "expect_clarification": True
        },
        {
            "name": "Non-technical Query - Should Be Rejected",
            "query": "What's the weather like?",
            "user_level": "EXPERIENCED",
            "expect_relevant": False
        },
        {
            "name": "Complex Technical Query",
            "query": "What are the torque specifications for Honda Civic engine bolts?",
            "user_level": "EXPERT",
            "expect_relevant": True
        }
    ]
    
    # Test each scenario
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{i}. Testing: {scenario['name']}")
        print(f"   Query: '{scenario['query']}'")
        print(f"   User Level: {scenario['user_level']}")
        
        # Create test state
        state = AgentState(
            messages=[HumanMessage(content=scenario['query'])],
            workflow_stage="initial",
            user_level=scenario['user_level'],
            session_id=f"test_session_{i}"
        )
        
        try:
            # Process with query analyzer agent
            result = qa_agent.process(state)
            
            # Extract response content
            response_message = result.update["messages"][0]
            response_content = response_message.content
            
            print(f"   Response: {response_content[:100]}...")
            
            # Check results
            analysis_results = result.update.get("analysis_results", {})
            workflow_stage = result.update.get("workflow_stage", "unknown")
            clarification_needed = result.update.get("clarification_needed", False)
            
            print(f"   Stage: {workflow_stage}")
            print(f"   Clarification needed: {clarification_needed}")
            
            # Validate expectations
            if scenario.get("expect_relevant") is False:
                if workflow_stage == "rejected":
                    print("   ✅ PASS - Query correctly rejected")
                else:
                    print("   ❌ FAIL - Expected rejection")
            
            elif scenario.get("expect_clarification"):
                if clarification_needed:
                    print("   ✅ PASS - Clarification correctly triggered")
                    questions = result.update.get("clarification_questions", [])
                    print(f"   Questions: {len(questions)} generated")
                else:
                    print("   ❌ FAIL - Expected clarification")
            
            elif scenario.get("expect_relevant"):
                if workflow_stage in ["analyzed", "clarifying"]:
                    print("   ✅ PASS - Query processed successfully")
                else:
                    print("   ❌ FAIL - Expected successful processing")
            
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            logger.exception(f"Error in scenario {i}")
    
    print(f"\n{'='*60}")
    print("✅ Query analyzer integration test completed")


def test_clarification_workflow():
    """Test the clarification workflow specifically."""
    
    print("\n🧪 Testing Clarification Workflow")
    print("=" * 50)
    
    qa_agent = QueryAnalyzerAgent(analyzer_type="ollama")
    
    # Step 1: Initial vague query
    print("\n1. Initial vague query")
    initial_state = AgentState(
        messages=[HumanMessage(content="How do I change this?")],
        workflow_stage="initial",
        user_level="NOVICE",
        session_id="clarification_test"
    )
    
    try:
        result1 = qa_agent.process(initial_state)
        
        clarification_needed = result1.update.get("clarification_needed", False)
        questions = result1.update.get("clarification_questions", [])
        
        print(f"   Clarification needed: {clarification_needed}")
        print(f"   Questions generated: {len(questions)}")
        
        if clarification_needed and questions:
            print("   ✅ PASS - Clarification workflow triggered")
            
            # Display questions
            for i, q in enumerate(questions[:3], 1):
                print(f"   Q{i}: {q}")
            
            # Step 2: Process clarification responses
            print("\n2. Processing clarification responses")
            
            # Simulate user responses
            responses = {
                questions[0]: "engine oil" if "what" in questions[0].lower() else "engine oil",
                questions[1]: "step by step guide" if len(questions) > 1 else "step by step guide"
            }
            
            clarification_state = AgentState(
                messages=[HumanMessage(content="How do I change this?")],
                workflow_stage="clarifying",
                user_level="NOVICE",
                session_id="clarification_test",
                clarification_needed=True,
                original_query="How do I change this?",
                user_responses=responses
            )
            
            result2 = qa_agent.process(clarification_state)
            
            enhanced_query = result2.update.get("enhanced_query", "")
            final_stage = result2.update.get("workflow_stage", "")
            
            print(f"   Enhanced query: {enhanced_query}")
            print(f"   Final stage: {final_stage}")
            
            if enhanced_query and "oil" in enhanced_query.lower():
                print("   ✅ PASS - Query successfully enhanced with clarification")
            else:
                print("   ❌ FAIL - Query enhancement failed")
        
        else:
            print("   ❌ FAIL - Clarification not triggered")
            
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        logger.exception("Error in clarification workflow test")
    
    print("✅ Clarification workflow test completed")


def test_session_management():
    """Test session management capabilities."""
    
    print("\n🧪 Testing Session Management")
    print("=" * 40)
    
    qa_agent = QueryAnalyzerAgent(analyzer_type="ollama")
    
    # Test multiple sessions
    sessions = ["session_1", "session_2", "session_3"]
    
    for session_id in sessions:
        print(f"\n   Testing session: {session_id}")
        
        state = AgentState(
            messages=[HumanMessage(content="Tell me about diesel engines")],
            workflow_stage="initial",
            user_level="EXPERIENCED",
            session_id=session_id
        )
        
        try:
            result = qa_agent.process(state)
            print(f"   ✅ Session {session_id} processed successfully")
            
        except Exception as e:
            print(f"   ❌ Session {session_id} failed: {e}")
    
    # Check that sessions are tracked
    print(f"\n   Active workflows: {len(qa_agent.workflows)}")
    print(f"   Session IDs: {list(qa_agent.workflows.keys())}")
    
    # Test session cleanup
    qa_agent.clear_session("session_1")
    print(f"   After cleanup: {len(qa_agent.workflows)} workflows")
    
    if len(qa_agent.workflows) == 2:
        print("   ✅ PASS - Session management working correctly")
    else:
        print("   ❌ FAIL - Session management issues")
    
    print("✅ Session management test completed")


if __name__ == "__main__":
    try:
        test_query_analyzer_integration()
        test_clarification_workflow()
        test_session_management()
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        print(f"\n❌ Test suite failed: {e}")
        exit(1)
    
    print(f"\n🎉 All query analyzer agent tests completed!")