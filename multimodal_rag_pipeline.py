import hashlib
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from llama_index.core import StorageContext
from llama_index.core.schema import Document as LlamaDocument
from llama_index.retrievers.bm25 import BM25Retriever

from src.modules.embeddings.factory import EmbedderFactory
from src.modules.image_processor.factory import ImageProcessorFactory
from src.modules.pdf_processor.processor import ExtractedContent, PDFProcessor, Section
from src.modules.semantic_chunker.chunker import TextProcessor
from src.modules.storage_manager import ChunkMetadata, StorageManagerFactory

logger = logging.getLogger(__name__)


# Helper function to load content from a pre-processed directory
def _load_content_from_pre_processed_dir(
    pre_processed_dir_path: Path,
) -> ExtractedContent:
    logger.info(
        f"Loading content from pre-processed directory: {pre_processed_dir_path}"
    )
    markdown_files = list(pre_processed_dir_path.glob("*.md"))
    if not markdown_files:
        raise FileNotFoundError(f"No markdown file found in {pre_processed_dir_path}")
    if len(markdown_files) > 1:
        logger.warning(
            f"Multiple markdown files found in {pre_processed_dir_path}, using {markdown_files[0]}"
        )
    markdown_file_path = markdown_files[0]

    with open(markdown_file_path, "r", encoding="utf-8") as f:
        markdown_content = f.read()
    logger.info(f"Loaded markdown from {markdown_file_path}")

    # Create a map of image filenames to their full paths for quick lookup
    image_path_map: Dict[str, Path] = {}
    image_extensions = ["*.jpeg", "*.jpg", "*.png", "*.gif", "*.bmp"]
    all_image_files = []
    for ext in image_extensions:
        all_image_files.extend(pre_processed_dir_path.glob(ext))

    logger.info(
        f"Found {len(all_image_files)} potential image files in {pre_processed_dir_path}"
    )
    for img_file in all_image_files:
        image_path_map[img_file.name] = img_file.resolve()
    logger.info(
        f"DEBUG: Image path map created: {json.dumps({k: str(v) for k, v in image_path_map.items()}, indent=2)}"
    )

    sections: List[Section] = []
    current_section_details: Optional[Dict] = None
    current_content_lines: List[str] = []
    current_page_for_section: int = 1
    page_separator = "-" * 48

    def create_section(details, content_lines, page_num):
        section_content = "\n".join(content_lines).strip()
        logger.info(
            f"DEBUG: Creating section '{details['title']}' with content:\n---\n{section_content[:500]}...\n---"
        )

        # Find all image references in the content of this section
        section_images = []
        image_tags = re.findall(r"!\[.*?\]\((.*?)\)", section_content)
        logger.info(
            f"DEBUG: Found image tags in section '{details['title']}': {image_tags}"
        )

        for img_filename in image_tags:
            img_basename = Path(img_filename).name
            logger.info(
                f"DEBUG: Checking for image basename '{img_basename}' in image_path_map."
            )
            if img_basename in image_path_map:
                logger.info(
                    f"DEBUG: Found '{img_basename}'! Adding path '{image_path_map[img_basename]}' to section."
                )
                section_images.append((image_path_map[img_basename], ""))
            else:
                logger.warning(
                    f"Image '{img_basename}' referenced in markdown but not found in directory."
                )

        return Section(
            title=details["title"],
            level=details["level"],
            content=section_content,
            images=list(set(section_images)),
            page_number=details.get("page", page_num),
        )

    for line in markdown_content.splitlines():
        stripped_line = line.strip()
        page_marker_match = re.match(
            r"^{(\d+)}" + re.escape(page_separator) + r"$", stripped_line
        )

        if stripped_line.startswith("#"):
            if current_section_details:
                sections.append(
                    create_section(
                        current_section_details,
                        current_content_lines,
                        current_page_for_section,
                    )
                )

            level = len(stripped_line.split(" ")[0])
            title = stripped_line.lstrip("#").strip()
            current_section_details = {
                "title": title,
                "level": level,
                "page": current_page_for_section,
            }
            current_content_lines = []

        elif page_marker_match:
            try:
                page_num_str = page_marker_match.group(1)
                current_page_for_section = int(page_num_str)
                logger.debug(
                    f"Encountered page marker for page {current_page_for_section}"
                )
                if current_section_details:
                    current_section_details["page"] = current_page_for_section
            except (IndexError, ValueError) as e:
                logger.warning(
                    f"Could not parse page number from marker: {stripped_line}. Error: {e}"
                )

        elif current_section_details is not None:
            current_content_lines.append(line)

    if current_section_details:
        sections.append(
            create_section(
                current_section_details, current_content_lines, current_page_for_section
            )
        )

    logger.info(f"Parsed {len(sections)} sections from markdown and image directory.")
    return ExtractedContent(sections=sections, metadata={}, document_summary=None)


def run_pipeline(
    pdf_path: Optional[str] = None,
    pre_processed_dir: Optional[str] = None,
    output_path: str = "output",
    storage_path: str = "rag_storage",
    document_summary: Optional[str] = None,
    storage_backend: str = "chroma",
    image_processor_impl: str = "local",
    embedder_impl: str = "local",
    image_processor_kwargs: Optional[dict] = None,
    embedder_kwargs: Optional[dict] = None,
):
    """
    Main pipeline for processing a PDF and storing its content.
    """
    if not pdf_path and not pre_processed_dir:
        raise ValueError("Provide either pdf_path or pre_processed_dir.")

    image_processor_kwargs = image_processor_kwargs or {}
    embedder_kwargs = embedder_kwargs or {}

    logger.info("Starting pipeline processing.")

    # 1. Initialize Embedder and get its dimension
    logger.info(f"Initializing embedder '{embedder_impl}' to determine dimension.")
    embedder = EmbedderFactory.create(implementation=embedder_impl, **embedder_kwargs)
    try:
        dummy_embedding = embedder.embed_text("test")
        embedding_dim = dummy_embedding.shape[0]
        logger.info(f"Determined embedding dimension: {embedding_dim}")
    except Exception as e:
        logger.error(f"Failed to initialize embedder or get dimension: {e}")
        raise

    # 2. Setup paths and load/create manifest
    storage_path_obj = Path(storage_path)
    storage_path_obj.mkdir(parents=True, exist_ok=True)
    manifest_path = storage_path_obj / "manifest.json"

    if manifest_path.exists():
        logger.info(f"Loading existing manifest from {manifest_path}")
        with open(manifest_path, "r") as f:
            manifest = json.load(f)

        # VALIDATION: Ensure the new embedding config matches the manifest
        if manifest["embedder_details"]["dimension"] != embedding_dim:
            raise ValueError(
                f"Dimension mismatch: The existing database expects dimension "
                f"{manifest['embedder_details']['dimension']}, but the current "
                f"configuration uses dimension {embedding_dim}. "
                "If this is intentional, wipe the database first."
            )
        manifest["last_updated"] = datetime.utcnow().isoformat()
    else:
        logger.info("No existing manifest found. Creating a new one.")
        manifest = {
            "creation_date": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat(),
            "embedder_details": {
                "implementation": embedder_impl,
                "model_name": getattr(embedder, "model_name", "N/A"),
                "dimension": embedding_dim,
            },
            "processed_files": [],
        }

    # 3. Extract content if not pre-processed
    extracted_content: ExtractedContent
    if pdf_path:
        if not output_path:
            raise ValueError("`output_path` is required when processing a new PDF.")
        logger.info(
            f"Stage 1: Extracting sections and images from PDF to {output_path}"
        )
        pdf_processor = PDFProcessor(output_dir=output_path)
        extracted_content = pdf_processor.process_pdf(pdf_path)
    elif pre_processed_dir:
        logger.info(
            f"Stage 1: Loading content from pre-processed directory: {pre_processed_dir}"
        )
        processed_dir_path = Path(pre_processed_dir)
        extracted_content = _load_content_from_pre_processed_dir(processed_dir_path)

    # Manually set the document summary on the extracted content object
    if document_summary:
        extracted_content.document_summary = document_summary
        logger.info(f"Using provided document summary: {document_summary}")

    # 4. Initialize Processors and Storage
    image_processor = ImageProcessorFactory.create(
        implementation=image_processor_impl, **image_processor_kwargs
    )
    text_processor = TextProcessor()

    metadata_file_path = storage_path_obj / "metadata.json"
    if metadata_file_path.exists():
        with open(metadata_file_path, "r") as f:
            metadata_store = json.load(f)
    else:
        metadata_store = {}

    storage = StorageManagerFactory.create(
        implementation=storage_backend,
        persist_directory=str(storage_path_obj),
        metadata_store_path=str(metadata_file_path),
        collection_name="document_chunks",
    )
    storage.initialize()

    # 5. Process sections
    logger.info("Stage 4: Processing sections")
    for section in extracted_content.sections:
        logger.info(f"\nProcessing section: {section.title}")

        # OPTIMIZATION: Process all images for the section once
        image_captions = []
        if section.images:
            logger.info(
                f"Processing {len(section.images)} images for section '{section.title}'..."
            )
            for img_path, _ in section.images:
                from PIL import Image

                logger.info(f"  - Processing image: {img_path}")
                img = Image.open(img_path)
                caption, _ = image_processor.process_image(img)
                image_captions.append((str(img_path), caption))
                logger.info(f"    Generated caption: {caption}")
            logger.info("✅ All images for this section processed successfully.")

        # Store image captions in the metadata store with a deterministic ID
        doc_identifier = Path(pdf_path or pre_processed_dir).name
        section_identifier_str = (
            f"{doc_identifier}-{section.title}-{section.page_number}-{section.level}"
        )
        section_id = hashlib.md5(section_identifier_str.encode()).hexdigest()

        metadata_store[section_id] = {
            "title": section.title,
            "level": section.level,
            "page_number": section.page_number,
            "images": image_captions,
        }

        # Process text into smaller chunks if needed
        text_chunks = text_processor.process_text(
            section.content,
            metadata={
                "title": section.title,
                "level": section.level,
                "page_number": section.page_number,
            },
        )

        logger.info(
            f"Created {len(text_chunks)} text chunks for section '{section.title}'"
        )
        for i, text_chunk in enumerate(text_chunks):
            logger.info(f"  - Processing chunk {i + 1}/{len(text_chunks)}")
            logger.info(f"    Chunk preview: {text_chunk.content[:100]}...")

            # HYBRID APPROACH: Create combined content for embedding
            caption_text = " ".join([caption for _, caption in image_captions])
            summary_text = extracted_content.document_summary or ""

            # Combine summary, chunk content, and captions for a richer embedding context
            combined_content_parts = []
            if summary_text:
                combined_content_parts.append(summary_text)
            combined_content_parts.append(text_chunk.content)
            if caption_text:
                combined_content_parts.append(caption_text)

            combined_content = "\n\n".join(combined_content_parts).strip()

            logger.info("    Generating embedding from combined text and captions...")
            embedding = embedder.embed_text(combined_content)
            logger.info(f"    Embedding shape: {embedding.shape}")

            # Prepare lean metadata with a reference to the external store
            metadata = ChunkMetadata(
                title=section.title,
                level=section.level,
                page_number=section.page_number,
                section_path=[section.title],
                images=[],  # Images are now in the external store
                additional_metadata={
                    "section_id": section_id,
                    "section_level": text_chunk.metadata.get("section_level", 0),
                },
            )
            logger.debug(f"    Metadata for chunk: {metadata}")

            # Store in vector DB
            logger.info("    Storing chunk in vector database...")
            storage.store_chunk(
                content=text_chunk.content, metadata=metadata, embeddings=embedding
            )

    # 6. Update and save manifest and metadata
    source_file = pdf_path or pre_processed_dir
    if source_file not in manifest["processed_files"]:
        manifest["processed_files"].append(source_file)

    logger.info(f"Saving updated manifest to {manifest_path}")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=4)

    logger.info(f"Saving updated metadata store to {metadata_file_path}")
    with open(metadata_file_path, "w") as f:
        json.dump(metadata_store, f, indent=4)

    # 7. Create and persist BM25 Retriever
    logger.info("Stage 5: Creating and persisting BM25 index.")
    # We need all the text chunk *content* to build the BM25 index.
    # We can retrieve them from the storage manager.
    # Note: This might be inefficient for very large stores. A better approach
    # for huge datasets would be to collect chunks during their creation.
    # However, for simplicity and to ensure all docs in the store are indexed,
    # we retrieve them here.
    all_docs = storage.get_all_documents()

    if all_docs:
        # The BM25Retriever expects LlamaIndex Document objects
        llama_docs = [LlamaDocument(text=doc) for doc in all_docs]

        # Create and persist the docstore
        docstore_path = storage_path_obj / "docstore.json"
        storage_context = StorageContext.from_defaults()
        storage_context.docstore.add_documents(llama_docs)
        storage_context.persist(persist_dir=str(storage_path_obj))
        logger.info(f"Document store persisted to {storage_path_obj}")

        # Create the BM25 retriever from the nodes in the docstore
        try:
            bm25_retriever = BM25Retriever.from_defaults(
                docstore=storage_context.docstore, similarity_top_k=5
            )

            # Persist the retriever's state to a file
            bm25_index_path = storage_path_obj / "bm25_index.json"
            # We don't need to persist the retriever itself, as we can reconstruct it
            # from the docstore and the index file (if it were separate).
            # LlamaIndex BM25Retriever doesn't have a separate index file, it's built from the docstore.
            # The `persist` method for the retriever is for caching which we aren't using here.
            # We will instead load the docstore and create the retriever on the fly.
            # To keep the logic simple, we will persist the BM25 index itself.
            bm25_retriever.persist(persist_path=str(bm25_index_path))

            logger.info(f"BM25 index created and saved to {bm25_index_path}")
        except Exception as e:
            logger.error(f"Failed to create or persist BM25 index: {e}", exc_info=True)
    else:
        logger.warning("No documents found in storage to create a BM25 index.")

    logger.info(
        f"Completed processing and storing all sections from {pdf_path or pre_processed_dir} into {storage_backend} vector store."
    )
