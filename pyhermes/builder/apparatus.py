"""
The document apparatus (#171): anchors, and the footnote and citation markers in copy.

Every anchor and number is derived in Python, once, so the markup and the
plain-text part agree about what a document calls its parts.
`.claude/rules/apparatus.md` carries why the print engine is asked to number
nothing but the page.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from .exceptions import ValidationError

#: An anchor a caller may supply: an HTML ``id`` that needs no escaping in a
#: ``#fragment`` and cannot be mistaken for a number.
ANCHOR = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")

_NOT_SLUG = re.compile(r"[^a-z0-9]+")

#: A link within the document in caller markup: ``href="#exhibit-3"``.
REFERENCE = re.compile(r"""href\s*=\s*(["'])#([^"']+)\1""", re.IGNORECASE)

#: A footnote marker in copy: ``[^1]``. A plain-text convention the builder
#: replaces, never markup, so the raw-HTML set stays closed at five.
MARKER = re.compile(r"\[\^(\d+)\]")

#: A citation key: what ``[@key]`` names and ``ref-<key>`` anchors (#310).
KEY = r"[A-Za-z0-9_][A-Za-z0-9_-]*"

#: A citation in copy: ``[@fama1993]``, or several, ``[@fama1993; @carhart1997]``.
#: The footnote marker's convention, so it too is plain text in any field.
CITATION = re.compile(rf"\[(@{KEY}(?:\s*;\s*@{KEY})*)\]")

_EITHER = re.compile(f"{MARKER.pattern}|{CITATION.pattern}")


@dataclass(frozen=True)
class Citing:
    """
    How one document spells its citations, handed to each component by the walk.

    ``labels`` maps a key to what a reader sees, "Fama and French 1993" or "3";
    the punctuation is the style's. A component rendered outside a document
    holds :data:`UNRESOLVED`, which spells each key as itself.
    """

    labels: Mapping[str, str] = field(default_factory=dict)
    open: str = "("
    close: str = ")"
    separator: str = "; "

    def cites(self, marker: str) -> list[dict[str, str]]:
        """``[{"label", "anchor"}]`` for each key a marker's inside names, in order."""
        return [
            {"label": self.labels.get(key, key), "anchor": reference_anchor(key)}
            for key in cited_keys(f"[{marker}]")
        ]

    def spell(self, marker: str) -> str:
        """A marker's inside as plain text: ``(Fama and French 1993; Carhart 1997)``."""
        labels = (cite["label"] for cite in self.cites(marker))
        return f"{self.open}{self.separator.join(labels)}{self.close}"


#: The citing a component holds until a document's walk hands it one.
UNRESOLVED = Citing()


class Note(Protocol):
    """What a marker needs from the note it calls: its copy and its number."""

    text: str
    number: int | None


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


def references(html: str) -> list[str]:
    """Every anchor ``html`` links to within the document, in order."""
    return [match.group(2) for match in REFERENCE.finditer(html)]


def note_anchor(number: int) -> str:
    """The ``id`` a note carries, at the sheet foot or in the endnotes."""
    return f"note-{number}"


def note_ref_anchor(number: int) -> str:
    """The ``id`` a note's marker carries, so a reader can be sent back to it."""
    return f"note-ref-{number}"


def reference_anchor(key: str) -> str:
    """The ``id`` a bibliography entry carries, which a citation links to."""
    return f"ref-{key}"


def cited_keys(copy: str) -> list[str]:
    """Every key ``copy`` cites, in reading order, repeats kept."""
    return [
        key.strip().lstrip("@") for match in CITATION.finditer(copy) for key in match[1].split(";")
    ]


def check_markers(copy: Sequence[str], count: int, owner: str) -> None:
    """
    Raise unless ``copy`` calls each of ``count`` notes exactly once.

    ``[^1]`` to ``[^count]``, each once, across every field that may carry a
    marker: a marker without a note and a note without a marker are both the
    renumbering mistake this exists to catch before a reader does.
    """
    seen = [int(match) for text in copy for match in MARKER.findall(text)]
    for local in seen:
        if not 1 <= local <= count:
            raise ValidationError(
                f"{owner} has a marker [^{local}] but carries {count} note(s); "
                f"markers run [^1] to [^{count}]."
            )
        if seen.count(local) > 1:
            raise ValidationError(f"{owner} calls note [^{local}] twice; a note has one marker.")
    missing = sorted(set(range(1, count + 1)) - set(seen))
    if missing:
        raise ValidationError(
            f"{owner} carries note {missing[0]} but its copy has no marker [^{missing[0]}]."
        )


def split_markers(
    copy: str, notes: Sequence[Note], citing: Citing = UNRESOLVED
) -> list[dict[str, Any]]:
    """
    ``copy`` cut at its markers, in the shape ``common/notes.html`` renders.

    Each part carries all five keys, as ``StrictUndefined`` requires: a run of
    copy has ``note`` 0 and no ``cites``; a footnote marker has ``note`` set to
    the document's number (or the local one when rendered alone); a citation
    has its ``cites`` and the style's punctuation. Copy with no marker is one
    run, which is what keeps it byte-identical.
    """
    parts: list[dict[str, Any]] = []
    cursor = 0
    for match in _EITHER.finditer(copy):
        parts.append(_run(copy[cursor : match.start()]))
        if match.group(1):
            note = notes[int(match.group(1)) - 1]
            number = note.number or int(match.group(1))
            parts.append({**_run(""), "note": number, "note_text": note.text})
        else:
            parts.append({**_run(""), "cites": citing.cites(match.group(2)), "citing": citing})
        cursor = match.end()
    parts.append(_run(copy[cursor:]))
    return [part for part in parts if part["note"] or part["cites"] or part["text"]] or [_run("")]


def _run(text: str) -> dict[str, Any]:
    """A run of copy between markers."""
    return {"text": text, "note": 0, "note_text": "", "cites": [], "citing": UNRESOLVED}


def text_markers(copy: str, notes: Sequence[Note], citing: Citing = UNRESOLVED) -> str:
    """``copy`` with each ``[^k]`` spelled ``[n]`` and each citation spelled as the style does."""
    copy = CITATION.sub(lambda match: citing.spell(match.group(1)), copy)
    return MARKER.sub(
        lambda match: f"[{notes[int(match.group(1)) - 1].number or match.group(1)}]", copy
    )


def unmarked(copy: str) -> str:
    """``copy`` with its markers removed, for a place that lists it, such as a list of exhibits."""
    return re.sub(rf"\s*{CITATION.pattern}", "", MARKER.sub("", copy))


__all__ = [
    "ANCHOR",
    "CITATION",
    "KEY",
    "MARKER",
    "UNRESOLVED",
    "Citing",
    "Note",
    "REFERENCE",
    "check_markers",
    "check_unique",
    "cited_keys",
    "note_anchor",
    "note_ref_anchor",
    "reference_anchor",
    "references",
    "slugify",
    "split_markers",
    "text_markers",
    "unmarked",
    "validate_anchor",
]
