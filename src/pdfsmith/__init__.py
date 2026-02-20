"""pdfsmith - PDF toolkit: compress, merge, and unlock PDF files."""

__version__ = "3.0.0"
__author__ = "Tiago Silva"

from pdfsmith.core.compressor import CompressionOutcome, PDFCompressor
from pdfsmith.merge.merger import MergeResult, merge_pdfs
from pdfsmith.unlock.unlocker import UnlockResult, unlock_pdf

__all__ = [
    "PDFCompressor",
    "CompressionOutcome",
    "MergeResult",
    "merge_pdfs",
    "UnlockResult",
    "unlock_pdf",
    "__version__",
]
