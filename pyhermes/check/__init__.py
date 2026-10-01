"""
Check a document for the problems real clients have, from the installed package (#278).

The portability rules, the size report and the command that runs them on a
draft. Standard library only, so the core install stays Jinja2 alone::

    from pyhermes.check import check, errors
    findings = check(email)

    python -m pyhermes.check drafts/weekly.py:build
"""

from __future__ import annotations

from pyhermes.builder.document import Document

from .lint import (
    RULE_MEDIA,
    SOURCES,
    Finding,
    RegionSize,
    Severity,
    SizeReport,
    errors,
    format_findings,
    lint_document,
    lint_html,
    render_for_check,
    rules_for,
    size_report,
)
from .target import TargetError, as_document, load_target

__all__ = [
    "RULE_MEDIA",
    "SOURCES",
    "Finding",
    "RegionSize",
    "Severity",
    "SizeReport",
    "TargetError",
    "as_document",
    "check",
    "errors",
    "format_findings",
    "lint_document",
    "lint_html",
    "load_target",
    "render_for_check",
    "rules_for",
    "size_report",
]


def check(document: Document) -> list[Finding]:
    """Every finding for ``document`` under its own medium's rules, with the size breakdown."""
    return lint_document(document)
