"""
The Supervisor Agent for the simplified, deterministic workflow.
"""

import asyncio
import functools
import logging

from src.modules.agent.action_extractor_agent import ActionExtractorAgent
from src.modules.agent.inventory_check_agent import InventoryCheckAgent
from src.modules.agent.manual_checker_agent import ManualCheckerAgent
from src.modules.agent.query_classifier_agent import QueryClassifierAgent
from src.modules.agent.query_refiner_agent import QueryRefinerAgent
from src.modules.agent.simple_rag_agent import SimpleRAGAgent
from src.modules.agent.web_search_agent import WebSearchAgent
from src.modules.query_answering.rag_with_chroma import MultimodalChromaRAGQueryEngine

logger = logging.getLogger(__name__)


class SimpleSupervisorAgent:
    """
    Orchestrates the workflow between worker agents to process a user query.
    """

    def __init__(self, rag_engine: MultimodalChromaRAGQueryEngine, model_name: str):
        """
        Initializes the supervisor and all its worker agents.
        """
        self.rag_engine = rag_engine
        self.model_name = model_name

        # Initialize worker agents
        self.query_classifier = QueryClassifierAgent(model_name=model_name)
        self.inventory_check_agent = InventoryCheckAgent(model_name=model_name)
        self.web_searcher = WebSearchAgent(model_name=model_name)
        self.action_extractor = ActionExtractorAgent(model_name=model_name)
        self.manual_checker = ManualCheckerAgent(model_name=model_name)
        self.query_refiner = QueryRefinerAgent(model_name=model_name)
        self.rag_agent = SimpleRAGAgent(rag_engine=self.rag_engine)

        # Get the list of available manuals for clarification
        self.available_manuals = self.rag_engine.get_all_document_summaries()

    async def process_query(self, query: str, **kwargs):
        """
        Processes the user's initial query, step-by-step.
        This is an async generator that yields the result of each agent's work.
        """
        loop = asyncio.get_running_loop()

        # Step 1: Classify the user's query
        classification_result = await loop.run_in_executor(
            None, self.query_classifier.process, query
        )
        query_type = classification_result.get("query_type")
        yield {
            "agent": "Query Classifier",
            "output": classification_result,
        }

        if query_type == "general":
            search_results = await loop.run_in_executor(
                None, self.web_searcher.process, query
            )
            yield {
                "agent": "Web Searcher",
                "output": {
                    "status": "web_search_complete",
                    "summary": search_results.get("summary"),
                    "urls": search_results.get("urls"),
                },
                "is_final": True,
            }
            return

        if query_type == "inventory_check":
            inventory_results = await self.inventory_check_agent.process(query)
            yield {
                "agent": "Inventory Check",
                "output": inventory_results,
                "is_final": True,
            }
            return

        if query_type == "technical":
            # V1 WORKFLOW FOR TECHNICAL QUERIES
            logger.info("Query classified as 'technical'. Starting V1 workflow.")

            # Step 2: Extract the core action from the query
            action_result = await loop.run_in_executor(
                None, self.action_extractor.process, query
            )
            action = action_result.get("action", query)
            yield {
                "agent": "Action Extractor",
                "output": action_result,
            }

            # Step 3: Check which manual is being referenced
            manual_result = await loop.run_in_executor(
                None, self.manual_checker.process, query, self.available_manuals
            )
            yield {
                "agent": "Manual Checker",
                "output": manual_result,
            }

            # Step 4: Decide the next step based on whether the manual was found
            if manual_result.get("manual_specified"):
                manual = manual_result.get("manual_name")
                # The manual was found, so we can proceed directly to the end
                # We call the resume_with_clarification generator and yield its results
                async for step in self.resume_with_clarification(
                    action=action, selected_manual=manual, **kwargs
                ):
                    yield step
            else:
                # The manual was not found, we need to ask the user for clarification
                yield {
                    "agent": "Supervisor",
                    "output": {
                        "status": "clarification_needed",
                        "message": "Please select the relevant technical manual.",
                        "action": action,  # Pass the action along for the next step
                        "options": self.available_manuals,
                    },
                }

        elif query_type == "general":
            # V2 WORKFLOW FOR GENERAL QUERIES
            logger.info("Query classified as 'general'. Starting V2 workflow.")
            web_search_result = self.web_searcher.process(query)
            yield {
                "agent": "Web Searcher",
                "output": {
                    "status": "web_search_complete",
                    "summary": web_search_result.get("summary"),
                    "urls": web_search_result.get("urls"),
                },
                "is_final": True,
            }

        else:
            logger.error(f"Unknown query type: {query_type}. Cannot proceed.")
            yield {
                "agent": "Supervisor",
                "output": {
                    "status": "error",
                    "message": f"Could not determine the query type. Received: {query_type}",
                },
                "is_final": True,
            }

    async def resume_with_clarification(
        self, action: str, selected_manual: str, **kwargs
    ):
        """
        Resumes the workflow after the manual has been identified.
        This is an async generator that yields the final steps of the process.
        """
        loop = asyncio.get_running_loop()

        # Step 5: Refine the query using the identified action and manual
        refiner_result = await loop.run_in_executor(
            None, self.query_refiner.process, action, selected_manual
        )
        final_query = refiner_result.get("final_query")
        yield {
            "agent": "Query Refiner",
            "output": refiner_result,
        }

        if not final_query:
            yield {
                "agent": "Supervisor",
                "output": {
                    "status": "error",
                    "message": "Could not generate the final query.",
                },
            }
            return

        # Step 6: Execute the final query using the RAG agent
        # We run the synchronous RAG process in a separate thread to avoid blocking.
        # functools.partial is used to bake in the kwargs for run_in_executor.
        process_func = functools.partial(self.rag_agent.process, **kwargs)
        rag_result = await loop.run_in_executor(None, process_func, final_query)
        yield {
            "agent": "RAG",
            "output": rag_result,
            "is_final": True,  # Mark this as the final step
        }
