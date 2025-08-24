import argparse
import logging
import os
from pathlib import Path

from src.modules.pdf_processor.processor import PDFProcessor


def setup_logging():
    """Set up logging for the application."""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_filename = "test_pdf_processor.log"
    log_filepath = os.path.join(log_dir, log_filename)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_filepath), logging.StreamHandler()],
    )
    logging.captureWarnings(True)


def main():
    """Main function to run the PDF processing test."""
    parser = argparse.ArgumentParser(description="Test the PDF Processor.")
    parser.add_argument(
        "--pdf_path",
        type=str,
        required=True,
        help="Path to the input PDF file to process.",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="./test_processed_output",
        help="Directory for the processed output.",
    )
    args = parser.parse_args()

    setup_logging()
    main_logger = logging.getLogger(__name__)

    main_logger.info(f"Starting PDF processing test for: {args.pdf_path}")

    try:
        # Ensure the output directory exists
        Path(args.output_dir).mkdir(parents=True, exist_ok=True)

        # Initialize PDFProcessor
        # This uses the configuration that includes 'paginate_output': True
        pdf_processor = PDFProcessor(output_dir=args.output_dir)

        # Process the PDF
        extracted_content = pdf_processor.process_pdf(args.pdf_path)

        # The markdown file is saved within the process_pdf method.
        # We can optionally print some stats here.
        main_logger.info("PDF processing completed successfully.")
        main_logger.info(f"Extracted {len(extracted_content.sections)} sections.")

        output_subdir = Path(args.output_dir) / Path(args.pdf_path).stem
        main_logger.info(f"Output saved in a subdirectory within: {args.output_dir}")

    except Exception as e:
        main_logger.error(
            f"An unexpected error occurred during PDF processing: {e}",
            exc_info=True,
        )


if __name__ == "__main__":
    main()
