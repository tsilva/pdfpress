"""Combined Ghostscript + pikepdf compression strategy."""

import tempfile
from pathlib import Path

from pdfsmith.core.strategies.base import CompressionResult, CompressionStrategy
from pdfsmith.core.strategies.ghostscript_strategy import GhostscriptStrategy
from pdfsmith.core.strategies.pikepdf_strategy import PikepdfStrategy


class CombinedStrategy(CompressionStrategy):
    """
    Two-stage compression: Ghostscript for image reduction,
    followed by pikepdf for PDF structure optimization.
    """

    name: str = "combined"

    def __init__(self, gs_quality: str = "screen"):
        """Initialize with Ghostscript quality preset."""
        self.gs_strategy = GhostscriptStrategy()
        self.pikepdf_strategy = PikepdfStrategy()
        self.gs_quality = gs_quality

    def compress(
        self,
        input_path: Path,
        output_path: Path,
        quality: str = "screen",
    ) -> CompressionResult:
        """Compress PDF using Ghostscript then pikepdf."""
        original_size = self._get_file_size(input_path)

        with tempfile.TemporaryDirectory() as tmpdir:
            intermediate_path = Path(tmpdir) / "gs_output.pdf"

            # Stage 1: Ghostscript compression
            gs_result = self.gs_strategy.compress(input_path, intermediate_path, quality)

            if not gs_result.success:
                return CompressionResult(
                    success=False,
                    output_path=None,
                    original_size=original_size,
                    compressed_size=0,
                    strategy_name=self.name,
                    error_message=f"Ghostscript stage failed: {gs_result.error_message}",
                )

            # Stage 2: pikepdf optimization
            pike_result = self.pikepdf_strategy.compress(
                intermediate_path,
                output_path,
                quality,
            )

            if not pike_result.success:
                return CompressionResult(
                    success=False,
                    output_path=None,
                    original_size=original_size,
                    compressed_size=0,
                    strategy_name=self.name,
                    error_message=f"Pikepdf stage failed: {pike_result.error_message}",
                )

            return CompressionResult(
                success=True,
                output_path=output_path,
                original_size=original_size,
                compressed_size=pike_result.compressed_size,
                strategy_name=f"{self.name}({quality})",
            )
