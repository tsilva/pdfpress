"""Compression strategy implementations."""

from pdfsmith.core.strategies.base import CompressionResult, CompressionStrategy
from pdfsmith.core.strategies.combined_strategy import CombinedStrategy
from pdfsmith.core.strategies.ghostscript_strategy import GhostscriptStrategy
from pdfsmith.core.strategies.pikepdf_strategy import PikepdfStrategy

__all__ = [
    "CompressionStrategy",
    "CompressionResult",
    "PikepdfStrategy",
    "GhostscriptStrategy",
    "CombinedStrategy",
]
