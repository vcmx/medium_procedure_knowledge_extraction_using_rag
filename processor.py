"""
PDF Processor implementation using Marker.
"""

import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from marker.config.parser import ConfigParser
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered

logger = logging.getLogger(__name__)


@dataclass
class Section:
    """Represents a section in the document."""

    title: str
    level: int
    content: str
    images: List[Tuple[Path, str]]  # List of (image_path, caption) tuples
    page_number: int


@dataclass
class ExtractedContent:
    """Represents the extracted content from a PDF."""

    sections: List[Section]
    metadata: Dict[str, Any]
    document_summary: Optional[str] = None


class PDFProcessor:
    """
    Handles PDF processing using Marker.

    This class is responsible for:
    1. Extracting text and images from PDFs
    2. Maintaining document structure
    3. Preserving relationships between content
    """

    def __init__(
        self,
        output_dir: str = "./processed_output",
        format_lines: bool = False,
        use_llm: bool = False,  # Disabled by default
        llm_service: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
    ):
        """
        Initialize the PDF processor.

        Args:
            output_dir: Directory to store processed content
            format_lines: Whether to reformat lines using OCR
            use_llm: Whether to use LLM for improved accuracy (disabled by default)
            llm_service: Which LLM service to use if use_llm is True
            gemini_api_key: API key for Gemini service if using Gemini
        """
        self.base_output_dir = Path(output_dir)
        self.base_output_dir.mkdir(parents=True, exist_ok=True)

        # Set up configuration
        config = {
            "format_lines": format_lines,
            "output_format": "markdown",  # Use markdown for better structure
            "use_llm": use_llm,  # Will be False by default
            "paginate_output": True,
        }

        # Add LLM configuration if enabled
        if use_llm:
            if not llm_service:
                llm_service = "marker.services.gemini.GoogleGeminiService"
            config["llm_service"] = llm_service

            if gemini_api_key:
                config["gemini_api_key"] = gemini_api_key
                os.environ["GOOGLE_API_KEY"] = gemini_api_key
            elif llm_service == "marker.services.gemini.GoogleGeminiService":
                logger.warning("No Gemini API key provided. LLM features may not work.")

        self.config_parser = ConfigParser(config)

        # Initialize converter with configuration
        self.converter = PdfConverter(
            config=self.config_parser.generate_config_dict(),
            artifact_dict=create_model_dict(),
            processor_list=self.config_parser.get_processors(),
            renderer=self.config_parser.get_renderer(),
            llm_service=self.config_parser.get_llm_service() if use_llm else None,
        )

    def _create_document_output_dir(self, pdf_path: str) -> Path:
        """
        Create a unique output directory for a document using its filename and timestamp.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Path to the created output directory
        """
        # Get PDF filename without extension
        pdf_name = Path(pdf_path).stem

        # Create timestamp string
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create directory path: base_output_dir/pdf_name_timestamp/
        doc_output_dir = self.base_output_dir / f"{pdf_name}_{timestamp}"
        doc_output_dir.mkdir(parents=True, exist_ok=True)

        return doc_output_dir

    def process_pdf(self, pdf_path: str) -> ExtractedContent:
        """
        Process a PDF file and extract its content.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            ExtractedContent object containing the document's content
        """
        try:
            logger.info(f"Processing PDF: {pdf_path}")

            # Create document-specific output directory
            doc_output_dir = self._create_document_output_dir(pdf_path)
            logger.info(f"Created output directory: {doc_output_dir}")

            # Get rendered content using Marker's built-in function
            rendered = self.converter(pdf_path)
            text, _, images_dict = text_from_rendered(rendered)

            logger.info(f"Extracted {len(images_dict)} images from PDF (PIL objects)")

            # Save markdown to file
            base_filename = Path(pdf_path).stem
            markdown_path = doc_output_dir / f"{base_filename}.md"
            with open(markdown_path, "w", encoding="utf-8") as f:
                f.write(text)
            logger.info(f"Saved markdown to {markdown_path}")

            # --- Reworked image to page association ---
            page_images: Dict[int, List[str]] = {}

            # First, save all images and get their actual saved paths
            saved_image_paths_map: Dict[str, str] = {}
            logger.info("Saving extracted images:")
            for img_name, img_obj in images_dict.items():
                # Sanitize img_name if necessary, though Marker usually provides usable names
                image_savename = img_name
                image_savepath = doc_output_dir / image_savename
                try:
                    img_obj.save(image_savepath)
                    saved_image_paths_map[img_name] = str(image_savepath)
                    logger.info(f"  - Saved image '{img_name}' to {image_savepath}")
                except Exception as e:
                    logger.error(f"  - Failed to save image '{img_name}': {e}")
                    continue

            # Now, associate saved images with pages by parsing their filenames
            logger.info("Associating saved images with pages based on filenames:")
            # This logic is being replaced by direct parsing in _parse_markdown_sections
            # We will pass the full image map instead.
            page_images: Dict[int, List[str]] = {}

            # Parse markdown into sections with the correct page-image mapping
            sections = self._parse_markdown_sections(text, saved_image_paths_map)
            logger.info(f"Created {len(sections)} sections from markdown")

            # Extract metadata
            metadata = rendered.metadata
            logger.info("Extracted metadata from document")

            return ExtractedContent(
                sections=sections, metadata=metadata, document_summary=None
            )

        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {str(e)}")
            raise

    def _parse_markdown_sections(
        self, markdown: str, image_path_map: Dict[str, str]
    ) -> List[Section]:
        """
        Parse markdown content into sections.

        Args:
            markdown: Markdown content from Marker
            image_path_map: Dictionary mapping image filenames to their full saved paths

        Returns:
            List of Section objects
        """
        sections = []
        current_section = None
        current_content = []
        current_page = 1  # Default to page 1 if not found

        # Regex to find {PAGENUM}--- page markers
        page_separator = "-" * 48
        page_marker_regex = re.compile(r"^{(\d+)}" + re.escape(page_separator) + r"$")

        def create_section(details, content_lines, page_num):
            section_content = "\n".join(content_lines).strip()

            # Find all image references in the content of this section
            section_images = []
            image_tags = re.findall(r"!\[.*?\]\((.*?)\)", section_content)
            for img_filename in image_tags:
                img_basename = Path(img_filename).name
                if img_basename in image_path_map:
                    section_images.append((Path(image_path_map[img_basename]), ""))
                else:
                    logger.warning(
                        f"Image '{img_basename}' referenced in markdown but not found in directory."
                    )

            return Section(
                title=details["title"],
                level=details["level"],
                content=section_content,
                images=list(set(section_images)),
                page_number=details.get("page", page_num),
            )

        for line in markdown.split("\n"):
            # Check for a page marker first
            page_match = page_marker_regex.search(line)
            if page_match:
                try:
                    parsed_page = int(page_match.group(1))
                    if parsed_page != current_page:
                        logger.debug(
                            f"Markdown parser: Page changed from {current_page} to {parsed_page} from marker: {line.strip()[:100]}"
                        )
                        current_page = parsed_page
                        if current_section:  # If a section is active, update its page
                            current_section["page"] = current_page
                except ValueError:
                    logger.warning(
                        f"Could not parse page number from marker: {line.strip()[:100]}"
                    )
                continue  # Skip adding the page marker line to content

            # Check for headers
            line_for_header_check = line.strip()

            if line_for_header_check.startswith("#"):
                # Save previous section if exists
                if current_section:
                    section_content = "\n".join(current_content).strip()
                    if current_section["title"] or section_content:
                        sections.append(
                            create_section(
                                current_section, current_content, current_page
                            )
                        )

                # Start new section
                level = len(line_for_header_check.split()[0])
                title = line_for_header_check.lstrip("#").strip()
                current_section = {"title": title, "level": level, "page": current_page}
                current_content = []

            if current_section:
                current_content.append(line)

        # Add the last section
        if current_section:
            final_content = "\n".join(current_content).strip()
            if final_content or current_section["title"]:
                sections.append(
                    create_section(current_section, current_content, current_page)
                )

        return sections
