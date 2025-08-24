import argparse
import json
import logging
import os
import shutil
from datetime import datetime

from dotenv import load_dotenv

from src.modules.pipeline.multimodal_rag_pipeline import (
    run_pipeline as run_rag_pipeline,
)


def setup_logging():
    """Set up logging for the application."""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"pipeline_{timestamp}.log"
    log_filepath = os.path.join(log_dir, log_filename)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_filepath), logging.StreamHandler()],
    )
    # Redirect warnings to the logging system
    logging.captureWarnings(True)


def main():
    """Main function to run the multimodal RAG pipeline."""
    parser = argparse.ArgumentParser(description="Run the multimodal RAG pipeline.")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--pdf_path",
        type=str,
        help="Path to the input PDF file to process from scratch.",
    )
    group.add_argument(
        "--pre_processed_dir",
        type=str,
        help="Path to a directory containing pre-processed markdown and images.",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="./processed_output",
        help="Directory for intermediate outputs (e.g., parsed markdown and images).",
    )
    parser.add_argument(
        "--storage_path",
        type=str,
        default="./rag_storage",
        help="Root directory for storing final RAG outputs (vector DB, metadata, etc.).",
    )
    parser.add_argument(
        "--wipe_db",
        action="store_true",
        help="Wipe the existing RAG storage directory before processing.",
    )
    parser.add_argument(
        "--image_processor_impl",
        type=str,
        default="local",
        help="Implementation for the image processor ('local', 'huggingface', 'openrouter').",
    )
    parser.add_argument(
        "--embedder_impl",
        type=str,
        default="clip",
        help="Implementation for the embedder ('clip', 'siglip', 'huggingface').",
    )
    parser.add_argument(
        "--storage_backend",
        type=str,
        default="chroma",
        help="Storage backend to use ('chroma').",
    )
    parser.add_argument(
        "--image_processor_kwargs",
        type=str,
        default="{}",
        help="JSON string of kwargs for the image processor.",
    )
    parser.add_argument(
        "--embedder_kwargs",
        type=str,
        default="{}",
        help="JSON string of kwargs for the embedder.",
    )
    parser.add_argument(
        "--document_summary",
        type=str,
        default=None,
        help="A one-line summary of the document to be included with each chunk.",
    )

    args = parser.parse_args()

    # Load environment variables from .env file
    dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
    load_dotenv(dotenv_path=dotenv_path, override=True)

    # Setup logging
    setup_logging()
    main_logger = logging.getLogger(__name__)

    # Log loaded environment variables for debugging
    main_logger.info("--- Checking loaded environment variables ---")
    keys_to_check = [
        "HUGGINGFACEHUB_API_TOKEN",
        "HUGGINGFACE_API_KEY",
        "OPENROUTER_API_KEY",
    ]
    for key in keys_to_check:
        value = os.getenv(key)
        if value:
            # Mask the value for security
            main_logger.info(f"Loaded {key}: {value[:4]}...{value[-4:]}")
        else:
            main_logger.info(f"{key} not found in environment.")
    main_logger.info("-------------------------------------------")

    # Early validation for Hugging Face API key format if Hugging Face is used
    if (
        args.image_processor_impl == "huggingface"
        or args.embedder_impl == "huggingface"
    ):
        hf_token = os.getenv("HUGGINGFACEHUB_API_TOKEN") or os.getenv(
            "HUGGINGFACE_API_KEY"
        )
        if not hf_token:
            raise ValueError(
                "Hugging Face implementation requires a token. Please set HUGGINGFACEHUB_API_TOKEN or HUGGINGFACE_API_KEY in your .env file."
            )
        if not hf_token.startswith("hf_"):
            raise ValueError(
                f"Invalid Hugging Face API token format. Token must start with 'hf_'. Token preview: {hf_token[:4]}..."
            )

    # Parse JSON string arguments
    image_processor_kwargs = json.loads(args.image_processor_kwargs)
    embedder_kwargs = json.loads(args.embedder_kwargs)

    if args.wipe_db:
        storage_dir = args.storage_path
        main_logger.info(
            f"Wipe DB flag is active. Attempting to wipe storage at: {storage_dir}"
        )
        try:
            if storage_dir and os.path.exists(storage_dir):
                main_logger.info(f"Directory '{storage_dir}' exists. Deleting...")
                shutil.rmtree(storage_dir)
                main_logger.info(f"Directory '{storage_dir}' wiped successfully.")
            else:
                main_logger.warning(
                    f"Directory '{storage_dir}' not found. Nothing to wipe."
                )
        except OSError as e:
            main_logger.error(
                f"Error wiping RAG storage directory '{storage_dir}': {e}"
            )
            return
    else:
        main_logger.info("Wipe DB flag is not active. Skipping wipe.")

    main_logger.info("Starting pipeline execution from run_pipeline.py script.")

    try:
        run_rag_pipeline(
            pdf_path=args.pdf_path,
            pre_processed_dir=args.pre_processed_dir,
            output_path=args.output_dir,
            storage_path=args.storage_path,
            document_summary=args.document_summary,
            image_processor_impl=args.image_processor_impl,
            image_processor_kwargs=image_processor_kwargs,
            embedder_impl=args.embedder_impl,
            embedder_kwargs=embedder_kwargs,
            storage_backend=args.storage_backend,
        )
        main_logger.info("Pipeline execution completed successfully.")
    except Exception as e:
        main_logger.error(
            f"An unexpected error occurred during pipeline execution: {e}",
            exc_info=True,
        )


if __name__ == "__main__":
    main()
