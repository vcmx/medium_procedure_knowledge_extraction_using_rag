"""
Agent Controller for managing the multi-agent system.

Provides a clean API interface for the LangGraph agent system,
handling session management, state coordination, and response formatting.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph

from ..utils.custom_openrouter import ChatOpenRouter
from .base import AgentState
from .mcp_agent import ModelContextProtocolAgent
from .query_analyzer_agent import QueryAnalyzerAgent
from .rag_agent import RAGAgent
from .search_agent import SearchAgent
from .supervisor import SupervisorAgent

logger = logging.getLogger(__name__)


class AgentController:
    """
    Controller for the multi-agent system.

    Provides a clean interface for:
    - Session management
    - Agent coordination via LangGraph
    - Response formatting
    - Error handling
    """

    def __init__(
        self,
        rag_path: str = "./rag_storage/clip_default",
        rag_embedder_impl: str = "clip",
        analyzer_type: str = "openrouter",
        analyzer_model_name: str = "meta-llama/llama-4-maverick",
        supervisor_model_name: str = "meta-llama/llama-4-maverick",
    ):
        self.rag_path = rag_path
        self.rag_embedder_impl = rag_embedder_impl
        self.analyzer_type = analyzer_type
        self.analyzer_model_name = analyzer_model_name
        self.supervisor_model_name = supervisor_model_name

        # Initialize agents
        self.rag_agent = RAGAgent(
            persist_directory=self.rag_path, embedder_impl=self.rag_embedder_impl
        )
        self.query_analyzer_agent = QueryAnalyzerAgent(
            analyzer_type=self.analyzer_type,
            query_engine=self.rag_agent.query_engine,
            model_name=self.analyzer_model_name,
        )
        self.search_agent = SearchAgent()
        self.mcp_agent = ModelContextProtocolAgent()

        # Define agent nodes and supervisor
        self.agent_nodes = {
            "query_analyzer": self.query_analyzer_agent,
            "rag": self.rag_agent,
            "search": self.search_agent,
            "mcp": self.mcp_agent,
        }

        supervisor_llm = ChatOpenRouter(model_name=self.supervisor_model_name)
        self.supervisor = SupervisorAgent(
            llm=supervisor_llm, available_agents=list(self.agent_nodes.keys())
        )

        self.graph = self._build_graph()

        # Session management
        self.sessions: Dict[str, Dict[str, Any]] = {}

        logger.info(
            f"Initialized AgentController with agents: {list(self.agent_nodes.keys())}"
        )

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph agent coordination graph."""
        builder = StateGraph(AgentState)

        # Add supervisor node
        builder.add_node("supervisor", self.supervisor.process)

        # Add agent nodes
        builder.add_node("query_analyzer", self.query_analyzer_agent.process)

        if self.rag_agent:
            builder.add_node("rag", self.rag_agent.process)

        if self.mcp_agent:
            builder.add_node("mcp", self.mcp_agent.process)

        if self.search_agent:
            builder.add_node("search", self.search_agent.process)

        # Set entry point
        builder.add_edge(START, "supervisor")

        # Add conditional routing from supervisor
        route_mapping = {agent: agent for agent in self.agent_nodes}
        route_mapping["FINISH"] = END

        builder.add_conditional_edges(
            "supervisor", self.supervisor.route_next, route_mapping
        )

        # All agents return to supervisor
        for agent in self.agent_nodes:
            builder.add_edge(agent, "supervisor")

        return builder.compile()

    def create_session(
        self, user_level: str = "EXPERIENCED", experience_years: int = 5
    ) -> str:
        """Create a new conversation session.

        Args:
            user_level: User expertise level (NOVICE, EXPERIENCED, EXPERT)
            experience_years: User experience in years

        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "created_at": datetime.now(),
            "user_level": user_level,
            "experience_years": experience_years,
            "message_history": [],
            "state_history": [],
        }

        logger.info(
            f"Created session {session_id} with user level {user_level} ({experience_years} years)"
        )
        return session_id

    def process_query(
        self,
        query: str,
        session_id: Optional[str] = None,
        user_level: str = "EXPERIENCED",
        experience_years: int = 5,
        clarification_responses: Optional[Dict[str, str]] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """Process a user query through the agent system.

        Args:
            query: User query
            session_id: Optional session ID (creates new if not provided)
            user_level: User expertise level
            experience_years: User experience in years
            clarification_responses: Responses to clarification questions

        Yields:
            Agent processing updates and final result
        """
        # Create session if needed
        if not session_id:
            session_id = self.create_session(
                user_level=user_level, experience_years=experience_years
            )

        try:
            # Build initial state
            initial_state = self._build_initial_state(
                query, session_id, user_level, experience_years, clarification_responses
            )

            # Store in session
            self.sessions[session_id]["message_history"].append(
                {"role": "user", "content": query, "timestamp": datetime.now()}
            )

            # Stream agent processing with recursion limit
            config = {"recursion_limit": 50}

            try:
                for step_output in self.graph.stream(initial_state, config=config):
                    # Process each agent step
                    logger.debug(
                        f"Step output type: {type(step_output)}, content: {step_output}"
                    )

                    if isinstance(step_output, dict):
                        for agent_name, agent_output in step_output.items():
                            if agent_name == "__end__":
                                # Handle workflow completion
                                logger.info(
                                    f"Workflow completed for session {session_id}"
                                )
                                return  # Exit the generator properly
                            elif agent_name not in [
                                "__start__",
                                "__end__",
                            ]:  # Skip internal markers
                                try:
                                    logger.info(
                                        f"[CLARIFY_DEBUG] Controller received step from '{agent_name}': {agent_output}"
                                    )
                                    yield {
                                        "agent": agent_name,
                                        "output": agent_output,
                                        "session_id": session_id,
                                    }

                                    # Store state update
                                    self.sessions[session_id]["state_history"].append(
                                        {
                                            "agent": agent_name,
                                            "output": agent_output,
                                            "timestamp": datetime.now(),
                                        }
                                    )

                                    # Check if workflow should terminate based on stage
                                    # Only terminate on true completion stages, not intermediate ones
                                    if isinstance(agent_output, dict):
                                        stage = agent_output.get("workflow_stage")
                                        if stage in [
                                            "complete",
                                            "error",
                                            "clarifying",
                                            "rejected",
                                        ]:
                                            logger.info(
                                                f"Workflow ending due to stage: {stage}"
                                            )
                                            return  # Exit early on completion

                                except Exception as output_error:
                                    logger.error(
                                        f"Error processing output from {agent_name}: {output_error}"
                                    )
                                    logger.error(f"Agent output: {agent_output}")
                                    raise
                    else:
                        logger.warning(
                            f"Unexpected step output format: {type(step_output)}: {step_output}"
                        )

            except Exception as stream_error:
                # Handle specific __end__ error gracefully
                if "'__end__'" in str(stream_error):
                    logger.info("Workflow completed (end marker encountered)")
                    return
                else:
                    logger.error(f"Error in graph stream: {stream_error}")
                    raise

            # Final result
            yield {
                "agent": "system",
                "output": {"type": "final_result", "session_id": session_id},
                "session_id": session_id,
            }

        except Exception as e:
            logger.error(f"Error processing query in session {session_id}: {e}")
            yield {
                "agent": "system",
                "output": {"type": "error", "error": str(e), "session_id": session_id},
                "session_id": session_id,
            }

    def _build_initial_state(
        self,
        query: str,
        session_id: str,
        user_level: str,
        experience_years: int,
        clarification_responses: Optional[Dict[str, str]],
    ) -> AgentState:
        """Build initial state for agent processing."""
        state = AgentState(
            messages=[HumanMessage(content=query)],
            current_agent="supervisor",
            next_agent=None,
            task_description=f"Process user query: {query}",
            workflow_stage="initial",
            clarification_needed=False,
            clarification_questions=[],
            user_responses=clarification_responses or {},
            original_query=None,
            enhanced_query=None,
            analysis_results={},
            retrieval_results=None,
            tool_calls=[],
            tool_results=[],
            session_id=session_id,
            user_level=user_level,
            experience_years=experience_years,
        )

        # If clarification responses provided, update state
        if clarification_responses:
            state["workflow_stage"] = "clarifying"
            state["user_responses"] = clarification_responses

        return state

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information.

        Args:
            session_id: Session ID

        Returns:
            Session information or None if not found
        """
        return self.sessions.get(session_id)

    def clear_session(self, session_id: str) -> bool:
        """Clear a conversation session.

        Args:
            session_id: Session ID to clear

        Returns:
            True if session was cleared, False if not found
        """
        if session_id in self.sessions:
            # Clear query analyzer session
            self.query_analyzer_agent.clear_session(session_id)

            # Remove from sessions
            del self.sessions[session_id]

            logger.info(f"Cleared session {session_id}")
            return True

        return False

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all active sessions.

        Returns:
            List of session information
        """
        return [
            {
                "session_id": sid,
                "created_at": info["created_at"],
                "user_level": info["user_level"],
                "message_count": len(info["message_history"]),
            }
            for sid, info in self.sessions.items()
        ]

    def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all agents.

        Returns:
            Agent status information
        """
        return {
            "supervisor": {
                "available_agents": list(self.agent_nodes.keys()),
                "llm_model": self.supervisor.llm.model,
            },
            "query_analyzer": {
                "active_sessions": len(self.query_analyzer_agent.workflows),
                "analyzer_type": self.query_analyzer_agent.analyzer_type,
            },
            "rag_agent": {
                "enabled": self.rag_agent is not None,
                "status": "placeholder" if self.rag_agent else "disabled",
            },
            "mcp_agent": {
                "enabled": self.mcp_agent is not None,
                "available_tools": len(self.mcp_agent.available_tools)
                if self.mcp_agent
                else 0,
                "status": "placeholder" if self.mcp_agent else "disabled",
            },
        }
