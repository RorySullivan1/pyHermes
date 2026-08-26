"""
``kitchen_sink`` at the ``compact`` density.

Denser: smaller type from the top of the scale down, tighter leading,
and — where most of the density actually comes from — less padding
everywhere. ``label`` and ``micro`` do not move: 9.5px fine print is the
readability floor, and a compact theme that made a disclaimer unreadable
would be broken rather than dense.

The fixture differs from ``kitchen_sink`` in exactly one metadata field —
``size_theme`` — and reuses its content rather than restating it, so the
two goldens diff as a pure A/B. What this one pins that no other golden
can:

* every layer of the scheme is live at once: type, spacing, the
  component sizes that do not follow the global scale, and the frame
  padding that every column width is computed from;
* ``base.html``'s ``@media`` block moves with the rest, so the email is
  not desktop-compact and mobile-standard;
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
    """Build the compact email. Deterministic: same bytes every call."""
    return kitchen_sink.build(template_dir=template_dir, size_theme=SizeTheme.COMPACT)
