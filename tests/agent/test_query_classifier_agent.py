import pytest

from src.modules.agent.query_classifier_agent import QueryClassifierAgent


@pytest.fixture
def classifier():
    """Provides a QueryClassifierAgent instance for testing."""
    return QueryClassifierAgent()


def test_technical_query_how_to(classifier):
    """Tests that 'how to' queries are classified as technical."""
    query = "how to remove the timing belt"
    result = classifier.process(query)
    assert result["query_type"] == "technical"


def test_technical_query_procedure(classifier):
    """Tests that 'procedure' queries are classified as technical."""
    query = "procedure for checking fluid levels"
    result = classifier.process(query)
    assert result["query_type"] == "technical"


def test_technical_query_case_insensitive(classifier):
    """Tests that classification is case-insensitive."""
    query = "Can you give me the Steps To replace the spark plugs?"
    result = classifier.process(query)
    assert result["query_type"] == "technical"


def test_general_query_what_is(classifier):
    """Tests that 'what is' queries are classified as general."""
    query = "what is a timing belt"
    result = classifier.process(query)
    assert result["query_type"] == "general"


def test_general_query_no_keywords(classifier):
    """Tests that queries without technical keywords are classified as general."""
    query = "Tell me about Subaru engines"
    result = classifier.process(query)
    assert result["query_type"] == "general"


def test_ambiguous_query_defaults_to_general(classifier):
    """Tests that a simple noun phrase defaults to general."""
    query = "timing belt"
    result = classifier.process(query)
    assert result["query_type"] == "general"
