from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.modules.storage_manager.base import BaseStorageManager, ChunkMetadata
from src.modules.storage_manager.chroma_manager import ChromaStorageManager
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


class DummyStorageManager(BaseStorageManager):
    def initialize(self):
        self._store = {}

    def store_chunk(self, content, metadata, embeddings=None, image_embeddings=None):
        self._store["chunk"] = (content, metadata, embeddings)
        return "chunk"

    def search(self, query, query_embedding=None, limit=10, filter_metadata=None):
        return []

    def get_chunk(self, chunk_id):
        return self._store.get(chunk_id, None)

    def delete_chunk(self, chunk_id):
        if chunk_id in self._store:
            del self._store[chunk_id]
            return True
        return False

    def clear(self):
        self._store.clear()


def test_base_storage_manager_interface(sample_metadata, sample_content):
    manager = DummyStorageManager()
    manager.initialize()
    chunk_id = manager.store_chunk(sample_content, sample_metadata)
    assert chunk_id == "chunk"
    assert manager.get_chunk("chunk")[0] == sample_content
    assert manager.delete_chunk("chunk") is True
    assert manager.get_chunk("chunk") is None
    manager.clear()


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
    # Simulate get
    mock_collection.get.return_value = {
        "ids": [chunk_id],
        "documents": [sample_content],
        "metadatas": [
            {
                "title": sample_metadata.title,
                "level": sample_metadata.level,
                "page_number": sample_metadata.page_number,
                "section_path": str(sample_metadata.section_path),
                "images": "[]",
                **sample_metadata.additional_metadata,
            }
        ],
    }
    result = manager.get_chunk(chunk_id)
    assert result is not None
    assert result[0] == sample_content


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
    # Simulate get
    mock_client.hgetall.return_value = {
        "title": sample_metadata.title,
        "level": sample_metadata.level,
        "page_number": sample_metadata.page_number,
        "section_path": str(sample_metadata.section_path),
        "images": "[]",
        **sample_metadata.additional_metadata,
        "content": sample_content,
    }
    result = manager.get_chunk(chunk_id)
    assert result is not None
    assert result[0] == sample_content
