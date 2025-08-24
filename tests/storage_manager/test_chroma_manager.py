from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.modules.storage_manager.base import ChunkMetadata
from src.modules.storage_manager.chroma_manager import ChromaStorageManager


@pytest.fixture
def sample_metadata():
    return ChunkMetadata(
        title="Test Section",
        level=1,
        page_number=1,
        section_path=["Root", "Test Section"],
        images=[(Path("/tmp/test.png"), b"fakebytes")],
        additional_metadata={"foo": "bar"},
    )


@pytest.fixture
def sample_content():
    return "This is a test chunk."


@pytest.fixture
def sample_embedding():
    return [0.1, 0.2, 0.3]


@patch("src.modules.storage_manager.chroma_manager.chromadb.PersistentClient")
def test_chroma_storage_manager_store_and_get(
    mock_chroma_client, sample_metadata, sample_content, sample_embedding
):
    # Mock ChromaDB collection
    mock_collection = MagicMock()
    mock_chroma_client.return_value.get_or_create_collection.return_value = (
        mock_collection
    )
    manager = ChromaStorageManager(persist_directory="/tmp/chroma_test")
    manager.initialize()
    # Store chunk
    chunk_id = manager.store_chunk(
        sample_content, sample_metadata, embeddings=sample_embedding
    )
    assert isinstance(chunk_id, str)
    # Simulate get (single-bracketed lists)
    mock_collection.get.return_value = {
        "ids": [chunk_id],
        "documents": [sample_content],
        "metadatas": [
            {
                "title": sample_metadata.title,
                "level": sample_metadata.level,
                "page_number": sample_metadata.page_number,
                "section_path": '["Root", "Test Section"]',
                "images": "[]",
                **sample_metadata.additional_metadata,
            }
        ],
    }
    result = manager.get_chunk(chunk_id)
    print("Chroma get_chunk result:", result)
    assert result is not None
    assert result[0] == sample_content
