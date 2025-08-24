import pytest

from src.modules.semantic_chunker.chunker import TextChunk, TextProcessor


@pytest.fixture
def text_processor():
    """Create a TextProcessor instance with default parameters."""
    return TextProcessor()


@pytest.fixture
def sample_text():
    """Create a sample text with headers and content."""
    return """# Main Title

This is the introduction paragraph. It contains some basic information about the topic.

## First Section

This is the first section with some content. It has multiple sentences.
This is another paragraph in the first section.

### Subsection 1.1

This is a subsection with its own content.
It also has multiple lines.

## Second Section

This is the second section.
It has different content than the first section.

### Subsection 2.1

This is another subsection.
It follows the same pattern as the first subsection."""


def test_identify_sections(text_processor, sample_text):
    """Test section identification from text."""
    sections = text_processor._identify_sections(sample_text)

    # Check number of sections
    assert len(sections) == 5  # Main title + 2 sections + 2 subsections

    # Check section levels
    assert sections[0]["level"] == 1  # Main title
    assert sections[1]["level"] == 2  # First section
    assert sections[2]["level"] == 3  # Subsection 1.1
    assert sections[3]["level"] == 2  # Second section
    assert sections[4]["level"] == 3  # Subsection 2.1

    # Check content presence
    assert "Main Title" in sections[0]["content"]
    assert "First Section" in sections[1]["content"]
    assert "Subsection 1.1" in sections[2]["content"]


def test_create_section_chunks_small_section(text_processor):
    """Test chunking of a small section that fits in one chunk."""
    section = {
        "content": "This is a small section that should fit in one chunk.",
        "level": 2,
    }
    metadata = {"title": "Test Section", "page": 1}

    chunks = text_processor._create_section_chunks(section, metadata)

    assert len(chunks) == 1
    assert chunks[0].content == section["content"]
    assert chunks[0].metadata["section_level"] == 2
    assert chunks[0].metadata["title"] == "Test Section"


def test_create_section_chunks_large_section(text_processor):
    """Test chunking of a large section that needs multiple chunks."""
    # Create a section that's larger than max_chunk_size
    long_text = "This is a sentence. " * 100  # Create a long text
    section = {"content": long_text, "level": 2}
    metadata = {"title": "Long Section", "page": 1}

    # Add debug prints
    print("\nDebug Info:")
    print(f"Text length: {len(long_text)}")
    print(f"Max chunk size: {text_processor.max_chunk_size}")
    print(f"Min chunk size: {text_processor.min_chunk_size}")
    print(f"Overlap size: {text_processor.overlap_size}")

    chunks = text_processor._create_section_chunks(section, metadata)

    # Print chunk information
    print(f"\nNumber of chunks created: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i} length: {len(chunk.content)}")

    # Check that we got multiple chunks
    assert len(chunks) > 1

    # Check that each chunk is within size limits
    for chunk in chunks:
        assert len(chunk.content) <= text_processor.max_chunk_size
        assert len(chunk.content) >= text_processor.min_chunk_size

    # Check that chunks have overlap
    for i in range(len(chunks) - 1):
        current_chunk = chunks[i].content
        next_chunk = chunks[i + 1].content
        overlap = text_processor.overlap_size
        assert current_chunk[-overlap:] in next_chunk


def test_process_text(text_processor, sample_text):
    """Test the main process_text method with a complete document."""
    metadata = {"title": "Test Document", "page": 1}
    chunks = text_processor.process_text(sample_text, metadata)

    # Check that we got chunks
    assert len(chunks) > 0

    # Check that all chunks have proper metadata
    for chunk in chunks:
        assert isinstance(chunk, TextChunk)
        assert "section_level" in chunk.metadata
        assert "title" in chunk.metadata
        assert chunk.content.strip()  # Content should not be empty


def test_merge_chunks(text_processor):
    """Test merging chunks back into a single text."""
    chunks = [
        TextChunk(content="First chunk", metadata={}),
        TextChunk(content="Second chunk", metadata={}),
        TextChunk(content="Third chunk", metadata={}),
    ]

    merged_text = text_processor.merge_chunks(chunks)

    assert merged_text == "First chunk\nSecond chunk\nThird chunk"


def test_chunk_hierarchy(text_processor):
    """Test that chunk hierarchy is maintained."""
    text = """# Parent
Content in parent.

## Child
Content in child.

### Grandchild
Content in grandchild."""

    chunks = text_processor.process_text(text, {"title": "Hierarchy Test"})

    # Check that we have chunks for each level
    assert len(chunks) >= 3

    # Check that metadata contains correct section levels
    levels = [chunk.metadata["section_level"] for chunk in chunks]
    assert 1 in levels  # Parent level
    assert 2 in levels  # Child level
    assert 3 in levels  # Grandchild level


def test_chunk_size_limits(text_processor):
    """Test that chunks respect size limits."""
    # Create a text that's just over max_chunk_size
    text = "This is a sentence. " * 100
    metadata = {"title": "Size Test"}

    chunks = text_processor.process_text(text, metadata)

    for chunk in chunks:
        assert len(chunk.content) <= text_processor.max_chunk_size
        assert len(chunk.content) >= text_processor.min_chunk_size


def test_custom_chunk_parameters():
    """Test TextProcessor with custom chunk parameters."""
    processor = TextProcessor(min_chunk_size=50, max_chunk_size=200, overlap_size=20)

    text = "This is a sentence. " * 20  # Create a medium-length text
    chunks = processor.process_text(text, {"title": "Custom Parameters"})

    for chunk in chunks:
        assert len(chunk.content) <= 200
        assert len(chunk.content) >= 50
