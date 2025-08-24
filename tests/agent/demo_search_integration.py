"""
Simple demo to show search agent integration in the agent system.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.modules.agent import AgentController
from unittest.mock import patch, Mock
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def demo_with_mock_search():
    """Demo search agent integration with mocked Tavily API."""
    
    print("🚀 Search Agent Integration Demo (Mocked)")
    print("="*60)
    
    # Mock Tavily API for demo purposes
    mock_search_results = [
        {
            "title": "Latest AI Research Breakthroughs 2024",
            "url": "https://example.com/ai-research-2024", 
            "content": "Recent advances in large language models and neural architectures have led to significant improvements in AI capabilities, including better reasoning and multimodal understanding."
        },
        {
            "title": "Quantum Computing Progress Report",
            "url": "https://example.com/quantum-progress",
            "content": "Quantum computers achieved new milestones in 2024 with improved error correction and increased qubit counts, bringing practical quantum advantage closer to reality."
        }
    ]
    
    with patch('src.modules.agent.search_agent.TavilySearchResults') as mock_tavily_class:
        # Mock the search tool
        mock_search_tool = Mock()
        mock_search_tool.invoke.return_value = mock_search_results
        mock_tavily_class.return_value = mock_search_tool
        
        # Mock environment variable for API key
        with patch.dict(os.environ, {'TAVILY_API_KEY': 'mock-api-key'}):
            
            print("✅ Mock Tavily API key set. Search agent enabled.")
            
            # Initialize controller with search agent
            print("\n🤖 Initializing Agent System with Search...")
            controller = AgentController(
                llm_model="llama3.2",
                enable_rag=False,  # Keep disabled for now
                enable_mcp=False,  # Keep disabled for now
                enable_search=True  # Enable search agent
            )
            
            print(f"📊 Available agents: {controller.available_agents}")
            
            # Create a session
            session_id = controller.create_session(user_level="EXPERIENCED")
            print(f"📝 Created session: {session_id}")
            
            # Test query that should use search
            query = "What are the latest developments in AI and quantum computing?"
            print(f"\n{'='*60}")
            print(f"Query: {query}")
            print('='*60)
            
            try:
                # Process the query
                for update in controller.process_query(query, session_id):
                    agent = update.get("agent", "unknown")
                    output = update.get("output", {})
                    
                    if agent == "system":
                        output_type = output.get("type", "unknown")
                        if output_type == "final_result":
                            print(f"\n✅ Processing completed!")
                        elif output_type == "error":
                            print(f"\n❌ Error: {output.get('error', 'Unknown error')}")
                    else:
                        print(f"\n🔄 {agent} agent processing...")
                        # If there are messages in the output, show the latest one
                        if "messages" in output and output["messages"]:
                            latest_message = output["messages"][-1]
                            if hasattr(latest_message, 'content'):
                                content = latest_message.content
                                # Show more content for search results
                                if agent == "search":
                                    print(f"   🔍 Search Results:")
                                    if len(content) > 500:
                                        content = content[:500] + "..."
                                    print(f"   {content}")
                                else:
                                    if len(content) > 200:
                                        content = content[:200] + "..."
                                    print(f"   Output: {content}")
                
                # Verify search was called
                if mock_search_tool.invoke.called:
                    print(f"\n✅ Search agent successfully called with query!")
                    call_args = mock_search_tool.invoke.call_args[0][0]
                    print(f"   Search query: {call_args.get('query', 'Unknown')}")
                else:
                    print(f"\n⚠️  Search agent was not called (supervisor didn't route to search)")
                
            except Exception as e:
                print(f"\n❌ Error processing query: {str(e)}")
                logger.error(f"Error details: ", exc_info=True)
    
    print(f"\n{'='*60}")
    print("Mock Search Demo completed!")
    print("\n💡 This demo shows that the search agent is properly integrated.")
    print("   In real usage, set TAVILY_API_KEY to enable actual web search.")


def demo_agent_routing():
    """Demo showing how the supervisor routes to different agents."""
    
    print("\n🧠 Agent Routing Demo")
    print("="*40)
    
    # Test different query types to see routing decisions
    test_queries = [
        ("Explain neural networks", "Should route to query_analyzer (general knowledge)"),
        ("What's happening in AI today?", "Should route to search (current events)"),
        ("Calculate the fibonacci sequence", "Should route to MCP (if enabled)")
    ]
    
    controller = AgentController(
        enable_search=False,  # Disable to see routing logic
        enable_rag=False,
        enable_mcp=False
    )
    
    session_id = controller.create_session()
    
    for query, expected in test_queries:
        print(f"\n📝 Query: {query}")
        print(f"🎯 Expected: {expected}")
        
        # Just check the first routing decision
        try:
            for update in controller.process_query(query, session_id):
                agent = update.get("agent", "unknown")
                if agent != "system":
                    print(f"✅ Routed to: {agent}")
                    break
        except:
            print("❌ Error in processing")


if __name__ == "__main__":
    # Run mock search demo
    demo_with_mock_search()
    
    # Run routing demo
    demo_agent_routing()