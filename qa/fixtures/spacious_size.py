"""
``kitchen_sink`` at the ``spacious`` density — the size axis's other A/B.

The pair with ``compact_size`` brackets ``standard`` from both sides, so a
token that moved in one direction only is visible. It is also the widest
fixture at 375px, which is what makes it the mobile-overflow canary (#133).
"""

from __future__ import annotations

from pathlib import Path

from svc.builder import Email
from svc.builder.enums import SizeTheme

from . import kitchen_sink


def build(template_dir: Path | None = None) -> Email:
    """Build the spacious email. Deterministic: same bytes every call."""
    return kitchen_sink.build(template_dir=template_dir, size_theme=SizeTheme.SPACIOUS)
