from typing import List, Optional

import chromadb
import numpy as np
from chromadb.config import Settings

from .factory import EmbedderFactory


class QueryManager:
    """Utility class for handling queries against the vector store."""

    def __init__(
        self,
        persist_directory: str = "./chroma_db",
        collection_name: str = "document_chunks",
        embedder_impl: str = "huggingface",
        embedding_kwargs: Optional[dict] = None,
    ):
        """
        Initialize the query manager.

        Args:
            persist_directory: Directory where ChromaDB is stored
            collection_name: Name of the ChromaDB collection
            embedder_impl: Name of the embedding model to use.
            embedding_kwargs: Additional arguments for the embedding model.
        """
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_collection(name=collection_name)
        self.embedder = EmbedderFactory.create(
            implementation=embedder_impl, **(embedding_kwargs or {})
        )

    def search(
        self,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[dict] = None,
        use_mmr: bool = True,
        lambda_param: float = 0.5,
    ) -> List[dict]:
        """
        Search the vector store using a text query.
        Can use Maximal Marginal Relevance for reranking.

        Args:
            query: The search query text
            n_results: Number of results to return
            filter_metadata: Optional metadata filters
            use_mmr: Whether to use MMR for reranking
            lambda_param: MMR trade-off (relevance vs. diversity)

        Returns:
            List of top-n_results documents.
        """
        if not self.embedder:
            raise RuntimeError("Embedder has not been initialized.")

        print(f"\nEmbedding query: {query}")
        query_embedding = self.embedder.embed_text(query)

        if not use_mmr:
            print("Performing standard similarity search.")
            results = self.collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=n_results,
                where=filter_metadata,
            )
            formatted_results = []
            if results["ids"]:
                for i in range(len(results["ids"][0])):
                    formatted_results.append(
                        {
                            "id": results["ids"][0][i],
                            "content": results["documents"][0][i],
                            "metadata": results["metadatas"][0][i],
                            "score": results["distances"][0][i]
                            if results["distances"]
                            else None,
                        }
                    )
            return formatted_results

        print("Performing search with Maximal Marginal Relevance (MMR).")
        query_embedding = np.array(query_embedding)

        # Step 2: Get a larger pool of results
        n_pool = max(n_results * 5, 20)
        print(f"Querying {n_pool} candidate results from ChromaDB...")

        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=n_pool,
            where=filter_metadata,
            include=["documents", "metadatas", "embeddings"],
        )

        if not results.get("embeddings") or len(results["embeddings"][0]) == 0:
            print("No documents retrieved from vector store.")
            return []

        doc_embeddings = np.array(results["embeddings"][0])
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        ids = results["ids"][0]

        # Step 3: Compute cosine similarities
        def cosine_similarity(vec_a, vec_b):
            norm_a = np.linalg.norm(vec_a)
            norm_b = np.linalg.norm(vec_b)
            return np.dot(vec_a, vec_b) / (norm_a * norm_b + 1e-8)

        similarities = np.dot(doc_embeddings, query_embedding) / (
            np.linalg.norm(doc_embeddings, axis=1) * np.linalg.norm(query_embedding)
            + 1e-8
        )

        # Step 4: Apply MMR
        selected_indices = []
        candidate_indices = list(range(len(doc_embeddings)))

        for _ in range(min(n_results, len(doc_embeddings))):
            if not candidate_indices:
                break

            if not selected_indices:
                selected = np.argmax(similarities)
                selected_indices.append(selected)
                candidate_indices.remove(selected)
                print(
                    f"Step {len(selected_indices)}: Selected most relevant index {selected} (score={similarities[selected]:.4f})"
                )
                continue

            mmr_scores = []
            for idx in candidate_indices:
                relevance = similarities[idx]
                diversity = max(
                    [
                        cosine_similarity(doc_embeddings[idx], doc_embeddings[sel_idx])
                        for sel_idx in selected_indices
                    ]
                )
                mmr_score = lambda_param * relevance - (1 - lambda_param) * diversity
                mmr_scores.append((idx, mmr_score))

            if not mmr_scores:
                break

            next_idx, next_score = max(mmr_scores, key=lambda x: x[1])
            selected_indices.append(next_idx)
            candidate_indices.remove(next_idx)
            print(
                f"Step {len(selected_indices)}: Selected index {next_idx} with MMR score={next_score:.4f}"
            )

        # Step 5: Format and return top documents
        formatted_results = []
        for idx in selected_indices:
            formatted_results.append(
                {
                    "id": ids[idx],
                    "content": documents[idx],
                    "metadata": metadatas[idx],
                    "score": float(similarities[idx]),
                }
            )

        return formatted_results

    def list_all_documents(self, limit: int = 10) -> List[dict]:
        """
        List all documents in the collection.

        Args:
            limit: Maximum number of documents to return

        Returns:
            List of documents with their content and metadata
        """
        results = self.collection.get()

        formatted_results = []
        for i in range(min(limit, len(results["ids"]))):
            formatted_results.append(
                {
                    "id": results["ids"][i],
                    "content": results["documents"][i],
                    "metadata": results["metadatas"][i],
                }
            )

        return formatted_results
