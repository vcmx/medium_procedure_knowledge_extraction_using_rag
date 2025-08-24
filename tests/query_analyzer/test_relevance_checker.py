"""Tests for contextual relevance checker."""

import pytest
import numpy as np
from unittest.mock import Mock, patch
from pathlib import Path

from src.modules.query_analyzer.relevance_checker import ContextualRelevanceChecker
from src.modules.query_analyzer.models import RelevanceConfig, RelevanceResult


class TestContextualRelevanceChecker:
    """Test suite for ContextualRelevanceChecker."""
    
    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        return RelevanceConfig(
            enabled=True,
            min_domain_terms=1,
            high_confidence_threshold=0.8,
            low_confidence_threshold=0.3,
            enable_semantic_validation=False,  # Disable for most tests
            rejection_mode="soft"
        )
    
    @pytest.fixture
    def mock_embedder(self):
        """Create a mock embedder."""
        embedder = Mock()
        embedder.embed_text.return_value = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
        return embedder
    
    @pytest.fixture
    def checker(self, config, mock_embedder):
        """Create a relevance checker instance."""
        return ContextualRelevanceChecker(config, mock_embedder)
    
    def test_initialization(self, config, mock_embedder):
        """Test checker initialization."""
        checker = ContextualRelevanceChecker(config, mock_embedder)
        
        assert checker.config == config
        assert checker.embedder == mock_embedder
        assert checker.domain_vocabulary is not None
        assert checker.domain_patterns is not None
        assert checker._query_cache == {}
    
    def test_relevant_technical_query(self, checker):
        """Test detection of relevant technical queries."""
        # Test automotive maintenance query
        result = checker.check_relevance("How do I replace the brake pads on my car?")
        
        assert result.is_relevant is True
        assert result.confidence >= checker.config.low_confidence_threshold
        assert result.stage == "pre-filter"
        assert "brake" in result.domain_matches or "replace" in result.domain_matches
        assert result.suggestions is None
    
    def test_relevant_with_part_number(self, checker):
        """Test detection of queries with part numbers."""
        result = checker.check_relevance("Where can I find part AB123-XY456 in the manual?")
        
        assert result.is_relevant is True
        assert result.confidence > 0.0
        assert "part_number" in result.explanation
    
    def test_relevant_with_measurements(self, checker):
        """Test detection of queries with technical measurements."""
        result = checker.check_relevance("What is the torque specification? Should be around 85 Nm.")
        
        assert result.is_relevant is True
        assert result.confidence > 0.0
        assert len(result.domain_matches) > 0
    
    def test_irrelevant_general_query(self, checker):
        """Test detection of irrelevant general queries."""
        result = checker.check_relevance("What's the weather like today?")
        
        assert result.is_relevant is False
        assert result.confidence < checker.config.low_confidence_threshold
        assert result.suggestions is not None
        assert len(result.suggestions) > 0
    
    def test_irrelevant_social_media_query(self, checker):
        """Test detection of social media related queries."""
        result = checker.check_relevance("How do I post on Instagram?")
        
        assert result.is_relevant is False
        assert "out-of-domain indicators" in result.explanation.lower()
    
    def test_edge_case_generic_technical(self, checker):
        """Test edge case with generic technical terms."""
        result = checker.check_relevance("How does this system work?")
        
        # Should have medium confidence due to "system" being technical but query being vague
        assert result.confidence > 0.0
        assert result.confidence < checker.config.high_confidence_threshold
    
    def test_query_caching(self, checker):
        """Test that queries are cached for performance."""
        query = "How to change engine oil?"
        
        # First call
        result1 = checker.check_relevance(query)
        
        # Second call - should return cached result
        with patch.object(checker, '_fast_prefilter') as mock_prefilter:
            result2 = checker.check_relevance(query)
            mock_prefilter.assert_not_called()
        
        assert result1.is_relevant == result2.is_relevant
        assert result1.confidence == result2.confidence
    
    def test_semantic_validation_fallback(self, checker):
        """Test semantic validation when confidence is medium."""
        # Enable semantic validation
        checker.config.enable_semantic_validation = True
        
        # Create representative embeddings
        checker.representative_embeddings = {
            "engine": [np.array([0.1, 0.2, 0.3, 0.4, 0.5])],
            "electrical": [np.array([0.5, 0.4, 0.3, 0.2, 0.1])]
        }
        
        # Query with medium confidence
        result = checker.check_relevance("Something about the motor")
        
        assert result.stage == "semantic"
        assert "Semantic validation" in result.explanation
    
    def test_domain_vocabulary_matching(self, checker):
        """Test domain vocabulary matching logic."""
        # Test single word match
        matches = checker._find_domain_terms("engine problem", {"engine", "problem"})
        assert "technical_terms" in matches
        assert "engine" in matches["technical_terms"]
        
        # Test multi-word term match
        matches = checker._find_domain_terms("cooling system maintenance", {"cooling", "system", "maintenance"})
        assert len(matches) > 0
    
    def test_pattern_matching(self, checker):
        """Test technical pattern matching."""
        # Test part number pattern
        matches = checker._find_pattern_matches("Part number ABC-123-XYZ")
        assert len(matches) > 0
        assert any("part_number" in match[0] for match in matches)
        
        # Test measurement pattern
        matches = checker._find_pattern_matches("Torque to 85 Nm")
        assert len(matches) > 0
        assert any("measurement" in match[0] for match in matches)
    
    def test_negative_indicators(self, checker):
        """Test negative indicator detection."""
        score = checker._check_negative_indicators("tell me a joke about cars")
        assert score > 0.0
        
        score = checker._check_negative_indicators("how to fix engine problems")
        assert score == 0.0
    
    def test_explanation_generation(self, checker):
        """Test explanation generation for different scenarios."""
        # With domain matches
        explanation = checker._generate_explanation(
            {"technical_terms": ["engine", "brake"]},
            [("part_number", "ABC-123")],
            0.1,
            0.0,
            0.7
        )
        assert "engine" in explanation
        assert "technical patterns" in explanation
        assert "0.70" in explanation
        
        # Without matches
        explanation = checker._generate_explanation({}, [], 0.0, 0.0, 0.1)
        assert "No clear domain indicators" in explanation
    
    def test_suggestions_generation(self, checker):
        """Test suggestion generation for irrelevant queries."""
        suggestions = checker._generate_suggestions("help me")
        
        assert len(suggestions) > 0
        assert len(suggestions) <= 3
        assert any("component" in s.lower() for s in suggestions)
    
    def test_cosine_similarity(self, checker):
        """Test cosine similarity calculation."""
        vec1 = np.array([1, 0, 0])
        vec2 = np.array([1, 0, 0])
        assert checker._cosine_similarity(vec1, vec2) == pytest.approx(1.0)
        
        vec3 = np.array([0, 1, 0])
        assert checker._cosine_similarity(vec1, vec3) == pytest.approx(0.0)
        
        # Test zero vector handling
        vec_zero = np.array([0, 0, 0])
        assert checker._cosine_similarity(vec1, vec_zero) == 0.0
    
    def test_update_representative_embeddings(self, checker):
        """Test updating representative embeddings."""
        embedding = np.array([0.1, 0.2, 0.3])
        
        # Add first embedding
        checker.update_representative_embeddings("test_category", embedding)
        assert "test_category" in checker.representative_embeddings
        assert len(checker.representative_embeddings["test_category"]) == 1
        
        # Add more embeddings
        for i in range(15):
            checker.update_representative_embeddings("test_category", embedding)
        
        # Should be limited to 10
        assert len(checker.representative_embeddings["test_category"]) == 10
    
    @pytest.mark.parametrize("query,expected_relevant", [
        ("How to replace transmission fluid?", True),
        ("What is the spark plug gap specification?", True),
        ("Diagnose P0301 error code", True),
        ("Tell me about Shakespeare", False),
        ("What's your favorite color?", False),
        ("Recipe for chocolate cake", False),
        ("Check engine light troubleshooting", True),
        ("Figure 12.3 shows the wiring diagram", True),
        ("The weather forecast for tomorrow", False),
        ("Install timing belt on 2020 model", True),
    ])
    def test_various_queries(self, checker, query, expected_relevant):
        """Test various queries for expected relevance."""
        result = checker.check_relevance(query)
        assert result.is_relevant == expected_relevant
    
    def test_config_rejection_modes(self, config, mock_embedder):
        """Test different rejection modes."""
        # Test hard rejection mode
        config.rejection_mode = "hard"
        checker = ContextualRelevanceChecker(config, mock_embedder)
        
        result = checker.check_relevance("What's the weather?")
        assert result.is_relevant is False
        
        # Test score mode
        config.rejection_mode = "score"
        checker = ContextualRelevanceChecker(config, mock_embedder)
        
        result = checker.check_relevance("What's the weather?")
        assert hasattr(result, 'confidence')
        assert 0.0 <= result.confidence <= 1.0


class TestRelevanceIntegration:
    """Integration tests for relevance checking with query analyzer."""
    
    def test_with_ollama_analyzer(self, config):
        """Test integration with OllamaQueryAnalyzer."""
        from src.modules.query_analyzer.ollama_analyzer import OllamaQueryAnalyzer
        from src.modules.query_analyzer.models import QueryAnalyzerConfig
        
        # This test would require Ollama to be running, so we'll mock it
        with patch('src.modules.query_analyzer.ollama_analyzer.ChatOllama'):
            analyzer_config = QueryAnalyzerConfig()
            relevance_config = RelevanceConfig(enabled=True)
            
            analyzer = OllamaQueryAnalyzer(analyzer_config, relevance_config)
            
            # Set up relevance checker
            mock_embedder = Mock()
            checker = ContextualRelevanceChecker(relevance_config, mock_embedder)
            analyzer.set_relevance_checker(checker)
            
            # Verify relevance checking is available
            assert analyzer.relevance_checker is not None
            assert analyzer.relevance_config.enabled is True