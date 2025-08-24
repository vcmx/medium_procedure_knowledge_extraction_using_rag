"""Unit tests for the SimpleRAGAgent."""

import unittest
from unittest.mock import MagicMock

from src.modules.agent.simple_rag_agent import SimpleRAGAgent


class TestSimpleRAGAgent(unittest.TestCase):
    """Test suite for the Simple RAG Agent."""

    def setUp(self):
        """Set up for the tests."""
        # Mock the RAG query engine
        self.mock_rag_engine = MagicMock()
        self.agent = SimpleRAGAgent(rag_engine=self.mock_rag_engine)

    def test_process_calls_rag_engine_with_correct_parameters(self):
        """
        Verify that the process method calls the RAG engine's query method
        with the correct query and keyword arguments.
        """
        query = "test query"
        kwargs = {"n_results": 5, "experience_years": 3}
        expected_result = {
            "answer": "This is a test answer.",
            "sources": [],
            "relevant_images": [],
        }

        # Configure the mock to return a specific value
        self.mock_rag_engine.query.return_value = expected_result

        # Call the process method
        result = self.agent.process(query, **kwargs)

        # Assert that the mock's query method was called once with the correct arguments
        self.mock_rag_engine.query.assert_called_once_with(query=query, **kwargs)

        # Assert that the result from the process method is what the mock returned
        self.assertEqual(result, expected_result)

    def test_process_handles_rag_engine_exception_gracefully(self):
        """
        Verify that if the RAG engine raises an exception, the agent
        catches it and returns a default error message.
        """
        query = "a query that will fail"
        kwargs = {"n_results": 10}
        error_message = "Test exception"

        # Configure the mock to raise an exception
        self.mock_rag_engine.query.side_effect = Exception(error_message)

        # Call the process method
        result = self.agent.process(query, **kwargs)

        # Assert that the RAG engine was called
        self.mock_rag_engine.query.assert_called_once_with(query=query, **kwargs)

        # Assert that the result is the default error dictionary
        self.assertEqual(
            result["answer"], "I encountered an error while searching the documents."
        )
        self.assertEqual(result["sources"], [])
        self.assertEqual(result["relevant_images"], [])


if __name__ == "__main__":
    unittest.main()
