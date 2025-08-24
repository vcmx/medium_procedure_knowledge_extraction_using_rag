import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.modules.agent.simple_supervisor_agent import SimpleSupervisorAgent

# --- Test Fixtures ---


@pytest.fixture
def mock_rag_engine():
    """Create a mock RAG engine for testing."""
    engine = MagicMock()
    engine.get_all_document_summaries.return_value = [
        "Subaru Manual",
        "Yamaha Manual",
    ]
    return engine


@pytest.fixture
def supervisor(mock_rag_engine):
    """Initialize the SimpleSupervisorAgent with a mock engine."""
    return SimpleSupervisorAgent(rag_engine=mock_rag_engine, model_name="mock-model")


# --- Test Cases ---


def test_initialization(supervisor, mock_rag_engine):
    """Test if the supervisor and its agents are initialized correctly."""
    assert supervisor.rag_engine is mock_rag_engine
    assert supervisor.model_name == "mock-model"
    assert supervisor.query_classifier is not None
    assert supervisor.web_searcher is not None
    assert supervisor.action_extractor is not None
    assert supervisor.manual_checker is not None
    assert supervisor.query_refiner is not None
    assert supervisor.rag_agent is not None
    assert supervisor.available_manuals == ["Subaru Manual", "Yamaha Manual"]


@patch("src.modules.agent.simple_supervisor_agent.QueryClassifierAgent.process")
@patch("src.modules.agent.simple_supervisor_agent.ActionExtractorAgent.process")
@patch("src.modules.agent.simple_supervisor_agent.ManualCheckerAgent.process")
def test_technical_v1_workflow_manual_found(
    mock_manual_checker, mock_action_extractor, mock_query_classifier, supervisor
):
    """
    Test the full V1 (technical) workflow when the manual is identified directly.
    """
    # --- Mock Agent Return Values ---
    mock_query_classifier.return_value = {"query_type": "technical"}
    mock_action_extractor.return_value = {"action": "remove timing belt"}
    mock_manual_checker.return_value = {
        "manual_specified": True,
        "manual_name": "Subaru Manual",
    }

    # --- Mock the rest of the chain ---
    supervisor.resume_with_clarification = MagicMock()
    # This mock will allow us to check if it was called, without executing it
    # We use a generator-like mock that yields a final step
    supervisor.resume_with_clarification.return_value = iter(
        [
            {
                "agent": "RAG",
                "output": {"answer": "Final answer from RAG."},
                "is_final": True,
            }
        ]
    )

    # --- Execute the generator ---
    query = "How to remove timing belt from Subaru Manual"
    generator = supervisor.process_query(query)
    results = list(generator)

    # --- Assertions ---
    # 1. Check that the correct agents were called
    mock_query_classifier.assert_called_once_with(query)
    mock_action_extractor.assert_called_once_with(query)
    mock_manual_checker.assert_called_once_with(
        query, ["Subaru Manual", "Yamaha Manual"]
    )
    supervisor.resume_with_clarification.assert_called_once()

    # 2. Verify the yielded steps from the initial processing
    assert len(results) == 4
    assert results[0]["agent"] == "Query Classifier"
    assert results[0]["output"]["query_type"] == "technical"
    assert results[1]["agent"] == "Action Extractor"
    assert results[1]["output"]["action"] == "remove timing belt"
    assert results[2]["agent"] == "Manual Checker"
    assert results[3]["agent"] == "RAG"  # From the mocked resume method


@patch("src.modules.agent.simple_supervisor_agent.QueryClassifierAgent.process")
@patch("src.modules.agent.simple_supervisor_agent.ActionExtractorAgent.process")
@patch("src.modules.agent.simple_supervisor_agent.ManualCheckerAgent.process")
def test_technical_v1_workflow_clarification_needed(
    mock_manual_checker, mock_action_extractor, mock_query_classifier, supervisor
):
    """
    Test the V1 (technical) workflow when the manual is NOT identified,
    triggering the clarification flow.
    """
    # --- Mock Agent Return Values ---
    mock_query_classifier.return_value = {"query_type": "technical"}
    mock_action_extractor.return_value = {"action": "remove timing belt"}
    mock_manual_checker.return_value = {"manual_specified": False}

    # --- Execute the generator ---
    query = "How to remove timing belt"
    generator = supervisor.process_query(query)
    results = list(generator)

    # --- Assertions ---
    assert len(results) == 4
    assert results[0]["agent"] == "Query Classifier"
    assert results[1]["agent"] == "Action Extractor"
    assert results[2]["agent"] == "Manual Checker"

    # Check the final "clarification_needed" step
    clarification_step = results[3]
    assert clarification_step["agent"] == "Supervisor"
    output = clarification_step["output"]
    assert output["status"] == "clarification_needed"
    assert output["action"] == "remove timing belt"
    assert output["options"] == ["Subaru Manual", "Yamaha Manual"]


@patch("src.modules.agent.simple_supervisor_agent.QueryRefinerAgent.process")
@patch("src.modules.agent.simple_supervisor_agent.SimpleRAGAgent.process")
def test_resume_with_clarification(mock_rag_agent, mock_query_refiner, supervisor):
    """
    Test the second half of the workflow after the user provides clarification.
    """
    # --- Mock Agent Return Values ---
    mock_query_refiner.return_value = {
        "final_query": "Give me steps for remove timing belt from Subaru Manual"
    }
    mock_rag_agent.return_value = {
        "answer": "Here are the steps...",
        "sources": ["source1"],
    }

    # --- Execute the generator ---
    generator = supervisor.resume_with_clarification(
        action="remove timing belt", selected_manual="Subaru Manual"
    )
    results = list(generator)

    # --- Assertions ---
    mock_query_refiner.assert_called_once_with(
        action="remove timing belt", manual="Subaru Manual"
    )
    mock_rag_agent.assert_called_once_with(
        query="Give me steps for remove timing belt from Subaru Manual"
    )

    assert len(results) == 2
    assert results[0]["agent"] == "Query Refiner"
    assert results[1]["agent"] == "RAG"
    assert results[1]["is_final"] is True
    assert results[1]["output"]["answer"] == "Here are the steps..."


@patch("src.modules.agent.simple_supervisor_agent.QueryClassifierAgent.process")
@patch("src.modules.agent.simple_supervisor_agent.WebSearchAgent.process")
def test_general_v2_workflow(mock_web_searcher, mock_query_classifier, supervisor):
    """
    Test the V2 (general) workflow to ensure the WebSearchAgent is called.
    """
    # --- Mock Agent Return Values ---
    mock_query_classifier.return_value = {"query_type": "general"}
    mock_web_searcher.return_value = {
        "summary": "A spark plug is a device...",
        "urls": ["http://example.com/spark-plug"],
    }

    # --- Execute the generator ---
    query = "What is a spark plug?"
    generator = supervisor.process_query(query)
    results = list(generator)

    # --- Assertions ---
    # 1. Check that the correct agents were called
    mock_query_classifier.assert_called_once_with(query)
    mock_web_searcher.assert_called_once_with(query)

    # 2. Verify the yielded steps
    assert len(results) == 2
    assert results[0]["agent"] == "Query Classifier"
    assert results[0]["output"]["query_type"] == "general"

    final_step = results[1]
    assert final_step["agent"] == "Web Searcher"
    assert final_step["is_final"] is True
    output = final_step["output"]
    assert output["status"] == "web_search_complete"
    assert "A spark plug is a device..." in output["summary"]
