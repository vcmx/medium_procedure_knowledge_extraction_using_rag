from pprint import pprint

import chromadb
from chromadb.config import Settings

from src.modules.embeddings.query_utils import QueryManager
from src.modules.storage_manager.factory import StorageManagerFactory


def wipe_database():
    """Wipe the ChromaDB database."""
    # Method 1: Using StorageManager
    storage = StorageManagerFactory.create(
        implementation="chroma",
        persist_directory="./chroma_db",
        collection_name="document_chunks",
    )
    storage.initialize()
    storage.clear()
    print("Database wiped using StorageManager")

    # Method 2: Direct ChromaDB client
    client = chromadb.PersistentClient(
        path="./chroma_db", settings=Settings(anonymized_telemetry=False)
    )
    try:
        collection = client.get_collection("document_chunks")
        collection.delete(where={})
        print("Database wiped using direct ChromaDB client")
    except Exception as e:
        print(f"Error wiping database: {e}")


def check_database():
    """Check the contents of the ChromaDB database."""
    # Initialize query manager
    query_manager = QueryManager(
        persist_directory="./chroma_db",
        collection_name="document_chunks",
        embedding_model="clip",
    )

    # List all documents
    print("\n=== All Stored Documents ===")
    results = query_manager.list_all_documents(limit=10)
    print(f"\nTotal documents retrieved: {len(results)}")

    # Print sample documents
    print("\n=== Sample Documents ===")
    for i, doc in enumerate(results):
        print(f"\nDocument {i+1}:")
        print(f"ID: {doc['id']}")
        print(f"Content preview: {doc['content'][:200]}...")
        print("Metadata:")
        pprint(doc["metadata"])

    # Try a sample search
    print("\n=== Sample Search Results ===")
    search_results = query_manager.search(query="engine section", n_results=2)

    print("\nSearch results for 'engine section':")
    for i, result in enumerate(search_results):
        print(f"\nResult {i+1}:")
        print(f"ID: {result['id']}")
        print(f"Content preview: {result['content'][:200]}...")
        print("Metadata:")
        pprint(result["metadata"])
        if result["score"] is not None:
            print(f"Distance score: {result['score']}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        if command == "wipe":
            wipe_database()
        elif command == "check":
            check_database()
        else:
            print("Unknown command. Use 'wipe' or 'check'")
    else:
        print("Please specify a command: 'wipe' or 'check'")
