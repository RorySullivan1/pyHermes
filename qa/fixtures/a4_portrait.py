"""
The shared paged content on A4 portrait — the first non-email golden.

What it pins is the whole paged path at once: the ``document/`` overlay
resolving a skeleton of its own, the medium's page reaching ``@page`` and the
body table, and every shared component rendering inside a 794px frame it was
never tuned for.
"""

from __future__ import annotations

from pathlib import Path

from svc.builder.document import Document
from svc.document import PAGED_MEDIUM

from . import _paged


def build(template_dir: Path | None = None) -> Document:
    """Build the A4 portrait document. Deterministic: same bytes every call."""
    return _paged.build_on(PAGED_MEDIUM, template_dir)
