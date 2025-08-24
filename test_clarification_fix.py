#!/usr/bin/env python3
"""Quick test to verify clarification fix works properly."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))

from src.modules.query_analyzer.conversational_workflow import ConversationalWorkflow
from src.modules.query_analyzer.conversation_state import UserLevel

def test_clarification_flow():
    """Test the clarification flow with a query that needs clarification."""
    
    # Create workflow with clarification enabled
    workflow = ConversationalWorkflow(
        analyzer_type="ollama",
        enable_relevance_check=True,
        enable_clarification=True
    )
    
    # Test query that should need clarification
    query = "How do I fix this?"
    session_id = "test_session"
    
    print(f"Testing query: '{query}'")
    print("-" * 50)
    
    # Step 1: Process without responses - should get clarifying questions
    result1, metadata1 = workflow.process_user_query(
        query=query,
        session_id=session_id,
        user_level=UserLevel.NOVICE
    )
    
    print(f"Initial processing:")
    print(f"  Rejection reason: {result1.rejection_reason}")
    print(f"  Has clarifying questions: {bool(result1.intent and result1.intent.clarifying_questions)}")
    
    if result1.intent and result1.intent.clarifying_questions:
        print(f"  Clarifying questions:")
        for i, q in enumerate(result1.intent.clarifying_questions[:3], 1):
            print(f"    {i}. {q}")
    
    # Step 2: Process with responses
    if result1.intent and result1.intent.clarifying_questions:
        print("\nProviding clarification responses...")
        responses = {
            result1.intent.clarifying_questions[0]: "jet engine compressor",
            result1.intent.clarifying_questions[1]: "noise during startup" if len(result1.intent.clarifying_questions) > 1 else "",
        }
        
        # Process with responses
        result2 = workflow.conversation_manager.process_query(
            query=query,
            session_id=session_id,
            user_responses=responses
        )
        
        print(f"\nAfter clarification:")
        print(f"  Final query: {result2.final_query}")
        print(f"  Clarifications made: {len(result2.clarifications)}")
        if result2.clarifications:
            for c in result2.clarifications:
                print(f"    Q: {c.question}")
                print(f"    A: {c.answer}")
        
        if result2.intent:
            print(f"  Intent: {result2.intent.semantic_intent}")
            print(f"  Entities: {result2.intent.entities}")

if __name__ == "__main__":
    test_clarification_flow()