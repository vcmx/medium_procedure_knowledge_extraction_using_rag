import json
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from llama_index.core import StorageContext, VectorStoreIndex, load_index_from_storage
from llama_index.core.base.response.schema import Response
from llama_index.core.prompts import PromptTemplate
from llama_index.core.query_engine import CustomQueryEngine
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import ImageNode, MetadataMode, NodeWithScore, TextNode
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openrouter import OpenRouter

# Load environment variables
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Constants
MODEL = "meta-llama/llama-4-maverick"  # Llama 4 via OpenRouter
PDF_FILE = "./your_pdf_file.pdf"  # Replace with your PDF file path
IMAGE_OUTPUT_DIR = "extracted_images"
USE_MARKER_JSON = True  # Flag to switch between parsing methods

# QA Prompt Template
QA_PROMPT_TMPL = """\
Use the text/markdown information provided in the context
below and the image provided.

---------------------
Context: {context_str}
---------------------
Given the context information and no prior knowledge, answer the query. Explain where you got the answer
from, and if there's discrepancies, and your reasoning for the final answer.

Query: {query_str}
Answer: """

QA_PROMPT = PromptTemplate(QA_PROMPT_TMPL)


def extract_page_num(block_id: str) -> int:
    """Extract page number from block ID."""
    # Block ID format: /page/{page_num}/...
    try:
        return int(block_id.split("/")[2])
    except (IndexError, ValueError):
        return 0


def extract_image_refs(block: Dict[str, Any]) -> List[tuple]:
    """
    Extract image references from a block.
    Returns a list of tuples (image_type, image_num) based on the block's images field.

    Example:
    {
        "id": "/page/49/Figure/21",
        "block_type": "Figure",
        "images": {
            "/page/49/Figure/21": "base64_encoded_image"
        }
    }
    """
    image_refs = []

    # Get the block's images dictionary
    images = block.get("images", {})

    # For each image in the block
    for img_id, _ in images.items():
        # Extract image type and number from the ID
        # Example ID: /page/49/Figure/21
        parts = img_id.split("/")
        if len(parts) >= 4:
            img_type = parts[3]  # e.g., "Figure"
            img_num = parts[4]  # e.g., "21"
            image_refs.append((img_type, img_num))

    return image_refs


def parse_pdf_with_marker_json(json_path: str) -> tuple[List[dict], List[dict]]:
    """
    Parse marker's JSON output file.
    Creates chunks based on content types while preserving section hierarchy.
    Returns a tuple of (text_nodes, image_nodes)
    """
    # Load the JSON file
    with open(json_path, "r") as f:
        json_str = f.read()
        # Handle potential double-encoded JSON
        try:
            pdf_data = json.loads(json_str)
        except json.JSONDecodeError:
            # If the first load fails, try loading the string itself
            pdf_data = json.loads(json.loads(json_str))

    # Ensure pdf_data is a dictionary with children
    if not isinstance(pdf_data, dict) or "children" not in pdf_data:
        raise ValueError(
            f"Expected JSON data to be a dictionary with 'children' key, got {type(pdf_data)}"
        )

    text_nodes = []
    image_nodes = []
    unknown_block_types = set()  # Track unknown block types

    # Define block types that should be chunked
    CONTENT_BLOCKS = {
        "Text",
        "Table",
        "Figure",
        "Code",
        "Equation",
        "Form",
        "ListItem",
        "TextInlineMath",
        "Caption",
    }

    # Define block types that are groups
    GROUP_BLOCKS = {"FigureGroup", "TableGroup", "ListGroup", "PictureGroup"}

    # Define block types that are structural elements
    STRUCTURAL_BLOCKS = {
        "Line",
        "Span",
        "Page",
        "Document",
        "PageFooter",
        "PageHeader",
        "Picture",
        "Footnote",
        "Handwriting",
        "SectionHeader",
        "TableOfContents",
        "Reference",
        "TableCell",
    }

    def process_block(block, parent_block_type=None):
        # Skip if block is None or doesn't have required fields
        if not block or not isinstance(block, dict):
            return

        block_type = block.get("block_type")
        if not block_type:
            return

        # Process content blocks
        if block_type in CONTENT_BLOCKS:
            page_num = extract_page_num(block["id"])

            # Create text node for this block
            text_nodes.append(
                {
                    "text": block["html"],
                    "metadata": {
                        "block_type": block_type,
                        "block_id": block["id"],
                        "page_num": page_num,
                        "section_hierarchy": block.get("section_hierarchy", {}),
                        "image_paths": [],
                        "parent_block_type": parent_block_type,
                    },
                }
            )

            # Handle images if this is a Figure or Picture block
            if block_type in ["Figure", "Picture"]:
                for img_type, img_num in extract_image_refs(block):
                    img_path = f"marker_output/markdown/13 subaru engine imp04_sec2_4-2/_page_{page_num}_{img_type}_{img_num}.jpeg"
                    if os.path.exists(img_path):
                        text_nodes[-1]["metadata"]["image_paths"].append(img_path)
                        image_nodes.append(
                            {
                                "path": img_path,
                                "page_number": page_num,
                                "block_id": block["id"],
                                "section_hierarchy": block.get("section_hierarchy", {}),
                            }
                        )

        # Process group blocks
        elif block_type in GROUP_BLOCKS:
            # Process children of group blocks
            if block.get("children"):
                for child in block["children"]:
                    process_block(child, block_type)

        # Process structural blocks
        elif block_type in STRUCTURAL_BLOCKS:
            # If the block has HTML content, create a chunk for it
            if block.get("html"):
                page_num = extract_page_num(block["id"])
                text_nodes.append(
                    {
                        "text": block["html"],
                        "metadata": {
                            "block_type": block_type,
                            "block_id": block["id"],
                            "page_num": page_num,
                            "section_hierarchy": block.get("section_hierarchy", {}),
                            "image_paths": [],
                            "parent_block_type": parent_block_type,
                        },
                    }
                )

            # Process children if they exist
            if block.get("children"):
                for child in block["children"]:
                    process_block(child, block_type)

        # Process unknown blocks
        else:
            unknown_block_types.add(block_type)
            print(f"Warning: Unknown block type encountered: {block_type}")

            # If the block has HTML content, create a chunk for it
            if block.get("html"):
                page_num = extract_page_num(block["id"])
                text_nodes.append(
                    {
                        "text": block["html"],
                        "metadata": {
                            "block_type": block_type,
                            "block_id": block["id"],
                            "page_num": page_num,
                            "section_hierarchy": block.get("section_hierarchy", {}),
                            "image_paths": [],
                            "is_unknown_type": True,  # Flag to indicate this was an unknown type
                            "parent_block_type": parent_block_type,
                        },
                    }
                )

            # Process children if they exist
            if block.get("children"):
                for child in block["children"]:
                    process_block(child, block_type)

    # Process all pages from the top-level children array
    for page in pdf_data["children"]:
        if page.get("block_type") == "Page":
            # Process the page's children
            if page.get("children"):
                for child in page["children"]:
                    process_block(child)

    # Print summary of unknown block types
    if unknown_block_types:
        print("\nSummary of unknown block types encountered:")
        for block_type in sorted(unknown_block_types):
            print(f"- {block_type}")

    return text_nodes, image_nodes


def parse_pdf_with_marker(pdf_path: str) -> tuple[List[dict], List[dict]]:
    """
    Main parsing function that uses either JSON or separate extraction based on USE_MARKER_JSON flag.
    """
    if USE_MARKER_JSON:
        # Use the JSON file from marker output
        json_path = "marker_output/json/13 subaru engine imp04_sec2_4-2/13 subaru engine imp04_sec2_4-2.json"
        return parse_pdf_with_marker_json(json_path)


def create_text_nodes(
    text_nodes: List[dict], image_nodes: List[dict]
) -> List[TextNode]:
    """Convert parsed text nodes into LlamaIndex TextNodes with image metadata."""
    nodes = []

    for node in text_nodes:
        # Create TextNode with all metadata
        llama_node = TextNode(text=node["text"], metadata=node.get("metadata", {}))
        nodes.append(llama_node)

    return nodes


class MultimodalQueryEngine(CustomQueryEngine):
    """Custom multimodal Query Engine."""

    qa_prompt: PromptTemplate
    retriever: BaseRetriever
    multi_modal_llm: OpenRouter

    def __init__(self, qa_prompt: Optional[PromptTemplate] = None, **kwargs) -> None:
        """Initialize."""
        super().__init__(qa_prompt=qa_prompt or QA_PROMPT, **kwargs)

    def custom_query(self, query_str: str):
        # retrieve text nodes
        nodes = self.retriever.retrieve(query_str)

        # create ImageNode items from text nodes
        image_nodes = [
            NodeWithScore(node=ImageNode(image_path=image_path))
            for n in nodes
            for image_path in n.metadata.get("image_paths", [])
        ]

        # create context string from text nodes
        context_str = "\n\n".join(
            [r.get_content(metadata_mode=MetadataMode.LLM) for r in nodes]
        )
        fmt_prompt = self.qa_prompt.format(context_str=context_str, query_str=query_str)

        # For OpenRouter, we need to include image information in the prompt
        if image_nodes:
            image_info = "\n\nImages referenced in the context:\n"
            for i, img_node in enumerate(image_nodes, 1):
                image_info += f"Image {i}: {img_node.node.image_path}\n"
            fmt_prompt += image_info

        # synthesize an answer from formatted text
        llm_response = self.multi_modal_llm.complete(prompt=fmt_prompt)

        return Response(
            response=str(llm_response),
            source_nodes=nodes,
            metadata={"text_nodes": nodes, "image_nodes": image_nodes},
        )


def main():
    # Initialize the embedding model for text
    vector_store_embedding = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")

    # Initialize the LLM
    llm_model = OpenRouter(
        model=MODEL,
        api_key=OPENROUTER_API_KEY,
        temperature=0.7,
        max_tokens=1024,
        base_url="https://openrouter.ai/api/v1",
    )

    # Parse PDF
    text_nodes, image_nodes = parse_pdf_with_marker(PDF_FILE)

    # Create LlamaIndex nodes
    nodes = create_text_nodes(text_nodes, image_nodes)

    # Build or load index
    index = None
    if not os.path.exists("storage_nodes"):
        index = VectorStoreIndex(nodes, embed_model=vector_store_embedding)
        # save index to disk
        index.set_index_id("vector_index")
        index.storage_context.persist("./storage_nodes")
    else:
        # rebuild storage context
        storage_context = StorageContext.from_defaults(persist_dir="storage_nodes")
        # load index
        index = load_index_from_storage(
            storage_context, index_id="vector_index", embed_model=vector_store_embedding
        )

    # Create query engine
    query_engine = MultimodalQueryEngine(
        retriever=index.as_retriever(similarity_top_k=5), multi_modal_llm=llm_model
    )

    # Example query
    # query = "What is the main topic of the document?"
    query = "tell me which page or images are relevant if i want to remove camshaft sprocket"
    response = query_engine.custom_query(query)
    print(f"Query: {query}")
    print(f"Response: {response}")


if __name__ == "__main__":
    main()
