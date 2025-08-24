from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from PIL import Image

from src.modules.utils import DeviceType, get_available_device


class BaseImageProcessor(ABC):
    """
    Abstract base class for image processors.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[DeviceType] = None,
    ):
        self.model_name = model_name
        self.device = get_available_device(device)

    @abstractmethod
    def process_image(
        self, image: Image.Image, output_dir: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Process a single image to generate a caption and store it.
        Args:
            image: PIL Image object to process.
            output_dir: Directory to store the processed image (optional).
        Returns:
            A tuple containing the caption and the path to the saved image.
        """
        pass

    @abstractmethod
    def process_batch(
        self, images: List[Image.Image], output_dir: Optional[str] = None
    ) -> List[Tuple[str, str]]:
        """
        Process a batch of images.
        Args:
            images: A list of PIL Image objects to process.
            output_dir: Directory to store the processed images (optional).
        Returns:
            A list of tuples, where each tuple contains the caption and image path for an image.
        """
        pass
