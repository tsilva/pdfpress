"""Parallel PDF compression executor."""

import os
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from pdfsmith.core.compressor import CompressionOutcome, PDFCompressor


def _compress_single(args: tuple[Path, Path, str]) -> CompressionOutcome:
    """
    Worker function for parallel compression.

    Must be at module level for pickling.
    """
    input_path, output_path, quality = args
    compressor = PDFCompressor(quality=quality)
    return compressor.compress(input_path, output_path)


class ParallelCompressor:
    """
    Parallel PDF compression using ProcessPoolExecutor.

    Uses processes instead of threads because:
    1. Ghostscript subprocess calls release GIL anyway
    2. pikepdf may hold GIL during C++ operations
    3. True parallelism for CPU-bound analysis
    """

    def __init__(
        self,
        quality: str = "screen",
        max_workers: int | None = None,
    ):
        """
        Initialize the parallel compressor.

        Args:
            quality: Quality preset (screen, ebook, printer, prepress)
            max_workers: Number of parallel workers (None = auto)
        """
        self.quality = quality
        # Default to CPU count, but cap at reasonable limit
        self.max_workers = max_workers or min(os.cpu_count() or 4, 8)

    def compress_batch(
        self,
        tasks: list[tuple[Path, Path]],
        on_complete: Callable[[CompressionOutcome], None] | None = None,
    ) -> list[CompressionOutcome]:
        """
        Compress multiple PDFs in parallel.

        Args:
            tasks: List of (input_path, output_path) tuples
            on_complete: Callback fired when each file completes

        Returns:
            List of CompressionOutcome in original order
        """
        # Prepare args with quality
        args_list = [(input_path, output_path, self.quality) for input_path, output_path in tasks]

        outcomes: list[CompressionOutcome | None] = [None] * len(tasks)

        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_index = {
                executor.submit(_compress_single, args): i for i, args in enumerate(args_list)
            }

            # Collect results as they complete
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    outcome = future.result()
                    outcomes[index] = outcome
                    if on_complete:
                        on_complete(outcome)
                except Exception:
                    # Create error outcome
                    input_path, output_path, _ = args_list[index]
                    error_outcome = CompressionOutcome(
                        input_path=input_path,
                        output_path=output_path,
                        original_size=input_path.stat().st_size if input_path.exists() else 0,
                        final_size=0,
                        best_strategy="error",
                        all_results=[],
                    )
                    outcomes[index] = error_outcome
                    if on_complete:
                        on_complete(error_outcome)

        return [o for o in outcomes if o is not None]
