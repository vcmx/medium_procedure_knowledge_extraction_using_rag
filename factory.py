from .base import BaseEmbedder
from .clip import CLIPEmbedder
from .huggingface_hub import HuggingFaceHubEmbedder
from .qwen import QwenEmbedder
from .siglip import SigLIPEmbedder


class EmbedderFactory:
    """Factory for creating embedding models."""

    @staticmethod
    def create(implementation: str = "clip", **kwargs) -> BaseEmbedder:
        """
        Create an embedding model instance.

        Args:
            implementation: Name of the embedding model to use.
                            Options: "clip", "siglip", "huggingface", "qwen".
            **kwargs: Additional arguments to pass to the model constructor.
                      For "huggingface", you can specify a "model_name".

        Returns:
            An instance of the specified embedding model.

        Raises:
            ValueError: If the specified implementation is not supported.
        """
        if implementation.lower() == "clip":
            return CLIPEmbedder(**kwargs)
        elif implementation.lower() == "siglip":
            return SigLIPEmbedder(**kwargs)
        elif implementation.lower() == "qwen":
            # Provide a default model if not specified in kwargs
            model_name = kwargs.pop("model_name", "Qwen/Qwen3-Embedding-4B")
            return QwenEmbedder(**kwargs)
        elif implementation.lower() == "huggingface":
            # Provide a default model if not specified in kwargs
            model_name = kwargs.pop("model_name", "BAAI/bge-small-en-v1.5")
            return HuggingFaceHubEmbedder(model_name=model_name, **kwargs)
        else:
            supported_implementations = ["clip", "siglip", "huggingface", "qwen"]
            raise ValueError(
                f"Unknown embedding model implementation: {implementation}. "
                f"Supported implementations: {supported_implementations}"
            )
