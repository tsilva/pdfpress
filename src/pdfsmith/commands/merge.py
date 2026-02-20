"""Merge subcommand for pdfsmith."""

from pathlib import Path
from typing import Annotated

import typer
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.prompt import Confirm

from pdfsmith.cli import console
from pdfsmith.merge.merger import MergeResult, group_similar_pdfs, merge_pdfs
from pdfsmith.utils.filesize import format_size


def register(app: typer.Typer) -> None:
    """Register the merge subcommand."""
    app.command(name="merge")(main)


def main(
    input: Annotated[
        list[Path],
        typer.Argument(
            help="PDF files to merge, or a single directory containing PDFs",
        ),
    ],
    output: Annotated[
        Path | None,
        typer.Option(
            "-o",
            "--output",
            help="Output filename (default: merged.pdf or <base>.merged.pdf)",
            dir_okay=False,
        ),
    ] = None,
    grouped: Annotated[
        bool,
        typer.Option(
            "-g",
            "--grouped",
            help=(
                "Merge files grouped by base name "
                "(e.g. report-1.pdf + report-2.pdf -> report.merged.pdf)"
            ),
        ),
    ] = False,
    ask: Annotated[
        bool,
        typer.Option(
            "-a",
            "--ask",
            help="Ask for confirmation before each merge operation",
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
    Merge PDF files into one or more output files.

    [bold]Examples:[/bold]

        pdfsmith merge dir/                            # Merge all PDFs in directory
        pdfsmith merge f1.pdf f2.pdf -o out.pdf        # Merge specific files
        pdfsmith merge dir/ --grouped                  # Merge by filename pattern
        pdfsmith merge dir/ --grouped --ask            # Ask before each group merge
    """
    # Determine mode: directory vs explicit files
    if len(input) == 1 and input[0].is_dir():
        _merge_directory(input[0], output, grouped, ask, quiet)
    else:
        # Explicit file list: validate all are files
        for path in input:
            if not path.exists():
                console.print(f"[red]Error:[/red] File not found: {path}")
                raise typer.Exit(1)
            if path.is_dir():
                console.print(f"[red]Error:[/red] Expected file, got directory: {path}")
                raise typer.Exit(1)
            if path.suffix.lower() != ".pdf":
                console.print(f"[red]Error:[/red] Not a PDF file: {path}")
                raise typer.Exit(1)

        if grouped:
            console.print(
                "[yellow]Warning:[/yellow] --grouped has no effect"
                " when files are specified explicitly."
            )

        out = output or (input[0].parent / "merged.pdf")
        _run_merge(list(input), out, ask, quiet)


def _merge_directory(
    directory: Path,
    output: Path | None,
    grouped: bool,
    ask: bool,
    quiet: bool,
) -> None:
    """Handle merge for a directory input."""
    if not directory.is_dir():
        console.print(f"[red]Error:[/red] Not a directory: {directory}")
        raise typer.Exit(1)

    if grouped:
        groups = group_similar_pdfs(directory)
        if not groups:
            console.print("[yellow]No groups of similar PDF files found.[/yellow]")
            raise typer.Exit(0)

        if not quiet:
            console.print(f"Found [bold]{len(groups)}[/bold] group(s) to merge.")

        failed = False
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
            disable=quiet,
        ) as progress:
            task_id = progress.add_task("Merging groups...", total=len(groups))

            for base_name, files in groups.items():
                out = output or (directory / f"{base_name}.merged.pdf")
                progress.update(task_id, description=f"[cyan]{base_name}[/cyan]")

                if ask:
                    progress.stop()
                    console.print(f"\nGroup [bold]{base_name}[/bold]: {len(files)} file(s)")
                    for f in files:
                        console.print(f"  • {f.name}")
                    if not Confirm.ask("Merge this group?"):
                        progress.start()
                        progress.advance(task_id)
                        continue
                    progress.start()

                result = merge_pdfs(files, out)
                if not quiet:
                    _show_result(result)
                if not result.success:
                    failed = True
                progress.advance(task_id)

        if failed:
            raise typer.Exit(1)
    else:
        # Merge all PDFs in the directory
        pdf_files = sorted(
            p for p in directory.iterdir()
            if p.suffix.lower() == ".pdf"
        )
        if not pdf_files:
            console.print("[yellow]No PDF files found in directory.[/yellow]")
            raise typer.Exit(0)

        out = output or (directory / "merged.pdf")
        _run_merge(pdf_files, out, ask, quiet)


def _run_merge(files: list[Path], output: Path, ask: bool, quiet: bool) -> None:
    """Run a single merge operation with optional confirmation."""
    if not quiet:
        console.print(f"Merging [bold]{len(files)}[/bold] file(s) -> [cyan]{output.name}[/cyan]")

    if ask:
        for f in files:
            console.print(f"  • {f.name}")
        if not Confirm.ask("Proceed with merge?"):
            console.print("Merge cancelled.")
            raise typer.Exit(0)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        disable=quiet,
    ) as progress:
        progress.add_task(f"Merging into {output.name}...", total=None)
        result = merge_pdfs(files, output)

    if not quiet:
        _show_result(result)

    if not result.success:
        raise typer.Exit(1)


def _show_result(result: MergeResult) -> None:
    """Display merge result."""
    if result.success:
        console.print(
            f"  [bold]{result.output_path.name}[/bold] "
            f"[green]OK[/green] "
            f"{result.page_count} page(s), {format_size(result.output_size)}"
        )
    else:
        console.print(
            f"  [bold]{result.output_path.name}[/bold] [red]ERROR[/red] {result.error_message}"
        )
