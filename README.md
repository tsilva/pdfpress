<div align="center">
  <img src="logo.png" alt="pdfpress" width="512"/>

  # pdfpress

  [![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)](https://www.python.org/)
  [![PyPI](https://img.shields.io/pypi/v/pdfpress?logo=pypi&logoColor=white)](https://pypi.org/project/pdfpress/)
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
  [![Ghostscript](https://img.shields.io/badge/Requires-Ghostscript-000000)](https://www.ghostscript.com/)

  **🔧 Compress, merge, split, and unlock PDF files with one tool ⚡**

  [Installation](#installation) · [Usage](#usage) · [How It Works](#how-it-works)
</div>

## Overview

pdfpress is a multi-command PDF toolkit that handles your most common PDF chores from the command line — compress bloated files, merge multiple PDFs, extract specific pages, and strip password protection.

## Features

- **Smart compression** - Tries 3 strategies (pikepdf, Ghostscript, combined) and picks the smallest result
- **Batch processing** - Compress multiple files with wildcards (`*.pdf`)
- **Parallel processing** - Compress multiple files concurrently with `-j`
- **Quality presets** - Choose between screen, ebook, printer, or prepress quality
- **Merge PDFs** - Combine multiple files or entire directories into one
- **Grouped merge** - Automatically merge files by name pattern (e.g. `report-1.pdf` + `report-2.pdf` → `report.merged.pdf`)
- **Split/extract pages** - Extract specific pages, ranges, odd/even, or each page individually
- **Unlock PDFs** - Remove password protection from encrypted files
- **Flexible output** - Custom filenames, directories, or in-place replacement
- **Scriptable** - Quiet mode for automation and pipelines

## Installation

### Prerequisites

Install Ghostscript (required for the compress command):

```bash
# macOS
brew install ghostscript

# Ubuntu/Debian
apt install ghostscript

# Fedora/RHEL
dnf install ghostscript
```

### Install from PyPI (recommended)

```bash
pip install pdfpress
```

Or with uv:

```bash
uv tool install pdfpress
```

### Install from source

```bash
pip install git+https://github.com/tsilva/pdfpress.git
```

## Usage

### Compress

```bash
# Compress all PDFs in current directory
pdfpress compress

# Compress a single file (creates document.compressed.pdf)
pdfpress compress document.pdf

# Specify output filename
pdfpress compress document.pdf -o small.pdf

# Batch compress to a directory
pdfpress compress *.pdf -d compressed/

# Replace original files (use with caution)
pdfpress compress -i large.pdf

# Use 4 parallel workers for batch compression
pdfpress compress *.pdf -j 4

# Use screen quality (72 DPI) for smallest size
pdfpress compress document.pdf -Q screen

# Preview compression without saving
pdfpress compress --dry-run
```

#### Compress Options

| Option | Description |
|--------|-------------|
| `-o, --output <file>` | Output filename (single file mode only) |
| `-d, --output-dir <dir>` | Output directory for compressed files |
| `-i, --in-place` | Replace original files |
| `-Q, --quality <preset>` | Quality preset: screen, ebook, printer, prepress |
| `-j, --jobs <n>` | Number of parallel jobs (0 = auto) |
| `-n, --dry-run` | Simulate compression without saving |
| `-q, --quiet` | Suppress output except errors |

#### Quality Presets

| Preset | DPI | Use Case |
|--------|-----|----------|
| `screen` | 72 | Web viewing, smallest size |
| `ebook` | 150 | E-readers and tablets (default) |
| `printer` | 300 | Office printing |
| `prepress` | 300 | Professional printing |

### Merge

```bash
# Merge all PDFs in a directory
pdfpress merge dir/

# Merge specific files into one output
pdfpress merge f1.pdf f2.pdf -o out.pdf

# Merge by filename pattern (report-1.pdf + report-2.pdf → report.merged.pdf)
pdfpress merge dir/ --grouped

# Ask before each group merge
pdfpress merge dir/ --grouped --ask
```

#### Merge Options

| Option | Description |
|--------|-------------|
| `-o, --output <file>` | Output filename |
| `-g, --grouped` | Merge by base name pattern |
| `-a, --ask` | Confirm before each merge |
| `-q, --quiet` | Suppress output except errors |

### Split

```bash
# Extract specific pages
pdfpress split document.pdf -p "1,3,5"

# Extract a page range
pdfpress split document.pdf -p "1-5"

# Extract odd or even pages
pdfpress split document.pdf -p "odd"
pdfpress split document.pdf -p "even"

# Custom output filename
pdfpress split document.pdf -p "1-5" -o out.pdf

# Export each page to a separate file
pdfpress split document.pdf -p "all" -i

# Individual files in a specific directory
pdfpress split document.pdf -p "all" -i -d out/
```

#### Split Options

| Option | Description |
|--------|-------------|
| `-p, --pages <spec>` | Pages to extract: `1,3,5-10`, `all`, `odd`, `even` |
| `-o, --output <file>` | Output filename |
| `-d, --output-dir <dir>` | Output directory |
| `-i, --individual` | Export each page to a separate file |
| `-q, --quiet` | Suppress output except errors |

### Unlock

```bash
# Unlock all PDFs in a directory (prompts for password)
pdfpress unlock dir/

# Unlock with password flag
pdfpress unlock file.pdf -p "secret"

# Custom output filename
pdfpress unlock file.pdf -o unlocked.pdf

# Unlock to a specific directory
pdfpress unlock dir/ -d unlocked/
```

#### Unlock Options

| Option | Description |
|--------|-------------|
| `-o, --output <file>` | Output filename (single file mode only) |
| `-d, --output-dir <dir>` | Output directory for unlocked files |
| `-p, --password <pass>` | Password (prompted interactively if not provided) |
| `-q, --quiet` | Suppress output except errors |

## How It Works

### Compress

The compress command tries three strategies and keeps the smallest result:

| Strategy | Method | Best For |
|----------|--------|----------|
| **pikepdf** | Linearizes and optimizes PDF object streams | Already-optimized PDFs |
| **Ghostscript** | Aggressive image downsampling | Image-heavy PDFs |
| **Combined** | Ghostscript followed by pikepdf optimization | Mixed content |

If none of the strategies produce a smaller file, the original is preserved.

### Merge

Groups files alphabetically when merging a directory. With `--grouped`, strips trailing `-N`/`_N` number suffixes to detect related files and merge each group separately.

### Split

Supports flexible page selection: individual pages (`1,3,5`), ranges (`1-5`), keywords (`all`, `odd`, `even`), and mixed combinations (`1,3,5-10,15`).

### Unlock

Uses pikepdf to open and re-save the PDF without password protection. Skips files that are not encrypted. Writes to a temp file atomically to avoid corrupting the original on failure.

## Example Results

| PDF Type | Original | Compressed | Reduction |
|----------|----------|------------|-----------|
| Scanned document | 434 KB | 38 KB | 91% |
| Digital form | 164 KB | 96 KB | 41% |
| Invoice | 32 KB | 21 KB | 33% |

Results vary depending on PDF content. Image-heavy PDFs typically see the largest reductions.

## Contributing

Found a bug or have a suggestion? Please open an issue:

[GitHub Issues](https://github.com/tsilva/pdfpress/issues)

## License

MIT License - see [LICENSE](LICENSE) for details.

## Author

**Tiago Silva** - [@tsilva](https://github.com/tsilva)
