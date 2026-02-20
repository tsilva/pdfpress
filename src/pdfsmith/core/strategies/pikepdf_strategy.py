"""Pikepdf-based lossless PDF optimization strategy."""

from pathlib import Path

import pikepdf

from pdfsmith.core.strategies.base import CompressionResult, CompressionStrategy


class PikepdfStrategy(CompressionStrategy):
    """
    Lossless PDF optimization using pikepdf (qpdf bindings).

    Performs:
    - Linearization (fast web view)
    - Stream compression with optimal settings
    - Object stream generation
    - Duplicate object deduplication
    """

    name: str = "pikepdf"

    def compress(
        self,
        input_path: Path,
        output_path: Path,
        quality: str = "default",
    ) -> CompressionResult:
        """Compress PDF using pikepdf optimization."""
        original_size = self._get_file_size(input_path)

        try:
            with pikepdf.open(input_path) as pdf:
                pdf.save(
                    output_path,
                    linearize=True,
                    compress_streams=True,
                    object_stream_mode=pikepdf.ObjectStreamMode.generate,
                    stream_decode_level=pikepdf.StreamDecodeLevel.specialized,
                    recompress_flate=True,
                    preserve_pdfa=True,
                )

            compressed_size = self._get_file_size(output_path)

            return CompressionResult(
                success=True,
                output_path=output_path,
                original_size=original_size,
                compressed_size=compressed_size,
                strategy_name=self.name,
            )

        except Exception as e:
            return CompressionResult(
                success=False,
                output_path=None,
                original_size=original_size,
                compressed_size=0,
                strategy_name=self.name,
                error_message=str(e),
            )
