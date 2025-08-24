"""
Base classes and types for the agent system.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from langgraph.graph import MessagesState


class AgentType(Enum):
    """Available agent types in the system."""

    SUPERVISOR = "supervisor"
    QUERY_ANALYZER = "query_analyzer"
    RAG = "rag"
    MCP = "mcp"
    SEARCH = "search"
    FINISH = "FINISH"


class AgentState(MessagesState):
    """Enhanced state for agent coordination.

    Extends LangGraph's MessagesState with additional fields for
    multi-agent coordination and task management.
    """

    # Agent routing
    current_agent: str
    next_agent: Optional[str]

    # Task management
    task_description: str
    workflow_stage: (
        str  # "analyzing", "clarifying", "retrieving", "processing", "complete"
    )

    # Query analysis state
    clarification_needed: bool
    clarification_questions: List[str]
    user_responses: Dict[str, str]
    original_query: Optional[str]
    enhanced_query: Optional[str]

    # Analysis results
    analysis_results: Dict[str, Any]

    # RAG state (placeholder for future implementation)
    retrieval_results: Optional[Dict[str, Any]]

    # MCP state (placeholder for future implementation)
    tool_calls: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]

    # Session management
    session_id: Optional[str]
    user_level: Optional[str]  # "NOVICE", "EXPERIENCED", "EXPERT"
    experience_years: Optional[int]


@dataclass
class AgentResponse:
    """Standardized response from an agent."""

    agent_name: str
    message: str
    metadata: Dict[str, Any]
    next_agent: Optional[str] = None
    requires_user_input: bool = False
    error: Optional[str] = None


@dataclass
class ToolCall:
    """Represents a tool call for MCP integration."""

    tool_name: str
    parameters: Dict[str, Any]
    call_id: str


@dataclass
class ToolResult:
    """Result from a tool execution."""

    call_id: str
    result: Any
    error: Optional[str] = None
    metadata: Dict[str, Any] = None


# Type aliases for better readability
AgentName = Literal["supervisor", "query_analyzer", "rag", "mcp", "search", "FINISH"]
WorkflowStage = Literal[
    "analyzing", "clarifying", "retrieving", "processing", "complete"
]
UserLevel = Literal["NOVICE", "EXPERIENCED", "EXPERT"]
