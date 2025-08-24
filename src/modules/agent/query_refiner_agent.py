"""Agent to build the final RAG query."""

import json
import logging
from typing import Dict, Optional

from langchain_core.prompts import ChatPromptTemplate

from ..utils.custom_openrouter import ChatOpenRouter

logger = logging.getLogger(__name__)


def _extract_json_from_content(content: str) -> Optional[Dict]:
    """Safely extracts a JSON object from a string, even with markdown code blocks."""
    try:
        if content.strip().startswith("```json"):
            content = content.strip()[7:-3].strip()
        elif content.strip().startswith("```"):
            content = content.strip()[3:-3].strip()
        return json.loads(content)
    except json.JSONDecodeError:
        logger.error(f"Could not decode JSON from content: {content}")
        return None


class QueryRefinerAgent:
    """
    Combines an action and a manual into a final, structured query for the RAG system.
    """

    def __init__(self, model_name: str = "meta-llama/llama-4-maverick"):
        self.llm = ChatOpenRouter(model_name=model_name, temperature=0.0)
        self.prompt = self._build_prompt()

    def _build_prompt(self) -> ChatPromptTemplate:
        system_prompt = """You are an expert assistant that creates a final, actionable query for a RAG system.

Your task is to combine a PERFORM ACT and a MANUAL into a single query string using the format below.

**FINAL QUERY FORMAT:**
"Give step by step procedure to {action} based on {manual}"

**RESPONSE FORMAT:**
You MUST respond with the following JSON format.
```json
{{
  "final_query": "The final, specific, and actionable query you generated."
}}
```
"""
        human_template = """PERFORM ACT: "{action}"
MANUAL: "{manual}"
"""
        return ChatPromptTemplate.from_messages(
            [("system", system_prompt), ("human", human_template)]
        )

    def process(self, action: str, manual: str) -> Dict:
        """
        Processes the action and manual to create a final query.

        Returns:
            A dictionary containing the 'final_query'.
        """
        logger.info(f"Refining query with action '{action}' and manual '{manual}'")
        chain = self.prompt | self.llm
        response = chain.invoke({"action": action, "manual": manual})
        logger.info(f"Query refiner LLM raw response: {response.content}")

        result = _extract_json_from_content(response.content)
        if result and "final_query" in result:
            return result

        logger.warning("Failed to parse query refiner response. Building manually.")
        return {
            "final_query": f"Give step by step procedure to {action} based on {manual}"
        }
