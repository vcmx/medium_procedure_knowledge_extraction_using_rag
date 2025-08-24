"""Conversation manager for orchestrating multi-turn query processing."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import BaseQueryAnalyzer, QueryIntent
from .conversation_state import ClarificationRecord, ConversationState, UserLevel
from .relevance_checker import ContextualRelevanceChecker

logger = logging.getLogger(__name__)


@dataclass
class ProcessedQuery:
    """Result of processing a query through the conversation flow."""

    original_query: str
    processed_query: str
    intent: QueryIntent
    session_state: ConversationState
    relevance_score: float
    clarifications: List[ClarificationRecord] = field(default_factory=list)
    rejection_reason: Optional[str] = None

    @property
    def final_query(self) -> str:
        """Get the final processed query."""
        return self.processed_query


@dataclass
class ClarificationRequest:
    """Request for clarification from the user."""

    questions: List[str]
    context: str
    required: bool = True


class ConversationManager:
    """Manages conversational query processing flow."""

    def __init__(
        self,
        query_analyzer: BaseQueryAnalyzer,
        relevance_checker: Optional[ContextualRelevanceChecker] = None,
        enable_clarification: bool = True,
        max_clarification_rounds: int = 2,
    ):
        """Initialize the conversation manager.

        Args:
            query_analyzer: The query analyzer to use
            relevance_checker: Optional relevance checker
            enable_clarification: Whether to enable clarification
            max_clarification_rounds: Maximum rounds of clarification
        """
        self.query_analyzer = query_analyzer
        self.relevance_checker = relevance_checker
        self.enable_clarification = enable_clarification
        self.max_clarification_rounds = max_clarification_rounds
        self.sessions: Dict[str, ConversationState] = {}
        self.query_engine = None  # Will be set by the agent

    def set_query_engine(self, query_engine: any):
        """
        Provides the manager with a query engine instance.
        This is used to fetch document summaries for context-aware clarification.
        """
        self.query_engine = query_engine
        # Pass it to the analyzer as well
        if hasattr(self.query_analyzer, "set_query_engine"):
            self.query_analyzer.set_query_engine(query_engine)

    def get_or_create_session(self, session_id: str) -> ConversationState:
        """Get existing session or create new one."""
        if session_id not in self.sessions:
            self.sessions[session_id] = ConversationState(
                session_id=session_id,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        return self.sessions[session_id]

    def process_query(
        self,
        query: str,
        session_id: str,
        user_responses: Optional[Dict[str, str]] = None,
    ) -> ProcessedQuery:
        """
        Process a query using a simplified, direct flow.

        1. Cleans the query.
        2. If document context is ambiguous, asks for clarification.
        3. Rephrases the query with the document context.
        """
        state = self.get_or_create_session(session_id)
        logger.info(f"Simplified processing for session {session_id}: {query}")

        document_summaries = []
        if self.query_engine:
            try:
                document_summaries = self.query_engine.get_all_document_summaries()
                logger.info(
                    f"Fetched {len(document_summaries)} document summaries for context."
                )
            except Exception as e:
                logger.error(f"Failed to fetch document summaries: {e}")

        # The core logic is now delegated to the analyzer
        intent = self.query_analyzer.clarify_and_refine(
            query, document_summaries=document_summaries, user_responses=user_responses
        )
        logger.info(f"ConversationManager received intent from analyzer: {intent}")

        state.add_turn(query, intent, [])

        return ProcessedQuery(
            original_query=query,
            processed_query=intent.final_query or query,
            intent=intent,
            session_state=state,
            relevance_score=1.0,  # Relevance check is disabled
        )

    def request_clarification(
        self, query: str, session_id: str
    ) -> ClarificationRequest:
        """Request clarification for a query.

        Returns:
            ClarificationRequest with questions for the user
        """
        state = self.get_or_create_session(session_id)
        intent = self.query_analyzer.analyze_with_all_features(query)

        if intent.clarifying_questions:
            return ClarificationRequest(
                questions=intent.clarifying_questions[:3],  # Limit to 3 questions
                context=query,
                required=state.should_clarify(),
            )

        return ClarificationRequest(questions=[], context=query, required=False)

    def process_clarification_response(
        self, session_id: str, responses: Dict[str, str]
    ) -> ProcessedQuery:
        """Process user's clarification responses.

        Args:
            session_id: Session identifier
            responses: Dict mapping questions to answers

        Returns:
            ProcessedQuery with clarified intent
        """
        state = self.get_or_create_session(session_id)

        if not state.turns:
            raise ValueError(f"No active query for session {session_id}")

        # Get the last query
        last_query = state.turns[-1].query

        # Process with clarification responses
        return self.process_query(last_query, session_id, responses)

    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Get summary of a conversation session."""
        state = self.get_or_create_session(session_id)
        return state.get_conversation_summary()

    def clear_session(self, session_id: str) -> None:
        """Clear a conversation session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Cleared session {session_id}")

    def update_user_level(self, session_id: str, level: UserLevel) -> None:
        """Update user level for a session."""
        state = self.get_or_create_session(session_id)
        state.update_user_level(level)
        logger.info(f"Updated user level to {level.name} for session {session_id}")
