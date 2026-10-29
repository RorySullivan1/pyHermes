"""The product-brochure reference report: a stand-in until the owner's real piece replaces it."""

from __future__ import annotations

from pathlib import Path

from qa.fixtures import tri_fold_letter

#: The source that builds the stand-in today.
SOURCE = Path("qa/fixtures/tri_fold_letter.py")


def build():
    """Build the product brochure, through the gallery fixture it stands in for."""
    return tri_fold_letter.build()
