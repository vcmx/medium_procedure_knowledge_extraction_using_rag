from pathlib import Path

import pytest

from src.modules.storage_manager.base import BaseStorageManager, ChunkMetadata


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
