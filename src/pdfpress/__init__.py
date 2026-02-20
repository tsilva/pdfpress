"""pdfpress - PDF toolkit: compress, merge, and unlock PDF files."""

__version__ = "1.0.2"
__author__ = "Tiago Silva"

from pdfpress.core.compressor import CompressionOutcome, PDFCompressor
from pdfpress.merge.merger import MergeResult, merge_pdfs
from pdfpress.unlock.unlocker import UnlockResult, unlock_pdf

__all__ = [
    "PDFCompressor",
    "CompressionOutcome",
    "MergeResult",
    "merge_pdfs",
    "UnlockResult",
    "unlock_pdf",
    "__version__",
]
