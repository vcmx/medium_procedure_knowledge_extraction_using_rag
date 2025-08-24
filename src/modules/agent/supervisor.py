"""
Supervisor Agent for coordinating multi-agent workflows.

The supervisor decides which agent should handle each step of the user's request,
based on the current state and conversation context.
"""

import logging
from typing import Any, Dict, List

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END
from pydantic import BaseModel

from .base import AgentState

logger = logging.getLogger(__name__)


class SupervisorDecision(BaseModel):
    """Structured output for supervisor decisions."""

    next_agent: str
    reasoning: str
    confidence: float


class SupervisorAgent:
    """
    Supervisor agent that coordinates the multi-agent system.

    Makes routing decisions based on:
    - Current workflow stage
    - Available agents and their capabilities
    - User needs and context
    - Task complexity
    """

    def __init__(self, llm: BaseChatModel, available_agents: List[str]):
        """Initialize the supervisor agent.

        Args:
            llm: Language model for decision making
            available_agents: List of available agent names
        """
        self.llm = llm
        self.available_agents = available_agents
        self.system_prompt = self._build_system_prompt()
        logger.info(f"Initialized SupervisorAgent with agents: {available_agents}")

    def _build_system_prompt(self) -> str:
        """Build the system prompt for the supervisor."""
        agent_descriptions = {
            "query_analyzer": "Analyzes user queries, handles clarification, and extracts intent. Use for understanding what the user wants.",
            "rag": "Retrieves relevant information from technical documentation. Use when specific information needs to be found.",
            "mcp": "Executes external tools and calculations. Use for computational tasks, simulations, or external API calls.",
            "search": "Performs web searches for current information, latest news, and real-time data. Use when information is not in local knowledge base.",
        }

        agents_info = "\n".join(
            [
                f"- **{agent}**: {agent_descriptions.get(agent, 'General purpose agent')}"
                for agent in self.available_agents
            ]
        )

        return f"""You are a supervisor coordinating a multi-agent system for technical documentation assistance.

AVAILABLE AGENTS:
{agents_info}

WORKFLOW STAGES:
- **initial**: New user query, route to query_analyzer first
- **analyzing**: Query analysis in progress, continue with query_analyzer
- **clarifying**: Waiting for user clarification, route to query_analyzer when responses received
- **analyzed**: Query understood, decide next step based on intent
- **retrieving**: Information retrieval in progress
- **processing**: Task execution in progress
- **complete**: Task finished, use FINISH

DECISION RULES:
1. **New queries** → Always start with query_analyzer
2. **Clarification needed** → Stay with query_analyzer until resolved
3. **Information needed** → Route to rag agent for local knowledge, search agent for web information
4. **Calculations/tools needed** → Route to mcp agent
5. **Task complete** → Use FINISH

Consider:
- Current workflow stage
- Whether clarification is needed/pending
- Type of task (informational vs computational)
- Previous agent results

Respond with the next agent name or FINISH."""

    def process(self, state: AgentState) -> Dict[str, Any]:
        """Make supervisor decision for next agent based on rules."""
        try:
            # Create a summary of the inputs used for the decision
            input_summary = {
                "workflow_stage": state.get("workflow_stage"),
                "clarification_needed": state.get("clarification_needed"),
                "user_responses_present": bool(state.get("user_responses")),
                "analysis_intent": state.get("analysis_results", {})
                .get("intent", {})
                .get("semantic_intent"),
            }

            decision = self._make_decision(state)
            logger.info(
                f"Supervisor decision: {decision.next_agent} (Reason: {decision.reasoning})"
            )

            output_dict = {
                "next_agent": decision.next_agent,
                "current_agent": "supervisor",
                "reasoning": decision.reasoning,
            }

            # If routing to RAG, include the final query in the output for display
            if decision.next_agent == "rag":
                final_query = state.get("analysis_results", {}).get("final_query")
                if final_query:
                    output_dict["final_query_for_rag"] = final_query

            # Add a cleaned summary of inputs to the output, removing None values for clarity
            output_dict["_input_summary"] = {
                k: v for k, v in input_summary.items() if v is not None
            }
            return output_dict

        except Exception as e:
            logger.error(f"Error in supervisor decision: {e}", exc_info=True)
            return {"next_agent": "FINISH", "current_agent": "supervisor"}

    def _make_decision(self, state: AgentState) -> SupervisorDecision:
        """
        Make the routing decision based on the current state using a rule-based approach.
        This method inspects the `workflow_stage` and other structured data in the state
        to determine the next agent, avoiding reliance on conversational history to prevent loops.
        """
        workflow_stage = state.get("workflow_stage", "initial")
        analysis_results = state.get("analysis_results")
        user_responses = state.get("user_responses")

        # Rule 1: Initial state -> always start with analysis
        if workflow_stage == "initial":
            return SupervisorDecision(
                next_agent="query_analyzer",
                reasoning="New query, starting analysis.",
                confidence=1.0,
            )

        # Rule 2: Handle clarification workflow
        if workflow_stage == "clarifying":
            if user_responses:
                # If user has responded, go back to analyzer to process the new info
                return SupervisorDecision(
                    next_agent="query_analyzer",
                    reasoning="User provided clarification, re-analyzing.",
                    confidence=1.0,
                )
            else:
                # If no response, we are waiting, so the workflow should pause.
                return SupervisorDecision(
                    next_agent="FINISH",
                    reasoning="Waiting for user clarification.",
                    confidence=1.0,
                )

        # Rule 3: Analysis is complete, route to the appropriate agent
        if workflow_stage == "analyzed" and analysis_results:
            intent = analysis_results.get("intent", {})

            # Check for tool requirements first
            if intent.get("requires_tools"):
                return SupervisorDecision(
                    next_agent="mcp",
                    reasoning="Analysis indicates tools are required.",
                    confidence=0.9,
                )

            # Default to search/rag for informational queries
            return SupervisorDecision(
                next_agent="rag",
                reasoning="Analysis complete, proceeding to information retrieval.",
                confidence=0.9,
            )

        # Rule 4: If a primary action agent has finished, the task is complete.
        if workflow_stage in [
            "retrieved",
            "processed",
            "searched",
            "complete",
            "rejected",
        ]:
            return SupervisorDecision(
                next_agent="FINISH",
                reasoning="Main task action is complete.",
                confidence=1.0,
            )

        # Fallback Rule: If no other rules match, end the workflow to prevent loops.
        logger.warning(
            f"Supervisor couldn't find a rule for stage '{workflow_stage}'. Ending workflow to prevent loops."
        )
        return SupervisorDecision(
            next_agent="FINISH",
            reasoning="Fallback: No specific rule matched the current state.",
            confidence=0.5,
        )

    def route_next(self, state: AgentState) -> str:
        """Route to the next agent based on supervisor decision.

        This method is used by LangGraph for conditional routing.
        """
        next_agent = state.get("next_agent", "FINISH")

        # Map FINISH to END for LangGraph
        if next_agent == "FINISH":
            return END

        return next_agent
