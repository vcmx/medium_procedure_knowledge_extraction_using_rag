"""
Demo script for the Tavily Search Agent integration.

This script demonstrates how to use the search agent within the multi-agent system.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.modules.agent import AgentController
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def demo_search_agent():
    """Demonstrate the search agent functionality."""
    
    # Check for API key
    if not os.getenv("TAVILY_API_KEY"):
        print("\n⚠️  WARNING: TAVILY_API_KEY not found in environment variables!")
        print("To use the search agent, please set your Tavily API key:")
        print("export TAVILY_API_KEY='your-api-key-here'")
        print("\nGet your API key from: https://tavily.com")
        print("\nContinuing demo without search agent...\n")
        enable_search = False
    else:
        enable_search = True
        print("✅ Tavily API key found. Search agent enabled.")
    
    # Initialize controller with search agent
    print("\n🤖 Initializing Agent System...")
    controller = AgentController(
        llm_model="llama3.2",
        enable_rag=False,  # Keep disabled for now
        enable_mcp=False,  # Keep disabled for now
        enable_search=enable_search
    )
    
    # Create a session
    session_id = controller.create_session(user_level="EXPERIENCED")
    print(f"📝 Created session: {session_id}")
    
    # Demo queries
    demo_queries = [
        "What are the latest developments in quantum computing in 2024?",
        "Tell me about recent breakthroughs in AI safety research",
        "What's the current state of renewable energy adoption globally?"
    ]
    
    if not enable_search:
        # Use simpler queries that don't require web search
        demo_queries = [
            "Explain how a neural network works",
            "What are the main components of a computer?",
            "Describe the software development lifecycle"
        ]
        print("\n📌 Using alternative queries that don't require web search...")
    
    # Process each query
    for i, query in enumerate(demo_queries, 1):
        print(f"\n{'='*60}")
        print(f"Query {i}: {query}")
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
                            if len(content) > 200:
                                content = content[:200] + "..."
                            print(f"   Output: {content}")
            
        except Exception as e:
            print(f"\n❌ Error processing query: {str(e)}")
            logger.error(f"Error details: ", exc_info=True)
    
    print(f"\n{'='*60}")
    print("Demo completed!")
    
    # Show available agents
    print(f"\n📊 Available agents in this session: {controller.available_agents}")
    
    if enable_search:
        print("\n💡 The search agent successfully integrated web search capabilities!")
        print("   It can now fetch current information from the internet.")
    else:
        print("\n💡 To enable web search, set your TAVILY_API_KEY environment variable.")


def demo_search_only():
    """Demo just the search agent directly."""
    if not os.getenv("TAVILY_API_KEY"):
        print("⚠️  TAVILY_API_KEY not set. Cannot run search-only demo.")
        return
    
    print("\n🔍 Direct Search Agent Demo")
    print("="*40)
    
    from src.modules.agent.search_agent import TavilySearchAgent
    from src.modules.agent.base import AgentState
    from langchain_core.messages import HumanMessage
    
    # Create search agent
    agent = TavilySearchAgent(max_results=3)
    
    # Create a simple state
    state = AgentState(
        messages=[HumanMessage(content="What happened in AI today?")],
        current_agent="search",
        next_agent=None,
        task_description="Search for AI news",
        workflow_stage="processing",
        clarification_needed=False,
        clarification_questions=[],
        user_responses={},
        original_query="What happened in AI today?",
        enhanced_query=None,
        analysis_results={},
        retrieval_results=None,
        tool_calls=[],
        tool_results=[],
        session_id="demo",
        user_level="EXPERIENCED"
    )
    
    # Process the search
    print("\n🔎 Searching for: 'What happened in AI today?'")
    response = agent.process(state)
    
    print(f"\n📄 Search Results:")
    print(response.message)
    
    print(f"\n📊 Metadata:")
    print(f"   - Query: {response.metadata.get('search_query')}")
    print(f"   - Results found: {response.metadata.get('num_results')}")


if __name__ == "__main__":
    print("🚀 Tavily Search Agent Integration Demo")
    print("="*60)
    
    # Run main demo
    demo_search_agent()
    
    # Optionally run direct search demo
    if os.getenv("TAVILY_API_KEY"):
        print("\n\n" + "="*60)
        input("\nPress Enter to run direct search agent demo...")
        demo_search_only()