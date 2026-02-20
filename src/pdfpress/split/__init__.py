"""Split module for pdfpress."""

from pdfpress.split.splitter import (
    SplitIndividualResult,
    SplitResult,
    parse_page_spec,
    split_pdf,
    split_pdf_individual,
)

__all__ = [
    "SplitResult",
    "SplitIndividualResult",
    "parse_page_spec",
    "split_pdf",
    "split_pdf_individual",
]
