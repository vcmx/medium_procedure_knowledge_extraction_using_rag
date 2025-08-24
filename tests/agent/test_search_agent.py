"""
Tests for the Tavily Search Agent.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import os
from langchain_core.messages import HumanMessage

from src.modules.agent.search_agent import TavilySearchAgent
from src.modules.agent.base import AgentState, AgentType


class TestTavilySearchAgent(unittest.TestCase):
    """Test cases for the Tavily Search Agent."""
    
    def setUp(self):
        """Set up test environment."""
        # Mock environment variable
        self.original_api_key = os.environ.get("TAVILY_API_KEY")
        os.environ["TAVILY_API_KEY"] = "test-api-key"
        
        # Create mock LLM
        self.mock_llm = Mock()
        self.mock_llm.invoke.return_value = Mock(content="Summarized search results")
    
    def tearDown(self):
        """Clean up test environment."""
        # Restore original API key
        if self.original_api_key:
            os.environ["TAVILY_API_KEY"] = self.original_api_key
        else:
            os.environ.pop("TAVILY_API_KEY", None)
    
    @patch('src.modules.agent.search_agent.TavilySearchResults')
    def test_initialization_with_api_key(self, mock_tavily_class):
        """Test agent initialization with API key."""
        # Initialize agent
        agent = TavilySearchAgent(
            llm=self.mock_llm,
            tavily_api_key="custom-api-key",
            max_results=3,
            search_depth="basic"
        )
        
        # Verify initialization
        self.assertEqual(agent.name, "search")
        mock_tavily_class.assert_called_once_with(
            api_key="custom-api-key",
            max_results=3,
            search_depth="basic",
            include_answer=True,
            include_raw_content=False,
            include_images=False
        )
    
    @patch('src.modules.agent.search_agent.TavilySearchResults')
    def test_initialization_with_env_var(self, mock_tavily_class):
        """Test agent initialization with environment variable."""
        # Initialize agent without explicit API key
        agent = TavilySearchAgent(llm=self.mock_llm)
        
        # Verify it uses environment variable
        mock_tavily_class.assert_called_once()
        call_args = mock_tavily_class.call_args[1]
        self.assertEqual(call_args['api_key'], "test-api-key")
    
    def test_initialization_without_api_key(self):
        """Test that initialization fails without API key."""
        # Remove API key from environment
        os.environ.pop("TAVILY_API_KEY", None)
        
        # Should raise ValueError
        with self.assertRaises(ValueError) as context:
            TavilySearchAgent(llm=self.mock_llm)
        
        self.assertIn("Tavily API key not provided", str(context.exception))
    
    @patch('src.modules.agent.search_agent.TavilySearchResults')
    def test_process_search_query(self, mock_tavily_class):
        """Test processing a search query."""
        # Mock search results
        mock_search_tool = Mock()
        mock_search_results = [
            {
                "title": "Result 1",
                "url": "https://example.com/1",
                "content": "First search result content"
            },
            {
                "title": "Result 2", 
                "url": "https://example.com/2",
                "content": "Second search result content"
            }
        ]
        mock_search_tool.invoke.return_value = mock_search_results
        mock_tavily_class.return_value = mock_search_tool
        
        # Initialize agent
        agent = TavilySearchAgent(llm=self.mock_llm)
        
        # Create test state
        state = AgentState(
            messages=[HumanMessage(content="What is the latest news about AI?")],
            current_agent="search",
            next_agent=None,
            task_description="Search for AI news",
            workflow_stage="processing",
            clarification_needed=False,
            clarification_questions=[],
            user_responses={},
            original_query="What is the latest news about AI?",
            enhanced_query=None,
            analysis_results={},
            retrieval_results=None,
            tool_calls=[],
            tool_results=[],
            session_id="test-session",
            user_level="EXPERIENCED"
        )
        
        # Process the query
        response = agent.process(state)
        
        # Verify search was performed
        mock_search_tool.invoke.assert_called_once_with(
            {"query": "What is the latest news about AI?"}
        )
        
        # Verify response
        self.assertEqual(response.agent_name, "search")
        self.assertEqual(response.next_agent, "supervisor")
        self.assertIn("Web Search Results", response.message)
        self.assertEqual(response.metadata["search_query"], "What is the latest news about AI?")
        self.assertEqual(response.metadata["num_results"], 2)
        self.assertFalse(response.requires_user_input)
        self.assertIsNone(response.error)
    
    @patch('src.modules.agent.search_agent.TavilySearchResults')
    def test_process_empty_state(self, mock_tavily_class):
        """Test processing with empty state."""
        # Initialize agent
        agent = TavilySearchAgent(llm=self.mock_llm)
        
        # Create empty state
        state = AgentState(
            messages=[],
            current_agent="search",
            next_agent=None,
            task_description="",
            workflow_stage="processing",
            clarification_needed=False,
            clarification_questions=[],
            user_responses={},
            original_query=None,
            enhanced_query=None,
            analysis_results={},
            retrieval_results=None,
            tool_calls=[],
            tool_results=[],
            session_id="test-session",
            user_level="EXPERIENCED"
        )
        
        # Process the empty state
        response = agent.process(state)
        
        # Should return error response
        self.assertEqual(response.agent_name, "search")
        self.assertEqual(response.message, "No search query provided.")
        self.assertEqual(response.error, "No messages in state")
    
    @patch('src.modules.agent.search_agent.TavilySearchResults')
    def test_process_search_error(self, mock_tavily_class):
        """Test handling of search errors."""
        # Mock search tool that raises exception
        mock_search_tool = Mock()
        mock_search_tool.invoke.side_effect = Exception("Search API error")
        mock_tavily_class.return_value = mock_search_tool
        
        # Initialize agent
        agent = TavilySearchAgent(llm=self.mock_llm)
        
        # Create test state
        state = AgentState(
            messages=[HumanMessage(content="Search query")],
            current_agent="search",
            next_agent=None,
            task_description="Search task",
            workflow_stage="processing",
            clarification_needed=False,
            clarification_questions=[],
            user_responses={},
            original_query="Search query",
            enhanced_query=None,
            analysis_results={},
            retrieval_results=None,
            tool_calls=[],
            tool_results=[],
            session_id="test-session",
            user_level="EXPERIENCED"
        )
        
        # Process should handle error gracefully
        response = agent.process(state)
        
        # Verify error response
        self.assertEqual(response.agent_name, "search")
        self.assertIn("encountered an error", response.message)
        self.assertEqual(response.error, "Search API error")
        self.assertEqual(response.next_agent, "supervisor")
    
    @patch('src.modules.agent.search_agent.TavilySearchResults')
    def test_callable_interface(self, mock_tavily_class):
        """Test the callable interface for LangGraph integration."""
        # Mock search results
        mock_search_tool = Mock()
        mock_search_tool.invoke.return_value = [
            {"title": "Result", "url": "https://example.com", "content": "Content"}
        ]
        mock_tavily_class.return_value = mock_search_tool
        
        # Initialize agent
        agent = TavilySearchAgent(llm=self.mock_llm)
        
        # Create test state
        state = {
            "messages": [HumanMessage(content="Test query")],
            "current_agent": "search",
            "analysis_results": {"existing": "data"}
        }
        
        # Call agent
        result = agent(state)
        
        # Verify result structure
        self.assertIn("messages", result)
        self.assertEqual(len(result["messages"]), 1)
        self.assertEqual(result["messages"][0].name, "search")
        self.assertEqual(result["current_agent"], "search")
        self.assertEqual(result["next_agent"], "supervisor")
        self.assertIn("search_results", result["analysis_results"])
        self.assertEqual(result["analysis_results"]["existing"], "data")


if __name__ == "__main__":
    unittest.main()