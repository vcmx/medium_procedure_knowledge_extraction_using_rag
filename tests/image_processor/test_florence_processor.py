import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
import torch
from PIL import Image

from src.modules.image_processor.florence_local_processor import (
    FlorenceLocalImageProcessor,
)

# Skip real model tests if running in CI or if explicitly disabled
pytestmark = pytest.mark.skipif(
    os.getenv("SKIP_MODEL_TESTS", "false").lower() == "true",
    reason="Model tests are disabled",
)


@pytest.fixture
def mock_model():
    """Create a mock model that returns predefined outputs."""
    model = MagicMock()
    model.generate.return_value = torch.tensor([[1, 2, 3]])  # Mock token IDs
    return model


@pytest.fixture
def mock_processor():
    """Create a mock processor that returns predefined outputs."""
    processor = MagicMock()
    processor.return_value = {
        "input_ids": torch.tensor([[1, 2, 3]]),
        "pixel_values": torch.randn(1, 3, 224, 224),
    }
    processor.batch_decode.return_value = ["A test caption for the image"]
    processor.post_process_generation.return_value = (
        "A detailed test caption for the image"
    )
    return processor


@pytest.fixture
def florence_processor(mock_model, mock_processor):
    """Create a Florence processor instance with mocked model and processor."""
    with (
        patch(
            "src.modules.image_processor.florence_local_processor.AutoModelForCausalLM.from_pretrained",
            return_value=mock_model,
        ),
        patch(
            "src.modules.image_processor.florence_local_processor.AutoProcessor.from_pretrained",
            return_value=mock_processor,
        ),
    ):
        processor = FlorenceLocalImageProcessor()
        processor.model = mock_model
        processor.processor = mock_processor
        return processor


@pytest.fixture
def sample_image():
    """Create a simple test image."""
    return Image.new("RGB", (100, 100), color="red")


@pytest.fixture
def temp_output_dir():
    """Create a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir


def test_florence_processor_initialization(mock_model, mock_processor):
    """Test Florence processor initialization with different device options."""
    with (
        patch(
            "src.modules.image_processor.florence_local_processor.AutoModelForCausalLM.from_pretrained",
            return_value=mock_model,
        ),
        patch(
            "src.modules.image_processor.florence_local_processor.AutoProcessor.from_pretrained",
            return_value=mock_processor,
        ),
    ):
        # Test default initialization
        processor = FlorenceLocalImageProcessor()
        assert processor.device in ["cuda", "mps", "cpu"]
        assert processor.processor is not None
        assert processor.model is not None
        assert processor.torch_dtype in [torch.float16, torch.float32]

        # Test CPU initialization
        processor = FlorenceLocalImageProcessor(device="cpu")
        assert processor.device == "cpu"
        assert processor.torch_dtype == torch.float32


def test_process_image(florence_processor, sample_image, temp_output_dir):
    """Test processing a single image with mocked model."""
    caption, image_path = florence_processor.process_image(
        sample_image, temp_output_dir
    )

    assert isinstance(caption, str)
    assert len(caption) > 0
    assert any(c.isalnum() for c in caption)
    assert os.path.exists(image_path)
    assert os.path.isfile(image_path)


def test_process_image_without_saving(florence_processor, sample_image):
    """Test processing an image without saving it."""
    caption, image_path = florence_processor.process_image(sample_image)

    assert isinstance(caption, str)
    assert len(caption) > 0
    assert any(c.isalnum() for c in caption)
    assert image_path == ""


def test_process_batch(florence_processor, temp_output_dir):
    """Test processing multiple images in batch."""
    images = [
        Image.new("RGB", (100, 100), color="red"),
        Image.new("RGB", (100, 100), color="blue"),
        Image.new("RGB", (100, 100), color="green"),
    ]

    results = florence_processor.process_batch(images, temp_output_dir)

    assert len(results) == len(images)
    for caption, image_path in results:
        assert isinstance(caption, str)
        assert len(caption) > 0
        assert any(c.isalnum() for c in caption)
        assert os.path.exists(image_path)
        assert os.path.isfile(image_path)


def test_error_handling(florence_processor):
    """Test error handling with invalid inputs."""
    # Test with None image
    with pytest.raises(ValueError, match="Image cannot be None"):
        florence_processor.process_image(None)

    # Test with invalid output directory
    with pytest.raises(RuntimeError, match="Failed to create output directory"):
        florence_processor.process_image(
            Image.new("RGB", (100, 100)), "/invalid/path/that/does/not/exist"
        )


# Real model tests (skipped by default)
@pytest.mark.skipif(
    os.getenv("SKIP_MODEL_TESTS", "true").lower() == "true",
    reason="Real model tests are disabled by default",
)
def test_real_florence_processor():
    """Test Florence processor with real model.

    This test also implicitly checks for compatibility issues during model loading
    (e.g., with the current transformers library version).
    """
    processor = FlorenceLocalImageProcessor()
    assert processor.device in ["cuda", "mps", "cpu"]
    assert processor.processor is not None
    assert processor.model is not None
    assert processor.torch_dtype in [torch.float16, torch.float32]


@pytest.mark.skipif(
    os.getenv("SKIP_MODEL_TESTS", "true").lower() == "true",
    reason="Real model tests are disabled by default",
)
def test_real_image_captioning(temp_output_dir):
    """Test captioning with real Florence model."""
    processor = FlorenceLocalImageProcessor()

    # Create a more complex test image
    img = Image.new("RGB", (512, 512), color="red")
    # Draw a simple shape to make it more interesting
    for x in range(512):
        for y in range(512):
            if (x - 256) ** 2 + (y - 256) ** 2 < 10000:  # Draw a circle
                img.putpixel((x, y), (0, 0, 255))

    caption, image_path = processor.process_image(img, temp_output_dir)

    assert isinstance(caption, str)
    assert len(caption) > 0
    assert any(c.isalnum() for c in caption)
    assert os.path.exists(image_path)
    assert os.path.isfile(image_path)
