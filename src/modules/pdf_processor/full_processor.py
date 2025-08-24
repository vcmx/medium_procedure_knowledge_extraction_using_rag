"""
Full-featured PDF processor that integrates Marker, Florence-2, and ChromaDB.
This module handles PDF processing, image captioning, and vector storage.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import chromadb
import torch
from chromadb.utils import embedding_functions
from marker import Marker
from PIL import Image
from transformers import AutoModelForCausalLM, AutoProcessor


@dataclass
class DocumentChunk:
    """Represents a chunk of document content with associated images and metadata."""

    text: str
    images: List[Tuple[str, str]]  # List of (image_path, caption) tuples
    metadata: Dict[str, Any]
    section_hierarchy: List[str]
    page_number: int


class FullPDFProcessor:
    """
    Full-featured PDF processor that integrates:
    1. Marker for PDF processing
    2. Florence-2 for image captioning
    3. ChromaDB for vector storage
    """

    def __init__(
        self,
        florence2_model_id: str = "microsoft/Florence-2-large",
        clip_model_name: str = "openai/clip-vit-base-patch32",
        chroma_persist_dir: str = "./chroma_db",
    ):
        """
        Initialize the full PDF processor.

        Args:
            florence2_model_id: Model ID for Florence-2
            clip_model_name: Model name for CLIP embeddings
            chroma_persist_dir: Directory to persist ChromaDB data
        """
        # Initialize Florence-2
        self.device = torch.device(
            "mps"
            if torch.backends.mps.is_available()
            else "cuda"
            if torch.cuda.is_available()
            else "cpu"
        )
        self.torch_dtype = torch.float32 if self.device.type == "mps" else torch.float16

        self.florence2_model = AutoModelForCausalLM.from_pretrained(
            florence2_model_id,
            trust_remote_code=True,
            revision="main",
            dtype=self.torch_dtype if self.device.type == "cuda" else None,
        ).to(self.device)

        self.florence2_processor = AutoProcessor.from_pretrained(
            florence2_model_id, trust_remote_code=True, revision="main"
        )

        # Initialize CLIP embedding function
        self.embedding_function = embedding_functions.CLIPEmbeddingFunction(
            model_name=clip_model_name
        )

        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(path=chroma_persist_dir)
        self.collection = self.chroma_client.get_or_create_collection(
            name="pdf_documents", embedding_function=self.embedding_function
        )

    def extract_caption(self, image: Image.Image) -> str:
        """
        Extract caption from image using Florence-2.

        Args:
            image: PIL Image to caption

        Returns:
            Generated caption for the image
        """
        prompt = "<MORE_DETAILED_CAPTION>"
        inputs = self.florence2_processor(
            text=prompt, images=image, return_tensors="pt"
        ).to(
            self.device,
            dtype=self.torch_dtype if self.device.type != "cpu" else torch.float32,
        )

        generated_ids = self.florence2_model.generate(
            input_ids=inputs["input_ids"],
            pixel_values=inputs["pixel_values"],
            max_new_tokens=1024,
            early_stopping=False,
            do_sample=False,
            num_beams=3,
        )

        generated_text = self.florence2_processor.batch_decode(
            generated_ids, skip_special_tokens=False
        )[0]

        return self.florence2_processor.post_process_generation(
            generated_text, task=prompt, image_size=image.size
        )

    def process_pdf(self, pdf_path: str, output_dir: str) -> List[DocumentChunk]:
        """
        Process PDF and create contextual chunks with captioned images.

        Args:
            pdf_path: Path to the PDF file
            output_dir: Directory to save processed content

        Returns:
            List of DocumentChunk objects
        """
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Initialize Marker
        marker = Marker()

        # Extract content from PDF
        doc = marker.process(pdf_path)

        chunks = []
        current_section = []
        current_images = []
        current_hierarchy = []

        # Process each page
        for page in doc.pages:
            # Extract headers and their levels
            headers = self._extract_headers(page)

            # Process content blocks
            for block in page.blocks:
                if block.type == "header":
                    # If we have accumulated content, create a chunk
                    if current_section:
                        chunks.append(
                            self._create_chunk(
                                current_section,
                                current_images,
                                current_hierarchy,
                                page.number,
                            )
                        )
                        current_section = []
                        current_images = []

                    # Update hierarchy
                    level = self._get_header_level(block)
                    current_hierarchy = current_hierarchy[: level - 1] + [block.text]

                elif block.type == "text":
                    current_section.append(block.text)

                elif block.type == "image":
                    # Save image and get caption
                    image_path = output_path / f"image_{len(current_images)}.png"
                    block.image.save(image_path)
                    caption = self.extract_caption(block.image)
                    current_images.append((str(image_path), caption))

        # Add final chunk
        if current_section:
            chunks.append(
                self._create_chunk(
                    current_section, current_images, current_hierarchy, page.number
                )
            )

        return chunks

    def _extract_headers(self, page) -> List[Tuple[str, int]]:
        """
        Extract headers and their levels from a page.

        Args:
            page: Marker page object

        Returns:
            List of (header_text, level) tuples
        """
        headers = []
        for block in page.blocks:
            if block.type == "header":
                level = self._get_header_level(block)
                headers.append((block.text, level))
        return headers

    def _get_header_level(self, block) -> int:
        """
        Determine header level based on formatting.

        Args:
            block: Marker block object

        Returns:
            Header level (1-3)
        """
        # This is a simplified version - you might want to enhance this
        # based on font size, style, etc.
        if block.text.isupper():
            return 1
        elif block.text[0].isupper():
            return 2
        return 3

    def _create_chunk(
        self,
        text_blocks: List[str],
        images: List[Tuple[str, str]],
        hierarchy: List[str],
        page_number: int,
    ) -> DocumentChunk:
        """
        Create a document chunk with context.

        Args:
            text_blocks: List of text blocks
            images: List of (image_path, caption) tuples
            hierarchy: List of section headers
            page_number: Page number

        Returns:
            DocumentChunk object
        """
        # Combine text blocks with proper spacing
        text = "\n".join(text_blocks)

        # Create metadata
        metadata = {
            "section_hierarchy": hierarchy,
            "page_number": page_number,
            "has_images": len(images) > 0,
        }

        return DocumentChunk(
            text=text,
            images=images,
            metadata=metadata,
            section_hierarchy=hierarchy,
            page_number=page_number,
        )

    def store_in_chroma(self, chunks: List[DocumentChunk]):
        """
        Store chunks in ChromaDB with embeddings.

        Args:
            chunks: List of DocumentChunk objects to store
        """
        for i, chunk in enumerate(chunks):
            # Create document text with image captions
            doc_text = chunk.text
            if chunk.images:
                doc_text += "\n\nRelated Images:\n"
                for _, caption in chunk.images:
                    doc_text += f"- {caption}\n"

            # Add to ChromaDB
            self.collection.add(
                documents=[doc_text], metadatas=[chunk.metadata], ids=[f"chunk_{i}"]
            )
