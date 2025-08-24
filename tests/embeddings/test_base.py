import numpy as np
import pytest
from PIL import Image

from src.modules.embeddings.base import BaseEmbedder


class MockEmbedder(BaseEmbedder):
    """Mock implementation of BaseEmbedder for testing."""

    def embed_text(self, text: str) -> np.ndarray:
        """Return a mock embedding for text."""
        return np.array([1.0] * 512)  # Mock 512-dim embedding

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Return mock embeddings for multiple texts."""
        return np.array([[1.0] * 512] * len(texts))

    def embed_image(self, image: Image.Image) -> np.ndarray:
        """Return a mock embedding for an image."""
        return np.array([1.0] * 512)

    def embed_images(self, images: list[Image.Image]) -> np.ndarray:
        """Return mock embeddings for multiple images."""
        return np.array([[1.0] * 512] * len(images))


@pytest.fixture
def mock_embedder():
    """Create a mock embedder instance."""
    return MockEmbedder()


def test_process_multimodal_text(mock_embedder):
    """Test processing single text input."""
    result = mock_embedder.process_multimodal(text="test text")
    assert "text" in result
    assert isinstance(result["text"], np.ndarray)
    assert result["text"].shape == (512,)


def test_process_multimodal_texts(mock_embedder):
    """Test processing multiple text inputs."""
    texts = ["text1", "text2", "text3"]
    result = mock_embedder.process_multimodal(texts=texts)
    assert "texts" in result
    assert isinstance(result["texts"], np.ndarray)
    assert result["texts"].shape == (3, 512)


def test_process_multimodal_image(mock_embedder):
    """Test processing single image input."""
    image = Image.new("RGB", (100, 100))
    result = mock_embedder.process_multimodal(image=image)
    assert "image" in result
    assert isinstance(result["image"], np.ndarray)
    assert result["image"].shape == (512,)


def test_process_multimodal_images(mock_embedder):
    """Test processing multiple image inputs."""
    images = [Image.new("RGB", (100, 100)) for _ in range(3)]
    result = mock_embedder.process_multimodal(images=images)
    assert "images" in result
    assert isinstance(result["images"], np.ndarray)
    assert result["images"].shape == (3, 512)


def test_process_multimodal_combined(mock_embedder):
    """Test processing combined text and image inputs."""
    text = "test text"
    image = Image.new("RGB", (100, 100))
    result = mock_embedder.process_multimodal(text=text, image=image)
    assert "text" in result
    assert "image" in result
    assert result["text"].shape == (512,)
    assert result["image"].shape == (512,)
