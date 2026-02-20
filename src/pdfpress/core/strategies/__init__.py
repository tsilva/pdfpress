"""Compression strategy implementations."""

from pdfpress.core.strategies.base import CompressionResult, CompressionStrategy
from pdfpress.core.strategies.combined_strategy import CombinedStrategy
from pdfpress.core.strategies.ghostscript_strategy import GhostscriptStrategy
from pdfpress.core.strategies.pikepdf_strategy import PikepdfStrategy

__all__ = [
    "CompressionStrategy",
    "CompressionResult",
    "PikepdfStrategy",
    "GhostscriptStrategy",
    "CombinedStrategy",
]
