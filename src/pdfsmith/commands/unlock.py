"""Unlock subcommand for pdfsmith."""

from pathlib import Path
from typing import Annotated

import typer
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.prompt import Prompt

from pdfsmith.cli import console
from pdfsmith.unlock.unlocker import UnlockResult, unlock_pdf
from pdfsmith.utils.filesize import format_size


def register(app: typer.Typer) -> None:
    """Register the unlock subcommand."""
    app.command(name="unlock")(main)


def main(
    input: Annotated[
        list[Path],
        typer.Argument(
            help="PDF files to unlock, or a single directory containing PDFs",
        ),
    ],
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
            help="Output directory for unlocked files",
            file_okay=False,
        ),
    ] = None,
    password: Annotated[
        str | None,
        typer.Option(
            "-p",
            "--password",
            help="Password for encrypted PDFs (prompted interactively if not provided)",
        ),
    ] = None,
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
    Unlock encrypted PDF files by removing password protection.

    [bold]Examples:[/bold]

        pdfsmith unlock dir/                           # Unlock all PDFs in directory
        pdfsmith unlock file.pdf -p "secret"           # Unlock with password flag
        pdfsmith unlock file.pdf -o unlocked.pdf       # Custom output filename
        pdfsmith unlock dir/ -d unlocked/              # Unlock to output directory
    """
    # Collect files to process
    files = _collect_files(input)

    if not files:
        console.print("[yellow]No PDF files found.[/yellow]")
        raise typer.Exit(0)

    if output and len(files) > 1:
        console.print("[red]Error:[/red] Cannot use -o with multiple files. Use -d instead.")
        raise typer.Exit(1)

    # Create output directory if specified
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    # Resolve password (prompt once if not provided)
    resolved_password = password
    if resolved_password is None:
        resolved_password = Prompt.ask("Password", password=True, default="")

    # Process files
    failed = False
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        disable=quiet,
    ) as progress:
        task_id = progress.add_task("Unlocking...", total=len(files))

        for input_path in files:
            out = _resolve_output_path(input_path, output, output_dir)
            progress.update(task_id, description=f"[cyan]{input_path.name}[/cyan]")

            result = unlock_pdf(input_path, out, resolved_password)

            if not quiet:
                _show_result(result)

            if not result.success:
                failed = True

            progress.advance(task_id)

    if failed:
        raise typer.Exit(1)


def _collect_files(input: list[Path]) -> list[Path]:
    """Resolve input arguments to a flat list of PDF paths."""
    if len(input) == 1 and input[0].is_dir():
        return sorted(p for p in input[0].iterdir() if p.suffix.lower() == ".pdf")

    files = []
    for path in input:
        if not path.exists():
            console.print(f"[red]Error:[/red] File not found: {path}")
            raise typer.Exit(1)
        if path.is_dir():
            console.print(f"[red]Error:[/red] Expected file, got directory: {path}")
            raise typer.Exit(1)
        files.append(path)
    return files


def _resolve_output_path(
    input_path: Path,
    output: Path | None,
    output_dir: Path | None,
) -> Path:
    """Determine output path for a given input."""
    if output:
        return output
    stem = f"{input_path.stem}.unlocked.pdf"
    if output_dir:
        return output_dir / stem
    return input_path.parent / stem


def _show_result(result: UnlockResult) -> None:
    """Display unlock result for a single file."""
    name = result.input_path.name
    if result.success:
        if result.was_encrypted:
            size = (
                format_size(result.output_path.stat().st_size)
                if result.output_path.exists()
                else "?"
            )
            console.print(
                f"  [bold]{name}[/bold] [green]unlocked[/green]"
                f" -> {result.output_path.name} ({size})"
            )
        else:
            console.print(f"  [bold]{name}[/bold] [dim]not encrypted, skipped[/dim]")
    else:
        console.print(f"  [bold]{name}[/bold] [red]ERROR[/red] {result.error_message}")
