import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Annotated, List, Optional, Literal, Any, Dict
from typing_extensions import TypedDict
import pprint

from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.tools import tool
from langchain_experimental.utilities import PythonREPL
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.types import Command
from langchain_core.messages import HumanMessage, trim_messages
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv
from llama_index.core import PromptTemplate
from llama_index.llms.openrouter import OpenRouter
from src.modules.embeddings.query_utils import QueryManager


# Load environment variables
load_dotenv(override=True)


# Configure logging
def setup_logging():
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"multiagent_rag_{timestamp}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# Global LLM for general agents (uses OpenAI)
openai_llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0,
    api_key=os.getenv("OPENAI_API_KEY"),
)

# Initialize tools
tavily_tool = TavilySearchResults(max_results=5)

@tool
def python_repl_tool(
    code: Annotated[str, "The python code to execute to generate your chart."],
):
    """Use this to execute python code. If you want to see the output of a value,
    you should print it out with `print(...)`. This is visible to the user."""
    try:
        repl = PythonREPL()
        result = repl.run(code)
    except BaseException as e:
        return f"Failed to execute. Error: {repr(e)}"
    return f"Successfully executed:\n```python\n{code}\n```\nStdout: {result}"


# RAG Query Engine Class
class MultimodalChromaRAGQueryEngine:
    """Query engine for multimodal RAG using ChromaDB."""

    def __init__(
        self,
        persist_directory: str = "./chroma_db",
        collection_name: str = "document_chunks",
        embedder_impl: str = "huggingface",
        embedding_kwargs: Optional[dict] = None,
        llm_model: Optional[str] = None,
        llm_api_key: Optional[str] = None,
    ):
        if QueryManager is None:
            raise ImportError("QueryManager not available. Please check your imports.")
            
        logger.info("Initializing MultimodalChromaRAGQueryEngine")
        
        self.persist_directory = persist_directory
        self.metadata_store_path = Path(self.persist_directory) / "metadata.json"
        self.metadata_store = {}
        
        # Load metadata store if exists
        if self.metadata_store_path.exists():
            logger.info(f"Loading metadata store from {self.metadata_store_path}")
            with open(self.metadata_store_path, "r") as f:
                self.metadata_store = json.load(f)
        else:
            logger.warning("Metadata store not found. Assuming OLD RAG format.")

        # Initialize query manager
        self.query_manager = QueryManager(
            persist_directory=persist_directory,
            collection_name=collection_name,
            embedder_impl=embedder_impl,
            embedding_kwargs=embedding_kwargs,
        )

        # Initialize LLM
        model_name = llm_model or os.getenv("SELECTED_LLM") or "meta-llama/llama-4-maverick"
        api_key = llm_api_key or os.getenv("OPENROUTER_API_KEY")
        
        self.llm = OpenRouter(
            model=model_name,
            api_key=api_key,
            temperature=0.7,
            max_tokens=1024,
            base_url="https://openrouter.ai/api/v1",
        )
        logger.info("Query engine initialization complete")

    def _format_document_context(self, result: Dict[str, Any], index: int) -> str:
        """Format a single document result with its metadata and images."""
        context_parts = [f"Document {index + 1} (Score: {result['score']:.3f}):"]

        metadata = result.get("metadata", {})
        if metadata:
            context_parts.append("\nMetadata:")
            if "title" in metadata:
                context_parts.append(f"Title: {metadata['title']}")
            if "page_number" in metadata:
                context_parts.append(f"Page: {metadata['page_number']}")
            if "section_level" in metadata:
                context_parts.append(f"Section Level: {metadata['section_level']}")

        context_parts.append(f"\nContent:\n{result['content']}")

        # Add image information if available
        if "image_paths" in metadata:
            image_paths = metadata["image_paths"]
            if isinstance(image_paths, str):
                try:
                    image_paths = json.loads(image_paths)
                except json.JSONDecodeError:
                    image_paths = [image_paths]
            elif not isinstance(image_paths, list):
                image_paths = [str(image_paths)]

            valid_image_paths = [
                img_path for img_path in image_paths 
                if isinstance(img_path, str) and os.path.exists(img_path)
            ]

            if valid_image_paths:
                context_parts.append("\nRelated Images:")
                for img_path in valid_image_paths:
                    context_parts.append(f"- {img_path}")

        return "\n".join(context_parts)

    def query(
        self,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[dict] = None,
        experience_years: int = 0,
        use_mmr: bool = True,
    ) -> dict:
        """Query the multimodal RAG system."""
        logger.info(f"Processing RAG query: {query}")

        # Retrieve relevant documents
        search_results = self.query_manager.search(
            query=query,
            n_results=n_results,
            filter_metadata=filter_metadata,
            use_mmr=use_mmr,
        )

        # Handle metadata store for new RAG format
        if self.metadata_store:
            for result in search_results:
                metadata = result.get("metadata", {})
                if (section_id := metadata.get("section_id")) and section_id in self.metadata_store:
                    section_data = self.metadata_store[section_id]
                    image_info = section_data.get("images", [])
                    image_paths = [
                        img[0] for img in image_info
                        if isinstance(img, (list, tuple)) and len(img) > 0
                    ]
                    if image_paths:
                        metadata["image_paths"] = image_paths

        # Prepare context
        context_str = "\n\n".join(
            self._format_document_context(result, i)
            for i, result in enumerate(search_results)
        )

        # Set experience level
        if experience_years < 3:
            audience_tag = "Beginner"
            tone_instruction = "Explain in simple, clear terms for a beginner. Avoid jargon."
        elif experience_years <= 5:
            audience_tag = "Novice"
            tone_instruction = "Assume intermediate knowledge. Use technical terms but explain complex ideas."
        else:
            audience_tag = "Advanced"
            tone_instruction = "User is advanced. Use concise, expert-level explanation."

        # Create prompt
        qa_prompt_tmpl = f"""User Experience Level: {audience_tag}

{tone_instruction}

Use the text/markdown information and image descriptions provided in the context below to answer the query.

---------------------
Context: {context_str}
---------------------

Given the context information and no prior knowledge, answer the query.
Explain where you got the answer from, and if there's any uncertainty in the answer.
If images are relevant to the answer, mention which images and what they show.

Query: {query}
Answer: """

        # Get response from LLM
        response = self.llm.complete(prompt=qa_prompt_tmpl)

        # Collect relevant images
        relevant_images = set()
        for res_dict in search_results:
            chroma_meta = res_dict.get("metadata", {})
            image_paths = chroma_meta.get("image_paths", [])

            if isinstance(image_paths, str):
                try:
                    image_paths = json.loads(image_paths)
                except json.JSONDecodeError:
                    image_paths = []

            if isinstance(image_paths, list):
                relevant_images.update(image_paths)

        return {
            "answer": str(response),
            "sources": search_results,
            "relevant_images": list(relevant_images),
        }


# Global RAG engine storage - using a class to avoid issues with tool attributes
class RAGEngineManager:
    def __init__(self):
        self._engine = None
    
    def set_engine(self, engine):
        self._engine = engine
    
    def get_engine(self):
        return self._engine
    
    def is_configured(self):
        return self._engine is not None

# Global instance
rag_manager = RAGEngineManager()


# RAG Agent Tool - completely rewritten to avoid any attribute assignment issues
@tool
def rag_query_tool(
    query: Annotated[str, "The query to search in the RAG knowledge base"],
    n_results: Annotated[int, "Number of results to retrieve"] = 5,
    experience_years: Annotated[int, "User experience level in years"] = 0,
) -> str:
    """Search the RAG knowledge base for relevant information."""
    try:
        # Get RAG engine from global manager
        rag_engine = rag_manager.get_engine()
        if rag_engine is None:
            return "RAG engine not configured. Please configure RAG in the sidebar first."
        
        result = rag_engine.query(
            query=query,
            n_results=n_results,
            experience_years=experience_years,
        )
        
        # Format the response for the agent
        formatted_response = f"RAG Answer: {result['answer']}\n\n"
        if result['sources']:
            formatted_response += "Sources:\n"
            for i, source in enumerate(result['sources'][:3], 1):  # Limit to top 3 sources
                metadata = source.get('metadata', {})
                title = metadata.get('title', 'Unknown')
                page = metadata.get('page_number', 'Unknown')
                formatted_response += f"- Source {i}: {title} (Page {page}) - Score: {source['score']:.3f}\n"
        
        if result['relevant_images']:
            formatted_response += f"\nRelevant Images: {len(result['relevant_images'])} images found\n"
        
        return formatted_response
        
    except Exception as e:
        logger.error(f"RAG query error: {e}", exc_info=True)
        return f"RAG search failed: {str(e)}"


# State definition
class State(MessagesState):
    next: str
    rag_config: Optional[Dict[str, Any]] = None


# Create agents
search_agent = create_react_agent(openai_llm, tools=[tavily_tool])
coder_agent = create_react_agent(openai_llm, tools=[python_repl_tool])
rag_agent = create_react_agent(openai_llm, tools=[rag_query_tool])


# Supervisor node
def make_supervisor_node(llm: BaseChatModel, members: list[str]):
    options = ["FINISH"] + members
    system_prompt = (
        "You are a supervisor responsible for coordinating the following specialized agents: "
        f"{', '.join(members)}. Your job is to decide which agent should handle the next step "
        "based on the user's request and the current conversation context.\n\n"
        "Each agent has a unique role:\n"
        "- **rag**: Retrieves and synthesizes information from a local knowledge base (technical manuals, documents).\n"
        "- **search**: Gathers up-to-date information from the internet using web search.\n"
        "- **coder**: Writes, executes, or explains code based on the request.\n\n"
        "Instructions:\n"
        "- Always explain your reasoning before making a decision.\n"
        "- End your response with a single line like: `Action: rag`, `Action: search`, or `Action: coder`\n"
        "- Use `Action: FINISH` only when the task is fully complete.\n\n"
        "Example:\n"
        "The user asked for Python code to visualize climate trends. This is clearly a programming task.\n"
        "Action: coder"
    )

    class Router(TypedDict):
        next: Literal[*options]

    def supervisor_node(state: State) -> Command[Literal[*members, "__end__"]]:
            messages = [{"role": "system", "content": system_prompt}] + state["messages"]

            # Get full model output for reasoning display
            raw_response = llm.invoke(messages)

            # Parse structured output to get the target agent
            parsed_response = llm.with_structured_output(Router).invoke(messages)
            goto = parsed_response["next"]
            if goto == "FINISH":
                goto = END

            # ✅ This is the critical part that enables reasoning display:
            state["messages"].append({
                "role": "assistant",
                "name": "supervisor",
                "content": raw_response.content  # Show reasoning
            })
            print("\n[Supervisor Reasoning Message]")
            pprint.pprint(state["messages"][-1])
            return Command(
                goto=goto,
                update={
                    "next": goto,
                    "messages": state["messages"]  # This ensures supervisor message is emitted into the step
                }
            )
    
    return supervisor_node



# Node functions
def search_node(state: State) -> Command[Literal["supervisor"]]:
    result = search_agent.invoke(state)
    return Command(
        update={
            "messages": [
                HumanMessage(content=result["messages"][-1].content, name="search")
            ]
        },
        goto="supervisor",
    )


def coder_node(state: State) -> Command[Literal["supervisor"]]:
    result = coder_agent.invoke(state)
    return Command(
        update={
            "messages": [
                HumanMessage(content=result["messages"][-1].content, name="coder")
            ]
        },
        goto="supervisor",
    )


def rag_node(state: State) -> Command[Literal["supervisor"]]:
    result = rag_agent.invoke(state)
    return Command(
        update={
            "messages": [
                HumanMessage(content=result["messages"][-1].content, name="rag")
            ]
        },
        goto="supervisor",
    )


# Build the graph
members = ["search", "coder", "rag"]
supervisor_node = make_supervisor_node(openai_llm, members)

research_builder = StateGraph(State)
research_builder.add_node("supervisor", supervisor_node)
research_builder.add_node("search", search_node)
research_builder.add_node("coder", coder_node)
research_builder.add_node("rag", rag_node)
research_builder.add_edge(START, "supervisor")
research_builder.add_edge("search", "supervisor")
research_builder.add_edge("coder", "supervisor")
research_builder.add_edge("rag", "supervisor")

research_graph = research_builder.compile()


# Function to set RAG configuration - completely rewritten
def set_rag_config(
    persist_directory: str = "./chroma_db",
    collection_name: str = "document_chunks",
    embedder_impl: str = "huggingface",
    llm_model: Optional[str] = None,
):
    """Configure the RAG engine for the multi-agent system."""
    try:
        logger.info(f"Configuring RAG with directory: {persist_directory}")
        rag_engine = MultimodalChromaRAGQueryEngine(
            persist_directory=persist_directory,
            collection_name=collection_name,
            embedder_impl=embedder_impl,
            llm_model=llm_model,
        )
        rag_manager.set_engine(rag_engine)
        logger.info(f"RAG engine successfully configured with directory: {persist_directory}")
        return True
    except Exception as e:
        logger.error(f"Failed to configure RAG engine: {e}", exc_info=True)
        return False


# Function to check if RAG is configured
def is_rag_configured():
    """Check if RAG is properly configured."""
    return rag_manager.is_configured()


# Function to get RAG engine directly (for direct RAG chat mode)
def get_rag_engine():
    """Get the RAG engine for direct use."""
    return rag_manager.get_engine()


if __name__ == "__main__":
    print("Multi-Agent Research Graph with RAG initialized!")
    
    # Test the system
    test_input = {
        "messages": [HumanMessage(content="Can you search for recent AI developments and also generate a simple Python chart?")]
    }
    
    for s in research_graph.stream(test_input):
        print("State update:", s)