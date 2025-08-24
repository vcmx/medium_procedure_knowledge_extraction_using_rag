import numpy as np
import pytest
from PIL import Image

from src.modules.embeddings.clip import CLIPEmbedder


@pytest.fixture
def clip_embedder():
    """Create a CLIP embedder instance."""
    return CLIPEmbedder()


def test_clip_embedder_initialization(clip_embedder):
    """Test CLIP embedder initialization."""
    assert clip_embedder.model is not None
    assert clip_embedder.processor is not None
    assert clip_embedder.device in ["cuda", "cpu"]


def test_embed_text(clip_embedder):
    """Test embedding a single text."""
    text = "A test sentence for embedding"
    embedding = clip_embedder.embed_text(text)

    assert isinstance(embedding, np.ndarray)
    assert embedding.ndim == 1
    assert embedding.shape[0] > 0
    # Check if embedding is normalized
    assert np.isclose(np.linalg.norm(embedding), 1.0, atol=1e-6)


def test_embed_texts(clip_embedder):
    """Test embedding multiple texts."""
    texts = ["First sentence", "Second sentence", "Third sentence"]
    embeddings = clip_embedder.embed_texts(texts)

    assert isinstance(embeddings, np.ndarray)
    assert embeddings.ndim == 2
    assert embeddings.shape[0] == len(texts)
    # Check if embeddings are normalized
    for embedding in embeddings:
        assert np.isclose(np.linalg.norm(embedding), 1.0, atol=1e-6)


def test_embed_image(clip_embedder):
    """Test embedding a single image."""
    image = Image.new("RGB", (224, 224))
    embedding = clip_embedder.embed_image(image)

    assert isinstance(embedding, np.ndarray)
    assert embedding.ndim == 1
    assert embedding.shape[0] > 0
    # Check if embedding is normalized
    assert np.isclose(np.linalg.norm(embedding), 1.0, atol=1e-6)


def test_embed_images(clip_embedder):
    """Test embedding multiple images."""
    images = [Image.new("RGB", (224, 224)) for _ in range(3)]
    embeddings = clip_embedder.embed_images(images)

    assert isinstance(embeddings, np.ndarray)
    assert embeddings.ndim == 2
    assert embeddings.shape[0] == len(images)
    # Check if embeddings are normalized
    for embedding in embeddings:
        assert np.isclose(np.linalg.norm(embedding), 1.0, atol=1e-6)


def test_text_image_similarity(clip_embedder):
    """Test that text and image embeddings are in the same space."""
    text = "A red square"
    image = Image.new("RGB", (224, 224), color="red")

    text_embedding = clip_embedder.embed_text(text)
    image_embedding = clip_embedder.embed_image(image)

    # Check that embeddings have the same shape
    assert text_embedding.shape == image_embedding.shape

    # Check that cosine similarity is a valid value
    similarity = np.dot(text_embedding, image_embedding)
    assert -1 <= similarity <= 1
