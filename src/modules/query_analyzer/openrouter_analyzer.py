"""
A simplified, direct OpenRouter-based implementation of the query analyzer.
This version focuses on a clear, three-step process:
1. Clean the user's query.
2. If the query's document context is ambiguous, ask for clarification.
3. Once clarified, rephrase the query to be specific and actionable for the RAG agent.
"""

import json
import logging
from typing import Dict, List, Optional

from langchain_core.prompts import ChatPromptTemplate

from ..utils.custom_openrouter import ChatOpenRouter
from .base import BaseQueryAnalyzer, QueryIntent
from .models import QueryAnalyzerConfig, QueryType

logger = logging.getLogger(__name__)


class OpenRouterQueryAnalyzer(BaseQueryAnalyzer):
    """A streamlined query analyzer using OpenRouter."""

    def __init__(self, config: Optional[QueryAnalyzerConfig] = None):
        """Initializes the simplified analyzer."""
        self.config = config or QueryAnalyzerConfig()
        try:
            from langchain_core.prompts import ChatPromptTemplate
        except ImportError:
            raise ImportError("Langchain core components not installed.")

        self.llm = ChatOpenRouter(
            model=self.config.model_name,
            model_kwargs={"temperature": self.config.temperature},
        )
        self.prompt_template = self._build_prompt()

    def _build_prompt(self) -> "ChatPromptTemplate":
        """Builds the single, streamlined prompt for the analyzer."""
        system_prompt = """You are an expert assistant that refines user queries for a RAG (Retrieval-Augmented Generation) system.
Your goal is to ensure every query is clean, unambiguous, and ready for efficient retrieval from a specific technical manual.

AVAILABLE MANUALS:
{document_summaries}

Your task is to follow a clear, three-step process:

STEP 1: CLEAN THE QUERY
- Correct any spelling mistakes.
- Fix grammatical errors.
- Rephrase for clarity and conciseness.
This produces the 'improved_query'.

STEP 2: CHECK FOR AMBIGUITY
- Examine the 'improved_query' and the list of AVAILABLE MANUALS.
- If the query is generic and could apply to more than one manual, you MUST ask for clarification.
- Your clarification question should be a single, direct question asking the user to choose a manual.

STEP 3: FINALIZE THE QUERY
- If clarification was NOT needed (the query was already specific), rephrase the 'improved_query' to be a direct instruction for the RAG agent.
- If clarification WAS needed and the user has provided a response (the 'user_response'), incorporate it to create a final, specific query.
- The final query should explicitly mention the target document.

**RESPONSE FORMAT**

You MUST respond in one of two JSON formats.

1.  If clarification is needed:
    ```json
    {{
      "clarification_needed": true,
      "question_to_user": "Your single question to the user.",
      "improved_query": "The cleaned-up version of the user's query."
    }}
    ```

2.  If the query is clear and ready for the RAG agent:
    ```json
    {{
      "clarification_needed": false,
      "final_query": "The final, specific, and actionable query for the RAG agent."
    }}
    ```

**IMPORTANT RULES:**
- Always respond with a valid JSON object.
- Do not add any explanations or conversational text outside the JSON.
- If no document summaries are available, assume the query is clear and proceed to generate the final query.
"""
        human_template = """
User Query: "{query}"
User Response to Clarification: {user_response}
"""
        return ChatPromptTemplate.from_messages(
            [("system", system_prompt), ("human", human_template)]
        )

    def clarify_and_refine(
        self,
        query: str,
        document_summaries: Optional[List[str]] = None,
        user_responses: Optional[Dict[str, str]] = None,
    ) -> QueryIntent:
        """
        Processes the user's query to clean it, ask for clarification if needed,
        and produce a final, actionable query for the RAG agent.
        """
        if not document_summaries:
            document_summaries = ["No specific manuals available."]

        summaries_str = "\n".join([f"- {s}" for s in document_summaries])

        # If user responses exist, we only need the first one.
        response_str = "N/A"
        if user_responses:
            response_str = next(iter(user_responses.values()), "N/A")

        chain = self.prompt_template | self.llm
        response = chain.invoke(
            {
                "query": query,
                "document_summaries": summaries_str,
                "user_response": response_str,
            }
        )
        logger.info(f"Analyzer LLM raw response: {response.content}")

        try:
            content = self._extract_json_from_content(response.content)

            if content.get("clarification_needed"):
                intent = QueryIntent(
                    query_type=QueryType.FACTUAL,
                    semantic_intent=content.get("improved_query", query),
                    final_query=None,
                    clarifying_questions=[content.get("question_to_user")],
                )
            else:
                final_query = content.get("final_query")
                intent = QueryIntent(
                    query_type=QueryType.FACTUAL,
                    semantic_intent=final_query,
                    final_query=final_query,
                )

            logger.info(f"Successfully created QueryIntent: {intent}")
            return intent

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(
                f"Failed to parse LLM response or find key: {e}\\nResponse: {response.content}"
            )
            # Fallback: just use the original query
            intent = QueryIntent(
                query_type=QueryType.FACTUAL,
                semantic_intent=query,
                final_query=query,
            )
            logger.warning(f"Returning fallback QueryIntent: {intent}")
            return intent

    def get_retrieval_queries(self, query: str) -> List[str]:
        """
        Runs the full clarification and refinement process and returns the
        single, final query suitable for retrieval.
        """
        intent = self.clarify_and_refine(query)
        return [intent.final_query]

    def _extract_json_from_content(self, content: str) -> dict:
        """Safely extracts a JSON object from a string, even with markdown code blocks."""
        try:
            # Handle markdown code blocks
            if content.strip().startswith("```json"):
                content = content.strip()[7:-3].strip()
            elif content.strip().startswith("```"):
                content = content.strip()[3:-3].strip()
            return json.loads(content)
        except json.JSONDecodeError:
            logger.error(f"Could not decode JSON from content: {content}")
            raise

    def analyze(self, query: str) -> QueryIntent:
        """DEPRECATED: Use clarify_and_refine instead."""
        logger.warning(
            "The 'analyze' method is deprecated and now calls 'clarify_and_refine'."
        )
        return self.clarify_and_refine(query)

    def set_query_engine(self, query_engine: any):
        """This analyzer does not require a query engine directly."""
        pass
