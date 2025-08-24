from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from PIL import Image


class BaseImageProcessor(ABC):
    """Abstract base class for image processors."""

    @abstractmethod
    def process_image(
        self, image: Image.Image, output_dir: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Process an image to generate a caption and store it.

        Args:
            image: PIL Image object to process
            output_dir: Directory to store the processed image (optional)

        Returns:
            Tuple of (caption, image_path)
        """
        pass

    @abstractmethod
    def process_batch(
        self, images: List[Image.Image], output_dir: Optional[str] = None
    ) -> List[Tuple[str, str]]:
        """
        Process multiple images in batch.

        Args:
            images: List of PIL Image objects
            output_dir: Directory to store the processed images (optional)

        Returns:
            List of tuples containing (caption, image_path) for each image
        """
        pass

    @abstractmethod
    def get_model_info(self) -> dict:
        """
        Get information about the current model configuration.

        Returns:
            Dictionary containing model information
        """
        pass
