from pathlib import Path
from typing import Dict, Tuple

import fitz  # PyMuPDF


class PDFClassifier:
    """Classifies PDF files as image-based or text-based based on content analysis."""

    def __init__(self, image_threshold: float = 0.7):
        """
        Initialize the PDF classifier.

        Args:
            image_threshold (float): Threshold ratio of image area to total area to classify as image-based.
                                   Default is 0.7 (70%).
        """
        self.image_threshold = image_threshold

    def _calculate_areas(self, page: fitz.Page) -> Tuple[float, float, float]:
        """
        Calculate the total image and text areas on a page.

        Args:
            page (fitz.Page): The PDF page to analyze.

        Returns:
            Tuple[float, float, float]: (image_area, text_area, total_page_area)
        """
        image_area = 0.0
        text_area = 0.0

        # Get page dimensions
        page_rect = page.rect
        total_page_area = abs(page_rect)

        # Method 1: Check for images in blocks
        blocks = page.get_text("blocks")
        for block in blocks:
            rect = fitz.Rect(block[:4])
            area = abs(rect)

            if "<image:" in block[4]:
                image_area += area
            else:
                text_area += area

        # Method 2: Check for images directly
        image_list = page.get_images(full=True)
        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = page.parent.extract_image(xref)
            if base_image:
                # Get image rectangle
                img_rect = page.get_image_bbox(img)
                if img_rect:
                    image_area += abs(img_rect)

        # Method 3: Check for vector graphics
        for path in page.get_drawings():
            rect = fitz.Rect(path["rect"])
            image_area += abs(rect)

        return image_area, text_area, total_page_area

    def classify_page(self, page: fitz.Page) -> Dict[str, float]:
        """
        Classify a single page as image-based or text-based.

        Args:
            page (fitz.Page): The PDF page to classify.

        Returns:
            Dict[str, float]: Dictionary containing classification metrics.
        """
        image_area, text_area, total_page_area = self._calculate_areas(page)

        if total_page_area == 0:
            return {
                "image_ratio": 0.0,
                "text_ratio": 0.0,
                "is_image_based": False,
                "is_text_based": False,
                "is_empty": True,
            }

        # Calculate ratios based on total page area
        image_ratio = image_area / total_page_area
        text_ratio = text_area / total_page_area

        # A page is considered image-based if it has significant image content
        # or if it has very little text content
        is_image_based = (image_ratio >= self.image_threshold) or (text_ratio < 0.1)

        return {
            "image_ratio": image_ratio,
            "text_ratio": text_ratio,
            "is_image_based": is_image_based,
            "is_text_based": text_ratio >= (1 - self.image_threshold),
            "is_empty": False,
        }

    def classify_pdf(self, pdf_path: str) -> Dict[str, any]:
        """
        Classify an entire PDF file as image-based or text-based.

        Args:
            pdf_path (str): Path to the PDF file.

        Returns:
            Dict[str, any]: Dictionary containing classification results for each page
                           and overall classification.
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        try:
            with open(pdf_path, "rb") as f:
                pdf = fitz.open(f)

                page_results = []
                total_pages = len(pdf)
                image_based_pages = 0
                text_based_pages = 0
                empty_pages = 0

                for page_num, page in enumerate(pdf):
                    result = self.classify_page(page)
                    page_results.append({"page_number": page_num + 1, **result})

                    if result["is_image_based"]:
                        image_based_pages += 1
                    elif result["is_text_based"]:
                        text_based_pages += 1
                    elif result["is_empty"]:
                        empty_pages += 1

                # Determine overall classification
                image_ratio = image_based_pages / total_pages
                text_ratio = text_based_pages / total_pages

                # A PDF is considered image-based if:
                # 1. More than threshold% of pages are image-based, or
                # 2. The average image ratio across all pages is high
                avg_image_ratio = (
                    sum(p["image_ratio"] for p in page_results) / total_pages
                )
                is_image_based = (image_ratio >= self.image_threshold) or (
                    avg_image_ratio >= 0.5
                )

                return {
                    "filename": pdf_path.name,
                    "total_pages": total_pages,
                    "image_based_pages": image_based_pages,
                    "text_based_pages": text_based_pages,
                    "empty_pages": empty_pages,
                    "image_ratio": image_ratio,
                    "text_ratio": text_ratio,
                    "avg_image_ratio": avg_image_ratio,
                    "is_image_based": is_image_based,
                    "is_text_based": text_ratio >= (1 - self.image_threshold),
                    "page_results": page_results,
                }

        except Exception as e:
            raise Exception(f"Error processing PDF {pdf_path}: {str(e)}")


def classify_pdf(pdf_path: str, image_threshold: float = 0.7) -> Dict[str, any]:
    """
    Convenience function to classify a PDF file.

    Args:
        pdf_path (str): Path to the PDF file.
        image_threshold (float): Threshold ratio of image area to total area to classify as image-based.
                               Default is 0.7 (70%).

    Returns:
        Dict[str, any]: Classification results.
    """
    classifier = PDFClassifier(image_threshold=image_threshold)
    return classifier.classify_pdf(pdf_path)
