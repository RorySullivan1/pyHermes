"""
``kitchen_sink`` at the ``spacious`` density.

Airier: type grows across the whole scale, leading opens further than
type does, and the frame gives up 8px of side padding on each edge. The
gutter widens to 24px, which is what pushes a two-up split just under
300px — and is why this theme is the only one that moves
``frame.narrow_column``, down rather than up.

The fixture differs from ``kitchen_sink`` in exactly one metadata field —
``size_theme`` — and reuses its content rather than restating it, so the
two goldens diff as a pure A/B. What this one pins that no other golden
can:

* every layer of the scheme is live at once: type, spacing, the
  component sizes that do not follow the global scale, and the frame
  padding that every column width is computed from;
* ``base.html``'s ``@media`` block moves with the rest, so the email is
  not desktop-spacious and mobile-standard;
* the columns still fill the content width to the pixel at a frame whose
  padding is not 32.

It also retires an exemption: ``kitchen_sink`` holds ``size_theme`` at its
default on purpose — it is the epic's byte-identity reference — so the
distinctive value has to live here. Same shape as ``slate_theme``.
"""

from __future__ import annotations

from pathlib import Path

from svc.builder import Email
from svc.builder.enums import SizeTheme

from . import kitchen_sink


def build(template_dir: Path | None = None) -> Email:
    """Build the spacious email. Deterministic: same bytes every call."""
    return kitchen_sink.build(template_dir=template_dir, size_theme=SizeTheme.SPACIOUS)
