import os
import sys
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.modules.agent.web_search_agent import WebSearchAgent, WebSearchResult


@patch("os.getenv")
@patch("src.modules.agent.web_search_agent.TavilySearch")
def test_web_search_agent_process_success(mock_tavily_class, mock_getenv):
    """
    Tests the happy path of the WebSearchAgent's process method,
    ensuring it calls the search tool and the LLM correctly.
    """
    # Arrange
    mock_getenv.return_value = "fake_tavily_api_key"

    # Mock Tavily search tool
    mock_search_tool_instance = MagicMock()
    mock_tavily_class.return_value = mock_search_tool_instance
    raw_results = [
        {"url": "http://example.com/1", "content": "About timing belts."},
    ]
    mock_search_tool_instance.invoke.return_value = raw_results

    # We need a dummy model name, but the chain itself will be mocked.
    agent = WebSearchAgent(model_name="mock-model")
    query = "what is a timing belt?"

    # Mock the response from the LLM chain
    mock_llm_response = WebSearchResult(
        summary="This is a summarized answer.", urls=["http://example.com/1"]
    )
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = mock_llm_response

    # Use patch.object to mock the _get_chain method on the agent instance
    with patch.object(agent, "_get_chain", return_value=mock_chain):
        # Act
        result = agent.process(query)

        # Assert
        mock_search_tool_instance.invoke.assert_called_once_with({"query": query})
        mock_chain.invoke.assert_called_once()
        assert result == {
            "summary": "This is a summarized answer.",
            "urls": ["http://example.com/1"],
        }


@patch("os.getenv")
@patch("src.modules.agent.web_search_agent.TavilySearch")
def test_web_search_agent_process_error(mock_tavily_class, mock_getenv):
    """
    Tests the error handling of the WebSearchAgent's process method
    when the search tool raises an exception.
    """
    # Arrange
    mock_getenv.return_value = "fake_tavily_api_key"
    mock_search_tool_instance = MagicMock()
    mock_tavily_class.return_value = mock_search_tool_instance

    error_message = "API connection failed"
    mock_search_tool_instance.invoke.side_effect = Exception(error_message)

    agent = WebSearchAgent(model_name="mock-model")
    query = "a query that will fail"

    # Act
    result = agent.process(query)

    # Assert
    assert "summary" in result
    assert error_message in result["summary"]
    assert result["urls"] == []
