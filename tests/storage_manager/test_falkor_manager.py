from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.modules.storage_manager.base import ChunkMetadata
from src.modules.storage_manager.falkor_manager import FalkorStorageManager


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


@patch("src.modules.storage_manager.falkor_manager.FalkorDB")
def test_falkor_storage_manager_store_and_get(
    mock_falkor_db, sample_metadata, sample_content, sample_embedding
):
    # Mock FalkorDB client
    mock_client = MagicMock()
    mock_falkor_db.return_value = mock_client
    manager = FalkorStorageManager(host="localhost", port=6379)
    manager.initialize()
    # Store chunk
    chunk_id = manager.store_chunk(
        sample_content, sample_metadata, embeddings=sample_embedding
    )
    assert isinstance(chunk_id, str)
    # Simulate get (ensure correct types and JSON string for section_path)
    mock_client.hgetall.return_value = {
        "title": sample_metadata.title,
        "level": 1,  # int, not str
        "page_number": 1,  # int, not str
        "section_path": '["Root", "Test Section"]',  # JSON string
        "images": "[]",
        **sample_metadata.additional_metadata,
        "content": sample_content,
    }
    result = manager.get_chunk(chunk_id)
    print("Falkor get_chunk result:", result)
    assert result is not None
    assert result[0] == sample_content
