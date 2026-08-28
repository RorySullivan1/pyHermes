"""
Alignment: one concept, spelled twice on purpose (#125).

pyHermes expressed "this copy sits left, centre or right" two ways — the
``align`` attribute on a cell, and ``text-align`` in an inline style — with
no rule about which. Both are correct; having two of them is what #106
learned to fix before parameterising anything, because a spelling variant
is equal to a client and different to a golden.

Since #125 every element that can carry both carries both, from one value.
These tests are what stop the drift coming back: the pairing is invisible
in every browser and every screenshot, so nothing else would notice.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

from qa.fixtures import all_fixtures

TEMPLATE_DIR = Path("svc/builder/templates")

#: The two elements where the spellings are **not** equivalent, so the
#: pairing deliberately does not apply. Each carries the style alone.
#:
#: ``caption`` is the trap: in HTML 4 its ``align`` attribute means
#: *placement* — top, bottom, left or right of the table — not the
#: alignment of the text inside it, so pairing it would move the caption
#: rather than leave the render alone. ``a`` has no ``align`` attribute in
#: any HTML specification.
STYLE_ONLY_ELEMENTS = frozenset({"caption", "a"})

_ALIGNMENTS = frozenset({"left", "center", "right"})
_TEXT_ALIGN = re.compile(r"text-align:\s*([a-z]+)")


#: ``align=`` but never ``valign=`` and never ``text-align:``. The masthead
#: pairs the two on one cell, so a looser pattern reports a cell that is
#: already correct.
_ATTRIBUTE = re.compile(r"(?<![-a-z])align\s*=")

_OPENING_TAG = re.compile(r"<([a-zA-Z][a-zA-Z0-9]*)")


def _opening_tags(source: str):
    """Every opening tag in a template, as ``(name, index)``."""
    return [(m.group(1).lower(), m.start()) for m in _OPENING_TAG.finditer(source)]


def _tag_text(source: str, start: int) -> str:
    """
    The text of the tag beginning at ``start``, to its closing bracket.

    Jinja expressions inside an attribute may themselves contain ``>``
    (``{% if x > y %}``), so the scan skips over ``{{ }}`` and ``{% %}``
    rather than taking the first bracket it meets.
    """
    i, end = start, len(source)
    while i < end:
        if source.startswith(("{{", "{%"), i):
            closer = "}}" if source[i + 1] == "{" else "%}"
            i = source.find(closer, i)
            if i == -1:
                return source[start:]
            i += 2
            continue
        if source[i] == ">":
            return source[start : i + 1]
        i += 1
    return source[start:]


class _AlignmentAudit(HTMLParser):
    """
    Every element in a rendered email that says anything about alignment.

    Parses rather than greps, for ``qa/lint.py``'s reason: the repo learned
    the expensive way that a substring search over rendered HTML matches
    inside comments and copy and answers confidently wrong.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.found: list[tuple[str, str | None, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        attribute = attributes.get("align")
        style = attributes.get("style") or ""
        match = _TEXT_ALIGN.search(style)
        declared = match.group(1) if match else None
        if attribute or declared:
            self.found.append((tag, attribute, declared))


def _audit(html: str) -> list[tuple[str, str | None, str | None]]:
    parser = _AlignmentAudit()
    parser.feed(html)
    return parser.found


def _templates() -> list[Path]:
    return sorted(TEMPLATE_DIR.rglob("*.html"))


@pytest.fixture(scope="module")
def gallery() -> dict[str, str]:
    return {name: build().render() for name, build in all_fixtures().items()}


class TestTheTwoSpellingsTravelTogether:
    def test_every_alignment_carries_both_spellings(self, gallery):
        """
        The invariant. An element that states an alignment states it twice
        — the attribute for Outlook's Word engine, the style because an
        attribute is not inherited by descendants and #124's whole
        mechanism is inheritance.
        """
        lonely: dict[str, set[str]] = {}
        for name, html in gallery.items():
            for tag, attribute, declared in _audit(html):
                if tag in STYLE_ONLY_ELEMENTS:
                    continue
                if attribute is None or declared is None:
                    missing = "the style" if declared is None else "the attribute"
                    lonely.setdefault(name, set()).add(f"{tag} is missing {missing}")
        assert not lonely, (
            f"alignment stated only one way: { {k: sorted(v) for k, v in lonely.items()} }. "
            "Every td/th/p/div that aligns must carry align= and text-align: together."
        )

    def test_the_two_spellings_never_disagree(self, gallery):
        """
        Stronger than the pairing, and the reason the pairing is worth
        having: two sources for one value is only safe while they agree.
        A future edit that changes one and not the other renders one way in
        Outlook and another everywhere else — the half-themed failure mode
        #106 found in the client hardest to check.
        """
        disagreements: dict[str, set[str]] = {}
        for name, html in gallery.items():
            for tag, attribute, declared in _audit(html):
                if attribute and declared and attribute != declared:
                    disagreements.setdefault(name, set()).add(
                        f'{tag}: align="{attribute}" but text-align:{declared}'
                    )
        assert not disagreements, (
            f"the two spellings disagree: { {k: sorted(v) for k, v in disagreements.items()} }"
        )

    def test_every_stated_alignment_is_in_the_vocabulary(self, gallery):
        """
        Three values, the set ``BoxSurface.ALIGNMENTS`` already declares.
        ``justify`` does nothing to a single short line and the rest of the
        CSS vocabulary is inline-level — see that class for the reasoning.
        """
        strays = {
            value
            for html in gallery.values()
            for _, attribute, declared in _audit(html)
            for value in (attribute, declared)
            if value is not None and value not in _ALIGNMENTS
        }
        assert not strays, f"alignment values outside the vocabulary: {sorted(strays)}"


class TestTheStyleOnlyElementsAreDeliberate:
    """
    An exception with no recorded reason is an exception someone deletes
    for looking like an oversight — the lesson the closed colour list is
    built on. So both are named, and both say why in the template.
    """

    @pytest.mark.parametrize(
        ("template", "element"),
        [("analysis/data-table.html", "caption"), ("text/contact-block.html", "a")],
    )
    def test_the_template_explains_why_it_is_unpaired(self, template, element):
        source = (TEMPLATE_DIR / template).read_text(encoding="utf-8")
        assert "#125" in source, (
            f"{template} carries the one unpaired {element} alignment in the "
            "package and must say why, or the next reader will 'fix' it."
        )

    def test_a_caption_is_never_given_the_attribute(self, gallery):
        """
        The specific regression the comment guards against. On a caption
        the attribute means placement, so adding it would move the element
        — an edit that looks like tidying and is not a no-op.
        """
        for name, html in gallery.items():
            for tag, attribute, _ in _audit(html):
                assert not (tag == "caption" and attribute), (
                    f"{name}: a caption carries align={attribute!r}, which in HTML 4 "
                    "means placement, not text alignment"
                )


class TestNoTemplateStatesAnAlignmentAlone:
    """
    The template-source half. The rendered checks above can only see what
    the gallery happens to exercise; this one reads every template, so a
    branch no fixture reaches is still covered.
    """

    def test_every_text_align_has_an_attribute_beside_it(self):
        """
        Read per *element*, not per line: several style attributes in this
        package wrap across three lines, so a line-oriented check reports
        the continuation and misses the opening tag. That mistake is the
        reason this docstring exists — it cost a false failure on
        ``footer.html`` while this test was being written.
        """
        offenders = []
        for path in _templates():
            source = path.read_text(encoding="utf-8")
            for tag, start in _opening_tags(source):
                if tag in STYLE_ONLY_ELEMENTS or "text-align" not in _tag_text(source, start):
                    continue
                if not _ATTRIBUTE.search(_tag_text(source, start)):
                    line = source[:start].count("\n") + 1
                    offenders.append(f"{path.relative_to(TEMPLATE_DIR)}:{line} ({tag})")
        assert not offenders, (
            f"text-align with no align attribute beside it: {offenders}. "
            "See #125 — both spellings, from one value."
        )
