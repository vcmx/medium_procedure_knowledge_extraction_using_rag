from typing import List, Optional

import numpy as np
import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

from src.modules.utils import to_device

from .base import BaseEmbedder


class CLIPEmbedder(BaseEmbedder):
    """CLIP-based embedding model implementation."""

    def __init__(
        self,
        model_name: str = "openai/clip-vit-base-patch32",
        device: Optional[str] = None,
    ):
        """
        Initialize CLIP model.

        Args:
            model_name: Name of the CLIP model to use
            device: The device to run the model on.
        """
        super().__init__(model_name=model_name, device=device)
        self.model = CLIPModel.from_pretrained(self.model_name)
        self.processor = CLIPProcessor.from_pretrained(self.model_name)
        self.model.to(self.device)

    def embed_text(self, text: str) -> np.ndarray:
        """Embed a single text string using CLIP."""
        inputs = self.processor(
            text=text, return_tensors="pt", padding=True, truncation=True
        )
        inputs = {k: to_device(v, self.device) for k, v in inputs.items()}

        with torch.no_grad():
            text_features = self.model.get_text_features(**inputs)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
            # Move to CPU and convert to numpy in one step
            return text_features.detach().cpu().numpy()[0]

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Embed multiple text strings using CLIP."""
        inputs = self.processor(text=texts, return_tensors="pt", padding=True)
        inputs = {k: to_device(v, self.device) for k, v in inputs.items()}

        with torch.no_grad():
            text_features = self.model.get_text_features(**inputs)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
            # Move to CPU and convert to numpy in one step
            return text_features.detach().cpu().numpy()

    def embed_image(self, image: Image.Image) -> np.ndarray:
        """Embed a single image using CLIP."""
        inputs = self.processor(images=image, return_tensors="pt")
        inputs = {k: to_device(v, self.device) for k, v in inputs.items()}

        with torch.no_grad():
            image_features = self.model.get_image_features(**inputs)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            # Move to CPU and convert to numpy in one step
            return image_features.detach().cpu().numpy()[0]

    def embed_images(self, images: List[Image.Image]) -> np.ndarray:
        """Embed multiple images using CLIP."""
        inputs = self.processor(images=images, return_tensors="pt")
        inputs = {k: to_device(v, self.device) for k, v in inputs.items()}

        with torch.no_grad():
            image_features = self.model.get_image_features(**inputs)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            # Move to CPU and convert to numpy in one step
            return image_features.detach().cpu().numpy()
