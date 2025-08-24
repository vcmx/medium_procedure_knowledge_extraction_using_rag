"""Example workflow orchestrator for the 5-step conversational query processing."""

import logging
from typing import Dict

from .conversation_manager import ConversationManager, ProcessedQuery
from .conversation_state import UserLevel
from .factory import QueryAnalyzerFactory

logger = logging.getLogger(__name__)


class ConversationalWorkflow:
    """
    Orchestrates a simplified, direct query processing flow.
    """

    def __init__(
        self,
        analyzer_type: str = "openrouter",
        model_name: str = None,
        **_kwargs,  # Accept and ignore other legacy arguments
    ):
        """Initialize the conversational workflow."""
        self.query_analyzer = QueryAnalyzerFactory.create(
            implementation=analyzer_type, model_name=model_name
        )
        self.conversation_manager = ConversationManager(
            query_analyzer=self.query_analyzer,
        )

    def process_query(self, *args, **kwargs) -> ProcessedQuery:
        """Directly passes the query to the conversation manager."""
        return self.conversation_manager.process_query(*args, **kwargs)

    def get_session_summary(self, session_id: str) -> Dict[str, any]:
        """Get a summary of the conversation session."""
        return self.conversation_manager.get_session_summary(session_id)

    def clear_session(self, session_id: str) -> None:
        """Clear a conversation session."""
        self.conversation_manager.clear_session(session_id)


def demonstrate_workflow():
    """Demonstrate the 5-step conversational workflow."""
    # Create workflow
    workflow = ConversationalWorkflow(
        analyzer_type="ollama", enable_relevance_check=True, enable_clarification=True
    )

    # Example queries
    test_queries = [
        # Relevant query that needs clarification
        "How do I fix the engine problem?",
        # Irrelevant query that should be rejected
        "What's the weather like today?",
        # Clear technical query
        "Explain the fuel injection system in a diesel engine",
    ]

    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Processing: {query}")
        print("=" * 60)

        session_id = f"demo_{query[:10].replace(' ', '_')}"

        # Process query through 5-step workflow
        result, metadata = workflow.process_user_query(
            query, session_id, user_level=UserLevel.NOVICE
        )

        # Display results
        print(f"\nWorkflow Steps Completed: {metadata['steps_completed']}")

        if result.rejection_reason:
            print(f"❌ Query Rejected: {result.rejection_reason}")
        else:
            print("✅ Query Accepted")
            print(f"   Relevance Score: {result.relevance_score:.2f}")

            if result.clarifications:
                print(f"   Clarifications Made: {len(result.clarifications)}")
                for c in result.clarifications:
                    print(f"     - Q: {c.question}")
                    print(f"       A: {c.answer}")

            if result.intent:
                print(f"   Intent: {result.intent.semantic_intent}")
                print(f"   Query Type: {result.intent.query_type}")

                if result.intent.entities:
                    print(f"   Entities: {', '.join(result.intent.entities)}")

                if result.intent.step_back_questions:
                    print(
                        f"   Step-back Questions: {len(result.intent.step_back_questions)}"
                    )

                if result.intent.expanded_queries:
                    print(f"   Query Expansions: {len(result.intent.expanded_queries)}")

                if result.intent.decomposed_questions:
                    print(
                        f"   Decomposed Questions: {len(result.intent.decomposed_questions)}"
                    )

        # Get session summary
        summary = workflow.get_session_summary(session_id)
        print(f"\nSession Summary: {summary}")

        # Clear session
        workflow.clear_session(session_id)


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run demonstration
    demonstrate_workflow()
