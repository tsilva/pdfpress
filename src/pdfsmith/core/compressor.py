"""Main PDF compression orchestrator."""

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from pdfsmith.core.strategies.base import CompressionResult, CompressionStrategy
from pdfsmith.core.strategies.combined_strategy import CombinedStrategy
from pdfsmith.core.strategies.ghostscript_strategy import GhostscriptStrategy
from pdfsmith.core.strategies.pikepdf_strategy import PikepdfStrategy


@dataclass
class CompressionOutcome:
    """Final compression outcome after trying all strategies."""

    input_path: Path
    output_path: Path
    original_size: int
    final_size: int
    best_strategy: str
    all_results: list[CompressionResult]

    @property
    def reduction_percent(self) -> int:
        """Return the reduction percentage."""
        if self.original_size == 0:
            return 0
        return int((1.0 - self.final_size / self.original_size) * 100)

    @property
    def improved(self) -> bool:
        """Return True if compression improved file size."""
        return self.final_size < self.original_size


class PDFCompressor:
    """
    Main compression orchestrator that tries multiple strategies
    and selects the best result.
    """

    def __init__(
        self,
        quality: str = "screen",
    ):
        """
        Initialize the compressor.

        Args:
            quality: Quality preset (screen, ebook, printer, prepress)
        """
        self.quality = quality

        # Initialize strategies
        self.strategies: list[CompressionStrategy] = [
            PikepdfStrategy(),
            GhostscriptStrategy(),
            CombinedStrategy(),
        ]

    def compress(
        self,
        input_path: Path,
        output_path: Path,
    ) -> CompressionOutcome:
        """
        Compress a PDF using all strategies and keep the best result.

        Args:
            input_path: Path to input PDF file
            output_path: Path for output file

        Returns:
            CompressionOutcome with details about the compression
        """
        original_size = input_path.stat().st_size
        results: list[CompressionResult] = []

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Try each strategy
            for i, strategy in enumerate(self.strategies):
                strategy_output = tmpdir_path / f"strategy_{i}.pdf"
                result = strategy.compress(input_path, strategy_output, self.quality)
                results.append(result)

            # Find best result (smallest successful output)
            best_result: CompressionResult | None = None
            best_size = original_size

            for result in results:
                if result.success and result.compressed_size < best_size:
                    best_result = result
                    best_size = result.compressed_size

            # Save best result or copy original
            if best_result and best_result.output_path:
                shutil.copy2(best_result.output_path, output_path)
                final_size = best_size
                best_strategy = best_result.strategy_name
            else:
                shutil.copy2(input_path, output_path)
                final_size = original_size
                best_strategy = "none"

        return CompressionOutcome(
            input_path=input_path,
            output_path=output_path,
            original_size=original_size,
            final_size=final_size,
            best_strategy=best_strategy,
            all_results=results,
        )
