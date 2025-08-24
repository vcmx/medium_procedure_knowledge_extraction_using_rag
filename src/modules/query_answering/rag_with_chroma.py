import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from llama_index.core import PromptTemplate, StorageContext
from llama_index.core.llms import LLM
from llama_index.llms.openrouter import OpenRouter
from llama_index.retrievers.bm25 import BM25Retriever

from src.modules.embeddings.query_utils import QueryManager


# Configure logging
def setup_logging():
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Create a log file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"rag_query_{timestamp}.log"

    # Configure logging to both file and console
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
    )
    return logging.getLogger(__name__)


logger = setup_logging()

# Load environment variables, overriding any existing ones
load_dotenv(override=True)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# change MODEL to be model selected by user in st.session_state["selected_llm"] = selected_llm
# If not set, default to Llama 4 via OpenRouter
env_model = os.getenv("SELECTED_LLM")
if not env_model:
    logger.warning(
        "Environment variable SELECTED_LLM not set. Defaulting to Llama 4 via OpenRouter."
    )
MODEL = env_model or "meta-llama/llama-4-maverick"

# QA Prompt Template
QA_PROMPT_TMPL = """\
Use the text/markdown information and image descriptions provided in the context below to answer the query.

---------------------
Context: {context_str}
---------------------

Given the context information and no prior knowledge, answer the query.
Explain where you got the answer from, and if there's any uncertainty in the answer.
If images are relevant to the answer, mention which images and what they show.

Query: {query_str}
Answer: """

QA_PROMPT = PromptTemplate(QA_PROMPT_TMPL)


class MultimodalChromaRAGQueryEngine:
    """Query engine for multimodal RAG using ChromaDB."""

    def __init__(
        self,
        persist_directory: str = "./chroma_db",
        collection_name: str = "document_chunks",
        embedder_impl: str = "huggingface",
        embedding_kwargs: Optional[dict] = None,
        llm: Optional[LLM] = None,  # Accept a LlamaIndex LLM object
        llm_model: Optional[str] = MODEL,
        llm_api_key: Optional[str] = None,
    ):
        """
        Initialize the multimodal RAG query engine.

        Args:
            persist_directory: Directory where ChromaDB is stored
            collection_name: Name of the ChromaDB collection
            embedder_impl: Name of the embedding model to use.
            embedding_kwargs: Additional arguments for the embedding model.
            llm: Optional pre-configured LlamaIndex LLM object.
            llm_model: Name of the LLM model to use (if llm object is not provided).
            llm_api_key: API key for the LLM service.
        """
        logger.info("Initializing MultimodalChromaRAGQueryEngine")
        logger.info(f"Collection: {collection_name}")
        logger.info(f"Embedding implementation: {embedder_impl}")

        self.persist_directory = persist_directory
        self.metadata_store_path = Path(self.persist_directory) / "metadata.json"
        self.metadata_store = {}
        # --- NEW RAG (HYBRID) LOGIC ---
        # If a metadata.json file exists, it means the RAG was prepared with the
        # new hybrid pipeline. This file acts as a relational store for image paths,
        # mapping a section_id to its associated images. We load it here.
        if self.metadata_store_path.exists():
            logger.info(f"Loading metadata store from {self.metadata_store_path}")
            with open(self.metadata_store_path, "r") as f:
                self.metadata_store = json.load(f)
        else:
            logger.warning(
                f"Metadata store not found at {self.metadata_store_path}. "
                "Assuming OLD RAG format. Image paths must be in the chunk metadata directly."
            )

        # Initialize query manager for ChromaDB
        self.query_manager = QueryManager(
            persist_directory=persist_directory,
            collection_name=collection_name,
            embedder_impl=embedder_impl,
            embedding_kwargs=embedding_kwargs,
        )

        # --- BM25 Retriever Initialization ---
        self.bm25_retriever = None
        try:
            # BM25 is built on top of a docstore, which is persisted by the pipeline.
            # We try to load it here. If it fails, hybrid search will be disabled.
            storage_context = StorageContext.from_defaults(
                persist_dir=self.persist_directory
            )
            self.bm25_retriever = BM25Retriever.from_defaults(
                docstore=storage_context.docstore, similarity_top_k=5
            )
            logger.info("Successfully loaded BM25 retriever for hybrid search.")
        except Exception as e:
            logger.warning(
                f"Could not load BM25 retriever from '{self.persist_directory}'. "
                f"Hybrid search will be disabled. Error: {e}"
            )

        # Initialize LLM
        if llm:
            self.llm = llm
        else:
            self.llm = OpenRouter(
                model=llm_model or MODEL,
                api_key=llm_api_key or OPENROUTER_API_KEY,
                temperature=0.7,
                max_tokens=1024,
                base_url="https://openrouter.ai/api/v1",
            )
        logger.info("Query engine initialization complete")

    def get_all_document_summaries(self) -> list[str]:
        """
        Fetches the metadata for all documents in the ChromaDB collection
        and returns a unique list of document titles.

        This is used to provide context to the Query Analyzer agent.
        """
        return [
            "System4 Electronic Fuel Injection (MEFI)",
            "Caterpillar C18 Industrial Engine",
            "Subaru vehicles",
            "Perkins workshop manual for marine engine applications",
        ]

    def update_llm(self, llm: LLM):
        """Updates the LLM used by the query engine."""
        self.llm = llm
        logger.info(f"LLM updated to: {llm.model}")

    def _format_document_context(self, result: Dict[str, Any], index: int) -> str:
        """Format a single document result with its metadata and images."""
        # Start with the main content
        context_parts = [f"Document {index + 1} (Score: {result['score']:.3f}):"]

        # Add metadata information
        metadata = result.get("metadata", {})
        if metadata:
            context_parts.append("\nMetadata:")
            if "title" in metadata:
                context_parts.append(f"Title: {metadata['title']}")
            if "page_number" in metadata:
                context_parts.append(f"Page: {metadata['page_number']}")
            if "section_level" in metadata:
                context_parts.append(f"Section Level: {metadata['section_level']}")

        # Add the main content
        context_parts.append(f"\nContent:\n{result['content']}")

        # Add image information if available
        if "image_paths" in metadata:
            logger.info(
                f"Document {index + 1} image_paths type: {type(metadata['image_paths'])}"
            )
            logger.info(
                f"Document {index + 1} image_paths raw value: {metadata['image_paths']}"
            )

            # Ensure we're working with a list of strings
            image_paths = metadata["image_paths"]
            if isinstance(image_paths, str):
                logger.info(
                    f"Document {index + 1} image_paths is a string, attempting to parse as JSON"
                )
                # If it's a JSON string, parse it
                try:
                    image_paths = json.loads(image_paths)
                    logger.info(
                        f"Document {index + 1} successfully parsed JSON image_paths: {image_paths}"
                    )
                except json.JSONDecodeError as e:
                    logger.warning(
                        f"Document {index + 1} failed to parse JSON image_paths: {e}"
                    )
                    image_paths = [image_paths]
            elif not isinstance(image_paths, list):
                logger.warning(
                    f"Document {index + 1} image_paths is not a list, converting to list: {image_paths}"
                )
                image_paths = [str(image_paths)]

            # Validate and filter image paths
            valid_image_paths = []
            for img_path in image_paths:
                if not isinstance(img_path, str):
                    logger.warning(
                        f"Document {index + 1} contains non-string image path: {img_path}"
                    )
                    continue

                # Check if file exists
                if os.path.exists(img_path):
                    valid_image_paths.append(img_path)
                    logger.info(f"Document {index + 1} valid image path: {img_path}")
                else:
                    logger.warning(
                        f"Document {index + 1} image file not found: {img_path}"
                    )

            if valid_image_paths:
                context_parts.append("\nRelated Images:")
                logger.info(
                    f"Document {index + 1} contains {len(valid_image_paths)} valid images:"
                )
                for img_path in valid_image_paths:
                    context_parts.append(f"- {img_path}")
                    logger.info(f"  - {img_path}")
            else:
                logger.info(f"Document {index + 1} contains no valid images")
        else:
            logger.info(f"Document {index + 1} contains no image_paths in metadata")

        return "\n".join(context_parts)

    def query(
        self,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[dict] = None,
        experience_years: int = 0,  # allow users of different experience levels to query the system
        fusion_method: Optional[str] = None,
        use_mmr: bool = False,
        llm_model: Optional[str] = None,
    ) -> dict:
        """
        Query the multimodal RAG system.

        Args:
            query: The query string
            n_results: Number of relevant documents to retrieve
            filter_metadata: Optional metadata filters for the search
            experience_years: User experience level for tailoring response.
            fusion_method: The fusion method to use for hybrid search
            use_mmr: Whether to use MMR for reranking vector search results.
            llm_model: The LLM model to use for this specific query.

        Returns:
            Dictionary containing:
            - answer: The LLM's response
            - sources: List of source documents with their metadata and scores
            - relevant_images: List of image paths mentioned in the sources
        """
        logger.info(f"Processing query: {query}")
        logger.info(f"Requested {n_results} results")
        if filter_metadata:
            logger.info(f"Using metadata filters: {filter_metadata}")

        # If a specific LLM is requested for this query, update the engine's LLM
        if llm_model:
            logger.info(f"Using specified LLM for this query: {llm_model}")
            self.llm.model = llm_model

        # Retrieve relevant documents
        if fusion_method in ["interleave", "rrf"]:
            if not self.bm25_retriever:
                logger.warning(
                    f"Hybrid search with fusion method '{fusion_method}' was requested, "
                    "but BM25 retriever is not available. Falling back to vector-only search."
                )
                search_results = self.query_manager.search(
                    query=query,
                    n_results=n_results,
                    filter_metadata=filter_metadata,
                    use_mmr=use_mmr,
                )
            else:
                logger.info(
                    f"Performing hybrid search with fusion method: {fusion_method}."
                )

                # 1. Vector search
                vector_results = self.query_manager.search(
                    query=query,
                    n_results=n_results,
                    filter_metadata=filter_metadata,
                    use_mmr=False,
                )
                logger.info(
                    f"Retrieved {len(vector_results)} results from vector search."
                )

                # 2. BM25 keyword search
                bm25_nodes = self.bm25_retriever.retrieve(query)
                bm25_results = [
                    {
                        "content": node.node.get_content(),
                        "metadata": node.node.metadata,
                        "score": node.score,
                    }
                    for node in bm25_nodes
                ]
                logger.info(f"Retrieved {len(bm25_results)} results from BM25 search.")

                if fusion_method == "interleave":
                    # 3. Fuse results using interleaving
                    search_results = []
                    seen_content = set()
                    vec_idx, bm25_idx = 0, 0

                    while len(search_results) < n_results and (
                        vec_idx < len(vector_results) or bm25_idx < len(bm25_results)
                    ):
                        # Add from vector results if available
                        if vec_idx < len(vector_results):
                            res = vector_results[vec_idx]
                            if res["content"] not in seen_content:
                                search_results.append(res)
                                seen_content.add(res["content"])
                            vec_idx += 1

                        if len(search_results) >= n_results:
                            break

                        # Add from BM25 results if available
                        if bm25_idx < len(bm25_results):
                            res = bm25_results[bm25_idx]
                            if res["content"] not in seen_content:
                                search_results.append(res)
                                seen_content.add(res["content"])
                            bm25_idx += 1

                elif fusion_method == "rrf":
                    # 3. Fuse results using Reciprocal Rank Fusion (RRF)
                    k = 60  # RRF constant
                    rrf_scores = {}
                    all_results = {}  # Store full result objects by content

                    # Process vector results
                    for i, res in enumerate(vector_results):
                        content = res["content"]
                        if content not in rrf_scores:
                            rrf_scores[content] = 0
                            all_results[content] = res
                        rrf_scores[content] += 1 / (k + i + 1)  # i+1 for 1-based rank

                    # Process BM25 results
                    for i, res in enumerate(bm25_results):
                        content = res["content"]
                        if content not in rrf_scores:
                            rrf_scores[content] = 0
                            all_results[content] = res
                        rrf_scores[content] += 1 / (k + i + 1)  # i+1 for 1-based rank

                    # Sort all unique documents by their RRF score in descending order
                    sorted_content = sorted(
                        rrf_scores.keys(), key=lambda c: rrf_scores[c], reverse=True
                    )

                    # Create the final list of results, truncated to n_results
                    search_results = [
                        all_results[content] for content in sorted_content
                    ][:n_results]

        else:
            logger.info(f"Performing vector-only search (MMR: {use_mmr}).")
            # Fallback to vector search, respecting the `use_mmr` flag.
            search_results = self.query_manager.search(
                query=query,
                n_results=n_results,
                filter_metadata=filter_metadata,
                use_mmr=use_mmr,
            )

        # --- NEW RAG (HYBRID) LOGIC ---
        # This block augments search results for RAGs built with the new pipeline.
        # It only runs if a `metadata.json` file was loaded (i.e., self.metadata_store is not empty).
        # It uses the `section_id` from a search result to look up the full image
        # context and injects it into the metadata to ensure compatibility.
        if self.metadata_store:
            for result in search_results:
                metadata = result.get("metadata", {})
                # We can now safely assume self.metadata_store exists.
                # Use walrus operator to check for, get, and assign section_id in one go.
                if (
                    section_id := metadata.get("section_id")
                ) and section_id in self.metadata_store:
                    section_data = self.metadata_store[section_id]
                    image_info = section_data.get("images", [])
                    # image_info is a list of [path, caption]
                    image_paths = [
                        img[0]
                        for img in image_info
                        if isinstance(img, (list, tuple)) and len(img) > 0
                    ]
                    if image_paths:
                        # By injecting `image_paths` here, we make the new RAG's data
                        # structure compatible with the downstream logic, which expects
                        # this key. The OLD RAG structure would already have this key
                        # (though stored inefficiently).
                        metadata["image_paths"] = image_paths
                        logger.debug(
                            f"Injected {len(image_paths)} image paths for section_id {section_id}"
                        )

        logger.info(f"Retrieved {len(search_results)} documents")

        # Prepare context from retrieved documents
        context_str = "\n\n".join(
            self._format_document_context(result, i)
            for i, result in enumerate(search_results)
        )
        if experience_years < 3:
            audience_tag = "Beginner"
            tone_instruction = (
                "Explain the answer in simple, clear terms assuming the user is a beginner (less than 3 years of experience). "
                "Avoid jargon. Use analogies if possible."
            )
        elif experience_years <= 5:
            audience_tag = "Novice"
            tone_instruction = (
                "Assume the user has intermediate knowledge (3–5 years experience). "
                "Use technical terms where helpful, but explain complex ideas."
            )
        else:
            audience_tag = "Advanced"
            tone_instruction = (
                "The user is advanced (5+ years of experience). "
                "Use concise, expert-level explanation and include technical depth if needed."
            )

        # Format prompt with context and query
        prompt = (
            f"User Experience Level: {audience_tag}\n\n"
            f"{tone_instruction}\n\n"
            + QA_PROMPT.format(context_str=context_str, query_str=query)
        )

        # Get response from LLM
        logger.info("Sending prompt to LLM")
        response = self.llm.complete(prompt=prompt)
        logger.info("Received response from LLM")

        # --- UNIVERSAL LOGIC (WORKS FOR BOTH RAGS) ---
        # This part of the code now works for both OLD and NEW RAG structures.
        # - For the NEW RAG, `image_paths` was injected in the previous step.
        # - For the OLD RAG, `image_paths` was already present in the metadata.
        # This loop collects all unique image paths from the retrieved source
        # documents to be displayed in the UI's "Relevant Images" section.
        relevant_images = set()
        for res_dict in search_results:
            chroma_meta = res_dict.get("metadata", {})
            image_paths = chroma_meta.get("image_paths", [])

            # The `image_paths` could be a list or a JSON string (from older versions).
            if isinstance(image_paths, str):
                try:
                    image_paths = json.loads(image_paths)
                except json.JSONDecodeError:
                    logger.warning(
                        f"Could not parse image_paths JSON string: {image_paths}"
                    )
                    image_paths = []

            if isinstance(image_paths, list):
                relevant_images.update(image_paths)

        logger.info(
            f"Found {len(relevant_images)} unique relevant images overall to return."
        )
        if relevant_images:
            logger.info("Relevant images:")
            for img_path in sorted(relevant_images):  # Sort for consistent logging
                logger.info(f"  - {img_path}")
                if not os.path.exists(img_path):
                    logger.warning(f"    Image file not found: {img_path}")
        else:
            logger.info("No images found in the retrieved documents")

        return {
            "answer": str(response),
            "sources": search_results,
            "relevant_images": list(relevant_images),
        }


def main():
    # Example usage
    query_engine = MultimodalChromaRAGQueryEngine()

    # Example query
    query = "tell me which page or images are relevant if i want to remove camshaft sprocket"
    result = query_engine.query(query)

    # Print results
    print(f"\nQuery: {query}")
    print("\nAnswer:")
    print(result["answer"])

    print("\nSources:")
    for i, source in enumerate(result["sources"], 1):
        print(f"\nSource {i}:")
        print(f"Content: {source['content'][:200]}...")
        print(f"Metadata: {source['metadata']}")
        print(f"Score: {source['score']}")

    if result["relevant_images"]:
        print("\nRelevant Images:")
        for img_path in result["relevant_images"]:
            print(f"- {img_path}")


if __name__ == "__main__":
    main()
