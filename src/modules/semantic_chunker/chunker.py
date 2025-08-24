import re
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class TextChunk:
    content: str
    metadata: Dict
    parent_chunk: Optional["TextChunk"] = None
    child_chunks: List["TextChunk"] = None

    def __post_init__(self):
        if self.child_chunks is None:
            self.child_chunks = []


class TextProcessor:
    def __init__(
        self,
        min_chunk_size: int = 100,
        max_chunk_size: int = 1000,
        overlap_size: int = 50,
    ):
        """
        Initialize the text processor with chunking parameters.

        Args:
            min_chunk_size: Minimum size of a chunk in characters
            max_chunk_size: Maximum size of a chunk in characters
            overlap_size: Number of characters to overlap between chunks
        """
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.overlap_size = overlap_size

    def process_text(self, text: str, metadata: Dict) -> List[TextChunk]:
        """
        Process text into chunks while maintaining structure and context.

        Args:
            text: The text to process
            metadata: Metadata about the text (e.g., section info, page numbers)

        Returns:
            List of TextChunk objects
        """
        # First, identify major structural elements
        sections = self._identify_sections(text)

        chunks = []
        for section in sections:
            section_chunks = self._create_section_chunks(section, metadata)
            chunks.extend(section_chunks)

        return chunks

    def _identify_sections(self, text: str) -> List[Dict]:
        """
        Identify major sections in the text based on headers and structure.
        """
        # Split by headers (assuming headers are in format like "## Header")
        header_pattern = r"^#{1,6}\s+.+$"
        sections = []
        current_section = {"content": "", "level": 0}

        for line in text.split("\n"):
            if re.match(header_pattern, line):
                if current_section["content"]:
                    sections.append(current_section)
                current_section = {
                    "content": line + "\n",
                    "level": len(re.match(r"^(#+)", line).group(1)),
                }
            else:
                current_section["content"] += line + "\n"

        if current_section["content"]:
            sections.append(current_section)

        return sections

    def _create_section_chunks(self, section: Dict, metadata: Dict) -> List[TextChunk]:
        """
        Create chunks from a section while maintaining context.
        """
        content = section["content"]
        chunks = []

        # If section is small enough, keep it as one chunk
        if len(content) <= self.max_chunk_size:
            return [
                TextChunk(
                    content=content,
                    metadata={**metadata, "section_level": section["level"]},
                )
            ]

        # Split into smaller chunks with overlap
        start = 0
        while start < len(content):
            # Calculate the end position for this chunk
            end = min(start + self.max_chunk_size, len(content))

            # If we're at the end of the content, create the final chunk
            if end == len(content):
                chunk_content = content[start:end].strip()
                if len(chunk_content) >= self.min_chunk_size:
                    chunks.append(
                        TextChunk(
                            content=chunk_content,
                            metadata={**metadata, "section_level": section["level"]},
                        )
                    )
                break

            # Try to find a natural break point
            break_point = max(
                content.rfind("\n\n", start, end),
                content.rfind(". ", start, end) + 2,
                content.rfind(" ", start, end),  # Fallback to any space
            )

            # If no break point found or break point is at start, force a break
            if break_point <= start:
                break_point = end

            # Create the chunk
            chunk_content = content[start:break_point].strip()
            if len(chunk_content) >= self.min_chunk_size:
                chunks.append(
                    TextChunk(
                        content=chunk_content,
                        metadata={**metadata, "section_level": section["level"]},
                    )
                )

            # Move to next chunk, ensuring we make progress
            next_start = max(start + 1, break_point - self.overlap_size)
            if next_start <= start:  # Prevent infinite loop
                next_start = start + self.max_chunk_size // 2

            start = next_start

        return chunks

    def merge_chunks(self, chunks: List[TextChunk]) -> str:
        """
        Merge chunks back into a single text, useful for context reconstruction.
        """
        return "\n".join(chunk.content for chunk in chunks)
