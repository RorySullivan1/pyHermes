"""
The same paged content on a 16:9 slide — landscape, and still one medium.

Its value is the diff against ``a4_portrait``: identical copy, one
``PageFormat`` apart. A slide is a *page*, not a medium of its own, and two
goldens that differ only in their dimensions are what makes that claim
checkable rather than asserted.
"""

from __future__ import annotations

from pathlib import Path

from pyhermes.builder.document import Document
from pyhermes.builder.sizing import SLIDE_16_9
from pyhermes.document import paged_medium

from . import _paged


def build(template_dir: Path | None = None) -> Document:
    """Build the 16:9 slide document. Deterministic: same bytes every call."""
    return _paged.build_on(paged_medium(SLIDE_16_9), template_dir)
