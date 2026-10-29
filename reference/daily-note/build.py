"""The daily-note reference report: a stand-in until the owner's real note replaces it."""

from __future__ import annotations

from pathlib import Path

from qa.reference import example

#: The source that builds the stand-in today.
SOURCE = Path("examples/daily-investment-note/daily-investment-note.py")


def build():
    """Build the daily note, through the worked example it stands in for."""
    return example("daily-investment-note").build()
