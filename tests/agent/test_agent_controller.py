#!/usr/bin/env python3
"""
Focused test for Agent Controller integration.

Tests the full agent coordination through the controller interface.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.modules.agent import AgentController
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_agent_controller_basic():
    """Test basic agent controller functionality."""
    
    print("🧪 Testing Agent Controller Basic Functionality")
    print("=" * 60)
    
    # Initialize controller
    controller = AgentController(
        llm_model="llama3.2",
        enable_rag=True,
        enable_mcp=True
    )
    
    print(f"✅ Controller initialized with agents: {controller.available_agents}")
    
    # Test session creation
    session_id = controller.create_session(user_level="EXPERIENCED")
    print(f"✅ Session created: {session_id}")
    
    # Test query processing
    query = "What are the steps to check engine oil level?"
    print(f"\n📝 Processing query: '{query}'")
    
    try:
        step_count = 0
        for step in controller.process_query(query, session_id):
            step_count += 1
            agent_name = step["agent"]
            output_type = step["output"].get("type", "agent_response")
            
            print(f"   Step {step_count}: {agent_name} ({output_type})")
            
            if agent_name == "system":
                if output_type == "final_result":
                    print("   ✅ Processing completed successfully")
                    break
                elif output_type == "error":
                    print(f"   ❌ Error: {step['output']['error']}")
                    break
            else:
                # Show key information from agent responses
                workflow_stage = step["output"].get("workflow_stage", "unknown")
                clarification_needed = step["output"].get("clarification_needed", False)
                print(f"      Stage: {workflow_stage}, Clarification: {clarification_needed}")
        
        print(f"✅ Query processed in {step_count} steps")
        
    except Exception as e:
        print(f"❌ Query processing failed: {e}")
        logger.exception("Query processing error")
    
    # Test session info
    session_info = controller.get_session_info(session_id)
    if session_info:
        print(f"✅ Session info retrieved: {len(session_info['message_history'])} messages")
    
    # Test agent status
    status = controller.get_agent_status()
    print(f"✅ Agent status retrieved: {len(status)} agents")


def test_clarification_through_controller():
    """Test clarification workflow through controller."""
    
    print("\n🧪 Testing Clarification Through Controller")
    print("=" * 50)
    
    controller = AgentController(
        llm_model="gpt-4",
        enable_rag=False,  # Simplified for testing
        enable_mcp=False
    )
    
    session_id = controller.create_session(user_level="NOVICE")
    
    # Step 1: Send vague query
    vague_query = "How do I fix this problem?"
    print(f"📝 Vague query: '{vague_query}'")
    
    clarification_questions = []
    
    try:
        for step in controller.process_query(vague_query, session_id):
            agent_name = step["agent"]
            output = step["output"]
            
            if agent_name == "query_analyzer":
                clarification_needed = output.get("clarification_needed", False)
                questions = output.get("clarification_questions", [])
                
                if clarification_needed and questions:
                    clarification_questions = questions
                    print(f"✅ Clarification triggered: {len(questions)} questions")
                    for i, q in enumerate(questions, 1):
                        print(f"   Q{i}: {q}")
                    break
            
            elif agent_name == "system":
                if output.get("type") == "final_result":
                    break
        
        # Step 2: Provide clarification responses
        if clarification_questions:
            print(f"\n📝 Providing clarification responses...")
            
            responses = {
                clarification_questions[0]: "engine starting",
                clarification_questions[1]: "cold weather conditions" if len(clarification_questions) > 1 else "cold weather"
            }
            
            for question, answer in responses.items():
                print(f"   Q: {question}")
                print(f"   A: {answer}")
            
            # Process with clarification
            enhanced_query_found = False
            for step in controller.process_query(vague_query, session_id, clarification_responses=responses):
                agent_name = step["agent"]
                output = step["output"]
                
                enhanced_query = output.get("enhanced_query", "")
                if enhanced_query and enhanced_query != vague_query:
                    print(f"✅ Enhanced query: '{enhanced_query}'")
                    enhanced_query_found = True
                
                if agent_name == "system" and output.get("type") == "final_result":
                    break
            
            if enhanced_query_found:
                print("✅ PASS - Clarification workflow completed successfully")
            else:
                print("❌ FAIL - Query enhancement not detected")
        
        else:
            print("❌ FAIL - Clarification not triggered")
            
    except Exception as e:
        print(f"❌ Clarification test failed: {e}")
        logger.exception("Clarification test error")


def test_session_management():
    """Test session management features."""
    
    print("\n🧪 Testing Session Management")
    print("=" * 40)
    
    controller = AgentController()
    
    # Create multiple sessions
    sessions = []
    for i, level in enumerate(["NOVICE", "EXPERIENCED", "EXPERT"], 1):
        session_id = controller.create_session(user_level=level)
        sessions.append(session_id)
        print(f"✅ Session {i} created: {session_id} ({level})")
    
    # List sessions
    session_list = controller.list_sessions()
    print(f"✅ Active sessions: {len(session_list)}")
    
    for session in session_list:
        print(f"   - {session['session_id']}: {session['user_level']} ({session['message_count']} messages)")
    
    # Test session clearing
    cleared = controller.clear_session(sessions[0])
    if cleared:
        print(f"✅ Session cleared: {sessions[0]}")
    
    remaining = controller.list_sessions()
    print(f"✅ Remaining sessions: {len(remaining)}")
    
    if len(remaining) == 2:
        print("✅ PASS - Session management working correctly")
    else:
        print("❌ FAIL - Session management issues")


if __name__ == "__main__":
    try:
        test_agent_controller_basic()
        test_clarification_through_controller()
        test_session_management()
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        print(f"\n❌ Test suite failed: {e}")
        exit(1)
    
    print(f"\n🎉 All agent controller tests completed!")