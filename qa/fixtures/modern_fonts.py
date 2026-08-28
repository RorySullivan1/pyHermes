"""
``kitchen_sink`` at the ``modern`` font theme — the axis's A/B.

The third design-system axis gets the proof its two siblings already have: a
preset nobody can compare against is a refactor, not a seam. This fixture
differs from ``kitchen_sink`` in exactly one metadata field — ``font_theme``
— and reuses its content rather than restating it, exactly as
``compact_size`` and ``slate_theme`` do, so the two goldens diff as a pure
A/B where **every difference is a typeface**.

What this one pins that no other golden can:

* **the role vocabulary was cut in the right place.** ``heading`` and
  ``body`` share a stack in the default, so nothing until now could show
  they are separate roles. Here the masthead title, the ``<h2>`` section
  titles, the item titles, the list ordinals, the contact heading and the
  author name all move to the sans while the prose, the standfirsts and the
  KPI values stay serif — which is only expressible because the roles are
  named by the job a face does rather than by which face does it;
* **the `[if mso]` fallback moves with everything else**, so the email is
  not custom-faced in Gmail and Georgia in Outlook — the half-themed
  failure the axis's standing rule exists to prevent, in the client hardest
  to check;
* **``numeric`` holds**, so the data table's figure columns still align.

Sizes do not move: a font swap changes no px, which is the epic's
orthogonality principle. Rendered line *lengths* do move with the metrics,
and that is what the screenshots judge rather than the golden.
"""

from __future__ import annotations

from pathlib import Path

from svc.builder import Email

from . import kitchen_sink


def build(template_dir: Path | None = None) -> Email:
    """Build the modern-fonts email. Deterministic: same bytes every call."""
    return kitchen_sink.build(template_dir=template_dir, font_theme="modern")
