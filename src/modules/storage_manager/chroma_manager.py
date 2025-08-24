import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

from .base import BaseStorageManager, ChunkMetadata, SearchResult


class ChromaStorageManager(BaseStorageManager):
    """ChromaDB implementation of the storage manager."""

    def __init__(
        self,
        persist_directory: str = "./chroma_db",
        collection_name: str = "document_chunks",
        embedding_function: Optional[Any] = None,
        metadata_store_path: Optional[str] = None,
    ):
        """
        Initialize the ChromaDB storage manager.

        Args:
            persist_directory: Directory to persist the database
            collection_name: Name of the collection to use
            embedding_function: Optional custom embedding function
            metadata_store_path: Optional path to the external JSON metadata store.
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )

        # Use default embedding function if none provided
        self.embedding_function = (
            embedding_function or embedding_functions.DefaultEmbeddingFunction()
        )

        self.collection = None

        # Load the external metadata store if a path is provided
        self.metadata_store = {}
        self.using_metadata_for_images = False
        if metadata_store_path:
            metadata_file_path = Path(metadata_store_path)
            if metadata_file_path.exists():
                with open(metadata_file_path, "r") as f:
                    self.metadata_store = json.load(f)
                self.using_metadata_for_images = True

    def initialize(self) -> None:
        """Initialize the storage system."""
        try:
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize ChromaDB: {str(e)}")

    def _serialize_images(self, images: List[Tuple[Path, str]]) -> List[Dict[str, str]]:
        """Serialize image path and caption for storage."""
        serialized = []
        for path, caption in images:
            serialized.append({"path": str(path), "caption": caption})
        return serialized

    def _deserialize_images(
        self, serialized: List[Dict[str, str]]
    ) -> List[Tuple[Path, str]]:
        """Deserialize image path and caption from storage."""
        images = []
        for img_meta in serialized:
            images.append((Path(img_meta["path"]), img_meta["caption"]))
        return images

    def store_chunk(
        self,
        content: str,
        metadata: ChunkMetadata,
        embeddings: Optional[List[float]] = None,
        image_embeddings: Optional[List[List[float]]] = None,
    ) -> str:
        """Store a chunk of content with its metadata and embeddings."""
        if not self.collection:
            self.initialize()

        # Convert metadata to dict and handle special fields
        metadata_dict = {
            "title": metadata.title,
            "level": metadata.level,
            "page_number": metadata.page_number,
            "section_path": json.dumps(metadata.section_path),
        }
        # OLD RAG way of handling images
        if self.using_metadata_for_images is False:
            metadata_dict["images"] = json.dumps(
                self._serialize_images(metadata.images)
            )

        # Add additional metadata, ensuring all values are primitive types
        if metadata.additional_metadata:
            for key, value in metadata.additional_metadata.items():
                if isinstance(value, (list, dict)):
                    metadata_dict[key] = json.dumps(value)
                else:
                    metadata_dict[key] = value

        # Generate a unique ID if not provided
        chunk_id = f"chunk_{hash(content + str(metadata_dict))}"

        # Upsert the chunk to avoid duplicates on re-runs
        self.collection.upsert(
            ids=[chunk_id],
            documents=[content],
            metadatas=[metadata_dict],
            embeddings=[embeddings.tolist()] if embeddings is not None else None,
        )

        return chunk_id

    def search(
        self,
        query: str,
        query_embedding: Optional[List[float]] = None,
        limit: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Search for content using semantic search."""
        if not self.collection:
            self.initialize()

        # Convert filter metadata to ChromaDB format
        where = None
        if filter_metadata:
            where = {}
            for key, value in filter_metadata.items():
                if isinstance(value, (list, dict)):
                    where[key] = json.dumps(value)
                else:
                    where[key] = value

        # Perform the search
        results = self.collection.query(
            query_texts=[query] if not query_embedding else None,
            query_embeddings=[query_embedding] if query_embedding else None,
            n_results=limit,
            where=where,
        )

        # Convert results to SearchResult objects
        search_results = []
        for i in range(len(results["ids"][0])):
            metadata_dict = results["metadatas"][0][i]

            # Reconstruct rich metadata from the external store
            if self.using_metadata_for_images:
                section_id = metadata_dict.get("section_id")
                images = []
                if section_id and section_id in self.metadata_store:
                    section_info = self.metadata_store[section_id]
                    images = [
                        (Path(img_path), caption)
                        for img_path, caption in section_info.get("images", [])
                    ]
            else:
                serialized_images = json.loads(metadata_dict["images"])
                images = self._deserialize_images(serialized_images)

            metadata = ChunkMetadata(
                title=metadata_dict["title"],
                level=metadata_dict["level"],
                page_number=metadata_dict["page_number"],
                section_path=json.loads(metadata_dict["section_path"]),
                images=images,
                additional_metadata={
                    k: v
                    for k, v in metadata_dict.items()
                    if k
                    not in [
                        "title",
                        "level",
                        "page_number",
                        "section_path",
                        "images",  # see if this works for both OLD RAG or hybrid RAG
                    ]
                },
            )

            search_results.append(
                SearchResult(
                    content=results["documents"][0][i],
                    metadata=metadata,
                    score=results["distances"][0][i] if "distances" in results else 0.0,
                    image_paths=[str(path) for path, _ in images],
                )
            )

        return search_results

    def get_chunk(self, chunk_id: str) -> Optional[Tuple[str, ChunkMetadata]]:
        """Retrieve a specific chunk by ID."""
        if not self.collection:
            self.initialize()

        try:
            results = self.collection.get(ids=[chunk_id])
            if not results["ids"]:
                return None

            metadata_dict = results["metadatas"][0]

            if self.using_metadata_for_images:
                # Reconstruct rich metadata from the external store
                section_id = metadata_dict.get("section_id")
                images = []
                if section_id and section_id in self.metadata_store:
                    section_info = self.metadata_store[section_id]
                    images = [
                        (Path(img_path), caption)
                        for img_path, caption in section_info.get("images", [])
                    ]
            else:
                serialized_images = json.loads(metadata_dict["images"])
                images = self._deserialize_images(serialized_images)

            metadata = ChunkMetadata(
                title=metadata_dict["title"],
                level=metadata_dict["level"],
                page_number=metadata_dict["page_number"],
                section_path=json.loads(metadata_dict["section_path"]),
                images=images,
                additional_metadata={
                    k: v
                    for k, v in metadata_dict.items()
                    if k
                    not in [
                        "title",
                        "level",
                        "page_number",
                        "section_path",
                        "images",
                    ]
                },
            )

            return results["documents"][0], metadata

        except Exception:
            return None

    def delete_chunk(self, chunk_id: str) -> bool:
        """Delete a chunk by ID."""
        if not self.collection:
            self.initialize()

        try:
            self.collection.delete(ids=[chunk_id])
            return True
        except Exception:
            return False

    def clear(self) -> None:
        """Clear all stored data."""
        if self.collection:
            self.collection.delete(where={})

    def get_all_documents(self) -> List[str]:
        """
        Retrieve the text content of all documents in the store.
        Uses the get() method to retrieve all entries and returns their content.
        """
        if not self.collection:
            self.initialize()

        results = self.collection.get()
        return results.get("documents", [])
