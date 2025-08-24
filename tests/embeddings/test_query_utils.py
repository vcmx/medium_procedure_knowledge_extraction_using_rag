import json
from unittest.mock import MagicMock, patch

import pytest
from chromadb.config import Settings

from src.modules.embeddings.query_utils import QueryManager


@pytest.fixture
def mock_chroma_client():
    """Create a mock ChromaDB client."""
    with patch("chromadb.PersistentClient") as mock_client:
        # Mock collection
        mock_collection = MagicMock()
        mock_client.return_value.get_collection.return_value = mock_collection
        yield mock_client


@pytest.fixture
def sample_documents():
    """Sample documents for testing."""
    return {
        "ids": ["doc1", "doc2"],
        "documents": [
            "This is the first document about engines.",
            "This is the second document about cars.",
        ],
        "metadatas": [
            {
                "title": "Engine Doc",
                "level": 1,
                "page_number": 1,
                "section_path": json.dumps(["Engine Section"]),
                "images": json.dumps([]),
            },
            {
                "title": "Car Doc",
                "level": 1,
                "page_number": 2,
                "section_path": json.dumps(["Car Section"]),
                "images": json.dumps([]),
            },
        ],
    }


@pytest.fixture
def sample_search_results():
    """Sample search results for testing."""
    return {
        "ids": [["doc1"]],
        "documents": [["This is the first document about engines."]],
        "metadatas": [
            [
                {
                    "title": "Engine Doc",
                    "level": 1,
                    "page_number": 1,
                    "section_path": json.dumps(["Engine Section"]),
                    "images": json.dumps([]),
                }
            ]
        ],
        "distances": [[0.5]],
    }


def test_query_manager_initialization(mock_chroma_client):
    """Test QueryManager initialization."""
    query_manager = QueryManager(
        persist_directory="./test_db",
        collection_name="test_collection",
        embedding_model="clip",
    )

    # Verify ChromaDB client was initialized correctly
    mock_chroma_client.assert_called_once()
    call_args = mock_chroma_client.call_args[1]
    assert call_args["path"] == "./test_db"
    assert isinstance(call_args["settings"], Settings)
    assert call_args["settings"].anonymized_telemetry is False

    # Verify collection was retrieved
    mock_chroma_client.return_value.get_collection.assert_called_once_with(
        name="test_collection"
    )


def test_list_all_documents(mock_chroma_client, sample_documents):
    """Test listing all documents."""
    # Setup mock collection
    mock_collection = mock_chroma_client.return_value.get_collection.return_value
    mock_collection.get.return_value = sample_documents

    # Initialize QueryManager
    query_manager = QueryManager()

    # Test list_all_documents
    results = query_manager.list_all_documents(limit=2)

    # Verify results
    assert len(results) == 2
    assert results[0]["id"] == "doc1"
    assert results[0]["content"] == "This is the first document about engines."
    assert results[0]["metadata"]["title"] == "Engine Doc"
    assert results[1]["id"] == "doc2"
    assert results[1]["content"] == "This is the second document about cars."
    assert results[1]["metadata"]["title"] == "Car Doc"

    # Verify collection.get was called
    mock_collection.get.assert_called_once()


def test_search(mock_chroma_client, sample_search_results):
    """Test search functionality."""
    # Setup mock collection
    mock_collection = mock_chroma_client.return_value.get_collection.return_value
    mock_collection.query.return_value = sample_search_results

    # Initialize QueryManager
    query_manager = QueryManager()

    # Test search
    results = query_manager.search(query="engine", n_results=1)

    # Verify results
    assert len(results) == 1
    assert results[0]["id"] == "doc1"
    assert results[0]["content"] == "This is the first document about engines."
    assert results[0]["metadata"]["title"] == "Engine Doc"
    assert results[0]["score"] == 0.5

    # Verify collection.query was called with correct parameters
    mock_collection.query.assert_called_once()
    call_args = mock_collection.query.call_args[1]
    assert "query_embeddings" in call_args
    assert call_args["n_results"] == 1


def test_search_with_filter(mock_chroma_client, sample_search_results):
    """Test search with metadata filter."""
    # Setup mock collection
    mock_collection = mock_chroma_client.return_value.get_collection.return_value
    mock_collection.query.return_value = sample_search_results

    # Initialize QueryManager
    query_manager = QueryManager()

    # Test search with filter
    filter_metadata = {"level": 1}
    results = query_manager.search(
        query="engine", n_results=1, filter_metadata=filter_metadata
    )

    # Verify collection.query was called with filter
    mock_collection.query.assert_called_once()
    call_args = mock_collection.query.call_args[1]
    assert call_args["where"] == filter_metadata


def test_search_no_results(mock_chroma_client):
    """Test search when no results are found."""
    # Setup mock collection to return empty results
    mock_collection = mock_chroma_client.return_value.get_collection.return_value
    mock_collection.query.return_value = {
        "ids": [[]],
        "documents": [[]],
        "metadatas": [[]],
        "distances": [[]],
    }

    # Initialize QueryManager
    query_manager = QueryManager()

    # Test search
    results = query_manager.search(query="nonexistent")

    # Verify empty results
    assert len(results) == 0
