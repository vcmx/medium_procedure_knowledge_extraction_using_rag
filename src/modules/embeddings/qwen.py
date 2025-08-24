from typing import List, Optional

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer

from src.modules.utils import to_device

from .base import BaseEmbedder


class QwenEmbedder(BaseEmbedder):
    """
    Qwen3-Embedding-4B model implementation.
    https://huggingface.co/Qwen/Qwen3-Embedding-4B
    """

    def __init__(
        self,
        model_name: str = "Qwen/Qwen3-Embedding-4B",
        device: Optional[str] = None,
    ):
        """
        Initialize the Qwen3-Embedding-4B model.

        Args:
            model_name: Name of the model to use.
            device: The device to run the model on.
        """
        super().__init__(model_name=model_name, device=device)
        self.model = AutoModel.from_pretrained(
            self.model_name,
            trust_remote_code=True,
        )
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            trust_remote_code=True,
            padding_side="left",
        )
        self.model.to(self.device)
        self.model.eval()

    def _mean_pooling(self, model_output, attention_mask):
        """Mean Pooling - Take attention mask into account for correct averaging"""
        token_embeddings = model_output[
            0
        ]  # First element of model_output contains all token embeddings
        input_mask_expanded = (
            attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        )
        return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(
            input_mask_expanded.sum(1), min=1e-9
        )

    def embed_text(self, text: str) -> np.ndarray:
        """Embed a single text string."""
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Embed multiple text strings."""
        inputs = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            return_tensors="pt",
            max_length=self.model.config.max_position_embeddings,
        )
        inputs = {k: to_device(v, self.device) for k, v in inputs.items()}

        with torch.no_grad():
            model_output = self.model(**inputs)
            sentence_embeddings = self._mean_pooling(
                model_output, inputs["attention_mask"]
            )
            # Normalize embeddings
            sentence_embeddings = torch.nn.functional.normalize(
                sentence_embeddings, p=2, dim=1
            )
            return sentence_embeddings.detach().cpu().numpy()

    def embed_image(self, image):
        """This model does not support image embedding."""
        raise NotImplementedError("Qwen34BEmbedder does not support image embedding.")

    def embed_images(self, images):
        """This model does not support image embedding."""
        raise NotImplementedError("Qwen34BEmbedder does not support image embedding.")
