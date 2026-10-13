"""
The long-form apparatus a research note carries (#220): its sources, and its terms.

A :class:`Reference` is a record cited by key; a :class:`Bibliography` lists the
records in a style and tells the document how a ``[@key]`` reads. Every number
and label is the document's walk's, so the markup and the text part agree.
`.claude/rules/apparatus.md` carries the decisions.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from pyhermes.config import get_config

from .apparatus import KEY, Citing, reference_anchor, slugify
from .components import Component
from .exceptions import ValidationError
from .models import _validate_url
from .sizing import Spacing
from .textgen import hang, join_blocks, underline, wrap

#: The two citation styles a bibliography sets, each a curated house form.
STYLES = ("author-year", "numeric")

_KEY = re.compile(rf"^{KEY}$")
_DOI = re.compile(r"^10\.\S+/\S+$")


@dataclass(frozen=True)
class Reference:
    """
    One source, cited by ``key`` from anywhere in a document as ``[@key]``.

    ``authors`` are written "Surname, Given", or as a single name for an
    institution: a citation prints the part before the comma. ``year`` is
    printed as given, so "2024" and "forthcoming" both work. A ``doi`` is
    linked through doi.org and wins over ``url`` when both are set.

    Raises:
        ValidationError: On a key that is not a citation key, no authors, a
            blank year or title, an unsafe ``url`` or a malformed ``doi``.
    """

    key: str
    authors: Sequence[str]
    year: int | str
    title: str
    venue: str | None = None
    url: str | None = None
    doi: str | None = None

    def __post_init__(self) -> None:
        if not _KEY.match(self.key or ""):
            raise ValidationError(
                f"reference.key must start with a letter, digit or '_' and hold only those "
                f"and '-', got: {self.key!r}"
            )
        if isinstance(self.authors, str) or not self.authors:
            raise ValidationError(
                f"reference {self.key!r}: authors is a sequence of names, got {self.authors!r}"
            )
        object.__setattr__(self, "authors", tuple(self.authors))
        for name, value in (("year", str(self.year)), ("title", self.title), *self._names()):
            if not value.strip():
                raise ValidationError(f"reference {self.key!r}: {name} must not be blank")
        _validate_url(self.url or "", f"reference {self.key!r}.url")
        if self.doi is not None and not _DOI.match(self.doi):
            raise ValidationError(
                f"reference {self.key!r}: a doi reads '10.prefix/suffix', got {self.doi!r}"
            )

    def _names(self) -> list[tuple[str, str]]:
        """Each author, named for an error."""
        return [(f"authors[{i}]", str(author)) for i, author in enumerate(self.authors)]

    def cited_authors(self) -> str:
        """The authors as a citation names them: surnames, shortened past the configured limit."""
        surnames = [author.split(",")[0].strip() for author in self.authors]
        if len(surnames) > get_config().citation_authors:
            return f"{surnames[0]} et al."
        return _joined(surnames)

    def listed_authors(self) -> str:
        """The authors as an entry lists them: the first inverted, the rest in reading order."""
        names = [self.authors[0], *(_natural(author) for author in self.authors[1:])]
        if len(names) == 1:
            return names[0]
        tail = f"{', ' if len(names) > 2 or ',' in names[0] else ' '}and {names[-1]}"
        return ", ".join(names[:-1]) + tail

    def link(self) -> str:
        """Where the entry links: the DOI's resolver, the URL, or nothing."""
        return f"https://doi.org/{self.doi}" if self.doi else (self.url or "")


def _joined(names: Sequence[str]) -> str:
    """``A``, ``A and B``, ``A, B and C``."""
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"


def _natural(author: str) -> str:
    """``"French, Kenneth R."`` -> ``"Kenneth R. French"``; a single name as it is."""
    surname, _, given = author.partition(",")
    return f"{given.strip()} {surname.strip()}" if given.strip() else author.strip()


def _stop(text: str) -> str:
    """The full stop after ``text``, unless it already ends in one of its own."""
    return "" if text.rstrip().endswith((".", "?", "!")) else "."


class Bibliography(Component):
    """
    The sources a document cites, listed in a curated style (#310).

    **Two styles, each a house form rather than a CSL engine.**
    ``"author-year"`` cites "(Fama and French 1993)" and sorts by first author,
    then year, lettering a collision "1993a", "1993b". ``"numeric"`` cites
    "[3]" and numbers in order of first citation, a reference cited again
    reusing its number; one never cited is listed after, in the order given.

    **The document resolves it.** The walk reads every ``[@key]`` in reading
    order, hands this list the order, and hands every component the labels it
    returns, so a citation and its entry cannot disagree. A document carries
    at most one, and ``validate()`` refuses a key it does not list.

    Each entry carries the ``id`` ``ref-<key>``, which each citation links to.
    It fixes its own left alignment, as the contents list does: an entry's
    hanging indent is its shape.

    Args:
        references: The sources, each a :class:`Reference` with a unique key.
        style:      ``"author-year"`` (the default) or ``"numeric"``.
        title:      An optional heading above the list, such as "References".
    """

    template_path = "text/bibliography.html"

    SPACING_TOKENS = ("caption_gap", "gutter")

    def __init__(
        self,
        references: Sequence[Reference],
        style: str = "author-year",
        title: str | None = None,
        spacing: Spacing | Mapping[str, int | float] | None = None,
    ):
        self.spacing = self._coerce_spacing(spacing)
        if style not in STYLES:
            raise ValidationError(
                f"Bibliography(style=...) takes one of {list(STYLES)}, got {style!r}"
            )
        references = list(references)
        if not references:
            raise ValidationError("a Bibliography needs at least one Reference.")
        seen: set[str] = set()
        for reference in references:
            if not isinstance(reference, Reference):
                raise ValidationError(
                    f"a Bibliography holds Reference records, got {type(reference).__name__}"
                )
            if reference.key in seen:
                raise ValidationError(
                    f"the key {reference.key!r} is listed twice in one Bibliography"
                )
            seen.add(reference.key)
        self.references = references
        self.style = style
        self.title = title
        #: Keys in order of first citation, handed down by the document's walk.
        self.cited: list[str] = []

    @property
    def keys(self) -> set[str]:
        """Every key this list can resolve."""
        return {reference.key for reference in self.references}

    def resolve(self, cited: Sequence[str]) -> Citing:
        """Take the document's citations in reading order; return how each key reads."""
        self.cited = list(dict.fromkeys(key for key in cited if key in self.keys))
        labels = {reference.key: label for label, _, reference in self._ordered()}
        if self.style == "numeric":
            return Citing(labels, "[", "]", ", ")
        return Citing(labels)

    def _ordered(self) -> list[tuple[str, str, Reference]]:
        """``(citation label, printed year, reference)`` in the order this list prints them."""
        if self.style == "numeric":
            by_key = {reference.key: reference for reference in self.references}
            first = [by_key[key] for key in self.cited]
            rest = [reference for reference in self.references if reference.key not in self.cited]
            return [(str(n), str(r.year), r) for n, r in enumerate(first + rest, start=1)]
        ordered = sorted(
            self.references,
            key=lambda r: (r.cited_authors().lower(), str(r.year), r.title.lower()),
        )
        shared = [(r.cited_authors(), str(r.year)) for r in ordered]
        years = [f"{r.year}{_suffix(shared, i)}" for i, r in enumerate(ordered)]
        return [
            (f"{r.cited_authors()} {year}", year, r) for r, year in zip(ordered, years, strict=True)
        ]

    def entries(self) -> list[dict[str, str]]:
        """Each entry's parts, punctuated, in print order: the one source both projections read."""
        entries = []
        for label, year, reference in self._ordered():
            authors = reference.listed_authors()
            venue = reference.venue or ""
            entries.append(
                {
                    "anchor": reference_anchor(reference.key),
                    "label": f"[{label}]" if self.style == "numeric" else "",
                    "authors": f"{authors}{_stop(authors)}",
                    "year": f"{year}.",
                    "title": f"{reference.title}{_stop(reference.title)}",
                    "venue": f"{venue}{_stop(venue)}" if venue else "",
                    "link": reference.link(),
                }
            )
        return entries

    def anchors(self) -> list[tuple[str, str]]:
        return [(reference_anchor(r.key), f"the reference {r.key!r}") for r in self.references]

    def text(self) -> str:
        """One entry per paragraph, its continuation lines hung under its first."""
        entries = self.entries()
        width = max(len(entry["label"]) for entry in entries)
        lines = []
        for entry in entries:
            parts = ("authors", "year", "title", "venue", "link")
            body = " ".join(entry[part] for part in parts if entry[part])
            lead = f"{entry['label'].ljust(width)} " if width else ""
            lines.append(hang(lead + body, " " * (len(lead) or 4)))
        return self._with_subtitle(underline(self.title or ""), "\n".join(lines))

    def context(self) -> dict[str, Any]:
        return {"bibliography_title": self.title or "", "entries": self.entries()}


@dataclass(frozen=True)
class Term:
    """
    A term and what it means, both plain text and escaped like any.

    Its anchor is ``term-<slug>``, so the body links a mention with an
    ordinary ``a href="#term-duration"``, which the document's dangling
    reference check already validates.

    Raises:
        ValidationError: On a blank term or definition.
    """

    term: str
    definition: str

    def __post_init__(self) -> None:
        for name in ("term", "definition"):
            if not str(getattr(self, name) or "").strip():
                raise ValidationError(f"term.{name} must not be blank, got {getattr(self, name)!r}")

    def anchor(self) -> str:
        """The ``id`` this term's entry carries."""
        return f"term-{slugify(self.term, 'term').removeprefix('term-')}"


class Glossary(Component):
    """
    A document's terms, defined once and laid out for reading (#311).

    A two-column layout table, the term in the label face beside its
    definition, which stacks on a phone through the skeleton's existing
    ``stack-column`` rule, so the email's ``@media`` block does not change.
    A layout table rather than a data table: there is nothing to head, and a
    paged data table must carry a ``thead`` a glossary has no use for.

    Each entry is anchored ``term-<slug>``, and those anchors join the
    document's, so a link to one validates and a link to a term it does not
    define is refused, named. Two terms with one anchor are refused here.

    Args:
        terms: The :class:`Term` entries.
        title: An optional heading above the list, such as "Glossary".
        sort:  List alphabetically (the default), or in the order given.
    """

    template_path = "text/glossary.html"

    SPACING_TOKENS = ("caption_gap", "gutter")

    def __init__(
        self,
        terms: Sequence[Term],
        title: str | None = None,
        sort: bool = True,
        spacing: Spacing | Mapping[str, int | float] | None = None,
    ):
        self.spacing = self._coerce_spacing(spacing)
        terms = list(terms)
        if not terms:
            raise ValidationError("a Glossary needs at least one Term.")
        seen: dict[str, str] = {}
        for term in terms:
            if not isinstance(term, Term):
                raise ValidationError(f"a Glossary holds Term entries, got {type(term).__name__}")
            if term.anchor() in seen:
                raise ValidationError(
                    f"the terms {seen[term.anchor()]!r} and {term.term!r} share the anchor "
                    f"#{term.anchor()}; a glossary defines a term once."
                )
            seen[term.anchor()] = term.term
        self.terms = sorted(terms, key=lambda t: t.term.casefold()) if sort else terms
        self.title = title
        self.sort = sort

    def anchors(self) -> list[tuple[str, str]]:
        return [(term.anchor(), f"the glossary's term {term.term!r}") for term in self.terms]

    def text(self) -> str:
        """``Term: definition``, wrapped, one per paragraph."""
        return self._with_subtitle(
            underline(self.title or ""),
            join_blocks(*(wrap(f"{term.term}: {term.definition}") for term in self.terms)),
        )

    def context(self) -> dict[str, Any]:
        return {
            "glossary_title": self.title or "",
            "terms": [
                {"term": t.term, "definition": t.definition, "anchor": t.anchor()}
                for t in self.terms
            ],
        }


def _suffix(labels: Sequence[tuple[str, str]], index: int) -> str:
    """``a``, ``b`` for an author-year pair another entry shares, else nothing."""
    same = [i for i, label in enumerate(labels) if label == labels[index]]
    return "abcdefghijklmnopqrstuvwxyz"[same.index(index)] if len(same) > 1 else ""


__all__ = ["STYLES", "Bibliography", "Glossary", "Reference", "Term"]
