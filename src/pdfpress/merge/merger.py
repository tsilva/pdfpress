"""PDF merging business logic."""

import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import pikepdf


@dataclass
class MergeResult:
    """Result of a PDF merge operation."""

    input_files: list[Path]
    output_path: Path
    success: bool
    page_count: int = 0
    output_size: int = 0
    error_message: str | None = None


def get_base_name(filename: str) -> str:
    """Extract base name from filename by removing numeric suffixes.

    Examples:
        "report-1.pdf" -> "report"
        "doc_3.pdf" -> "doc"
    """
    return re.sub(r"[-_ ]+\d+$", "", Path(filename).stem)


def group_similar_pdfs(directory: Path) -> dict[str, list[Path]]:
    """Group PDF files in a directory by their base names.

    Returns only groups with multiple files, sorted alphabetically within each group.
    """
    groups: dict[str, list[Path]] = defaultdict(list)
    for path in directory.iterdir():
        if path.suffix.lower() == ".pdf":
            base_name = get_base_name(path.name)
            groups[base_name].append(path)

    return {k: sorted(v) for k, v in groups.items() if len(v) > 1}


def merge_pdfs(input_files: list[Path], output_path: Path) -> MergeResult:
    """Merge multiple PDF files into a single output file.

    Uses context managers to ensure all handles are properly closed.

    Args:
        input_files: List of paths to PDF files to merge
        output_path: Path for the merged output file

    Returns:
        MergeResult with details about the merge operation
    """
    handles = []
    try:
        merged = pikepdf.new()
        for input_file in input_files:
            src = pikepdf.open(input_file)
            handles.append(src)
            merged.pages.extend(src.pages)

        merged.save(output_path)
        page_count = len(merged.pages)

        return MergeResult(
            input_files=list(input_files),
            output_path=output_path,
            success=True,
            page_count=page_count,
            output_size=output_path.stat().st_size,
        )
    except Exception as e:
        return MergeResult(
            input_files=list(input_files),
            output_path=output_path,
            success=False,
            error_message=str(e),
        )
    finally:
        for handle in handles:
            handle.close()
