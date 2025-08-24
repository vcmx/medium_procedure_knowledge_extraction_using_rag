"""
Tavily Search Agent for web information retrieval.
"""

import logging
import os
from typing import Any, Dict, List, Literal, Optional

from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.messages import AIMessage, HumanMessage
from langchain_ollama import ChatOllama
from langgraph.types import Command

from .base import AgentState, AgentType

logger = logging.getLogger(__name__)


class SearchAgent:
    """Agent that performs web searches using Tavily API.

    This agent is responsible for:
    - Searching the web for current information
    - Gathering real-time data and news
    - Finding information not available in local knowledge base
    """

    def __init__(
        self,
        llm: Optional[ChatOllama] = None,
        tavily_api_key: Optional[str] = None,
        max_results: int = 5,
        search_depth: str = "advanced",
    ):
        """Initialize the Search Agent.

        Args:
            llm: Language model for processing search results
            tavily_api_key: Tavily API key (defaults to TAVILY_API_KEY env var)
            max_results: Maximum number of search results to return
            search_depth: Search depth ("basic" or "advanced")
        """
        self.llm = llm or ChatOllama(model="llama3.2", temperature=0)

        # Get API key from parameter or environment
        api_key = tavily_api_key or os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise ValueError(
                "Tavily API key not provided. Set TAVILY_API_KEY environment variable "
                "or pass tavily_api_key parameter."
            )

        # Initialize Tavily search tool
        self.search_tool = TavilySearchResults(
            api_key=api_key,
            max_results=max_results,
            search_depth=search_depth,
            include_answer=True,
            include_raw_content=False,
            include_images=False,
        )

        self.name = AgentType.SEARCH.value
        logger.info(f"Initialized SearchAgent with max_results={max_results}")

    def process(self, state: AgentState) -> Command[Literal["supervisor"]]:
        """Process the current state and perform web search.

        Args:
            state: Current agent state

        Returns:
            Command object with updated state
        """
        try:
            # Get the latest message for search query
            query = state.get("analysis_results", {}).get("final_query") or state.get(
                "messages", [{}]
            )[-1].get("content")
            if not query:
                raise ValueError("No search query found in the current state.")

            input_summary = {"query": query}
            logger.info(f"Performing web search for: {query}")

            # Perform the search
            search_results = self.search_tool.invoke({"query": query})

            # Format search results
            response_message = self._create_response_message(query, search_results)

            update_dict = {
                "messages": [AIMessage(content=response_message, name="search")],
                "workflow_stage": "searched",
                "_input_summary": input_summary,
                "analysis_results": {
                    **state.get("analysis_results", {}),
                    "search_results": search_results,
                },
            }

            return Command(update=update_dict, goto="supervisor")

        except Exception as e:
            logger.error(f"Error in search agent: {str(e)}", exc_info=True)
            return Command(
                update={
                    "messages": [
                        AIMessage(
                            content=f"I encountered an error while searching: {str(e)}",
                            name="search",
                        )
                    ],
                    "workflow_stage": "error",
                },
                goto="supervisor",
            )

    def _format_search_results(self, results: List[Dict[str, Any]]) -> str:
        """Format search results for presentation.

        Args:
            results: Raw search results from Tavily

        Returns:
            Formatted string of search results
        """
        if not results:
            return ""

        formatted = []
        for i, result in enumerate(results, 1):
            formatted.append(f"{i}. **{result.get('title', 'No title')}**")
            formatted.append(f"   URL: {result.get('url', 'No URL')}")
            formatted.append(f"   {result.get('content', 'No content')}")
            formatted.append("")

        return "\n".join(formatted)

    def _create_response_message(self, query: str, results: List[Dict]) -> str:
        """Create a response message with search results.

        Args:
            query: Original search query
            results: Raw search results from Tavily

        Returns:
            Complete response message
        """
        if not results:
            return "No search results found."

        formatted_results = self._format_search_results(results)

        prompt = f"""Based on the search query: "{query}"

Here are the search results:

{formatted_results}

Please provide a concise summary of the key findings from these search results."""

        # Use LLM to summarize the results
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            summary = response.content
        except Exception as e:
            logger.warning(f"Failed to summarize with LLM: {e}")
            summary = formatted_results

        return f"## Web Search Results\n\n{summary}"
