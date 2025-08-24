import os
from typing import Literal

from .base_processor import BaseImageProcessor
from .florence_local_processor import FlorenceLocalImageProcessor
from .qwen_huggingface_processor import QwenVLHuggingFaceImageProcessor
from .qwen_local_processor import QwenLocalImageProcessor
from .vision_api_processor import VisionAPIImageProcessor


class ImageProcessorFactory:
    @staticmethod
    def create(
        implementation: Literal[
            "florence",
            "qwen",
            "haiku3_openrouter",
            "qwen-api",
            "qwen_openrouter",
        ],
        **kwargs,
    ) -> BaseImageProcessor:
        """
        Factory to create an image processor instance.

        Args:
            implementation: The type of processor to create.
                - "florence": For running Florence2 on local hardware.
                - "qwen": For running Qwen on local hardware
                - "haiku3_openrouter": For using the OpenRouter API with a default model (Claude 3 Haiku).
                - "qwen-api": For using QwenVL via Hugging Face Inference API.
                - "together-ai": For using the TogetherAI API with a default model (Qwen-VL 72B).
                - "qwen_openrouter": A shortcut for using the Qwen-VL 72B model via OpenRouter.
            **kwargs: Provider-specific arguments, e.g., overriding the model name.
        """
        if implementation == "florence":
            local_model = kwargs.get("local_model", "florence")
            if local_model == "florence":
                return FlorenceLocalImageProcessor(
                    model_name=kwargs.get("model_name", "microsoft/Florence-2-large"),
                    device=kwargs.get("device"),
                )
            elif local_model == "qwen":
                return QwenLocalImageProcessor(
                    model_name=kwargs.get("model_name", "Qwen/Qwen-VL-Chat"),
                    device=kwargs.get("device"),
                )
            else:
                raise ValueError(f"Unknown local model type: {local_model}")

        elif implementation == "haiku3_openrouter":
            api_key = os.getenv("OPENROUTER_API_KEY")
            return VisionAPIImageProcessor(
                api_key=api_key,
                model=kwargs.get("model", "anthropic/claude-3-haiku-20240307"),
                base_url="https://openrouter.ai/api/v1",
                provider="openrouter",
            )

        elif implementation == "qwen_openrouter":
            api_key = os.getenv("OPENROUTER_API_KEY")
            return VisionAPIImageProcessor(
                api_key=api_key,
                model="qwen/qwen2.5-vl-72b-instruct",  # The specific model for Qwen on OpenRouter
                base_url="https://openrouter.ai/api/v1",
                provider="openrouter",
            )

        elif implementation == "qwen-api":
            return QwenVLHuggingFaceImageProcessor(
                model_name=kwargs.get("model_name", "Qwen/Qwen-VL-Chat"),
                api_token=kwargs.get("api_token"),
            )

        else:
            raise ValueError(
                f"Unknown image processor implementation: {implementation}"
            )
