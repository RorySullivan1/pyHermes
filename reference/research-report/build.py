"""The research-report reference report: a stand-in until a real long-form report replaces it."""

from __future__ import annotations

from pathlib import Path

from qa.reference import example

#: The source that builds the stand-in today.
SOURCE = Path("examples/quarterly-review/quarterly-review.py")
_EXAMPLE = example("quarterly-review")


def build():
    """Build the research report, through the worked example it stands in for."""
    return _EXAMPLE.build()
