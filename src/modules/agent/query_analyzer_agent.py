"""
Query Analyzer Agent wrapper for the existing query analyzer module.

This agent wraps the existing conversational workflow and query analyzer
to work within the LangGraph multi-agent system.
"""

import logging
from typing import Dict, Literal

from langchain_core.messages import AIMessage
from langgraph.types import Command

from ..query_analyzer import ConversationalWorkflow
from ..query_analyzer.conversation_manager import ProcessedQuery
from ..query_analyzer.conversation_state import UserLevel
from .base import AgentState

logger = logging.getLogger(__name__)


class QueryAnalyzerAgent:
    """
    Agent wrapper for the existing query analyzer module.

    Integrates the conversational workflow into the LangGraph agent system,
    handling query analysis, clarification, and enhancement.
    """

    def __init__(
        self,
        analyzer_type: str = "ollama",
        query_engine: any = None,
        model_name: str = None,
    ):
        """Initialize the Query Analyzer Agent.

        Args:
            analyzer_type: Type of analyzer to use ("ollama", etc.)
            query_engine: The query engine instance for context-aware clarification.
            model_name: The name of the model to be used by the analyzer.
        """
        self.analyzer_type = analyzer_type
        self.workflows = {}  # Session ID -> ConversationalWorkflow
        self.query_engine = query_engine
        self.model_name = model_name
        logger.info(
            f"Initialized QueryAnalyzerAgent with {analyzer_type} and model {model_name}"
        )

    def get_workflow(self, session_id: str) -> ConversationalWorkflow:
        """Get or create a conversational workflow for the session."""
        if session_id not in self.workflows:
            self.workflows[session_id] = ConversationalWorkflow(
                analyzer_type=self.analyzer_type,
                model_name=self.model_name,
            )
            # If the engine is already set, pass it to the new workflow
            if self.query_engine:
                self.workflows[session_id].conversation_manager.set_query_engine(
                    self.query_engine
                )
        return self.workflows[session_id]

    def process(self, state: AgentState) -> Command[Literal["supervisor"]]:
        """Process the query using the existing query analyzer module.

        Args:
            state: Current agent state

        Returns:
            Command with updated state and routing to supervisor
        """
        try:
            # Extract current query from messages
            last_message = state["messages"][-1]
            query = (
                last_message.content
                if hasattr(last_message, "content")
                else str(last_message)
            )

            # Get or create session
            session_id = state.get("session_id", f"agent_session_{id(state)}")
            workflow = self.get_workflow(session_id)

            # Set user level if provided
            user_level_str = state.get("user_level", "EXPERIENCED")
            try:
                user_level = UserLevel[user_level_str]
                workflow.conversation_manager.update_user_level(session_id, user_level)
            except KeyError:
                logger.warning(
                    f"Invalid user level: {user_level_str}, using EXPERIENCED"
                )
                workflow.conversation_manager.update_user_level(
                    session_id, UserLevel.EXPERIENCED
                )

            # Process query
            if state.get("clarification_needed") and state.get("user_responses"):
                # Processing clarification responses
                logger.info("Processing clarification responses")
                result = workflow.conversation_manager.process_query(
                    query=state.get("original_query", query),
                    session_id=session_id,
                    user_responses=state["user_responses"],
                )
            else:
                # Initial query processing
                logger.info(f"Processing initial query: {query}")
                result = workflow.conversation_manager.process_query(
                    query=query, session_id=session_id
                )

            logger.info(
                f"[CLARIFY_DEBUG] QueryAnalyzerAgent received result from manager: {result}"
            )
            # Build response
            response_content, update_state = self._format_response(result, query, state)
            logger.info(
                f"[CLARIFY_DEBUG] QueryAnalyzerAgent prepared state update: {update_state}"
            )

            update_dict = {
                "messages": [
                    AIMessage(content=response_content, name="query_analyzer")
                ],
                "session_id": session_id,
                **update_state,
            }

            # Add a summary of the inputs used for analysis
            input_summary = {
                "query": query,
                "user_level": user_level_str,
                "clarification_responses": state.get("user_responses"),
            }
            # Clean the summary by removing any None or empty values
            update_dict["_input_summary"] = {
                k: v for k, v in input_summary.items() if v
            }

            return Command(
                update=update_dict,
                goto="supervisor",
            )

        except Exception as e:
            logger.error(f"Error in QueryAnalyzerAgent: {e}")
            return Command(
                update={
                    "messages": [
                        AIMessage(
                            content=f"❌ Error in query analysis: {str(e)}",
                            name="query_analyzer",
                        )
                    ],
                    "workflow_stage": "error",
                },
                goto="supervisor",
            )

    def _format_response(
        self, result: "ProcessedQuery", query: str, state: AgentState
    ) -> tuple[str, Dict]:
        """
        Formats the analysis result into a simple response for the UI and extracts state updates.
        """
        state_updates = {}
        response_content = ""

        # Case 1: Clarification is needed.
        if result.intent.clarifying_questions:
            question = result.intent.clarifying_questions[0]
            response_content = f"🤔 **Clarification Needed:**\n{question}"
            state_updates.update(
                {
                    "clarification_needed": True,
                    "clarification_questions": [question],
                    "original_query": query,
                    "workflow_stage": "clarifying",
                }
            )

        # Case 2: Query is finalized and ready for the next agent.
        elif result.final_query:
            response_content = f"✅ **Query Refined:**\n{result.final_query}"
            state_updates.update(
                {
                    "clarification_needed": False,
                    "workflow_stage": "analyzed",
                    "analysis_results": {
                        "final_query": result.final_query,
                        "original_query": query,
                        "intent": {"semantic_intent": result.intent.semantic_intent},
                    },
                }
            )

        # Fallback Case: Something went wrong.
        else:
            response_content = "⚠️ Analysis complete, but no final query was generated. Proceeding with the original query."
            state_updates.update(
                {
                    "clarification_needed": False,
                    "workflow_stage": "analyzed",
                    "analysis_results": {"final_query": query},
                }
            )

        return response_content, state_updates

    def clear_session(self, session_id: str) -> None:
        """Clear a session's workflow."""
        if session_id in self.workflows:
            del self.workflows[session_id]
            logger.info(f"Cleared session: {session_id}")
