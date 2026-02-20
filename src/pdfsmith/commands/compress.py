"""Compress subcommand for pdfsmith."""

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated

import typer
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

from pdfsmith.cli import console
from pdfsmith.core.compressor import CompressionOutcome, PDFCompressor
from pdfsmith.parallel.executor import ParallelCompressor
from pdfsmith.utils.dependencies import check_dependencies, get_install_instructions
from pdfsmith.utils.filesize import format_size


def register(app: typer.Typer) -> None:
    """Register the compress subcommand."""
    app.command(name="compress")(main)


def main(
    files: Annotated[
        list[Path] | None,
        typer.Argument(
            help="Input PDF file(s) to compress (default: *.pdf in current directory)",
        ),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option(
            "-o",
            "--output",
            help="Output filename (single file mode only)",
            dir_okay=False,
        ),
    ] = None,
    output_dir: Annotated[
        Path | None,
        typer.Option(
            "-d",
            "--output-dir",
            help="Output directory for compressed files",
            file_okay=False,
        ),
    ] = None,
    in_place: Annotated[
        bool,
        typer.Option(
            "-i",
            "--in-place",
            help="Replace original files (use with caution)",
        ),
    ] = False,
    quality: Annotated[
        str,
        typer.Option(
            "-Q",
            "--quality",
            help="Quality preset: screen (72dpi), ebook (150dpi), printer (300dpi), prepress",
            case_sensitive=False,
        ),
    ] = "ebook",
    jobs: Annotated[
        int,
        typer.Option(
            "-j",
            "--jobs",
            help="Number of parallel jobs (0 = auto)",
            min=0,
        ),
    ] = 0,
    quiet: Annotated[
        bool,
        typer.Option(
            "-q",
            "--quiet",
            help="Suppress output except errors",
        ),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "-n",
            "--dry-run",
            help="Simulate compression without saving output files",
        ),
    ] = False,
) -> None:
    """
    Compress PDF files using multiple strategies, keeping the smallest result.

    [bold]Examples:[/bold]

        pdfsmith compress                               # Compress all *.pdf in current directory
        pdfsmith compress document.pdf                  # Creates document.compressed.pdf
        pdfsmith compress document.pdf -o small.pdf    # Creates small.pdf
        pdfsmith compress *.pdf -d compressed/         # Batch compress to directory
        pdfsmith compress -i *.pdf                     # Replace original files
        pdfsmith compress *.pdf -j 4                   # Use 4 parallel workers
        pdfsmith compress --dry-run                    # Preview compression without saving
    """
    # Resolve files (handles default *.pdf pattern)
    files = _discover_pdf_files(files)

    if not files:
        console.print("[yellow]No PDF files found in current directory.[/yellow]")
        raise typer.Exit(0)

    if output and len(files) > 1:
        console.print("[red]Error:[/red] Cannot use -o with multiple files. Use -d instead.")
        raise typer.Exit(1)

    if output and in_place:
        console.print("[red]Error:[/red] Cannot use -o and -i together.")
        raise typer.Exit(1)

    if dry_run and (output or in_place):
        console.print("[red]Error:[/red] Cannot use --dry-run with -o or -i.")
        raise typer.Exit(1)

    # Validate quality preset
    valid_qualities = ["screen", "ebook", "printer", "prepress", "default"]
    if quality.lower() not in valid_qualities:
        console.print(
            f"[red]Error:[/red] Invalid quality '{quality}'. "
            f"Choose from: {', '.join(valid_qualities)}"
        )
        raise typer.Exit(1)

    # Check dependencies
    missing = check_dependencies()
    if missing:
        console.print(f"[red]Error:[/red] Missing dependencies: {', '.join(missing)}")
        console.print(get_install_instructions())
        raise typer.Exit(1)

    # Create output directory if needed
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    # Confirm operation (skip in dry-run or quiet mode)
    if not dry_run and not quiet:
        if not _confirm_operation(files, output_dir, in_place):
            console.print("Operation cancelled.")
            raise typer.Exit(0)

    # Process files
    if dry_run:
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            if len(files) > 1 and jobs != 1:
                outcomes = _process_parallel(files, temp_path, False, quality, jobs, quiet)
            else:
                outcomes = _process_sequential(files, None, temp_path, False, quality, quiet)
            if not quiet and len(outcomes) > 1:
                _show_summary(outcomes)
    else:
        if len(files) > 1 and jobs != 1:
            outcomes = _process_parallel(files, output_dir, in_place, quality, jobs, quiet)
        else:
            outcomes = _process_sequential(files, output, output_dir, in_place, quality, quiet)

        if not quiet and len(outcomes) > 1:
            _show_summary(outcomes)

    if any(o.best_strategy == "error" for o in outcomes):
        raise typer.Exit(1)


def _discover_pdf_files(files: list[Path] | None) -> list[Path]:
    """Resolve file arguments, defaulting to *.pdf in CWD."""
    if files:
        resolved = []
        for f in files:
            path = Path(f).resolve()
            if not path.exists():
                console.print(f"[red]Error:[/red] File not found: {f}")
                raise typer.Exit(1)
            if path.is_dir():
                console.print(f"[red]Error:[/red] Expected file, got directory: {f}")
                raise typer.Exit(1)
            resolved.append(path)
        return resolved

    cwd = Path.cwd()
    return sorted(cwd.glob("*.pdf"))


def _confirm_operation(
    files: list[Path],
    output_dir: Path | None,
    in_place: bool,
) -> bool:
    """Show operation summary and ask for confirmation."""
    cwd = Path.cwd()

    console.print()
    console.print(f"[bold]Working directory:[/bold] {cwd}")
    console.print(f"[bold]Files to compress:[/bold] {len(files)}")

    sample_count = min(5, len(files))
    for f in files[:sample_count]:
        console.print(f"  • {f.name}")
    if len(files) > sample_count:
        console.print(f"  ... and {len(files) - sample_count} more")

    if in_place:
        console.print("[bold]Output:[/bold] [yellow]Replacing original files[/yellow]")
    elif output_dir:
        console.print(f"[bold]Output:[/bold] {output_dir}/")
    else:
        console.print("[bold]Output:[/bold] Same directory as input (*.compressed.pdf)")

    console.print()
    return typer.confirm("Proceed with compression?")


def _process_sequential(
    files: list[Path],
    output: Path | None,
    output_dir: Path | None,
    in_place: bool,
    quality: str,
    quiet: bool,
) -> list[CompressionOutcome]:
    """Process files sequentially with progress display."""
    outcomes = []
    compressor = PDFCompressor(quality=quality)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        disable=quiet,
    ) as progress:
        task = progress.add_task("Compressing...", total=len(files))

        for input_path in files:
            output_path = _resolve_output_path(input_path, output, output_dir, in_place)

            progress.update(task, description=f"[cyan]{input_path.name}[/cyan]")
            outcome = compressor.compress(input_path, output_path)
            outcomes.append(outcome)

            if not quiet:
                _show_result(outcome)

            progress.advance(task)

    return outcomes


def _process_parallel(
    files: list[Path],
    output_dir: Path | None,
    in_place: bool,
    quality: str,
    jobs: int,
    quiet: bool,
) -> list[CompressionOutcome]:
    """Process files in parallel with progress display."""
    parallel_compressor = ParallelCompressor(
        quality=quality,
        max_workers=jobs if jobs > 0 else None,
    )

    tasks = []
    for input_path in files:
        output_path = _resolve_output_path(input_path, None, output_dir, in_place)
        tasks.append((input_path, output_path))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        disable=quiet,
    ) as progress:
        task_id = progress.add_task("Compressing files...", total=len(tasks))

        def on_complete(outcome: CompressionOutcome) -> None:
            progress.advance(task_id)
            if not quiet:
                _show_result(outcome)

        outcomes = parallel_compressor.compress_batch(tasks, on_complete)

    return outcomes


def _resolve_output_path(
    input_path: Path,
    output: Path | None,
    output_dir: Path | None,
    in_place: bool,
) -> Path:
    """Determine output path based on options."""
    if output:
        return output
    if in_place:
        return input_path
    if output_dir:
        return output_dir / f"{input_path.stem}.compressed.pdf"
    return input_path.parent / f"{input_path.stem}.compressed.pdf"


def _show_result(outcome: CompressionOutcome) -> None:
    """Display compression result for a single file."""
    name = outcome.input_path.name
    orig = format_size(outcome.original_size)
    final = format_size(outcome.final_size)

    if outcome.best_strategy == "error":
        console.print(f"  [bold]{name}[/bold] [red]ERROR[/red]")
    elif outcome.improved:
        console.print(
            f"  [bold]{name}[/bold] {orig} -> [green]{final}[/green] "
            f"([green]-{outcome.reduction_percent}%[/green]) via {outcome.best_strategy}"
        )
    else:
        console.print(f"  [bold]{name}[/bold] {orig} -> [yellow]{final}[/yellow] (no reduction)")


def _show_summary(outcomes: list[CompressionOutcome]) -> None:
    """Display summary table for batch operations."""
    from rich.table import Table

    table = Table(title="Compression Summary")
    table.add_column("File", style="cyan")
    table.add_column("Original", justify="right")
    table.add_column("Compressed", justify="right")
    table.add_column("Reduction", justify="right")
    table.add_column("Strategy")

    total_original = 0
    total_final = 0

    for o in outcomes:
        total_original += o.original_size
        total_final += o.final_size

        if o.best_strategy == "error":
            table.add_row(
                o.input_path.name, format_size(o.original_size), "-", "[red]ERROR[/red]", "-"
            )
        else:
            reduction = f"-{o.reduction_percent}%" if o.improved else "0%"
            style = "green" if o.improved else "yellow"

            table.add_row(
                o.input_path.name,
                format_size(o.original_size),
                format_size(o.final_size),
                f"[{style}]{reduction}[/{style}]",
                o.best_strategy,
            )

    total_reduction = int((1 - total_final / total_original) * 100) if total_original else 0
    table.add_row(
        "[bold]TOTAL[/bold]",
        f"[bold]{format_size(total_original)}[/bold]",
        f"[bold]{format_size(total_final)}[/bold]",
        f"[bold green]-{total_reduction}%[/bold green]",
        "",
    )

    console.print()
    console.print(table)
