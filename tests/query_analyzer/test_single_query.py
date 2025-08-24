"""Test a single query with the improved analyzer."""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.modules.query_analyzer.ollama_analyzer import OllamaQueryAnalyzer
from src.modules.query_analyzer.models import QueryAnalyzerConfig
from src.modules.query_analyzer.conversation_manager import ConversationManager
from src.modules.query_analyzer.conversation_state import UserLevel

def test_single_query():
    """Test a single query to see the full flow."""
    print("🧪 Testing Single Query Analysis")
    print("=" * 50)
    
    # Create analyzer
    config = QueryAnalyzerConfig(
        model_name="llama3.2",
        temperature=0.0,
        enable_query_expansion=True,
        enable_decomposition=False,
        enable_step_back=False,
        enable_clarification=False
    )
    
    analyzer = OllamaQueryAnalyzer(config)
    
    # Test query
    test_query = "How to optimize database performance?"
    print(f"Test Query: '{test_query}'")
    print("\n" + "─" * 50)
    
    # Test the schema extraction directly with debug content
    debug_content = '{"properties": {"expanded_queries": {"anyOf": [{"type": "string"}, {"type": "null"}], "title": "Optimization Techniques", "type": "array"}, "entities": {"description": "Key entities mentioned in the query", "items": {"type": "string"}, "title": "Entities", "type": "array"}, "query_type": {"description": "The type of query being asked", "enum": ["factual", "comparison", "aggregation", "explanation"], "title": "Query Type", "type": "string"}, "semantic_intent": {"description": "The core intent of what the user is trying to find", "title": "Semantic Intent", "type": "string"}, "time_filter": {"anyOf": [{"type": "string"}, {"type": "null"}], "default": null, "description": "Any time-based constraints in the query", "title": "Time Filter"}, "title": "Optimize Database Performance", "type": "object"}}'
    
    print("\n🔧 Testing Schema Extraction:")
    try:
        import json
        schema_dict = json.loads(debug_content)
        print("✅ Parsed schema successfully")
        print(f"Schema dict keys: {list(schema_dict.keys())}")
        print(f"Schema title: {schema_dict.get('title', 'NO TITLE')}")
        
        data = analyzer._extract_data_from_schema(schema_dict)
        print("✅ Schema extraction successful!")
        print(f"Extracted data: {data}")
    except Exception as e:
        print(f"❌ Schema extraction failed: {e}")
        import traceback
        traceback.print_exc()

    # Analyze
    try:
        intent = analyzer.analyze(test_query)
        
        print("\n✅ Analysis successful!")
        print(f"Query Type: {intent.query_type}")
        print(f"Entities: {intent.entities}")
        print(f"Semantic Intent: {intent.semantic_intent}")
        print(f"Expanded Queries: {intent.expanded_queries}")
        print(f"Time Filter: {intent.time_filter}")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()

def test_conversational_context():
    """Test query analysis with conversational context."""
    print("\n\n🧪 Testing Query Analysis with Conversational Context")
    print("=" * 50)
    
    # Create analyzer
    config = QueryAnalyzerConfig(
        model_name="llama3.2",
        temperature=0.0,
        enable_query_expansion=True,
        enable_decomposition=True,
        enable_step_back=True,
        enable_clarification=True
    )
    
    analyzer = OllamaQueryAnalyzer(config)
    
    # Create conversation manager
    manager = ConversationManager(
        query_analyzer=analyzer,
        enable_clarification=True
    )
    
    session_id = "test_session_123"
    
    # First query
    print("\n📝 First Query: 'Tell me about diesel engines'")
    result1 = manager.process_query(
        "Tell me about diesel engines",
        session_id=session_id
    )
    
    print(f"✅ Query Type: {result1.intent.query_type}")
    print(f"✅ Entities: {result1.intent.entities}")
    print(f"✅ Intent: {result1.intent.semantic_intent}")
    
    # Second query with context
    print("\n📝 Second Query: 'What about their maintenance?' (uses context)")
    result2 = manager.process_query(
        "What about their maintenance?",
        session_id=session_id
    )
    
    print(f"✅ Query Type: {result2.intent.query_type}")
    print(f"✅ Entities: {result2.intent.entities}")
    print(f"✅ Intent: {result2.intent.semantic_intent}")
    
    # Get session summary
    summary = manager.get_session_summary(session_id)
    print(f"\n📊 Session Summary:")
    print(f"   - Total turns: {summary['turn_count']}")
    print(f"   - Entities discussed: {summary['entities_mentioned']}")
    print(f"   - Topics: {summary['topics_discussed']}")
    
    # Test context-aware analysis directly
    print("\n🔬 Testing analyze_with_context directly:")
    context = "Previous discussion about diesel engines and their characteristics."
    intent_with_context = analyzer.analyze_with_context(
        "How often should they be serviced?",
        context=context
    )
    
    print(f"✅ Intent with context: {intent_with_context.semantic_intent}")
    print(f"✅ Entities: {intent_with_context.entities}")

def test_user_level_adaptation():
    """Test how analysis adapts to different user levels."""
    print("\n\n🧪 Testing User Level Adaptation")
    print("=" * 50)
    
    # Create analyzer and manager
    config = QueryAnalyzerConfig(
        model_name="llama3.2",
        temperature=0.0,
        enable_query_expansion=True
    )
    
    analyzer = OllamaQueryAnalyzer(config)
    manager = ConversationManager(query_analyzer=analyzer)
    
    query = "Explain how fuel injection works"
    
    # Test with novice user
    print("\n👶 Testing with NOVICE user:")
    manager.update_user_level("novice_session", UserLevel.NOVICE)
    result_novice = manager.process_query(query, "novice_session")
    
    print(f"✅ Query expansions for novice: {len(result_novice.intent.expanded_queries)}")
    if result_novice.intent.expanded_queries:
        print(f"   Example: {result_novice.intent.expanded_queries[0]}")
    
    # Test with expert user
    print("\n🎓 Testing with EXPERT user:")
    manager.update_user_level("expert_session", UserLevel.EXPERT)
    result_expert = manager.process_query(query, "expert_session")
    
    print(f"✅ Query expansions for expert: {len(result_expert.intent.expanded_queries)}")
    if result_expert.intent.expanded_queries:
        print(f"   Example: {result_expert.intent.expanded_queries[0]}")

if __name__ == "__main__":
    test_single_query()
    test_conversational_context()
    test_user_level_adaptation()