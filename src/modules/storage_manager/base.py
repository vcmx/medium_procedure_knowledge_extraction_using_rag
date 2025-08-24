from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ChunkMetadata:
    """Metadata for a document chunk."""

    title: str
    level: int
    page_number: int
    section_path: List[str]  # List of section titles from root to current
    images: List[Tuple[Path, bytes]]
    additional_metadata: Dict[str, Any] = None  # Made optional with default None


@dataclass
class SearchResult:
    """Result from a semantic search."""

    content: str
    metadata: ChunkMetadata
    score: float
    image_paths: List[str]  # Keep this as List[str] for search results


class BaseStorageManager(ABC):
    """Abstract base class for storage managers."""

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the storage system."""
        pass

    @abstractmethod
    def store_chunk(
        self,
        content: str,
        metadata: ChunkMetadata,
        embeddings: Optional[List[float]] = None,
        image_embeddings: Optional[List[List[float]]] = None,
    ) -> str:
        """
        Store a chunk of content with its metadata and embeddings.

        Args:
            content: The text content to store
            metadata: Metadata associated with the chunk
            embeddings: Optional text embeddings
            image_embeddings: Optional list of image embeddings

        Returns:
            str: ID of the stored chunk
        """
        pass

    @abstractmethod
    def search(
        self,
        query: str,
        query_embedding: Optional[List[float]] = None,
        limit: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """
        Search for content using semantic search.

        Args:
            query: Text query
            query_embedding: Optional pre-computed query embedding
            limit: Maximum number of results to return
            filter_metadata: Optional metadata filters

        Returns:
            List of search results
        """
        pass

    @abstractmethod
    def get_chunk(self, chunk_id: str) -> Optional[Tuple[str, ChunkMetadata]]:
        """
        Retrieve a specific chunk by ID.

        Args:
            chunk_id: ID of the chunk to retrieve

        Returns:
            Tuple of (content, metadata) if found, None otherwise
        """
        pass

    @abstractmethod
    def delete_chunk(self, chunk_id: str) -> bool:
        """
        Delete a chunk by ID.

        Args:
            chunk_id: ID of the chunk to delete

        Returns:
            bool: True if deleted, False if not found
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all stored data."""
        pass

    @abstractmethod
    def get_all_documents(self) -> List[str]:
        """
        Retrieve the text content of all documents in the store.

        Returns:
            List[str]: A list of all document contents.
        """
        pass
