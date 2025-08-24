import base64
import os
from io import BytesIO
from typing import List, Optional, Tuple

import requests
from PIL import Image

from .base_processor import BaseImageProcessor


class QwenVLHuggingFaceImageProcessor(BaseImageProcessor):
    """
    Image processor that uses the Hugging Face Inference API for QwenVL.
    """

    def __init__(
        self,
        model_name: str = "Qwen/Qwen-VL-Chat",
        api_token: Optional[str] = None,
    ):
        """
        Initialize the Hugging Face QwenVL image processor.
        Args:
            model_name: The name of the QwenVL model on Hugging Face Hub.
            api_token: Your Hugging Face API token.
        """
        self.model_name = model_name
        self.api_url = f"https://api-inference.huggingface.co/models/{self.model_name}"
        self.api_token = (
            api_token
            or os.getenv("HUGGINGFACEHUB_API_TOKEN")
            or os.getenv("HUGGINGFACE_API_KEY")
        )

        if not self.api_token:
            raise ValueError(
                "Hugging Face API token is required. Please provide it as an argument or set the HUGGINGFACEHUB_API_TOKEN environment variable."
            )

        self.headers = {"Authorization": f"Bearer {self.api_token}"}

    def _encode_image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string."""
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()

    def process_image(
        self, image: Image.Image, output_dir: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Process an image to generate a caption using the Hugging Face API.
        Args:
            image: PIL Image object to process.
            output_dir: Directory to store the processed image (optional).
        Returns:
            A tuple containing the caption and the path to the saved image.
        """
        if image is None:
            raise ValueError("Image cannot be None")

        # Convert image to base64
        image_base64 = self._encode_image_to_base64(image)

        # Prepare the payload for QwenVL
        payload = {
            "inputs": {
                "question": "Describe this image in detail.",
                "image": f"data:image/png;base64,{image_base64}",
            },
            "options": {"wait_for_model": True},
        }

        # Make the API call
        response = requests.post(self.api_url, headers=self.headers, json=payload)

        if response.status_code != 200:
            raise RuntimeError(
                f"Hugging Face API request failed with status {response.status_code}: {response.text}"
            )

        try:
            result = response.json()
            # QwenVL typically returns the response in a specific format
            if isinstance(result, list) and len(result) > 0:
                caption = result[0].get("generated_text", "")
            elif isinstance(result, dict):
                caption = result.get("generated_text", result.get("answer", ""))
            else:
                caption = str(result)

            # Clean up the caption
            caption = caption.strip()

        except (KeyError, IndexError, TypeError) as e:
            raise RuntimeError(
                f"Failed to parse response from Hugging Face API: {response.text}, error: {e}"
            )

        # Store image if output directory is provided
        image_path = ""
        if output_dir:
            try:
                os.makedirs(output_dir, exist_ok=True)
                image_hash = hash(image_base64)
                image_path = os.path.join(output_dir, f"qwen_image_{image_hash}.png")
                image.save(image_path)
            except Exception as e:
                raise RuntimeError(
                    f"Failed to create output directory or save image: {e}"
                )

        return caption, image_path

    def process_batch(
        self, images: List[Image.Image], output_dir: Optional[str] = None
    ) -> List[Tuple[str, str]]:
        """
        Process multiple images in batch.
        """
        results = []
        for image in images:
            caption, image_path = self.process_image(image, output_dir)
            results.append((caption, image_path))
        return results

    def get_model_info(self) -> dict:
        """Get information about the current model configuration."""
        return {
            "type": "huggingface_api",
            "model_name": self.model_name,
            "api_url": self.api_url,
        }
