#!/usr/bin/env python3
"""
Demo script for the multi-agent system.

Demonstrates the Supervisor + Query Analyzer Agent + RAG/MCP placeholders
working together to process technical queries.
"""

import sys
import os
import json
from typing import Dict, Any

# Add src to path (adjust for tests/agent/ location)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.modules.agent import AgentController
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def print_separator(title: str = ""):
    """Print a visual separator."""
    print("\n" + "=" * 80)
    if title:
        print(f" {title} ".center(80, "="))
        print("=" * 80)


def print_agent_output(agent_name: str, output: Dict[str, Any]):
    """Print agent output in a readable format."""
    print(f"\n🤖 **{agent_name.upper()} AGENT**")
    
    if "messages" in output:
        for message in output["messages"]:
            content = message.content if hasattr(message, 'content') else str(message)
            print(f"   {content}")
    
    # Show workflow stage
    if "workflow_stage" in output:
        print(f"   📊 Stage: {output['workflow_stage']}")
    
    # Show clarification status
    if output.get("clarification_needed"):
        questions = output.get("clarification_questions", [])
        print(f"   🤔 Clarification needed: {len(questions)} questions")


def demo_basic_query():
    """Demo basic query processing."""
    print_separator("DEMO 1: Basic Query Processing")
    
    controller = AgentController(
        llm_model="llama3.2",
        enable_rag=True,
        enable_mcp=True
    )
    
    # Test query
    query = "What are the torque specifications for engine bolts?"
    print(f"User Query: {query}")
    
    session_id = controller.create_session(user_level="EXPERIENCED")
    print(f"Created session: {session_id}")
    
    print("\n🔄 Processing through agent system...")
    
    # Process query
    for step in controller.process_query(query, session_id):
        agent_name = step["agent"]
        output = step["output"]
        
        if agent_name == "system":
            if output["type"] == "final_result":
                print("\n✅ **PROCESSING COMPLETE**")
                # Show final state summary
                final_state = output["state"]
                print(f"   Final stage: {final_state.get('workflow_stage', 'unknown')}")
            elif output["type"] == "error":
                print(f"\n❌ **ERROR**: {output['error']}")
        else:
            print_agent_output(agent_name, output)


def demo_clarification_workflow():
    """Demo clarification workflow."""
    print_separator("DEMO 2: Clarification Workflow")
    
    controller = AgentController(
        llm_model="gpt-4",
        enable_rag=False,  # Disable for cleaner demo
        enable_mcp=False
    )
    
    # Vague query that should trigger clarification
    query = "How do I change this?"
    print(f"User Query: {query}")
    
    session_id = controller.create_session(user_level="NOVICE")
    
    print("\n🔄 Processing query (should trigger clarification)...")
    
    clarification_questions = []
    for step in controller.process_query(query, session_id):
        agent_name = step["agent"]
        output = step["output"]
        
        if agent_name == "query_analyzer":
            print_agent_output(agent_name, output)
            
            # Check if clarification is needed
            if output.get("clarification_needed"):
                clarification_questions = output.get("clarification_questions", [])
                break
        elif agent_name == "system":
            if output["type"] == "final_result":
                print("\n✅ **INITIAL PROCESSING COMPLETE**")
                break
    
    # Simulate user providing clarification responses
    if clarification_questions:
        print("\n📝 **Simulating user clarification responses:**")
        
        responses = {
            clarification_questions[0]: "engine oil",
            clarification_questions[1]: "step by step instructions",
            clarification_questions[2]: "all the detailed steps"
        }
        
        for question, answer in responses.items():
            print(f"   Q: {question}")
            print(f"   A: {answer}")
        
        print("\n🔄 Processing with clarification responses...")
        
        # Process with clarification
        for step in controller.process_query(
            query, 
            session_id, 
            clarification_responses=responses
        ):
            agent_name = step["agent"]
            output = step["output"]
            
            print_agent_output(agent_name, output)
            
            if agent_name == "system" and output["type"] == "final_result":
                print("\n✅ **CLARIFICATION PROCESSING COMPLETE**")
                break


def demo_multi_agent_coordination():
    """Demo multi-agent coordination."""
    print_separator("DEMO 3: Multi-Agent Coordination")
    
    controller = AgentController(
        llm_model="gpt-4",
        enable_rag=True,
        enable_mcp=True
    )
    
    # Complex query that should use multiple agents
    query = "I need to change the engine oil in my 2019 Honda Civic. What are the torque specs for the drain plug and how much oil does it take?"
    print(f"User Query: {query}")
    print("Expected: Query Analyzer → RAG Agent → MCP Agent")
    
    session_id = controller.create_session(user_level="EXPERIENCED")
    
    print("\n🔄 Processing through multi-agent system...")
    
    agent_sequence = []
    for step in controller.process_query(query, session_id):
        agent_name = step["agent"]
        output = step["output"]
        
        if agent_name != "system":
            agent_sequence.append(agent_name)
        
        print_agent_output(agent_name, output)
        
        if agent_name == "system" and output["type"] == "final_result":
            print("\n✅ **MULTI-AGENT PROCESSING COMPLETE**")
            print(f"   Agent sequence: {' → '.join(agent_sequence)}")
            break


def demo_session_management():
    """Demo session management features."""
    print_separator("DEMO 4: Session Management")
    
    controller = AgentController()
    
    # Create multiple sessions
    print("Creating multiple sessions...")
    session1 = controller.create_session("NOVICE")
    session2 = controller.create_session("EXPERT")
    
    print(f"Session 1: {session1} (NOVICE)")
    print(f"Session 2: {session2} (EXPERT)")
    
    # List sessions
    sessions = controller.list_sessions()
    print(f"\nActive sessions: {len(sessions)}")
    for session in sessions:
        print(f"  - {session['session_id']}: {session['user_level']} ({session['message_count']} messages)")
    
    # Get agent status
    status = controller.get_agent_status()
    print(f"\nAgent Status:")
    print(json.dumps(status, indent=2, default=str))
    
    # Clear sessions
    print(f"\nClearing session 1...")
    cleared = controller.clear_session(session1)
    print(f"Session cleared: {cleared}")
    
    remaining_sessions = controller.list_sessions()
    print(f"Remaining sessions: {len(remaining_sessions)}")


def main():
    """Run all demos."""
    print("🚀 Multi-Agent System Demo")
    print("Demonstrating Supervisor + Query Analyzer + RAG/MCP placeholders")
    
    try:
        # Run demos
        demo_basic_query()
        demo_clarification_workflow()
        demo_multi_agent_coordination()
        demo_session_management()
        
        print_separator("DEMO COMPLETE")
        print("✅ All demos completed successfully!")
        print("\nKey Features Demonstrated:")
        print("- Supervisor agent coordination")
        print("- Query analyzer integration")
        print("- Clarification workflow")
        print("- Multi-agent task routing")
        print("- Session management")
        print("- RAG and MCP placeholder integration")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        logger.exception("Demo error")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())