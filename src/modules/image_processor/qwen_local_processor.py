import os
from typing import List, Optional, Tuple

import torch
from PIL import Image
from transformers import AutoModelForCausalLM, AutoProcessor

from src.modules.image_processor.local_processor import LocalImageProcessor
from src.modules.utils import DeviceType, to_device


class QwenLocalImageProcessor(LocalImageProcessor):
    """Qwen-VL image processor implementation."""

    def __init__(
        self,
        model_name: str = "Qwen/Qwen-VL-Chat",
        device: Optional[DeviceType] = None,
    ):
        """
        Initialize the Qwen-VL image processor.

        Args:
            model_name: The name of the Qwen-VL model to use
            device: Optional preferred device type ("cuda", "mps", or "cpu").
                   If not specified, the best available device will be used.
        """
        super().__init__(model_name, device)
        self._load_model_and_processor(model_name)

    def _load_model_and_processor(self, model_name: str):
        """Load model and processor with appropriate dtype handling"""
        # Only use dtype for CUDA devices
        if self.device == "cuda":
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                trust_remote_code=True,
                device_map="auto",
                torch_dtype=self.torch_dtype,
            )
        else:
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                trust_remote_code=True,
                device_map="auto",
            )

        self.processor = AutoProcessor.from_pretrained(
            model_name,
            trust_remote_code=True,
        )

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

        Raises:
            ValueError: If image is None
            RuntimeError: If output directory creation fails
        """
        # Validate input
        if image is None:
            raise ValueError("Image cannot be None")

        # Prepare image for the model
        inputs = self.processor(
            text="Describe this image in detail.", images=image, return_tensors="pt"
        )

        # Move inputs to device with appropriate dtype
        inputs = {
            k: to_device(v, self.device) if torch.is_tensor(v) else v
            for k, v in inputs.items()
        }

        # Generate caption
        with torch.no_grad():
            outputs = self.model.generate(
                input_ids=inputs["input_ids"],
                pixel_values=inputs["pixel_values"],
                max_new_tokens=1024,
                early_stopping=False,
                do_sample=False,
                num_beams=3,
            )

        # Decode the generated text
        caption = self.processor.batch_decode(outputs, skip_special_tokens=True)[0]

        # Store image if output directory is provided
        image_path = ""
        if output_dir:
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception as e:
                raise RuntimeError(f"Failed to create output directory: {e}")
            image_path = os.path.join(output_dir, f"image_{hash(str(image))}.png")
            image.save(image_path)

        return caption, image_path

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
        results = []
        for image in images:
            caption, image_path = self.process_image(image, output_dir)
            results.append((caption, image_path))
        return results

    def get_model_info(self) -> dict:
        """Get information about the current model configuration."""
        return {
            "type": "local",
            "model_name": self.model_name,
            "device": self.device,
            "torch_dtype": str(self.torch_dtype),
        }
