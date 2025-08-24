"""Agent to check if a manual is specified in the user query."""

import json
import logging
from typing import Dict, List, Optional

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


class ManualCheckerAgent:
    """
    Analyzes a user query to determine if it explicitly refers to one of the
    available technical manuals.
    """

    def __init__(self, model_name: str = "meta-llama/llama-4-maverick"):
        self.llm = ChatOpenRouter(model_name=model_name, temperature=0.0)
        self.prompt = self._build_prompt()

    def _build_prompt(self) -> ChatPromptTemplate:
        system_prompt = """You are a specialized assistant responsible for checking if a user's query specifies a technical manual.

Your task is to analyze the user's query and determine if it explicitly mentions one of the manuals from the provided list.

AVAILABLE MANUALS:
{document_summaries}

---

**RESPONSE FORMAT:**

1.  **If the query CLEARLY specifies ONE manual from the list:**
    ```json
    {{
      "manual_specified": true,
      "manual_name": "The name of the specified manual"
    }}
    ```

2.  **If the query does NOT specify a manual or is ambiguous:**
    ```json
    {{
      "manual_specified": false,
      "manual_name": null
    }}
    ```

You MUST respond with a valid JSON object.
"""
        human_template = 'User Query: "{query}"'
        return ChatPromptTemplate.from_messages(
            [("system", system_prompt), ("human", human_template)]
        )

    def process(self, query: str, document_summaries: List[str]) -> Dict:
        """
        Processes the query to check for a specified manual.

        Returns:
            A dictionary containing 'manual_specified' (bool) and 'manual_name' (str or None).
        """
        logger.info(f"Checking for manual in query: '{query}'")
        chain = self.prompt | self.llm
        summaries_str = "\\n".join([f"- {s}" for s in document_summaries])

        response = chain.invoke({"query": query, "document_summaries": summaries_str})

        logger.info(f"Manual checker LLM raw response: {response.content}")

        result = _extract_json_from_content(response.content)
        if result:
            return result

        logger.warning(
            "Failed to parse manual checker response. Assuming manual not specified."
        )
        return {"manual_specified": False, "manual_name": None}
