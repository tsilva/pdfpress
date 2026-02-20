"""PDF unlock business logic."""

import tempfile
from dataclasses import dataclass
from pathlib import Path

import pikepdf


@dataclass
class UnlockResult:
    """Result of a PDF unlock operation."""

    input_path: Path
    output_path: Path
    success: bool
    was_encrypted: bool
    error_message: str | None = None


def is_encrypted(path: Path) -> bool:
    """Return True if the PDF is password-protected."""
    try:
        pikepdf.open(path)
        return False
    except pikepdf.PasswordError:
        return True


def unlock_pdf(input_path: Path, output_path: Path, password: str = "") -> UnlockResult:
    """Unlock an encrypted PDF, writing the result to output_path.

    Uses a temporary file for atomicity: the output is only written if
    the unlock fully succeeds and the result can be re-opened cleanly.

    Args:
        input_path: Path to the encrypted PDF
        output_path: Destination path for the unlocked PDF
        password: Password to use for decryption (empty string tries no password)

    Returns:
        UnlockResult with details about the operation
    """
    # Check if encrypted first
    if not is_encrypted(input_path):
        return UnlockResult(
            input_path=input_path,
            output_path=output_path,
            success=True,
            was_encrypted=False,
        )

    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            suffix=".pdf",
            dir=output_path.parent,
            delete=False,
        ) as tmp:
            tmp_path = Path(tmp.name)

        with pikepdf.open(input_path, password=password) as pdf:
            pdf.save(tmp_path)

        # Verify the saved file opens without a password
        pikepdf.open(tmp_path)

        tmp_path.replace(output_path)
        tmp_path = None  # Ownership transferred

        return UnlockResult(
            input_path=input_path,
            output_path=output_path,
            success=True,
            was_encrypted=True,
        )
    except pikepdf.PasswordError:
        return UnlockResult(
            input_path=input_path,
            output_path=output_path,
            success=False,
            was_encrypted=True,
            error_message="Incorrect password",
        )
    except Exception as e:
        return UnlockResult(
            input_path=input_path,
            output_path=output_path,
            success=False,
            was_encrypted=True,
            error_message=str(e),
        )
    finally:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink()
