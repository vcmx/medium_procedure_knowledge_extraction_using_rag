import logging
from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from src.modules.utils.custom_openrouter import ChatOpenRouter

logger = logging.getLogger(__name__)


class QueryType(BaseModel):
    """Categorizes the user's query."""

    query_type: Literal["technical", "general", "inventory_check"] = Field(
        description="The type of query. 'technical' for how-to questions about procedures, 'general' for conceptual questions, and 'inventory_check' for questions about tool availability."
    )


class QueryClassifierAgent:
    def __init__(self, model_name: str):
        self.llm = ChatOpenRouter(model_name=model_name).with_structured_output(
            QueryType
        )
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a query classifier. Your task is to analyze the user's query and classify it into one of three categories:\n"
                    "- 'technical': The query asks for instructions or a 'how-to' guide on performing a specific task (e.g., 'how to remove a timing belt').\n"
                    "- 'general': The query is a general or conceptual question (e.g., 'what is a timing belt?', 'who are you?').\n"
                    "- 'inventory_check': The query asks about the availability, stock, or location of a specific tool (e.g., 'do we have a torque wrench?', 'is there a 10mm socket available?').",
                ),
                ("user", "Query: {query}"),
            ]
        )
        self.chain = self.prompt | self.llm

    def process(self, query: str) -> dict:
        """
        Classifies the user query using an LLM.

        Args:
            query: The user's input query.

        Returns:
            A dictionary with the key 'query_type' set to 'technical', 'general', or 'inventory_check'.
        """
        logger.info(f"Classifying query: '{query}'")
        try:
            result = self.chain.invoke({"query": query})
            logger.info(f"LLM classified query as: {result.query_type}")
            return {"query_type": result.query_type}
        except Exception as e:
            logger.error(f"Error during query classification: {e}", exc_info=True)
            # Fallback to a default value in case of an error
            return {"query_type": "general"}
