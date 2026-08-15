"""Security-boundary and end-to-end regression tests for locked dependencies."""

from importlib.metadata import version
from io import BytesIO
from pathlib import Path

import pikepdf
import pytest
from lxml import etree
from PIL import Image, UnidentifiedImageError

from pdfpress.core.strategies.pikepdf_strategy import PikepdfStrategy
from pdfpress.merge.merger import merge_pdfs
from pdfpress.split.splitter import parse_page_spec, split_pdf
from pdfpress.unlock.unlocker import unlock_pdf


def _version_tuple(distribution: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version(distribution).split(".") if part.isdigit())


def _write_pdf(path: Path, pages: int = 1) -> None:
    with pikepdf.new() as pdf:
        for _ in range(pages):
            pdf.add_blank_page(page_size=(72, 72))
        pdf.save(path)


def test_locked_packages_are_outside_vulnerable_ranges() -> None:
    assert _version_tuple("Pillow") >= (12, 3, 0)
    assert _version_tuple("lxml") >= (6, 1, 0)
    assert _version_tuple("pytest") >= (9, 0, 3)
    assert _version_tuple("Pygments") >= (2, 20, 0)


def test_pillow_accepts_valid_image_and_rejects_malformed_input() -> None:
    buffer = BytesIO()
    Image.new("RGB", (2, 2), "blue").save(buffer, format="PNG")
    buffer.seek(0)

    with Image.open(buffer) as image:
        image.load()
        assert image.size == (2, 2)

    with pytest.raises(UnidentifiedImageError):
        Image.open(BytesIO(b"not-an-image")).load()


def test_lxml_parser_blocks_external_entity_and_parses_legitimate_xml(tmp_path: Path) -> None:
    secret = tmp_path / "secret.txt"
    secret.write_text("must-not-be-read", encoding="utf-8")
    payload = (
        '<!DOCTYPE root [<!ENTITY xxe SYSTEM "'
        + secret.as_uri()
        + '">]><root>&xxe;</root>'
    ).encode()
    parser = etree.XMLParser(resolve_entities=False, no_network=True)

    root = etree.fromstring(payload, parser=parser)
    assert root.text is None
    assert b"must-not-be-read" not in etree.tostring(root)

    valid = etree.fromstring(b"<root><value>safe</value></root>", parser=parser)
    assert valid.findtext("value") == "safe"


def test_pdf_merge_split_and_lossless_compression(tmp_path: Path) -> None:
    first = tmp_path / "first.pdf"
    second = tmp_path / "second.pdf"
    merged = tmp_path / "merged.pdf"
    split = tmp_path / "split.pdf"
    compressed = tmp_path / "compressed.pdf"
    _write_pdf(first)
    _write_pdf(second, pages=2)

    merge_result = merge_pdfs([first, second], merged)
    assert merge_result.success
    assert merge_result.page_count == 3
    assert parse_page_spec("1,3", total_pages=3) == [0, 2]

    split_result = split_pdf(merged, split, [0, 2])
    assert split_result.success
    with pikepdf.open(split) as pdf:
        assert len(pdf.pages) == 2

    compression_result = PikepdfStrategy().compress(merged, compressed)
    assert compression_result.success
    with pikepdf.open(compressed) as pdf:
        assert len(pdf.pages) == 3


def test_unlock_rejects_wrong_password_and_preserves_valid_pdf(tmp_path: Path) -> None:
    encrypted = tmp_path / "encrypted.pdf"
    unlocked = tmp_path / "unlocked.pdf"
    with pikepdf.new() as pdf:
        pdf.add_blank_page(page_size=(72, 72))
        pdf.save(
            encrypted,
            encryption=pikepdf.Encryption(owner="owner", user="correct-password", R=6),
        )

    rejected = unlock_pdf(encrypted, unlocked, password="wrong-password")
    assert not rejected.success
    assert rejected.error_message == "Incorrect password"
    assert not unlocked.exists()

    accepted = unlock_pdf(encrypted, unlocked, password="correct-password")
    assert accepted.success
    assert accepted.was_encrypted
    with pikepdf.open(unlocked) as pdf:
        assert len(pdf.pages) == 1
