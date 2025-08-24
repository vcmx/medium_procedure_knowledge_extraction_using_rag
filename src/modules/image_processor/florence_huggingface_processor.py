import os
from typing import Optional, Tuple

import requests
from PIL import Image

from .base import BaseImageProcessor


class FlorenceHuggingFaceImageProcessor(BaseImageProcessor):
    """
    Image processor that uses the Hugging Face Inference API for Florence-2.
    """

    def __init__(
        self,
        model_name: str = "microsoft/Florence-2-large",
        api_token: Optional[str] = None,
    ):
        """
        Initialize the Hugging Face image processor.
        Args:
            model_name: The name of the Florence model on Hugging Face Hub.
            api_token: Your Hugging Face API token. If not provided, it will
                       try to read from the HUGGINGFACE_API_KEY or HUGGING_FACE_API_TOKEN environment variable.
        """
        self.model_name = model_name
        self.api_url = f"https://api-inference.huggingface.co/models/{self.model_name}"
        self.api_token = (
            api_token
            or os.getenv("HUGGINGFACE_API_KEY")
            or os.getenv("HUGGING_FACE_API_TOKEN")
        )

        if not self.api_token:
            raise ValueError(
                "Hugging Face API token is required. Please provide it as an argument or set the HUGGINGFACE_API_KEY or HUGGING_FACE_API_TOKEN environment variable."
            )

        self.headers = {"Authorization": f"Bearer {self.api_token}"}

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
        Raises:
            ValueError: If the image is None.
            RuntimeError: If the API call fails or image saving fails.
        """
        if image is None:
            raise ValueError("Image cannot be None")

        # Convert image to bytes
        import io

        image_bytes = io.BytesIO()
        image.save(image_bytes, format="PNG")
        image_bytes = image_bytes.getvalue()

        # Prepare the payload for the API
        payload = {
            "inputs": "<MORE_DETAILED_CAPTION>",
            "parameters": {
                "max_new_tokens": 1024,
                "do_sample": False,
            },
        }

        # Make the API call
        response = requests.post(self.api_url, headers=self.headers, data=image_bytes)

        if response.status_code != 200:
            raise RuntimeError(
                f"Hugging Face API request failed with status {response.status_code}: {response.text}"
            )

        try:
            # The response is a list of dictionaries, we need to parse it correctly
            result = response.json()
            # Assuming the API returns something like: [{'generated_text': '...<MORE_DETAILED_CAPTION>A detailed caption.'}]
            generated_text = result[0]["generated_text"]
            # Simple post-processing to get the caption text
            caption = generated_text.split("<MORE_DETAILED_CAPTION>")[-1].strip()

        except (KeyError, IndexError, TypeError) as e:
            raise RuntimeError(
                f"Failed to parse response from Hugging Face API: {response.text}, error: {e}"
            )

        # Store image if output directory is provided
        image_path = ""
        if output_dir:
            try:
                os.makedirs(output_dir, exist_ok=True)
                # Using a hash of the image bytes for a unique filename
                image_hash = hash(image_bytes)
                image_path = os.path.join(output_dir, f"image_{image_hash}.png")
                image.save(image_path)
            except Exception as e:
                raise RuntimeError(
                    f"Failed to create output directory or save image: {e}"
                )

        return caption, image_path

    def process_batch(
        self, images: list[Image.Image], output_dir: Optional[str] = None
    ) -> list[Tuple[str, str]]:
        """
        Process multiple images in a batch by calling process_image for each.
        Note: The Hugging Face Inference API for Florence-2 does not support batching in a single call.
        """
        results = []
        for image in images:
            caption, image_path = self.process_image(image, output_dir)
            results.append((caption, image_path))
        return results
