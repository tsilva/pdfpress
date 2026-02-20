"""Command-line interface for pdfsmith."""

from typing import Annotated

import typer
from rich.console import Console

from pdfsmith import __version__

app = typer.Typer(
    name="pdfsmith",
    help="PDF toolkit: compress, merge, split, and unlock PDF files.",
    add_completion=False,
    rich_markup_mode="rich",
    no_args_is_help=True,
)
console = Console()


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        console.print(f"pdfsmith v{__version__}")
        raise typer.Exit()


@app.callback()
def _callback(
    version: Annotated[
        bool | None,
        typer.Option(
            "-v",
            "--version",
            help="Show version and exit",
            callback=version_callback,
            is_eager=True,
        ),
    ] = None,
) -> None:
    pass


def _register_commands() -> None:
    from pdfsmith.commands import compress, merge, split, unlock

    compress.register(app)
    merge.register(app)
    split.register(app)
    unlock.register(app)


_register_commands()


if __name__ == "__main__":
    app()
