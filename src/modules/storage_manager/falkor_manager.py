import base64
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from falkordb import FalkorDB

from .base import BaseStorageManager, ChunkMetadata, SearchResult


class FalkorStorageManager(BaseStorageManager):
    """FalkorDB implementation of the storage manager."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        embedding_dim: int = 768,  # Default CLIP embedding dimension
    ):
        """
        Initialize the FalkorDB storage manager.

        Args:
            host: FalkorDB host
            port: FalkorDB port
            db: Database number
            embedding_dim: Dimension of embeddings
        """
        self.client = FalkorDB(host=host, port=port, db=db)
        self.embedding_dim = embedding_dim
        self.initialized = False

    def initialize(self) -> None:
        """Initialize the storage system."""
        if not self.initialized:
            # Create vector index for text embeddings
            self.client.ft_create(
                "text_idx",
                {
                    "content": "TEXT",
                    "title": "TEXT",
                    "level": "NUMERIC",
                    "page_number": "NUMERIC",
                    "section_path": "TEXT",
                    "images": "TEXT",  # Store serialized images
                    "embedding": f"VECTOR FLOAT32 {self.embedding_dim}",
                },
            )
            self.initialized = True

    def _serialize_images(
        self, images: List[Tuple[Path, bytes]]
    ) -> List[Dict[str, str]]:
        """Serialize image data for storage."""
        serialized = []
        for path, data in images:
            serialized.append(
                {"path": str(path), "data": base64.b64encode(data).decode("utf-8")}
            )
        return serialized

    def _deserialize_images(
        self, serialized: List[Dict[str, str]]
    ) -> List[Tuple[Path, bytes]]:
        """Deserialize image data from storage."""
        images = []
        for img in serialized:
            images.append(
                (Path(img["path"]), base64.b64decode(img["data"].encode("utf-8")))
            )
        return images

    def store_chunk(
        self,
        content: str,
        metadata: ChunkMetadata,
        embeddings: Optional[List[float]] = None,
        image_embeddings: Optional[List[List[float]]] = None,
    ) -> str:
        """Store a chunk of content with its metadata and embeddings."""
        if not self.initialized:
            self.initialize()

        # Generate a unique ID
        chunk_id = f"chunk_{hash(content + str(metadata.__dict__))}"

        # Prepare document for storage
        doc = {
            "content": content,
            "title": metadata.title,
            "level": metadata.level,
            "page_number": metadata.page_number,
            "section_path": json.dumps(metadata.section_path),
            "images": json.dumps(self._serialize_images(metadata.images)),
            **(metadata.additional_metadata or {}),
        }

        # Add embeddings if provided
        if embeddings:
            doc["embedding"] = np.array(embeddings, dtype=np.float32).tobytes()

        # Store the document
        self.client.hset(chunk_id, mapping=doc)

        # Add to vector index
        if embeddings:
            self.client.ft_add(
                "text_idx",
                chunk_id,
                doc,
                embedding=np.array(embeddings, dtype=np.float32),
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
        if not self.initialized:
            self.initialize()

        # Build query
        search_query = ""
        if filter_metadata:
            conditions = []
            for key, value in filter_metadata.items():
                if isinstance(value, (list, dict)):
                    conditions.append(f"@{key} == '{json.dumps(value)}'")
                else:
                    conditions.append(f"@{key} == {value}")
            search_query = " ".join(conditions)

        # Perform vector search if embedding provided
        if query_embedding:
            results = self.client.ft_search(
                "text_idx",
                search_query,
                vector=np.array(query_embedding, dtype=np.float32),
                limit=limit,
            )
        else:
            # Fallback to text search
            results = self.client.ft_search(
                "text_idx", f"{query} {search_query}", limit=limit
            )

        # Convert results to SearchResult objects
        search_results = []
        for result in results:
            metadata_dict = result
            serialized_images = json.loads(metadata_dict["images"])
            images = self._deserialize_images(serialized_images)

            metadata = ChunkMetadata(
                title=metadata_dict["title"],
                level=int(metadata_dict["level"]),
                page_number=int(metadata_dict["page_number"]),
                section_path=json.loads(metadata_dict["section_path"]),
                images=images,
                additional_metadata={
                    k: v
                    for k, v in metadata_dict.items()
                    if k
                    not in [
                        "content",
                        "title",
                        "level",
                        "page_number",
                        "section_path",
                        "images",
                        "embedding",
                    ]
                },
            )

            search_results.append(
                SearchResult(
                    content=metadata_dict["content"],
                    metadata=metadata,
                    score=float(result.get("score", 0.0)),
                    image_paths=[str(path) for path, _ in images],
                )
            )

        return search_results

    def get_chunk(self, chunk_id: str) -> Optional[Tuple[str, ChunkMetadata]]:
        """Retrieve a specific chunk by ID."""
        if not self.initialized:
            self.initialize()

        try:
            result = self.client.hgetall(chunk_id)
            if not result:
                return None

            serialized_images = json.loads(result["images"])
            images = self._deserialize_images(serialized_images)

            metadata = ChunkMetadata(
                title=result["title"],
                level=int(result["level"]),
                page_number=int(result["page_number"]),
                section_path=json.loads(result["section_path"]),
                images=images,
                additional_metadata={
                    k: v
                    for k, v in result.items()
                    if k
                    not in [
                        "content",
                        "title",
                        "level",
                        "page_number",
                        "section_path",
                        "images",
                        "embedding",
                    ]
                },
            )

            return result["content"], metadata

        except Exception:
            return None

    def delete_chunk(self, chunk_id: str) -> bool:
        """Delete a chunk by ID."""
        if not self.initialized:
            self.initialize()

        try:
            # Remove from vector index
            self.client.ft_del("text_idx", chunk_id)
            # Remove from hash storage
            self.client.delete(chunk_id)
            return True
        except Exception:
            return False

    def clear(self) -> None:
        """Clear all stored data."""
        if self.initialized:
            self.client.ft_drop("text_idx")
            self.initialized = False
