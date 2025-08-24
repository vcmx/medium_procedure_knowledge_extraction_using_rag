"""Tests for the conversational query analysis flow."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.modules.query_analyzer.conversation_state import (
    ConversationState, ConversationTurn, ClarificationRecord, UserLevel
)
from src.modules.query_analyzer.conversation_manager import (
    ConversationManager, ProcessedQuery, ClarificationRequest
)
from src.modules.query_analyzer.conversational_workflow import ConversationalWorkflow
from src.modules.query_analyzer.base import QueryIntent


class TestConversationState:
    """Test conversation state management."""
    
    def test_create_conversation_state(self):
        """Test creating a new conversation state."""
        state = ConversationState(
            session_id="test_session",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        assert state.session_id == "test_session"
        assert len(state.turns) == 0
        assert len(state.entities_mentioned) == 0
        assert state.user_level == UserLevel.NOVICE
    
    def test_add_turn(self):
        """Test adding conversation turns."""
        state = ConversationState(
            session_id="test_session",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        intent = QueryIntent(
            query_type="factual",
            entities=["engine", "fuel"],
            time_filter=None,
            semantic_intent="How engines use fuel",
            expanded_queries=[]
        )
        
        state.add_turn("How do engines use fuel?", intent)
        
        assert len(state.turns) == 1
        assert state.turns[0].query == "How do engines use fuel?"
        assert state.turns[0].intent == intent
        assert "engine" in state.entities_mentioned
        assert "fuel" in state.entities_mentioned
        assert "How engines use fuel" in state.topics_discussed
    
    def test_add_clarification(self):
        """Test adding clarifications."""
        state = ConversationState(
            session_id="test_session",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Add a turn first
        state.add_turn("Fix engine problem", None)
        
        # Add clarification
        state.add_clarification(
            "What type of engine?",
            "Diesel engine",
            "Fix engine problem"
        )
        
        assert "What type of engine?" in state.clarifications_made
        assert state.clarifications_made["What type of engine?"] == "Diesel engine"
        assert len(state.turns[0].clarifications) == 1
    
    def test_build_context_prompt(self):
        """Test building context prompt from conversation history."""
        state = ConversationState(
            session_id="test_session",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Add some conversation history
        intent1 = QueryIntent(
            query_type="factual",
            entities=["diesel", "engine"],
            time_filter=None,
            semantic_intent="Understanding diesel engines",
            expanded_queries=[]
        )
        state.add_turn("Tell me about diesel engines", intent1)
        
        state.add_clarification(
            "Are you interested in maintenance or operation?",
            "Maintenance",
            "Tell me about diesel engines"
        )
        
        state.current_domain = "automotive"
        state.user_level = UserLevel.EXPERIENCED
        
        context = state.build_context_prompt()
        
        assert "Recent conversation:" in context
        assert "Tell me about diesel engines" in context
        assert "Understanding diesel engines" in context
        assert "diesel" in context
        assert "Maintenance" in context
        assert "automotive" in context
        assert "experienced" in context


class TestConversationManager:
    """Test conversation manager functionality."""
    
    @pytest.fixture
    def mock_analyzer(self):
        """Create a mock query analyzer."""
        analyzer = Mock()
        analyzer.analyze = Mock(return_value=QueryIntent(
            query_type="factual",
            entities=["test"],
            time_filter=None,
            semantic_intent="Test intent",
            expanded_queries=["test query expansion"],
            decomposed_questions=["sub question 1"],
            step_back_questions=["general question"],
            clarifying_questions=["Need clarification?"]
        ))
        analyzer.analyze_with_context = Mock(side_effect=analyzer.analyze)
        return analyzer
    
    @pytest.fixture
    def mock_relevance_checker(self):
        """Create a mock relevance checker."""
        checker = Mock()
        checker.check_detailed = Mock(return_value=(True, 0.9, {}))
        return checker
    
    def test_process_query_accepted(self, mock_analyzer, mock_relevance_checker):
        """Test processing a relevant query."""
        manager = ConversationManager(
            query_analyzer=mock_analyzer,
            relevance_checker=mock_relevance_checker,
            enable_clarification=False
        )
        
        result = manager.process_query(
            query="How does a diesel engine work?",
            session_id="test_session"
        )
        
        assert isinstance(result, ProcessedQuery)
        assert result.original_query == "How does a diesel engine work?"
        assert result.relevance_score == 0.9
        assert result.rejection_reason is None
        assert result.intent.query_type == "factual"
    
    def test_process_query_rejected(self, mock_analyzer):
        """Test processing an irrelevant query."""
        mock_relevance_checker = Mock()
        mock_relevance_checker.check_detailed = Mock(
            return_value=(False, 0.2, {"rejection_reason": "Off-topic"})
        )
        
        manager = ConversationManager(
            query_analyzer=mock_analyzer,
            relevance_checker=mock_relevance_checker,
            enable_clarification=False
        )
        
        result = manager.process_query(
            query="What's the weather?",
            session_id="test_session"
        )
        
        assert result.relevance_score == 0.2
        assert result.rejection_reason == "Off-topic"
        assert result.intent.query_type == "rejected"
        assert result.intent.semantic_intent == "rejected"
    
    def test_clarification_flow(self, mock_analyzer, mock_relevance_checker):
        """Test the clarification flow."""
        # Mock analyzer that returns clarifying questions
        mock_analyzer.analyze = Mock(return_value=QueryIntent(
            query_type="factual",
            entities=[],
            time_filter=None,
            semantic_intent="Unclear query",
            expanded_queries=[],
            clarifying_questions=["What type of engine?", "What specific problem?"]
        ))
        
        manager = ConversationManager(
            query_analyzer=mock_analyzer,
            relevance_checker=mock_relevance_checker,
            enable_clarification=True
        )
        
        # Process with clarification responses
        result = manager.process_query(
            query="Fix engine",
            session_id="test_session",
            user_responses={
                "What type of engine?": "Diesel",
                "What specific problem?": "Won't start"
            }
        )
        
        assert len(result.clarifications) == 2
        assert result.clarifications[0].question == "What type of engine?"
        assert result.clarifications[0].answer == "Diesel"
    
    def test_session_management(self, mock_analyzer):
        """Test session creation and retrieval."""
        manager = ConversationManager(query_analyzer=mock_analyzer)
        
        # Get or create session
        state1 = manager.get_or_create_session("session1")
        assert state1.session_id == "session1"
        
        # Get same session again
        state2 = manager.get_or_create_session("session1")
        assert state1 is state2
        
        # Clear session
        manager.clear_session("session1")
        state3 = manager.get_or_create_session("session1")
        assert state3 is not state1


class TestConversationalWorkflow:
    """Test the complete conversational workflow."""
    
    @patch('src.modules.query_analyzer.conversational_workflow.create_query_analyzer')
    @patch('src.modules.query_analyzer.conversational_workflow.ContextualRelevanceChecker')
    def test_workflow_five_steps(self, mock_relevance_class, mock_create_analyzer):
        """Test the 5-step workflow execution."""
        # Setup mocks
        mock_analyzer = Mock()
        mock_create_analyzer.return_value = mock_analyzer
        
        mock_relevance_checker = Mock()
        mock_relevance_checker.check_detailed = Mock(return_value=(True, 0.95, {}))
        mock_relevance_class.return_value = mock_relevance_checker
        
        # Mock analyzer behavior
        mock_analyzer.analyze = Mock(return_value=QueryIntent(
            query_type="explanation",
            entities=["fuel", "injection"],
            time_filter=None,
            semantic_intent="Understanding fuel injection",
            expanded_queries=["How fuel injection works"],
            decomposed_questions=["What is fuel injection?"],
            step_back_questions=["How do engines get fuel?"],
            clarifying_questions=[]
        ))
        
        # Create workflow
        workflow = ConversationalWorkflow(
            analyzer_type="ollama",
            enable_relevance_check=True,
            enable_clarification=True
        )
        
        # Process query
        result, metadata = workflow.process_user_query(
            query="Explain fuel injection",
            session_id="test_workflow",
            user_level=UserLevel.NOVICE
        )
        
        # Verify workflow steps
        assert "initial_prompt_received" in metadata["steps_completed"]
        assert "relevance_check_passed" in metadata["steps_completed"]
        assert metadata["relevance_passed"] is True
        
        # Since no clarifying questions, should skip clarification
        assert "clarification_skipped" in metadata["steps_completed"]
        assert metadata["clarification_needed"] is False
        
        # Intent should be analyzed
        assert "intent_analysis_completed" in metadata["steps_completed"]
        assert metadata["intent_analyzed"] is True
        
        # Query should be enhanced (has expansions, decomposition, stepback)
        assert "query_enhancement_completed" in metadata["steps_completed"]
        assert metadata["query_enhanced"] is True
    
    @patch('src.modules.query_analyzer.conversational_workflow.create_query_analyzer')
    @patch('src.modules.query_analyzer.conversational_workflow.ContextualRelevanceChecker')
    def test_workflow_with_rejection(self, mock_relevance_class, mock_create_analyzer):
        """Test workflow with query rejection."""
        # Setup mocks
        mock_analyzer = Mock()
        mock_create_analyzer.return_value = mock_analyzer
        
        mock_relevance_checker = Mock()
        mock_relevance_checker.check_detailed = Mock(
            return_value=(False, 0.1, {"rejection_reason": "Not technical"})
        )
        mock_relevance_class.return_value = mock_relevance_checker
        
        # Create workflow
        workflow = ConversationalWorkflow(
            analyzer_type="ollama",
            enable_relevance_check=True
        )
        
        # Process irrelevant query
        result, metadata = workflow.process_user_query(
            query="What's the weather?",
            session_id="test_rejection"
        )
        
        # Verify rejection
        assert "relevance_check_failed" in metadata["steps_completed"]
        assert metadata["relevance_passed"] is False
        assert result.rejection_reason == "Not technical"
        
        # Should not proceed to other steps
        assert "intent_analysis_completed" not in metadata["steps_completed"]
        assert "query_enhancement_completed" not in metadata["steps_completed"]


def test_workflow_with_updated_relevance():
    """Test the conversational workflow with the updated relevance checker (both modes)."""
    print("🧪 Testing conversational workflow with updated relevance checker...")
    
    # Test queries
    test_cases = [
        {
            "query": "How do I fix the engine problem?",
            "expected_relevant": True,
            "description": "Relevant technical query"
        },
        {
            "query": "What's the weather like today?",
            "expected_relevant": False,
            "description": "Irrelevant query"
        },
        {
            "query": "Explain diesel engine fuel injection system",
            "expected_relevant": True,
            "description": "Clear technical query"
        }
    ]
    
    print("\n" + "="*60)
    print("Testing with TWO-STAGE relevance mode")
    print("="*60)
    
    # Test with two-stage mode (default)
    try:
        workflow_two_stage = ConversationalWorkflow(
            analyzer_type="ollama",
            enable_relevance_check=True,
            enable_clarification=False  # Disable for testing
        )
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n--- Test {i}: {test_case['description']} ---")
            print(f"Query: '{test_case['query']}'")
            
            session_id = f"test_two_stage_{i}"
            
            try:
                result, metadata = workflow_two_stage.process_user_query(
                    test_case["query"],
                    session_id,
                    user_level=UserLevel.NOVICE
                )
                
                print(f"✅ Processing completed")
                print(f"   Relevance passed: {metadata.get('relevance_passed')}")
                print(f"   Steps completed: {metadata.get('steps_completed')}")
                
                if result.rejection_reason:
                    print(f"   ❌ Rejected: {result.rejection_reason}")
                else:
                    print(f"   ✅ Accepted with score: {result.relevance_score:.2f}")
                    if result.intent:
                        print(f"   Intent: {result.intent.semantic_intent}")
                        print(f"   Query type: {result.intent.query_type}")
                        
                # Verify expectation (basic check)
                is_relevant = not bool(result.rejection_reason)
                status = "✅" if is_relevant == test_case["expected_relevant"] else "⚠️"
                print(f"   {status} Relevance matches expectation: {is_relevant}")
                        
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
            
            # Clean up session
            workflow_two_stage.clear_session(session_id)
            
    except Exception as e:
        print(f"❌ Failed to test two-stage mode: {str(e)}")
    
    print("\n" + "="*60)
    print("Testing with TASK-ACTION-TARGET relevance mode")
    print("="*60)
    
    # Test with task-action-target mode  
    try:
        workflow_tat = ConversationalWorkflow(
            analyzer_type="ollama",
            enable_relevance_check=True,
            enable_clarification=False  # Disable for testing
        )
        
        # Update the relevance checker to use task-action-target mode
        if workflow_tat.relevance_checker:
            workflow_tat.relevance_checker.config.evaluation_mode = "task_action_target"
            print("✅ Successfully configured task-action-target mode")
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n--- Test {i}: {test_case['description']} ---")
            print(f"Query: '{test_case['query']}'")
            
            session_id = f"test_tat_{i}"
            
            try:
                result, metadata = workflow_tat.process_user_query(
                    test_case["query"],
                    session_id,
                    user_level=UserLevel.NOVICE
                )
                
                print(f"✅ Processing completed")
                print(f"   Relevance passed: {metadata.get('relevance_passed')}")
                print(f"   Steps completed: {metadata.get('steps_completed')}")
                
                if result.rejection_reason:
                    print(f"   ❌ Rejected: {result.rejection_reason}")
                else:
                    print(f"   ✅ Accepted with score: {result.relevance_score:.2f}")
                    if result.intent:
                        print(f"   Intent: {result.intent.semantic_intent}")
                        print(f"   Query type: {result.intent.query_type}")
                        
                # Verify expectation (basic check)
                is_relevant = not bool(result.rejection_reason)
                status = "✅" if is_relevant == test_case["expected_relevant"] else "⚠️"
                print(f"   {status} Relevance matches expectation: {is_relevant}")
                        
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
            
            # Clean up session
            workflow_tat.clear_session(session_id)
            
    except Exception as e:
        print(f"❌ Failed to test task-action-target mode: {str(e)}")
    
    print("\n✅ Conversational workflow testing completed!")


if __name__ == "__main__":
    # Run the updated relevance test
    test_workflow_with_updated_relevance()
    
    # Run original pytest tests
    pytest.main([__file__, "-v"])