import json
import logging
import os

from langchain_core.prompts import ChatPromptTemplate
from langchain_tavily import TavilySearch
from pydantic import BaseModel, Field

from src.modules.utils.custom_openrouter import ChatOpenRouter

logger = logging.getLogger(__name__)

# --- LLM and Prompt Configuration ---


# Define the output structure for the LLM using Pydantic V2
class WebSearchResult(BaseModel):
    summary: str = Field(
        default="",
        description="A concise, synthesized answer to the user's query based on the provided search results. The answer should be a paragraph, not a list.",
    )
    urls: list[str] = Field(
        default_factory=list,
        description="A list of the URLs of the most relevant search results used to generate the summary.",
    )


# Define the prompt for the LLM
PROMPT_TEMPLATE = """
Based on the following web search results, please provide a concise, synthesized answer to the user's query.
Do not just list the search results. Your answer should be a helpful, standalone paragraph.

User Query:
{query}

Search Results:
{results}
"""
prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)


class WebSearchAgent:
    def __init__(self, model_name: str, max_results: int = 3):
        """
        Initializes the WebSearchAgent.

        Args:
            model_name: The name of the LLM to use for summarization.
            max_results: The maximum number of search results to retrieve.
        """
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise ValueError(
                "Tavily API key not provided. Set the TAVILY_API_KEY environment variable."
            )

        self.search_tool = TavilySearch(
            api_key=api_key,
            max_results=max_results,
            search_depth="basic",
            include_answer=False,
            include_raw_content=False,
            include_images=False,
        )
        self.llm = ChatOpenRouter(model_name=model_name).with_structured_output(
            WebSearchResult
        )

    def _get_chain(self):
        """Creates and returns the LangChain expression chain."""
        return prompt | self.llm

    def process(self, query: str) -> dict:
        """
        Performs a web search, then uses an LLM to summarize the results.

        Args:
            query: The user's search query.

        Returns:
            A dictionary containing the summarized answer and source URLs.
        """
        logger.info(f"Performing Tavily web search for: {query}")
        try:
            # 1. Get search results from Tavily
            raw_results = self.search_tool.invoke({"query": query})

            if not raw_results:
                return {"summary": "No web search results found.", "urls": []}

            # 2. Use LLM to summarize the results
            logger.info("Summarizing search results with LLM...")
            chain = self._get_chain()
            response = chain.invoke(
                {"query": query, "results": json.dumps(raw_results, indent=2)}
            )

            return {"summary": response.summary, "urls": response.urls}

        except Exception as e:
            logger.error(
                f"Error during web search and summarization: {e}", exc_info=True
            )
            return {"summary": f"An error occurred: {e}", "urls": []}
