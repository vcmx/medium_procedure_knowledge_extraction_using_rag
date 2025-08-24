"""Test conversational workflow with updated relevance checker including LLM-based task-action-target mode."""

from src.modules.query_analyzer.conversation_manager import ConversationManager
from src.modules.query_analyzer.conversation_state import UserLevel
from src.modules.query_analyzer.factory import QueryAnalyzerFactory
from src.modules.query_analyzer.relevance_checker import ContextualRelevanceChecker
from src.modules.query_analyzer.models import QueryAnalyzerConfig, RelevanceConfig


def test_conversation_with_two_stage_relevance():
    """Test conversation with two-stage relevance checking."""
    print("Test 1: Conversation with Two-Stage Relevance Checking")
    print("=" * 50)
    
    # Configure two-stage relevance checking
    relevance_config = RelevanceConfig(
        enabled=True,
        evaluation_mode="two_stage",
        rejection_mode="soft"
    )
    
    # Create analyzer with relevance checking
    analyzer = QueryAnalyzerFactory.create(
        implementation="ollama",
        relevance_config=relevance_config
    )
    
    # Create conversation manager
    conversation_manager = ConversationManager(
        query_analyzer=analyzer,
        relevance_checker=analyzer.relevance_checker if hasattr(analyzer, 'relevance_checker') else None,
        enable_clarification=True
    )
    
    session_id = "test_session_1"
    
    # Test relevant query
    query1 = "How do I replace the brake pads?"
    print(f"\nQuery 1: '{query1}'")
    result1 = conversation_manager.process_query(query1, session_id)
    print(f"Relevant: {result1.rejection_reason is None}")
    if result1.rejection_reason:
        print(f"Rejection reason: {result1.rejection_reason}")
    else:
        print(f"Intent: {result1.final_intent.semantic_intent if result1.final_intent else 'None'}")
    
    # Test irrelevant query
    query2 = "What's the weather today?"
    print(f"\nQuery 2: '{query2}'")
    result2 = conversation_manager.process_query(query2, session_id)
    print(f"Relevant: {result2.rejection_reason is None}")
    if result2.rejection_reason:
        print(f"Rejection reason: {result2.rejection_reason}")


def test_conversation_with_task_action_target():
    """Test conversation with task-action-target relevance checking."""
    print("\n\nTest 2: Conversation with Task-Action-Target Relevance Checking")
    print("=" * 50)
    
    # Try to create LLM provider
    try:
        from langchain_ollama import ChatOllama
        llm = ChatOllama(model="llama3.2", temperature=0.0)
    except ImportError:
        print("Ollama not available, using fallback mode")
        llm = None
    
    # Configure task-action-target relevance checking
    relevance_config = RelevanceConfig(
        enabled=True,
        evaluation_mode="task_action_target",
        rejection_mode="soft"
    )
    
    # Create relevance checker with LLM
    relevance_checker = ContextualRelevanceChecker(relevance_config, llm_provider=llm)
    
    # Create analyzer
    analyzer = QueryAnalyzerFactory.create(
        implementation="ollama",
        relevance_config=relevance_config
    )
    
    # Set the relevance checker with LLM
    if hasattr(analyzer, 'set_relevance_checker'):
        analyzer.set_relevance_checker(relevance_checker)
    
    # Create conversation manager
    conversation_manager = ConversationManager(
        query_analyzer=analyzer,
        relevance_checker=relevance_checker,
        enable_clarification=True
    )
    
    session_id = "test_session_2"
    
    # Test complete task query
    query1 = "remove the oil filter"
    print(f"\nQuery 1: '{query1}'")
    result1 = conversation_manager.process_query(query1, session_id)
    print(f"Relevant: {result1.rejection_reason is None}")
    if result1.rejection_reason:
        print(f"Rejection reason: {result1.rejection_reason}")
    else:
        print(f"Intent: {result1.final_intent.semantic_intent if result1.final_intent else 'None'}")
    
    # Test incomplete task query
    query2 = "the engine"
    print(f"\nQuery 2: '{query2}'")
    result2 = conversation_manager.process_query(query2, session_id)
    print(f"Relevant: {result1.rejection_reason is None}")
    if result2.rejection_reason:
        print(f"Rejection reason: {result2.rejection_reason}")
        if result2.suggestions:
            print(f"Suggestions: {result2.suggestions}")


def test_multi_turn_conversation():
    """Test multi-turn conversation with relevance checking."""
    print("\n\nTest 3: Multi-Turn Conversation with Context")
    print("=" * 50)
    
    # Configure relevance checking
    relevance_config = RelevanceConfig(
        enabled=True,
        evaluation_mode="two_stage",
        rejection_mode="soft"
    )
    
    # Create analyzer with relevance checking
    analyzer = QueryAnalyzerFactory.create(
        implementation="ollama",
        relevance_config=relevance_config
    )
    
    # Create conversation manager
    conversation_manager = ConversationManager(
        query_analyzer=analyzer,
        relevance_checker=analyzer.relevance_checker if hasattr(analyzer, 'relevance_checker') else None,
        enable_clarification=False  # Disable for simpler test
    )
    
    session_id = "test_session_3"
    
    # First query establishes context
    query1 = "Tell me about brake systems"
    print(f"\nQuery 1: '{query1}'")
    result1 = conversation_manager.process_query(query1, session_id)
    print(f"Context established: brake systems")
    
    # Follow-up query uses context
    query2 = "How do I service them?"
    print(f"\nQuery 2: '{query2}'")
    result2 = conversation_manager.process_query(query2, session_id)
    print(f"Should understand 'them' refers to brake systems")
    
    # Get conversation history
    history = conversation_manager.get_conversation_history(session_id)
    print(f"\nConversation history:")
    for i, entry in enumerate(history, 1):
        print(f"  Turn {i}: {entry.get('query', 'N/A')}")


if __name__ == "__main__":
    test_conversation_with_two_stage_relevance()
    test_conversation_with_task_action_target()
    test_multi_turn_conversation()