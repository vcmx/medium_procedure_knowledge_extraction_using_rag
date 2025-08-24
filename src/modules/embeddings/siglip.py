from abc import ABC, abstractmethod
from typing import Dict, List, Union

import numpy as np
import torch
from PIL import Image
from transformers import SiglipModel, SiglipProcessor

from .base import BaseEmbedder


class EmbeddingModel(ABC):
    """Abstract base class for embedding models."""

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


class SigLIPEmbedder(BaseEmbedder):
    """SigLIP-based embedding model implementation."""

    def __init__(self, model_name: str = "google/siglip-base-patch16-224"):
        """
        Initialize SigLIP model.

        Args:
            model_name: Name of the SigLIP model to use
        """
        self.model = SiglipModel.from_pretrained(model_name)
        self.processor = SiglipProcessor.from_pretrained(model_name)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)

    def embed_text(self, text: str) -> np.ndarray:
        """Embed a single text string using SigLIP."""
        inputs = self.processor(text=text, return_tensors="pt", padding=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            text_features = self.model.get_text_features(**inputs)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)

        return text_features.cpu().numpy()[0]

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Embed multiple text strings using SigLIP."""
        inputs = self.processor(text=texts, return_tensors="pt", padding=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            text_features = self.model.get_text_features(**inputs)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)

        return text_features.cpu().numpy()

    def embed_image(self, image: Image.Image) -> np.ndarray:
        """Embed a single image using SigLIP."""
        inputs = self.processor(images=image, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            image_features = self.model.get_image_features(**inputs)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)

        return image_features.cpu().numpy()[0]

    def embed_images(self, images: List[Image.Image]) -> np.ndarray:
        """Embed multiple images using SigLIP."""
        inputs = self.processor(images=images, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            image_features = self.model.get_image_features(**inputs)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)

        return image_features.cpu().numpy()


class EmbeddingProcessor:
    """Main class for handling embeddings with different models."""

    def __init__(self, model: Union[str, EmbeddingModel] = "clip"):
        """
        Initialize the embedding processor.

        Args:
            model: Either a string identifier for a model or an EmbeddingModel instance
        """
        if isinstance(model, str):
            if model.lower() == "clip":
                self.model = CLIPEmbeddingModel()
            else:
                raise ValueError(f"Unknown model type: {model}")
        else:
            self.model = model

    def process_text(self, text: str) -> np.ndarray:
        """Process a single text string into an embedding."""
        return self.model.embed_text(text)

    def process_texts(self, texts: List[str]) -> np.ndarray:
        """Process multiple text strings into embeddings."""
        return self.model.embed_texts(texts)

    def process_image(self, image: Image.Image) -> np.ndarray:
        """Process a single image into an embedding."""
        return self.model.embed_image(image)

    def process_images(self, images: List[Image.Image]) -> np.ndarray:
        """Process multiple images into embeddings."""
        return self.model.embed_images(images)

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
            result["text"] = self.process_text(text)
        if texts is not None:
            result["texts"] = self.process_texts(texts)
        if image is not None:
            result["image"] = self.process_image(image)
        if images is not None:
            result["images"] = self.process_images(images)

        return result
