"""
Example usage of the PDF Processor.
"""

import logging
import os
from pathlib import Path

from src.modules.pdf_processor.processor import PDFProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def print_sections(result):
    """Print the sections in a structured way."""
    logger.info(f"\nProcessed {len(result.sections)} sections")

    # Print table of contents
    logger.info("\nTable of Contents:")
    for section in result.sections:
        indent = "  " * (section.level - 1)
        logger.info(
            f"{indent}{'#' * section.level} {section.title} (Page {section.page_number})"
        )

    # Print first section as example
    if result.sections:
        first_section = result.sections[0]
        logger.info(f"\nExample Section: {first_section.title}")
        logger.info(f"Level: {first_section.level}")
        logger.info(f"Page: {first_section.page_number}")
        logger.info("\nContent preview:")
        preview = (
            first_section.content[:200] + "..."
            if len(first_section.content) > 200
            else first_section.content
        )
        logger.info(preview)
        logger.info(f"\nImages in section: {len(first_section.images)}")


def main():
    # Initialize processor with format_lines enabled
    processor = PDFProcessor(
        output_dir="./processed_output",
        format_lines=True,  # Enable line formatting for better accuracy
    )

    # Process a PDF
    input_dir = Path("input-pdfs")
    if not input_dir.exists():
        logger.error(f"Input directory {input_dir} does not exist")
        return

    pdf_files = list(input_dir.glob("*.pdf"))
    if not pdf_files:
        logger.error("No PDF files found in input directory")
        return

    # Process the first PDF found
    pdf_path = str(pdf_files[0])
    logger.info(f"Processing PDF: {pdf_path}")

    try:
        # First, process without LLM
        logger.info("\n=== Processing without LLM ===")
        result = processor.process_pdf(pdf_path)
        print_sections(result)

        # Check if we should reprocess with LLM
        gemini_api_key = os.getenv("GOOGLE_API_KEY")
        if gemini_api_key:
            logger.info("\n=== Reprocessing with LLM ===")
            llm_result = processor.reprocess_with_llm(pdf_path)
            print_sections(llm_result)

            # Compare results
            logger.info("\n=== Comparison ===")
            logger.info(f"Regular processing sections: {len(result.sections)}")
            logger.info(f"LLM processing sections: {len(llm_result.sections)}")

            # Print metadata
            logger.info("\nDocument Metadata:")
            for key, value in result.metadata.items():
                logger.info(f"{key}: {value}")
        else:
            logger.info("\nSkipping LLM reprocessing (no GOOGLE_API_KEY found)")

    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")


if __name__ == "__main__":
    main()
