"""File size formatting utilities."""


def format_size(bytes_count: float) -> str:
    """
    Format bytes to human-readable string.

    Args:
        bytes_count: Number of bytes

    Returns:
        Human-readable string (e.g., "1.5MB")
    """
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_count < 1024:
            if unit == "B":
                return f"{bytes_count}{unit}"
            return f"{bytes_count:.1f}{unit}"
        bytes_count /= 1024
    return f"{bytes_count:.1f}TB"
