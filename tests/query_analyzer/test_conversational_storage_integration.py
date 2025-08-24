"""Integration test for conversational flow with storage retrieval."""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.modules.query_analyzer.conversational_workflow import ConversationalWorkflow
from src.modules.query_analyzer.conversation_state import UserLevel
from src.modules.query_analyzer.enhanced_retriever import EnhancedRetriever
from src.modules.embeddings.factory import EmbedderFactory
from src.modules.storage_manager.factory import StorageManagerFactory
from src.modules.query_analyzer.factory import create_query_analyzer
import tempfile
import shutil


def test_conversational_retrieval_integration():
    """Test conversational flow integrated with retrieval."""
    print("🧪 Testing Conversational Flow with Storage Integration")
    print("=" * 60)
    
    # Create temporary directory for test storage
    temp_dir = tempfile.mkdtemp()
    print(f"📁 Using temporary storage: {temp_dir}")
    
    try:
        # 1. Setup storage and embedder
        print("\n1️⃣ Setting up storage and embedder...")
        embedder = EmbedderFactory.create(implementation="clip")
        storage_manager = StorageManagerFactory.create(
            implementation="chroma",
            persist_directory=temp_dir
        )
        
        # 2. Add some test documents
        print("\n2️⃣ Adding test documents to storage...")
        test_documents = [
            {
                "content": "Diesel engines use compression ignition. They compress air to high temperatures, then inject fuel which auto-ignites.",
                "metadata": {"topic": "diesel_engines", "subtopic": "operation"}
            },
            {
                "content": "Diesel engine maintenance includes regular oil changes every 5,000-10,000 miles, fuel filter replacement, and air filter checks.",
                "metadata": {"topic": "diesel_engines", "subtopic": "maintenance"}
            },
            {
                "content": "Common diesel engine problems include injector failures, turbocharger issues, and EGR valve problems.",
                "metadata": {"topic": "diesel_engines", "subtopic": "problems"}
            },
            {
                "content": "Fuel injection systems deliver precise amounts of fuel at high pressure. Modern systems use electronic control for optimal timing.",
                "metadata": {"topic": "fuel_systems", "subtopic": "injection"}
            }
        ]
        
        for i, doc in enumerate(test_documents):
            embedding = embedder.embed_text(doc["content"])
            storage_manager.add(
                embeddings=[embedding],
                metadatas=[doc["metadata"]],
                documents=[doc["content"]],
                ids=[f"doc_{i}"]
            )
        
        print(f"✅ Added {len(test_documents)} documents to storage")
        
        # 3. Create conversational workflow
        print("\n3️⃣ Creating conversational workflow...")
        workflow = ConversationalWorkflow(
            analyzer_type="ollama",
            enable_relevance_check=True,
            enable_clarification=True
        )
        
        # 4. Create enhanced retriever
        print("\n4️⃣ Creating enhanced retriever...")
        analyzer = create_query_analyzer("ollama")
        retriever = EnhancedRetriever(
            query_analyzer=analyzer,
            storage_manager=storage_manager,
            embedder=embedder
        )
        
        session_id = "test_retrieval_session"
        
        # 5. Test conversational queries with retrieval
        print("\n5️⃣ Testing conversational queries with retrieval...")
        
        # Query 1: Initial broad query
        print("\n📝 Query 1: 'Tell me about diesel engines'")
        result1, metadata1 = workflow.process_user_query(
            "Tell me about diesel engines",
            session_id=session_id,
            user_level=UserLevel.NOVICE
        )
        
        if not result1.rejection_reason:
            # Retrieve documents using the analyzed intent
            retrieval_queries = analyzer.get_retrieval_queries(result1.processed_query)
            print(f"   Retrieval queries: {retrieval_queries[:2]}")  # Show first 2
            
            search_results = retriever.retrieve(
                result1.processed_query,
                limit=3,
                use_query_expansion=True
            )
            
            print(f"   ✅ Retrieved {len(search_results)} documents")
            for i, result in enumerate(search_results, 1):
                print(f"      {i}. Score: {result.score:.3f} | Topic: {result.metadata.get('subtopic', 'N/A')}")
        
        # Query 2: Follow-up with context
        print("\n📝 Query 2: 'What maintenance do they need?' (using context)")
        result2, metadata2 = workflow.process_user_query(
            "What maintenance do they need?",
            session_id=session_id
        )
        
        if not result2.rejection_reason:
            # The query should understand "they" refers to diesel engines
            print(f"   Intent: {result2.intent.semantic_intent}")
            print(f"   Entities: {result2.intent.entities}")
            
            search_results = retriever.retrieve(
                result2.processed_query,
                limit=3,
                use_query_expansion=True
            )
            
            print(f"   ✅ Retrieved {len(search_results)} documents")
            for i, result in enumerate(search_results, 1):
                print(f"      {i}. Score: {result.score:.3f} | Topic: {result.metadata.get('subtopic', 'N/A')}")
                if i == 1:  # Show content of top result
                    print(f"         Content: {result.content[:100]}...")
        
        # Query 3: More specific follow-up
        print("\n📝 Query 3: 'What about common problems?' (using context)")
        result3, metadata3 = workflow.process_user_query(
            "What about common problems?",
            session_id=session_id
        )
        
        if not result3.rejection_reason:
            print(f"   Intent: {result3.intent.semantic_intent}")
            
            # Use enhanced retrieval with analysis
            retrieval_result = retriever.retrieve_with_analysis(
                result3.processed_query,
                limit=3
            )
            
            print(f"   ✅ Analysis included {len(retrieval_result['analysis']['retrieval_queries'])} query variations")
            print(f"   ✅ Retrieved {len(retrieval_result['results'])} documents")
            
            # Show top result
            if retrieval_result['results']:
                top_result = retrieval_result['results'][0]
                print(f"   📄 Top result (score: {top_result.score:.3f}):")
                print(f"      {top_result.content[:150]}...")
        
        # 6. Test session summary
        print("\n6️⃣ Session Summary:")
        summary = workflow.get_session_summary(session_id)
        print(f"   Total turns: {summary['turn_count']}")
        print(f"   Entities discussed: {summary['entities_mentioned']}")
        print(f"   Topics: {summary['topics_discussed']}")
        print(f"   Duration: {summary['duration_seconds']:.1f} seconds")
        
        # 7. Test irrelevant query rejection
        print("\n7️⃣ Testing irrelevant query rejection:")
        result_irrelevant, _ = workflow.process_user_query(
            "What's the weather like today?",
            session_id=session_id
        )
        
        if result_irrelevant.rejection_reason:
            print(f"   ❌ Query correctly rejected: {result_irrelevant.rejection_reason}")
        else:
            print(f"   ⚠️  Query was not rejected (relevance score: {result_irrelevant.relevance_score})")
        
    finally:
        # Cleanup
        print(f"\n🧹 Cleaning up temporary storage: {temp_dir}")
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    print("\n✅ Integration test completed successfully!")


def test_clarification_with_retrieval():
    """Test clarification flow with retrieval."""
    print("\n\n🧪 Testing Clarification Flow with Retrieval")
    print("=" * 60)
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Setup
        embedder = EmbedderFactory.create(implementation="clip")
        storage_manager = StorageManagerFactory.create(
            implementation="chroma",
            persist_directory=temp_dir
        )
        
        # Add documents about different types of engines
        documents = [
            "Diesel engines in cars require oil changes every 5,000-10,000 miles.",
            "Marine diesel engines need specialized maintenance due to saltwater exposure.",
            "Truck diesel engines have different maintenance schedules than passenger vehicles.",
            "Generator diesel engines require regular load testing and fuel treatment."
        ]
        
        for i, doc in enumerate(documents):
            embedding = embedder.embed_text(doc)
            storage_manager.add(
                embeddings=[embedding],
                documents=[doc],
                ids=[f"clarify_doc_{i}"]
            )
        
        # Create workflow and retriever
        workflow = ConversationalWorkflow(
            analyzer_type="ollama",
            enable_clarification=True
        )
        
        analyzer = create_query_analyzer("ollama")
        retriever = EnhancedRetriever(
            query_analyzer=analyzer,
            storage_manager=storage_manager,
            embedder=embedder
        )
        
        session_id = "clarification_test"
        
        # Ambiguous query that should trigger clarification
        print("\n📝 Ambiguous Query: 'How often to change oil?'")
        
        # Simulate clarification responses
        clarification_responses = {
            "What type of engine?": "Diesel engine",
            "What type of vehicle?": "Passenger car",
            "What are the typical driving conditions?": "Mixed city and highway"
        }
        
        # Process with simulated clarifications
        from src.modules.query_analyzer.conversation_manager import ConversationManager
        manager = ConversationManager(
            query_analyzer=analyzer,
            enable_clarification=True
        )
        
        result = manager.process_query(
            "How often to change oil?",
            session_id=session_id,
            user_responses=clarification_responses
        )
        
        print(f"\n✅ Original query: '{result.original_query}'")
        print(f"✅ Processed query: '{result.processed_query}'")
        print(f"✅ Clarifications made: {len(result.clarifications)}")
        
        if result.clarifications:
            print("\n📋 Clarification details:")
            for c in result.clarifications:
                print(f"   Q: {c.question}")
                print(f"   A: {c.answer}")
        
        # Retrieve with clarified query
        print("\n🔍 Retrieving with clarified context...")
        search_results = retriever.retrieve(
            result.processed_query,
            limit=2
        )
        
        print(f"✅ Retrieved {len(search_results)} relevant documents:")
        for i, sr in enumerate(search_results, 1):
            print(f"   {i}. Score: {sr.score:.3f}")
            print(f"      Content: {sr.content}")
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    test_conversational_retrieval_integration()
    test_clarification_with_retrieval()