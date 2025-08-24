"""
Example usage of the full PDF processor with Marker, Florence-2, and ChromaDB integration.
"""

import logging
from pathlib import Path

from .full_processor import FullPDFProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    # Initialize the processor
    processor = FullPDFProcessor(
        florence2_model_id="microsoft/Florence-2-large",
        clip_model_name="openai/clip-vit-base-patch32",
        chroma_persist_dir="./chroma_db",
    )

    # Define paths
    pdf_path = "input-pdfs/sample.pdf"
    output_dir = "processed_output"

    # Ensure input PDF exists
    if not Path(pdf_path).exists():
        logger.error(f"Input PDF not found: {pdf_path}")
        return

    try:
        # Process PDF and create chunks
        logger.info(f"Processing PDF: {pdf_path}")
        chunks = processor.process_pdf(pdf_path, output_dir)

        # Log results
        logger.info(f"Processed {len(chunks)} chunks")
        for i, chunk in enumerate(chunks):
            logger.info(f"\nChunk {i+1}:")
            logger.info(f"Section: {' > '.join(chunk.section_hierarchy)}")
            logger.info(f"Page: {chunk.page_number}")
            logger.info(f"Text preview: {chunk.text[:200]}...")
            if chunk.images:
                logger.info(f"Images: {len(chunk.images)}")
                for img_path, caption in chunk.images:
                    logger.info(f"- {img_path}: {caption}")

        # Store in ChromaDB
        logger.info("\nStoring chunks in ChromaDB...")
        processor.store_in_chroma(chunks)
        logger.info("Done!")

    except Exception as e:
        logger.error(f"Error processing PDF: {e}", exc_info=True)


if __name__ == "__main__":
    main()
