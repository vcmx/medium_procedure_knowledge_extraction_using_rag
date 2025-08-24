"""
Tests for the PDF Processor module.
"""

import os
from pathlib import Path

import pytest

from src.modules.pdf_processor.processor import PDFProcessor


@pytest.fixture
def processor():
    """Create a PDFProcessor instance for testing."""
    return PDFProcessor(
        output_dir="./test_output",
        use_llm=False,  # Disable LLM for testing
        format_lines=False,  # Disable format_lines
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
    """Test PDFProcessor initialization."""
    processor = PDFProcessor(output_dir="./test_output")
    assert processor.output_dir == Path("./test_output")
    assert processor.output_dir.exists()


def test_process_pdf(processor, sample_pdf):
    """Test PDF processing."""
    results = processor.process_pdf(sample_pdf)

    # Check that we got results
    assert results is not None
    assert hasattr(results, "sections")
    assert len(results.sections) > 0

    # Check the structure of the first section
    first_section = results.sections[0]
    assert hasattr(first_section, "title")
    assert hasattr(first_section, "level")
    assert hasattr(first_section, "content")
    assert hasattr(first_section, "images")
    assert hasattr(first_section, "page_number")

    # Check metadata
    assert hasattr(results, "metadata")
    assert "table_of_contents" in results.metadata
    assert "page_stats" in results.metadata


def test_process_nonexistent_pdf(processor):
    """Test processing a non-existent PDF."""
    with pytest.raises(Exception):
        processor.process_pdf("nonexistent.pdf")


def test_processor_with_llm():
    """Test PDFProcessor with LLM enabled."""
    # Skip if no API key
    if not os.getenv("GOOGLE_API_KEY"):
        pytest.skip("No GOOGLE_API_KEY found in environment variables")

    processor = PDFProcessor(
        output_dir="./test_output", use_llm=True, format_lines=True
    )
    config = processor.config_parser.generate_config_dict()
    assert config.get("use_llm", False) is True


def test_processor_without_llm():
    """Test PDFProcessor without LLM."""
    processor = PDFProcessor(
        output_dir="./test_output", use_llm=False, format_lines=True
    )
    config = processor.config_parser.generate_config_dict()
    assert config.get("use_llm", False) is False
