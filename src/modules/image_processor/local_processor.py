import os
from typing import List, Optional, Tuple

import torch
from PIL import Image
from transformers import AutoModelForCausalLM, AutoProcessor

from src.modules.image_processor.base_processor import BaseImageProcessor
from src.modules.utils import DeviceType, get_available_device, to_device

# Workaround for flash_attn import issue on Mac MPS
try:
    from transformers.dynamic_module_utils import get_imports

    def fixed_get_imports(filename: str | os.PathLike) -> list[str]:
        if not str(filename).endswith("/modeling_florence2.py"):
            return get_imports(filename)
        imports = get_imports(filename)
        if "flash_attn" in imports:
            imports.remove("flash_attn")
        return imports
except ImportError:
    fixed_get_imports = None


class LocalImageProcessor(BaseImageProcessor):
    """Base class for local image processors."""

    def __init__(
        self,
        model_name: str,
        device: Optional[DeviceType] = None,
    ):
        """
        Initialize the local image processor.

        Args:
            model_name: The name of the model to use
            device: Optional preferred device type ("cuda", "mps", or "cpu").
                   If not specified, the best available device will be used.
        """
        self.model_name = model_name
        self.device = get_available_device(device)
        self.torch_dtype = torch.float16 if self.device == "cuda" else torch.float32

        # Load model and processor with appropriate dtype handling
        # The derived class should handle its own model loading.
        # if fixed_get_imports is not None:
        #     with patch(
        #         "transformers.dynamic_module_utils.get_imports", fixed_get_imports
        #     ):
        #         self._load_model_and_processor(model_name)
        # else:
        #     self._load_model_and_processor(model_name)

    def _load_model_and_processor(self, model_name: str):
        """Load model and processor with appropriate dtype handling"""
        # Only use dtype for CUDA devices
        if self.device == "cuda":
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                trust_remote_code=True,
                revision="main",
                dtype=self.torch_dtype,
            ).to(self.device)
        else:
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name, trust_remote_code=True, revision="main"
            ).to(self.device)

        self.processor = AutoProcessor.from_pretrained(
            model_name, trust_remote_code=True, revision="main"
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
        """
        # Prepare image for the model
        inputs = self.processor(
            text="<MORE_DETAILED_CAPTION>", images=image, return_tensors="pt"
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

        try:
            generated_text = self.processor.batch_decode(
                outputs, skip_special_tokens=False
            )[0]
            image_size = image.size
            caption = self.processor.post_process_generation(
                generated_text, task="<MORE_DETAILED_CAPTION>", image_size=image_size
            )
        except Exception as e:
            print(f"Error during post-processing: {e}")
            # Fallback to basic decoding
            caption = self.processor.batch_decode(outputs, skip_special_tokens=True)[0]

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
