"""
Demo script showing enhanced search functionality in the agent system.
This demonstrates how step-back questions can be sent to the search agent.
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch, Mock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.modules.agent import AgentController
from src.modules.agent.search_agent import TavilySearchAgent
from src.modules.agent.base import AgentState
from langchain_core.messages import HumanMessage
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def demo_search_with_step_back_questions():
    """Demo search functionality with step-back questions."""
    
    print("🚀 Enhanced Search Agent Demo")
    print("="*60)
    print("This demo shows how step-back questions can be sent to the search agent")
    print("="*60)
    
    # Mock search results for demo
    mock_search_results = [
        {
            "title": "Latest AI Research 2024 - Machine Learning Advances",
            "url": "https://example.com/ai-research",
            "content": "Recent breakthroughs in artificial intelligence include improved transformer architectures, better reasoning capabilities, and enhanced multimodal understanding."
        },
        {
            "title": "What is Artificial Intelligence? Complete Guide",
            "url": "https://example.com/ai-guide", 
            "content": "AI is the simulation of human intelligence processes by machines, especially computer systems. These processes include learning, reasoning, and self-correction."
        },
        {
            "title": "History of AI Development Timeline",
            "url": "https://example.com/ai-history",
            "content": "The history of AI spans from the 1950s with early computational theories to modern deep learning and neural networks of the 2020s."
        }
    ]
    
    with patch('src.modules.agent.search_agent.TavilySearchResults') as mock_tavily_class:
        # Mock the search tool
        mock_search_tool = Mock()
        mock_search_tool.invoke.return_value = mock_search_results
        mock_tavily_class.return_value = mock_search_tool
        
        # Mock environment variable for API key
        with patch.dict(os.environ, {'TAVILY_API_KEY': 'mock-api-key'}):
            
            print("✅ Mock Tavily API key set")
            
            # Initialize controller with search enabled
            print("\n🤖 Initializing Agent System with Search...")
            controller = AgentController(
                llm_model="llama3.2",
                enable_rag=False,
                enable_mcp=False,
                enable_search=True
            )
            
            print(f"📊 Available agents: {controller.available_agents}")
            
            # Create session
            session_id = controller.create_session("EXPERIENCED")
            print(f"📝 Created session: {session_id}")
            
            # Demo query that generates step-back questions
            query = "How does artificial intelligence work?"
            print(f"\n{'='*60}")
            print(f"Demo Query: {query}")
            print(f"{'='*60}")
            
            # Process query to get step-back questions
            print("\n🔍 Step 1: Processing query to get analysis and step-back questions...")
            
            step_back_questions = []
            analysis_results = {}
            
            try:
                for update in controller.process_query(query, session_id):
                    agent = update.get("agent", "unknown")
                    output = update.get("output", {})
                    
                    print(f"🔄 {agent} agent processing...")
                    
                    if agent == "query_analyzer":
                        # Extract step-back questions from analysis
                        analysis_results = output.get("analysis_results", {})
                        step_back_questions = analysis_results.get("step_back_questions", [])
                        
                        if step_back_questions:
                            print(f"\n📋 Generated {len(step_back_questions)} step-back questions:")
                            for i, q in enumerate(step_back_questions[:3], 1):
                                print(f"   {i}. {q}")
                        break
                    
                    if agent == "system" and output.get("type") == "error":
                        print(f"❌ Error: {output.get('error')}")
                        break
            
            except Exception as e:
                print(f"❌ Error in query processing: {e}")
                return
            
            # Demo searching for step-back questions
            if step_back_questions:
                print(f"\n🔍 Step 2: Searching for step-back questions...")
                print(f"{'─'*60}")
                
                # Search for first few step-back questions
                for i, question in enumerate(step_back_questions[:2], 1):
                    print(f"\n🔎 Search {i}: {question}")
                    print("─" * 40)
                    
                    # Create search agent and search
                    search_agent = TavilySearchAgent(max_results=3)
                    
                    # Create state for search
                    search_state = AgentState(
                        messages=[HumanMessage(content=question)],
                        current_agent="search",
                        next_agent=None,
                        task_description=f"Search for: {question}",
                        workflow_stage="processing",
                        clarification_needed=False,
                        clarification_questions=[],
                        user_responses={},
                        original_query=question,
                        enhanced_query=None,
                        analysis_results={},
                        retrieval_results=None,
                        tool_calls=[],
                        tool_results=[],
                        session_id=session_id,
                        user_level="EXPERIENCED"
                    )
                    
                    # Process search
                    search_response = search_agent.process(search_state)
                    
                    if search_response.error:
                        print(f"❌ Search error: {search_response.error}")
                    else:
                        print("📄 Search Results:")
                        content = search_response.message.replace("## Web Search Results", "").strip()
                        print(content)
                        
                        metadata = search_response.metadata
                        print(f"\n📊 Found {metadata.get('num_results', 0)} results")
                
                print(f"\n{'='*60}")
                print("✅ Search demo completed successfully!")
                print("\n💡 In the interactive demo, users would be prompted:")
                print("   'Would you like to search the web for these questions? (y/n)'")
                print("   This provides additional context for better answers.")
                
            else:
                print("\n⚠️ No step-back questions generated for this query")


def demo_direct_search_command():
    """Demo the direct search command functionality."""
    
    print(f"\n🔍 Direct Search Command Demo")
    print("="*40)
    
    # Mock search for a specific query
    mock_results = [
        {
            "title": "Current AI Stock Market Trends 2024",
            "url": "https://example.com/ai-stocks",
            "content": "AI companies have seen significant growth in 2024, with major investments in generative AI and machine learning infrastructure."
        }
    ]
    
    with patch('src.modules.agent.search_agent.TavilySearchResults') as mock_tavily:
        mock_tool = Mock()
        mock_tool.invoke.return_value = mock_results
        mock_tavily.return_value = mock_tool
        
        with patch.dict(os.environ, {'TAVILY_API_KEY': 'mock-key'}):
            
            search_query = "What are the latest AI stock market trends?"
            print(f"\nDirect search query: {search_query}")
            print("─" * 40)
            
            # Create search agent directly
            search_agent = TavilySearchAgent(max_results=3)
            
            # Create simple state
            state = AgentState(
                messages=[HumanMessage(content=search_query)],
                current_agent="search",
                next_agent=None,
                task_description=f"Search for: {search_query}",
                workflow_stage="processing",
                clarification_needed=False,
                clarification_questions=[],
                user_responses={},
                original_query=search_query,
                enhanced_query=None,
                analysis_results={},
                retrieval_results=None,
                tool_calls=[],
                tool_results=[],
                session_id="direct-search",
                user_level="EXPERIENCED"
            )
            
            # Process search
            response = search_agent.process(state)
            
            if response.error:
                print(f"❌ Error: {response.error}")
            else:
                print("📄 Search Results:")
                content = response.message.replace("## Web Search Results", "").strip()
                print(content)
                
                print(f"\n📊 Search completed: {response.metadata.get('num_results', 0)} results found")
    
    print("\n💡 In the interactive demo, users can run:")
    print("   search <query>  - to perform direct web searches")


def main():
    """Run all demos."""
    # Demo 1: Step-back questions with search
    demo_search_with_step_back_questions()
    
    # Demo 2: Direct search command
    demo_direct_search_command()
    
    print(f"\n{'='*60}")
    print("🎉 All search enhancement demos completed!")
    print("\n🚀 To use the interactive demo with search:")
    print("   1. Set TAVILY_API_KEY environment variable")
    print("   2. Run: python tests/agent/interactive_agent_demo.py")
    print("   3. Enable search agent when prompted")
    print("   4. Try queries that generate step-back questions")
    print("   5. Use 'search <query>' command for direct searches")


if __name__ == "__main__":
    main()