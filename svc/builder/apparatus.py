"""
The document apparatus (#171): the anchors a reader navigates by.

Every anchor is derived in Python, once, so the markup and the plain-text part
agree about what a document calls its parts. `.claude/rules/apparatus.md`
carries why the print engine is asked to number nothing but the page.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

from .exceptions import ValidationError

#: An anchor a caller may supply: an HTML ``id`` that needs no escaping in a
#: ``#fragment`` and cannot be mistaken for a number.
ANCHOR = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")

_NOT_SLUG = re.compile(r"[^a-z0-9]+")


def slugify(text: str, fallback: str = "section") -> str:
    """``"Factor Returns"`` -> ``"factor-returns"``; ``fallback`` when nothing survives."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = _NOT_SLUG.sub("-", ascii_text.lower()).strip("-")
    if not slug or not slug[0].isalpha():
        slug = f"{fallback}-{slug}" if slug else fallback
    return slug


def validate_anchor(value: str, name: str) -> None:
    """Raise unless ``value`` is empty or an anchor :data:`ANCHOR` accepts."""
    if value and not ANCHOR.match(value):
        raise ValidationError(
            f"'{name}' must start with a letter and hold only letters, digits, '-' "
            f"and '_', got: {value!r}"
        )


def check_unique(anchors: Iterable[tuple[str, str]]) -> None:
    """
    Raise on the first anchor two parts of one document both claim.

    ``anchors`` pairs each anchor with a description of its owner, so the error
    names both claimants and the caller can see which to rename.
    """
    seen: dict[str, str] = {}
    for anchor, owner in anchors:
        if anchor in seen:
            raise ValidationError(
                f"anchor {anchor!r} is claimed twice in one document, by {seen[anchor]} "
                f"and by {owner}. Pass anchor= to one of them."
            )
        seen[anchor] = owner


__all__ = ["ANCHOR", "check_unique", "slugify", "validate_anchor"]
