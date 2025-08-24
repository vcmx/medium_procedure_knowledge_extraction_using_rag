import numpy as np
import pytest
from PIL import Image

from src.modules.embeddings.siglip import SigLIPEmbedder


@pytest.fixture
def siglip_embedder():
    """Create a SigLIP embedder instance."""
    return SigLIPEmbedder()


def test_siglip_embedder_initialization(siglip_embedder):
    """Test SigLIP embedder initialization."""
    assert siglip_embedder.model is not None
    assert siglip_embedder.processor is not None
    assert siglip_embedder.device in ["cuda", "cpu"]


def test_embed_text(siglip_embedder):
    """Test embedding a single text."""
    text = "A test sentence for embedding"
    embedding = siglip_embedder.embed_text(text)

    assert isinstance(embedding, np.ndarray)
    assert embedding.ndim == 1
    assert embedding.shape[0] > 0
    # Check if embedding is normalized
    assert np.isclose(np.linalg.norm(embedding), 1.0, atol=1e-6)


def test_embed_texts(siglip_embedder):
    """Test embedding multiple texts."""
    texts = ["First sentence", "Second sentence", "Third sentence"]
    embeddings = siglip_embedder.embed_texts(texts)

    assert isinstance(embeddings, np.ndarray)
    assert embeddings.ndim == 2
    assert embeddings.shape[0] == len(texts)
    # Check if embeddings are normalized
    for embedding in embeddings:
        assert np.isclose(np.linalg.norm(embedding), 1.0, atol=1e-6)


def test_embed_image(siglip_embedder):
    """Test embedding a single image."""
    image = Image.new("RGB", (224, 224))
    embedding = siglip_embedder.embed_image(image)

    assert isinstance(embedding, np.ndarray)
    assert embedding.ndim == 1
    assert embedding.shape[0] > 0
    # Check if embedding is normalized
    assert np.isclose(np.linalg.norm(embedding), 1.0, atol=1e-6)


def test_embed_images(siglip_embedder):
    """Test embedding multiple images."""
    images = [Image.new("RGB", (224, 224)) for _ in range(3)]
    embeddings = siglip_embedder.embed_images(images)

    assert isinstance(embeddings, np.ndarray)
    assert embeddings.ndim == 2
    assert embeddings.shape[0] == len(images)
    # Check if embeddings are normalized
    for embedding in embeddings:
        assert np.isclose(np.linalg.norm(embedding), 1.0, atol=1e-6)


def test_text_image_similarity(siglip_embedder):
    """Test that text and image embeddings are in the same space."""
    text = "A red square"
    image = Image.new("RGB", (224, 224), color="red")

    text_embedding = siglip_embedder.embed_text(text)
    image_embedding = siglip_embedder.embed_image(image)

    # Check that embeddings have the same shape
    assert text_embedding.shape == image_embedding.shape

    # Check that cosine similarity is a valid value
    similarity = np.dot(text_embedding, image_embedding)
    assert -1 <= similarity <= 1


def test_custom_model_name():
    """Test SigLIP embedder with a custom model name."""
    model_name = "google/siglip-base-patch16-224"
    embedder = SigLIPEmbedder(model_name=model_name)
    assert embedder.model is not None
    assert embedder.processor is not None
