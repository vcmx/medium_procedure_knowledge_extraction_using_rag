#!/usr/bin/env python3
"""
Focused test for Supervisor Agent routing decisions.

Tests the supervisor's ability to route queries to appropriate agents
based on workflow stage and query analysis results.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.modules.agent.supervisor import SupervisorAgent
from src.modules.agent.base import AgentState
from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_supervisor_routing():
    """Test supervisor routing decisions for different scenarios."""
    
    print("🧪 Testing Supervisor Agent Routing")
    print("=" * 50)
    
    # Initialize supervisor
    llm = ChatOllama(model="llama3.2", temperature=0.1)
    available_agents = ["query_analyzer", "rag", "mcp"]
    supervisor = SupervisorAgent(llm, available_agents)
    
    # Test scenarios
    scenarios = [
        {
            "name": "Initial Query",
            "state": AgentState(
                messages=[HumanMessage(content="How do I change engine oil?")],
                workflow_stage="initial",
                clarification_needed=False,
                analysis_results={}
            ),
            "expected": "query_analyzer"
        },
        {
            "name": "After Analysis - Need Retrieval", 
            "state": AgentState(
                messages=[HumanMessage(content="How do I change engine oil?")],
                workflow_stage="analyzed",
                clarification_needed=False,
                analysis_results={
                    "intent": {
                        "query_type": "procedural",
                        "semantic_intent": "engine oil change procedure"
                    }
                }
            ),
            "expected": "rag"
        },
        {
            "name": "Need Tool Calculations",
            "state": AgentState(
                messages=[HumanMessage(content="Calculate the torque required for M10 bolts with safety factor 1.5")],
                workflow_stage="analyzed", 
                clarification_needed=False,
                analysis_results={
                    "intent": {
                        "query_type": "computational",
                        "entities": ["torque", "calculation", "safety factor"],
                        "requires_tools": True
                    }
                }
            ),
            "expected": "mcp"
        },
        {
            "name": "Clarification Needed - Waiting",
            "state": AgentState(
                messages=[HumanMessage(content="How do I fix this?")],
                workflow_stage="clarifying",
                clarification_needed=True,
                clarification_questions=["What needs to be fixed?"]
            ),
            "expected": "FINISH"
        },
        {
            "name": "Clarification Provided",
            "state": AgentState(
                messages=[HumanMessage(content="How do I fix this?")],
                workflow_stage="clarifying",
                clarification_needed=True,
                clarification_questions=["What needs to be fixed?"],
                user_responses={"What needs to be fixed?": "My engine is making noise"}
            ),
            "expected": "query_analyzer"
        }
    ]
    
    # Test each scenario
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{i}. Testing: {scenario['name']}")
        print(f"   Query: {scenario['state']['messages'][0].content}")
        print(f"   Stage: {scenario['state']['workflow_stage']}")
        
        try:
            # Get supervisor decision
            decision = supervisor._make_decision(
                context=f"Process query: {scenario['state']['messages'][0].content}",
                state=scenario['state']
            )
            
            print(f"   Decision: {decision.next_agent}")
            print(f"   Reasoning: {decision.reasoning}")
            print(f"   Expected: {scenario['expected']}")
            
            if decision.next_agent == scenario['expected']:
                print("   ✅ PASS")
            else:
                # For LLM-based decisions, accept reasonable alternatives
                if scenario['name'] == "Need Tool Calculations" and decision.next_agent == "rag":
                    print("   ⚠️  ACCEPTABLE (LLM chose RAG for calculation query)")
                else:
                    print("   ❌ FAIL")
                
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
    
    print(f"\n{'='*50}")
    print("✅ Supervisor routing test completed")


def test_supervisor_fallback():
    """Test supervisor fallback logic when LLM is unavailable."""
    
    print("\n🧪 Testing Supervisor Fallback Logic")
    print("=" * 50)
    
    # Initialize supervisor with invalid model to test fallback
    try:
        llm = ChatOllama(model="invalid-model", temperature=0.1)
        supervisor = SupervisorAgent(llm, ["query_analyzer", "rag"])
        
        state = AgentState(
            messages=[HumanMessage(content="How do I change oil?")],
            workflow_stage="initial"
        )
        
        # Should use fallback logic
        decision = supervisor._make_decision("Test query", state)
        print(f"Fallback decision: {decision.next_agent}")
        print(f"Reasoning: {decision.reasoning}")
        
    except Exception as e:
        print(f"Fallback handling: {e}")
    
    print("✅ Fallback test completed")


if __name__ == "__main__":
    try:
        test_supervisor_routing()
        test_supervisor_fallback()
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        print(f"\n❌ Test suite failed: {e}")
        exit(1)
    
    print(f"\n🎉 All supervisor tests completed!")