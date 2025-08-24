"""
PDF Processor module that provides both simple and full-featured PDF processing capabilities.
"""

from .processor import PDFProcessor

__all__ = ["PDFProcessor"]

# Optional imports for full processor
try:
    from .full_processor import DocumentChunk, FullPDFProcessor

    __all__.extend(["FullPDFProcessor", "DocumentChunk"])
except ImportError:
    pass  # Full processor dependencies not available
