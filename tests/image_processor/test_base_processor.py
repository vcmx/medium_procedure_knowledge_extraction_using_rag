import os
import tempfile
from typing import Optional
from unittest.mock import MagicMock

import pytest
import torch
from PIL import Image

from src.modules.image_processor.base_processor import BaseImageProcessor
from src.modules.image_processor.local_processor import LocalImageProcessor
from src.modules.utils import DeviceType, get_available_device


class MockLocalProcessor(LocalImageProcessor):
    """Mock implementation of LocalImageProcessor for testing."""

    def __init__(self, model_name: str, device: Optional[DeviceType] = None):
        # Skip the parent's __init__ to avoid actual model loading
        self.model_name = model_name
        self.device = get_available_device(device)
        self.torch_dtype = torch.float16 if self.device == "cuda" else torch.float32

        # Create mock model and processor
        self.model = MagicMock()
        self.processor = MagicMock()
        self.processor.return_value = {
            "input_ids": torch.tensor([[1, 2, 3]]),
            "pixel_values": torch.randn(1, 3, 224, 224),
        }
        self.processor.batch_decode.return_value = ["A test caption for the image"]
        self.processor.decode.return_value = "A test caption for the image"

    def process_image(
        self, image: Image.Image, output_dir: Optional[str] = None
    ) -> tuple[str, str]:
        """Mock implementation of process_image."""
        # Handle invalid inputs
        if image is None:
            raise ValueError("Image cannot be None")

        if output_dir and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception as e:
                raise RuntimeError(f"Failed to create output directory: {e}")

        caption = self.processor.decode(torch.tensor([[1, 2, 3]]))
        image_path = ""
        if output_dir:
            image_path = os.path.join(output_dir, f"image_{hash(str(image))}.png")
            image.save(image_path)
        return caption, image_path


@pytest.fixture
def mock_processor():
    """Create a mock processor instance."""
    return MockLocalProcessor("mock-model")


@pytest.fixture
def sample_image():
    """Create a simple test image."""
    return Image.new("RGB", (100, 100), color="red")


@pytest.fixture
def temp_output_dir():
    """Create a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir


def test_base_processor_initialization():
    """Test that BaseImageProcessor cannot be instantiated."""
    with pytest.raises(TypeError):
        BaseImageProcessor()


def test_local_processor_initialization():
    """Test LocalImageProcessor initialization."""
    processor = MockLocalProcessor("test-model")
    assert processor.model_name == "test-model"
    assert processor.device in ["cuda", "mps", "cpu"]
    assert processor.torch_dtype in [torch.float16, torch.float32]


def test_local_processor_cpu_initialization():
    """Test LocalImageProcessor initialization with CPU device."""
    processor = MockLocalProcessor("test-model", device="cpu")
    assert processor.device == "cpu"
    assert processor.torch_dtype == torch.float32


def test_process_batch(mock_processor, sample_image, temp_output_dir):
    """Test batch processing functionality."""
    images = [sample_image, sample_image, sample_image]
    results = mock_processor.process_batch(images, temp_output_dir)

    assert len(results) == len(images)
    for caption, image_path in results:
        assert isinstance(caption, str)
        assert len(caption) > 0
        assert os.path.exists(image_path)
        assert os.path.isfile(image_path)


def test_process_batch_without_saving(mock_processor, sample_image):
    """Test batch processing without saving images."""
    images = [sample_image, sample_image]
    results = mock_processor.process_batch(images)

    assert len(results) == len(images)
    for caption, image_path in results:
        assert isinstance(caption, str)
        assert len(caption) > 0
        assert image_path == ""


def test_get_model_info(mock_processor):
    """Test model info retrieval."""
    info = mock_processor.get_model_info()
    assert info["type"] == "local"
    assert info["model_name"] == "mock-model"
    assert info["device"] in ["cuda", "mps", "cpu"]
    assert info["torch_dtype"] in ["torch.float16", "torch.float32"]


def test_error_handling(mock_processor):
    """Test error handling for invalid inputs."""
    with pytest.raises(ValueError):
        mock_processor.process_image(None)

    with pytest.raises(RuntimeError):
        mock_processor.process_image(
            Image.new("RGB", (100, 100)), "/invalid/path/that/does/not/exist"
        )
