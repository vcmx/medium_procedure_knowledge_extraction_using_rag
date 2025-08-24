from abc import ABC, abstractmethod
from typing import Dict, List, Optional

import numpy as np
from PIL import Image

from src.modules.utils import DeviceType, get_available_device


class BaseEmbedder(ABC):
    """Abstract base class for embedding models."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[DeviceType] = None,
    ):
        self.model_name = model_name
        self.device = get_available_device(device)

    @abstractmethod
    def embed_text(self, text: str) -> np.ndarray:
        """Embed a single text string."""
        pass

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Embed multiple text strings."""
        pass

    @abstractmethod
    def embed_image(self, image: Image.Image) -> np.ndarray:
        """Embed a single image."""
        pass

    @abstractmethod
    def embed_images(self, images: List[Image.Image]) -> np.ndarray:
        """Embed multiple images."""
        pass

    def process_multimodal(
        self,
        text: str = None,
        image: Image.Image = None,
        texts: List[str] = None,
        images: List[Image.Image] = None,
    ) -> Dict[str, np.ndarray]:
        """
        Process both text and image inputs into embeddings.

        Args:
            text: Single text string
            image: Single image
            texts: List of text strings
            images: List of images

        Returns:
            Dictionary containing embeddings for each input type
        """
        result = {}

        if text is not None:
            result["text"] = self.embed_text(text)
        if texts is not None:
            result["texts"] = self.embed_texts(texts)
        if image is not None:
            result["image"] = self.embed_image(image)
        if images is not None:
            result["images"] = self.embed_images(images)

        return result
