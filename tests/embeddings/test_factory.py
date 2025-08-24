import time

import pytest

from src.modules.embeddings.clip import CLIPEmbedder
from src.modules.embeddings.factory import EmbedderFactory
from src.modules.embeddings.siglip import SigLIPEmbedder


def test_create_clip_embedder():
    """Test creating a CLIP embedder."""
    embedder = EmbedderFactory.create("clip")
    assert isinstance(embedder, CLIPEmbedder)


@pytest.mark.timeout(30)  # Add timeout of 30 seconds
def test_create_siglip_embedder():
    """Test creating a SigLIP embedder."""
    print("\nInitializing SigLIP embedder...")
    start_time = time.time()

    # Use a smaller model for testing
    embedder = EmbedderFactory.create(
        "siglip",
        model_name="google/siglip-base-patch16-224",  # Smaller model
    )

    end_time = time.time()
    print(f"SigLIP initialization took {end_time - start_time:.2f} seconds")

    assert isinstance(embedder, SigLIPEmbedder)
    assert embedder.model is not None
    assert embedder.processor is not None


def test_create_with_custom_model():
    """Test creating embedders with custom model names."""
    clip_embedder = EmbedderFactory.create(
        "clip", model_name="openai/clip-vit-base-patch32"
    )
    assert isinstance(clip_embedder, CLIPEmbedder)

    siglip_embedder = EmbedderFactory.create(
        "siglip", model_name="google/siglip-base-patch16-224"
    )
    assert isinstance(siglip_embedder, SigLIPEmbedder)


def test_create_invalid_implementation():
    """Test creating an embedder with invalid implementation."""
    with pytest.raises(ValueError) as exc_info:
        EmbedderFactory.create("invalid_implementation")
    assert "Unknown embedding model implementation" in str(exc_info.value)


def test_register_embedder():
    """Test registering a new embedder implementation."""

    # Create a mock embedder class
    class MockEmbedder(CLIPEmbedder):
        pass

    # Register the mock embedder
    EmbedderFactory.register_embedder("mock", MockEmbedder)

    # Create an instance of the mock embedder
    embedder = EmbedderFactory.create("mock")
    assert isinstance(embedder, MockEmbedder)


def test_register_invalid_embedder():
    """Test registering an invalid embedder class."""

    class InvalidEmbedder:
        pass

    with pytest.raises(ValueError) as exc_info:
        EmbedderFactory.register_embedder("invalid", InvalidEmbedder)
    assert "Model class must inherit from BaseEmbedder" in str(exc_info.value)


def test_default_implementation():
    """Test that CLIP is the default implementation."""
    embedder = EmbedderFactory.create()
    assert isinstance(embedder, CLIPEmbedder)
