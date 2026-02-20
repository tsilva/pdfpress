"""PDF splitting business logic."""

import re
from dataclasses import dataclass
from pathlib import Path

import pikepdf


@dataclass
class SplitResult:
    """Result of a PDF split operation."""

    input_path: Path
    output_path: Path
    pages: list[int]
    success: bool
    error_message: str | None = None


@dataclass
class SplitIndividualResult:
    """Result of splitting PDF into individual pages."""

    input_path: Path
    results: list[SplitResult]
    success_count: int
    failed_count: int


def parse_page_spec(spec: str, total_pages: int) -> list[int]:
    """Parse a page specification string into a list of page numbers.

    Supports:
        - Single pages: "1,3,5"
        - Ranges: "1-5", "10-15"
        - Keywords: "all", "odd", "even"
        - Combinations: "1,3,5-10,15"

    Page numbers are 1-indexed in the spec but returned as 0-indexed.

    Args:
        spec: Page specification string
        total_pages: Total number of pages in the PDF

    Returns:
        List of 0-indexed page numbers

    Raises:
        ValueError: If the spec is invalid
    """
    spec = spec.strip().lower()

    if spec == "all":
        return list(range(total_pages))

    if spec == "odd":
        return [i for i in range(total_pages) if i % 2 == 0]

    if spec == "even":
        return [i for i in range(total_pages) if i % 2 == 1]

    pages: set[int] = set()

    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue

        if "-" in part:
            # Range: "1-5"
            match = re.match(r"^(\d+)-(\d+)$", part)
            if not match:
                raise ValueError(f"Invalid range: {part}")
            start, end = int(match.group(1)), int(match.group(2))
            if start < 1 or end > total_pages or start > end:
                raise ValueError(f"Invalid range: {part} (valid: 1-{total_pages})")
            pages.update(range(start - 1, end))
        else:
            # Single page
            try:
                page = int(part)
                if page < 1 or page > total_pages:
                    raise ValueError(f"Invalid page: {part} (valid: 1-{total_pages})")
                pages.add(page - 1)
            except ValueError as e:
                if "Invalid page" in str(e):
                    raise
                raise ValueError(f"Invalid page number: {part}") from None

    if not pages:
        raise ValueError(f"No pages specified: {spec}")

    return sorted(pages)


def split_pdf(input_path: Path, output_path: Path, pages: list[int]) -> SplitResult:
    """Extract specific pages from a PDF into a new file.

    Args:
        input_path: Path to the input PDF
        output_path: Path for the output PDF
        pages: List of 0-indexed page numbers to extract

    Returns:
        SplitResult with details about the split operation
    """
    try:
        with pikepdf.open(input_path) as src:
            total_pages = len(src.pages)

            # Validate pages
            invalid_pages = [p for p in pages if p < 0 or p >= total_pages]
            if invalid_pages:
                return SplitResult(
                    input_path=input_path,
                    output_path=output_path,
                    pages=pages,
                    success=False,
                    error_message=(
                        f"Invalid page numbers: {invalid_pages} (PDF has {total_pages} pages)"
                    ),
                )

            # Create new PDF with selected pages
            dst = pikepdf.new()
            for page_num in pages:
                dst.pages.append(src.pages[page_num])

            dst.save(output_path)

            return SplitResult(
                input_path=input_path,
                output_path=output_path,
                pages=pages,
                success=True,
            )

    except Exception as e:
        return SplitResult(
            input_path=input_path,
            output_path=output_path,
            pages=pages,
            success=False,
            error_message=str(e),
        )


def split_pdf_individual(
    input_path: Path,
    output_dir: Path,
    pages: list[int],
    filename_pattern: str = "{stem}_page_{page:03d}.pdf",
) -> SplitIndividualResult:
    """Extract each page to a separate PDF file.

    Args:
        input_path: Path to the input PDF
        output_dir: Directory for output files
        pages: List of 0-indexed page numbers to extract
        filename_pattern: Pattern for output filenames, supports {stem} and {page}

    Returns:
        SplitIndividualResult with details about all split operations
    """
    results: list[SplitResult] = []
    success_count = 0
    failed_count = 0

    try:
        with pikepdf.open(input_path) as src:
            total_pages = len(src.pages)
            stem = input_path.stem

            for page_num in pages:
                # Validate page
                if page_num < 0 or page_num >= total_pages:
                    result = SplitResult(
                        input_path=input_path,
                        output_path=output_dir / f"{stem}_page_{page_num + 1:03d}.pdf",
                        pages=[page_num],
                        success=False,
                        error_message=(
                            f"Invalid page number: {page_num + 1} (PDF has {total_pages} pages)"
                        ),
                    )
                    results.append(result)
                    failed_count += 1
                    continue

                # Generate output filename
                output_name = filename_pattern.format(stem=stem, page=page_num + 1)
                output_path = output_dir / output_name

                # Create single-page PDF
                dst = pikepdf.new()
                dst.pages.append(src.pages[page_num])
                dst.save(output_path)

                result = SplitResult(
                    input_path=input_path,
                    output_path=output_path,
                    pages=[page_num],
                    success=True,
                )
                results.append(result)
                success_count += 1

    except Exception as e:
        # If we can't even open the PDF, create a single failed result
        result = SplitResult(
            input_path=input_path,
            output_path=output_dir / f"{input_path.stem}_page_001.pdf",
            pages=pages,
            success=False,
            error_message=str(e),
        )
        results.append(result)
        failed_count += 1

    return SplitIndividualResult(
        input_path=input_path,
        results=results,
        success_count=success_count,
        failed_count=failed_count,
    )
