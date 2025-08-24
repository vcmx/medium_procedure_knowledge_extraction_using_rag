import logging
import os
from typing import List, Optional

import numpy as np
import requests
from PIL import Image

from src.modules.utils.image_utils import image_to_base64

from .base import BaseEmbedder


class HuggingFaceHubEmbedder(BaseEmbedder):
    """
    Embedder that uses the Hugging Face Inference API.
    Supports both text and image embeddings.
    """

    def __init__(self, model_name: str, api_token: Optional[str] = None):
        """
        Initialize the Hugging Face Hub embedder.
        Args:
            model_name: The name of the embedding model on Hugging Face Hub.
            api_token: Your Hugging Face API token.
        """
        logger = logging.getLogger(__name__)

        self.model_name = model_name
        self.api_url = f"https://api-inference.huggingface.co/models/{model_name}"
        self.api_token = (
            api_token
            or os.getenv("HUGGINGFACEHUB_API_TOKEN")
            or os.getenv("HUGGINGFACE_API_KEY")
        )

        if self.api_token:
            logger.info("Hugging Face API token loaded in HuggingFaceHubEmbedder.")
            # Validate the token format
            if not self.api_token.startswith("hf_"):
                logger.error(
                    "The provided Hugging Face API token appears to be invalid. It should start with 'hf_'."
                )
                logger.error(
                    f"Current token preview: {self.api_token[:4]}...{self.api_token[-4:]}"
                )
                raise ValueError("Invalid Hugging Face API token format.")

            logger.info(f"Token length: {len(self.api_token)}")
            if len(self.api_token) > 8:
                logger.info(
                    f"Token preview: {self.api_token[:4]}...{self.api_token[-4:]}"
                )
        else:
            logger.warning(
                "Hugging Face API token not found in HuggingFaceHubEmbedder."
            )

        if not self.api_token:
            raise ValueError(
                "Hugging Face API token is required. Please provide it as an argument or set the HUGGINGFACEHUB_API_TOKEN environment variable."
            )

        self.headers = {"Authorization": f"Bearer {self.api_token}"}

    def _query_api(self, payload: dict) -> np.ndarray:
        """Sends a payload to the Hugging Face API and processes the response."""
        response = requests.post(self.api_url, headers=self.headers, json=payload)
        if response.status_code != 200:
            raise RuntimeError(
                f"Hugging Face API request failed with status {response.status_code}: {response.text}"
            )

        result = response.json()

        # The API returns a list of embeddings. For single inputs, it's a list with one item.
        if isinstance(result, list) and all(isinstance(i, list) for i in result):
            return np.array(result)
        # Some models might return a single embedding directly
        elif isinstance(result, list):
            return np.array([result])
        else:
            raise ValueError(f"Unexpected API response format: {result}")

    def embed_text(self, text: str) -> np.ndarray:
        """Embed a single text string using the Hugging Face API."""
        payload = {"inputs": text, "options": {"wait_for_model": True}}
        embeddings = self._query_api(payload)
        return embeddings[0]

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Embed multiple text strings using the Hugging Face API."""
        payload = {"inputs": texts, "options": {"wait_for_model": True}}
        return self._query_api(payload)

    def embed_image(self, image: Image.Image) -> np.ndarray:
        """Embed a single image using the Hugging Face API."""
        base64_image = image_to_base64(image)
        payload = {"inputs": base64_image, "options": {"wait_for_model": True}}
        embeddings = self._query_api(payload)
        return embeddings[0]

    def embed_images(self, images: List[Image.Image]) -> np.ndarray:
        """
        Embed multiple images using the Hugging Face API.
        Note: This sends images one by one as the inference API for many vision
              models doesn't support batching images in a single JSON payload.
        """
        return np.array([self.embed_image(img) for img in images])
