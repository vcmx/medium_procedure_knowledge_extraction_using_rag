"""Agent to extract the main action from a user query."""

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


class ActionExtractorAgent:
    """
    Analyzes a user query to extract the core action or task.
    """

    def __init__(self, model_name: str = "meta-llama/llama-4-maverick"):
        self.llm = ChatOpenRouter(model_name=model_name, temperature=0.0)
        self.prompt = self._build_prompt()

    def _build_prompt(self) -> ChatPromptTemplate:
        system_prompt = """You are a precision expert assistant. Your sole purpose is to extract the core task or action from a user's query.

You MUST remove conversational filler and phrases like "What is the step-by-step procedure for", "How do I", "Can you tell me how to", etc. The result should be a direct, concise command or description of the task.

**Example 1:**
- User Query: "Can you show me the procedure for replacing the spark plugs?"
- Extracted Action: "replacing the spark plugs"

**Example 2:**
- User Query: "installation and removal of timing belt cover"
- Extracted Action: "installation and removal of timing belt cover"

**RESPONSE FORMAT:**
You MUST respond with the following JSON format:
```json
{{
  "action": "The extracted concise action"
}}
```
"""
        human_template = 'User Query: "{query}"'
        return ChatPromptTemplate.from_messages(
            [("system", system_prompt), ("human", human_template)]
        )

    def process(self, query: str) -> Dict:
        """
        Processes the query to extract the main action.

        Returns:
            A dictionary containing the 'action'.
        """
        logger.info(f"Extracting action from query: '{query}'")
        chain = self.prompt | self.llm
        response = chain.invoke({"query": query})
        logger.info(f"Action extractor LLM raw response: {response.content}")

        result = _extract_json_from_content(response.content)
        if result and "action" in result:
            return result

        logger.warning("Failed to parse action extractor response. Using full query.")
        return {"action": query}
