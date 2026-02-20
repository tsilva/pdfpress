"""Split subcommand for pdfsmith."""

from pathlib import Path
from typing import Annotated

import typer
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

from pdfsmith.cli import console
from pdfsmith.split.splitter import (
    SplitResult,
    parse_page_spec,
    split_pdf,
)
from pdfsmith.utils.filesize import format_size


def register(app: typer.Typer) -> None:
    """Register the split subcommand."""
    app.command(name="split")(main)


def main(
    input: Annotated[
        Path,
        typer.Argument(
            help="Input PDF file to split",
        ),
    ],
    pages: Annotated[
        str,
        typer.Option(
            "-p",
            "--pages",
            help="Pages to extract (e.g., '1,3,5-10', 'all', 'odd', 'even')",
        ),
    ],
    output: Annotated[
        Path | None,
        typer.Option(
            "-o",
            "--output",
            help="Output filename (default: <input>.split.pdf)",
            dir_okay=False,
        ),
    ] = None,
    output_dir: Annotated[
        Path | None,
        typer.Option(
            "-d",
            "--output-dir",
            help="Output directory for split file(s)",
            file_okay=False,
        ),
    ] = None,
    individual: Annotated[
        bool,
        typer.Option(
            "-i",
            "--individual",
            help="Export each page to a separate PDF file",
        ),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option(
            "-q",
            "--quiet",
            help="Suppress output except errors",
        ),
    ] = False,
) -> None:
    """
    Extract specific pages from a PDF file.

    [bold]Examples:[/bold]

        pdfsmith split document.pdf -p "1,3,5"           # Extract pages 1, 3, and 5
        pdfsmith split document.pdf -p "1-5"             # Extract pages 1 through 5
        pdfsmith split document.pdf -p "1,3,5-10,15"     # Mixed selection
        pdfsmith split document.pdf -p "all"             # Extract all pages
        pdfsmith split document.pdf -p "odd"             # Extract odd pages (1,3,5...)
        pdfsmith split document.pdf -p "even"            # Extract even pages (2,4,6...)
        pdfsmith split document.pdf -p "1-5" -o out.pdf  # Custom output filename
        pdfsmith split document.pdf -p "all" -i          # Each page to separate file
        pdfsmith split document.pdf -p "all" -i -d out/  # Individual files in out/
    """
    # Validate input file
    if not input.exists():
        console.print(f"[red]Error:[/red] File not found: {input}")
        raise typer.Exit(1)

    if input.is_dir():
        console.print(f"[red]Error:[/red] Expected file, got directory: {input}")
        raise typer.Exit(1)

    if input.suffix.lower() != ".pdf":
        console.print(f"[red]Error:[/red] Not a PDF file: {input}")
        raise typer.Exit(1)

    # Cannot use -o with --individual
    if individual and output:
        console.print(
            "[red]Error:[/red] Cannot use -o with --individual. Use -d to specify output directory."
        )
        raise typer.Exit(1)

    # Create output directory if specified
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    # Resolve output directory
    out_dir = output_dir or input.parent

    # Parse page specification
    try:
        import pikepdf

        with pikepdf.open(input) as src:
            total_pages = len(src.pages)
            page_list = parse_page_spec(pages, total_pages)
    except ValueError as e:
        console.print(f"[red]Error:[/red] Invalid page specification: {e}")
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"[red]Error:[/red] Could not read PDF: {e}")
        raise typer.Exit(1) from None

    if not quiet:
        console.print(f"Extracting {len(page_list)} page(s) from [cyan]{input.name}[/cyan]")

    # Process based on mode
    if individual:
        _process_individual(input, out_dir, page_list, quiet)
    else:
        _process_single(input, output, out_dir, page_list, quiet)


def _process_single(
    input: Path,
    output: Path | None,
    output_dir: Path,
    page_list: list[int],
    quiet: bool,
) -> None:
    """Process single output mode."""
    out = _resolve_output_path(input, output, output_dir)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        disable=quiet,
    ) as progress:
        progress.add_task("Splitting PDF...", total=None)
        result = split_pdf(input, out, page_list)

    if not quiet:
        _show_result(result)

    if not result.success:
        raise typer.Exit(1)


def _process_individual(
    input: Path,
    output_dir: Path,
    page_list: list[int],
    quiet: bool,
) -> None:
    """Process individual page mode."""
    failed = False

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        disable=quiet,
    ) as progress:
        task_id = progress.add_task("Splitting PDF...", total=len(page_list))

        # Process pages one by one to show progress
        for page_num in page_list:
            # Generate output filename
            output_name = f"{input.stem}_page_{page_num + 1:03d}.pdf"
            output_path = output_dir / output_name

            progress.update(task_id, description=f"[cyan]Page {page_num + 1}[/cyan]")

            result = split_pdf(input, output_path, [page_num])

            if not quiet:
                _show_individual_result(result)

            if not result.success:
                failed = True

            progress.advance(task_id)

    if not quiet and len(page_list) > 1:
        console.print(f"[green]Created {len(page_list)} file(s) in {output_dir}/[/green]")

    if failed:
        raise typer.Exit(1)


def _resolve_output_path(
    input_path: Path,
    output: Path | None,
    output_dir: Path,
) -> Path:
    """Determine output path for the split operation."""
    if output:
        return output
    stem = f"{input_path.stem}.split.pdf"
    return output_dir / stem


def _show_result(result: SplitResult) -> None:
    """Display split result for single file mode."""
    if result.success:
        size = (
            format_size(result.output_path.stat().st_size) if result.output_path.exists() else "?"
        )
        page_str = _format_page_list(result.pages)
        console.print(
            f"  [bold]{result.output_path.name}[/bold] "
            f"[green]OK[/green] "
            f"({len(result.pages)} page(s): {page_str}) "
            f"{size}"
        )
    else:
        console.print(f"  [red]ERROR[/red] {result.error_message}")


def _show_individual_result(result: SplitResult) -> None:
    """Display split result for individual page mode."""
    if result.success:
        size = (
            format_size(result.output_path.stat().st_size) if result.output_path.exists() else "?"
        )
        console.print(f"  [bold]{result.output_path.name}[/bold] [green]OK[/green] {size}")
    else:
        console.print(f"  [red]ERROR[/red] {result.error_message}")


def _format_page_list(pages: list[int]) -> str:
    """Format a list of page numbers for display."""
    if not pages:
        return ""

    # Convert to 1-indexed for display
    pages_1idx = [p + 1 for p in pages]

    if len(pages_1idx) <= 5:
        return ", ".join(map(str, pages_1idx))

    return f"{pages_1idx[0]}, {pages_1idx[1]}, ..., {pages_1idx[-1]}"
