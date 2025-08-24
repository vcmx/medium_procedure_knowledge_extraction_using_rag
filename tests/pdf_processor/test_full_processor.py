"""
Tests for the Full PDF Processor module with Florence-2 and ChromaDB integration.
"""

import os
from pathlib import Path

import pytest

from src.modules.pdf_processor.full_processor import DocumentChunk, FullPDFProcessor


@pytest.fixture
def processor():
    """Create a FullPDFProcessor instance for testing."""
    return FullPDFProcessor(
        florence2_model_id="microsoft/Florence-2-large",
        clip_model_name="openai/clip-vit-base-patch32",
        chroma_persist_dir="./test_chroma_db",
    )


@pytest.fixture
def sample_pdf():
    """Create a sample PDF file for testing."""
    # Create input directory if it doesn't exist
    input_dir = Path("input-pdfs")
    input_dir.mkdir(exist_ok=True)

    # Check if sample PDF exists
    pdf_path = input_dir / "sample.pdf"
    if not pdf_path.exists():
        pytest.skip(
            "Sample PDF not found. Please add a PDF file to input-pdfs/sample.pdf"
        )

    return str(pdf_path)


def test_processor_initialization():
    """Test FullPDFProcessor initialization."""
    processor = FullPDFProcessor()
    assert processor.device is not None
    assert processor.florence2_model is not None
    assert processor.florence2_processor is not None
    assert processor.embedding_function is not None
    assert processor.chroma_client is not None
    assert processor.collection is not None


def test_process_pdf(processor, sample_pdf):
    """Test PDF processing with image captioning."""
    output_dir = "./test_output"
    chunks = processor.process_pdf(sample_pdf, output_dir)

    # Check that we got chunks
    assert len(chunks) > 0

    # Check the structure of the first chunk
    first_chunk = chunks[0]
    assert isinstance(first_chunk, DocumentChunk)
    assert hasattr(first_chunk, "text")
    assert hasattr(first_chunk, "images")
    assert hasattr(first_chunk, "metadata")
    assert hasattr(first_chunk, "section_hierarchy")
    assert hasattr(first_chunk, "page_number")

    # Check metadata structure
    assert "section_hierarchy" in first_chunk.metadata
    assert "page_number" in first_chunk.metadata
    assert "has_images" in first_chunk.metadata


def test_process_nonexistent_pdf(processor):
    """Test processing a non-existent PDF."""
    with pytest.raises(Exception):
        processor.process_pdf("nonexistent.pdf", "./test_output")


def test_store_in_chroma(processor, sample_pdf):
    """Test storing chunks in ChromaDB."""
    # Process PDF first
    chunks = processor.process_pdf(sample_pdf, "./test_output")

    # Store in ChromaDB
    processor.store_in_chroma(chunks)

    # Verify chunks were stored
    results = processor.collection.get()
    assert len(results["ids"]) == len(chunks)


@pytest.mark.skipif(
    not os.getenv("GOOGLE_API_KEY"),
    reason="No GOOGLE_API_KEY found in environment variables",
)
def test_image_captioning(processor):
    """Test image captioning with Florence-2."""
    # Skip if no API key
    if not os.getenv("GOOGLE_API_KEY"):
        pytest.skip("No GOOGLE_API_KEY found in environment variables")

    # Create a simple test image
    import numpy as np
    from PIL import Image

    # Create a 100x100 white image
    test_image = Image.fromarray(np.ones((100, 100, 3), dtype=np.uint8) * 255)

    # Get caption
    caption = processor.extract_caption(test_image)

    # Check caption
    assert isinstance(caption, str)
    assert len(caption) > 0
