"""Base compression strategy interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CompressionResult:
    """Result of a compression attempt."""

    success: bool
    output_path: Path | None
    original_size: int
    compressed_size: int
    strategy_name: str
    error_message: str | None = None

    @property
    def reduction_ratio(self) -> float:
        """Return the reduction ratio (0.0 to 1.0)."""
        if self.original_size == 0:
            return 0.0
        return 1.0 - (self.compressed_size / self.original_size)

    @property
    def reduction_percent(self) -> int:
        """Return the reduction percentage (0 to 100)."""
        return int(self.reduction_ratio * 100)


class CompressionStrategy(ABC):
    """Abstract base class for compression strategies."""

    name: str = "base"

    @abstractmethod
    def compress(
        self,
        input_path: Path,
        output_path: Path,
        quality: str = "default",
    ) -> CompressionResult:
        """
        Compress a PDF file.

        Args:
            input_path: Path to input PDF
            output_path: Path for compressed output
            quality: Quality preset name

        Returns:
            CompressionResult with outcome details
        """
        pass

    def _get_file_size(self, path: Path) -> int:
        """Get file size in bytes."""
        return path.stat().st_size if path.exists() else 0
