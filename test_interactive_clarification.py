#!/usr/bin/env python3
"""
Simple test script to demonstrate interactive clarification fix.
Run with: python test_interactive_clarification.py
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))

from src.modules.query_analyzer.conversational_workflow import ConversationalWorkflow
from src.modules.query_analyzer.conversation_state import UserLevel

def test_clarification():
    """Test the interactive clarification flow."""
    print("=== Testing Interactive Clarification Flow ===\n")
    
    # Create workflow
    workflow = ConversationalWorkflow(
        analyzer_type="ollama",
        enable_relevance_check=True,
        enable_clarification=True
    )
    
    # Test query that needs clarification
    query = "How do I fix this?"
    session_id = "test_session_123"
    
    print(f"Query: '{query}'")
    print("-" * 50)
    
    # Step 1: Initial processing
    print("\n1. Initial processing (no clarification responses):")
    result1, metadata1 = workflow.process_user_query(
        query=query,
        session_id=session_id,
        user_level=UserLevel.NOVICE
    )
    
    print(f"   - Relevance passed: {metadata1.get('relevance_passed')}")
    print(f"   - Clarification needed: {metadata1.get('clarification_needed')}")
    
    if result1.intent and result1.intent.clarifying_questions:
        print(f"   - Clarifying questions found: {len(result1.intent.clarifying_questions)}")
        for i, q in enumerate(result1.intent.clarifying_questions[:3], 1):
            print(f"     {i}. {q}")
    
    # Step 2: Simulate user providing clarification
    if result1.intent and result1.intent.clarifying_questions and not result1.rejection_reason:
        print("\n2. User provides clarification responses:")
        
        # Simulate responses
        responses = {
            result1.intent.clarifying_questions[0]: "the jet engine compressor",
        }
        if len(result1.intent.clarifying_questions) > 1:
            responses[result1.intent.clarifying_questions[1]] = "it's making a loud noise during startup"
        
        for q, a in responses.items():
            print(f"   Q: {q}")
            print(f"   A: {a}")
        
        # Re-process with clarification
        print("\n3. Re-processing with clarification:")
        result2 = workflow.conversation_manager.process_query(
            query=query,
            session_id=session_id,
            user_responses=responses
        )
        
        print(f"   - Final query: '{result2.final_query}'")
        print(f"   - Clarifications made: {len(result2.clarifications)}")
        
        if result2.intent:
            print(f"   - Intent: {result2.intent.semantic_intent}")
            print(f"   - Query type: {result2.intent.query_type}")
            if result2.intent.entities:
                print(f"   - Entities: {result2.intent.entities}")
    
    print("\n✅ Test completed!")

if __name__ == "__main__":
    test_clarification()