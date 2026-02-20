"""External dependency checking utilities."""

import shutil


def check_dependencies() -> list[str]:
    """
    Check for required external dependencies.

    Returns:
        List of missing dependency names
    """
    missing = []

    # Ghostscript
    gs_names = ["gs", "gswin64c", "gswin32c"]
    if not any(shutil.which(name) for name in gs_names):
        missing.append("ghostscript")

    return missing


def get_install_instructions() -> str:
    """
    Get installation instructions for missing dependencies.

    Returns:
        Installation instructions string
    """
    return (
        "Install Ghostscript:\n"
        "  macOS:        brew install ghostscript\n"
        "  Ubuntu/Debian: apt install ghostscript\n"
        "  Fedora/RHEL:  dnf install ghostscript"
    )
