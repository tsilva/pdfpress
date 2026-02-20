"""Ghostscript-based lossy PDF compression strategy."""

import shutil
import subprocess
from pathlib import Path

from pdfsmith.core.strategies.base import CompressionResult, CompressionStrategy


class GhostscriptStrategy(CompressionStrategy):
    """
    Lossy PDF compression using Ghostscript subprocess.

    Best for image-heavy PDFs where quality loss is acceptable
    for significant size reduction.
    """

    name: str = "ghostscript"

    # Quality presets mapping to Ghostscript PDFSETTINGS
    QUALITY_SETTINGS = {
        "screen": "/screen",  # 72 DPI - aggressive, web viewing
        "ebook": "/ebook",  # 150 DPI - balanced
        "printer": "/printer",  # 300 DPI - high quality
        "prepress": "/prepress",  # 300 DPI - highest quality
        "default": "/default",  # General purpose
    }

    def __init__(self, gs_path: str | None = None):
        """Initialize with optional Ghostscript path."""
        self.gs_path = gs_path or self._find_ghostscript()

    def _find_ghostscript(self) -> str:
        """Find Ghostscript executable."""
        for name in ["gs", "gswin64c", "gswin32c"]:
            if shutil.which(name):
                return name
        raise RuntimeError(
            "Ghostscript not found. Install with: brew install ghostscript (macOS) "
            "or apt install ghostscript (Linux)"
        )

    def compress(
        self,
        input_path: Path,
        output_path: Path,
        quality: str = "screen",
    ) -> CompressionResult:
        """Compress PDF using Ghostscript."""
        original_size = self._get_file_size(input_path)
        pdf_setting = self.QUALITY_SETTINGS.get(quality, "/screen")

        cmd = [
            self.gs_path,
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            f"-dPDFSETTINGS={pdf_setting}",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            "-dDetectDuplicateImages=true",
            "-dCompressFonts=true",
            "-dSubsetFonts=true",
            f"-sOutputFile={output_path}",
            str(input_path),
        ]

        try:
            subprocess.run(
                cmd,
                capture_output=True,
                timeout=300,  # 5 minute timeout
                check=True,
            )

            compressed_size = self._get_file_size(output_path)

            return CompressionResult(
                success=True,
                output_path=output_path,
                original_size=original_size,
                compressed_size=compressed_size,
                strategy_name=f"{self.name}({quality})",
            )

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            return CompressionResult(
                success=False,
                output_path=None,
                original_size=original_size,
                compressed_size=0,
                strategy_name=self.name,
                error_message=f"Ghostscript error: {error_msg}",
            )
        except subprocess.TimeoutExpired:
            return CompressionResult(
                success=False,
                output_path=None,
                original_size=original_size,
                compressed_size=0,
                strategy_name=self.name,
                error_message="Ghostscript timeout exceeded (5 minutes)",
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
