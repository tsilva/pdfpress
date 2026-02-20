# AGENTS.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**pdfsmith** is a multi-command PDF toolkit CLI. It compresses, merges, and unlocks PDF files. Uses Python with typer for CLI and rich for output formatting.

## Commands

```bash
# Install as global tool
uv tool install .

# Install for development (editable with dev dependencies)
uv pip install -e ".[dev]"

# Run the tool
pdfsmith --help
pdfsmith compress document.pdf
pdfsmith compress *.pdf -j 4 -Q screen    # parallel + quality preset
pdfsmith merge dir/                        # merge all PDFs in directory
pdfsmith merge f1.pdf f2.pdf -o out.pdf   # merge specific files
pdfsmith merge dir/ --grouped             # merge by filename pattern
pdfsmith unlock dir/                       # unlock encrypted PDFs (interactive password)
pdfsmith unlock file.pdf -p "secret"      # unlock with password flag

# Run tests
pytest

# Run linter
ruff check src/

# Run type checker
mypy src/
```

## Architecture

### CLI Structure

`cli.py` defines the root `app = typer.Typer(no_args_is_help=True)` and registers subcommands via `_register_commands()`. Each subcommand lives in `commands/`:

- `commands/compress.py` — compression subcommand
- `commands/merge.py` — merge subcommand
- `commands/unlock.py` — unlock subcommand

### Compress

**Strategy Pattern**: Each compression method in `core/strategies/` implements `CompressionStrategy`. The orchestrator (`PDFCompressor` in `core/compressor.py`) tries all strategies and keeps the smallest successful output.

Three strategies:
- `PikepdfStrategy` — Lossless optimization via pikepdf (linearization, stream compression)
- `GhostscriptStrategy` — Lossy compression via subprocess to `gs`, uses quality presets (screen/ebook/printer/prepress)
- `CombinedStrategy` — Runs Ghostscript then pikepdf

**Parallel Processing**: `ParallelCompressor` in `parallel/executor.py` uses `ProcessPoolExecutor` (not threads) because Ghostscript subprocess calls and pikepdf C++ operations benefit from true parallelism.

### Merge

Business logic in `merge/merger.py`. Key functions:
- `merge_pdfs(input_files, output_path)` → `MergeResult` — merges a list of PDFs into one using pikepdf with proper resource management
- `group_similar_pdfs(directory)` → `dict[str, list[Path]]` — groups PDFs by base name (strips trailing `-N`/`_N` suffixes)
- `get_base_name(filename)` → `str` — extracts base name using regex `r'[-_ ]+\d+$'`

### Unlock

Business logic in `unlock/unlocker.py`. Key functions:
- `unlock_pdf(input_path, output_path, password)` → `UnlockResult` — removes password protection; uses a temp file for atomic writes
- `is_encrypted(path)` → `bool` — probes encryption by attempting `pikepdf.open()`

### Package Layout

```
src/pdfsmith/
    __init__.py              # v3.0.0, exports public API
    __main__.py              # python -m pdfsmith entry point
    cli.py                   # app definition, subcommand registration

    commands/
        __init__.py
        compress.py
        merge.py
        unlock.py

    core/
        __init__.py
        compressor.py
        strategies/
            base.py
            pikepdf_strategy.py
            ghostscript_strategy.py
            combined_strategy.py

    merge/
        __init__.py
        merger.py

    unlock/
        __init__.py
        unlocker.py

    parallel/
        __init__.py
        executor.py

    utils/
        __init__.py
        filesize.py
        dependencies.py
```

## External Dependencies

Requires Ghostscript (`gs`) installed on system for the compress command. Checked at runtime via `utils/dependencies.py`.
