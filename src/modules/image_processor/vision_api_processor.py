import base64
import os
from io import BytesIO
from typing import List, Optional, Tuple

import requests
from PIL import Image

from .base_processor import BaseImageProcessor


class VisionAPIImageProcessor(BaseImageProcessor):
    """A generalized API-based image processor for vision models."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        provider: str = "openrouter",
    ):
        """
        Initialize the image processor with a generic vision API.
        Args:
            api_key: The API key for the service.
            model: The model to use for image captioning.
            base_url: The base URL for the API.
            provider: The name of the provider (e.g., "openrouter", "together-ai").
        """
        if not api_key:
            raise ValueError("An API key must be provided.")

        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.provider = provider

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.provider == "openrouter":
            # OpenRouter requires these specific headers
            self.headers["HTTP-Referer"] = "https://github.com/your-repo"
            self.headers["X-Title"] = "Your App Name"

    def _encode_image(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string."""
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()

    def process_image(
        self, image: Image.Image, output_dir: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Process an image using OpenRouter API to generate a caption.

        Args:
            image: PIL Image object to process
            output_dir: Directory to store the processed image (optional)

        Returns:
            Tuple of (caption, image_path)
        """
        # Encode image to base64
        image_base64 = self._encode_image(image)

        # Prepare API request
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Please provide a detailed caption for this image.",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            },
                        },
                    ],
                }
            ],
            "max_tokens": 1024,
        }

        # Make API request
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=self.headers,
            json=payload,
        )
        response.raise_for_status()

        # Extract caption from response
        caption = response.json()["choices"][0]["message"]["content"]

        # Store image if output directory is provided
        image_path = ""
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            image_path = os.path.join(output_dir, f"image_{hash(str(image))}.png")
            image.save(image_path)

        return caption, image_path

    def process_batch(
        self, images: List[Image.Image], output_dir: Optional[str] = None
    ) -> List[Tuple[str, str]]:
        """
        Process multiple images in batch using OpenRouter API.

        Args:
            images: List of PIL Image objects
            output_dir: Directory to store the processed images (optional)

        Returns:
            List of tuples containing (caption, image_path) for each image
        """
        results = []
        for image in images:
            caption, image_path = self.process_image(image, output_dir)
            results.append((caption, image_path))
        return results

    def get_model_info(self) -> dict:
        """Get information about the current model configuration."""
        return {
            "type": "api",
            "provider": self.provider,
            "model": self.model,
            "api_base": self.base_url,
        }
