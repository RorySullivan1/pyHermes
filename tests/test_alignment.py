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
from svc.builder import (
    CardGroup,
    DataTable,
    EmailBuilder,
    FullWidth,
    TextBlock,
    TwoColumn,
)
from svc.builder.models import Card, TableRow

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

#: The one place the pairing runs the *other* way — an ``align`` attribute
#: with no style beside it. ``base.html``'s outer cell centres the
#: email-container table as a **block**, which a browser expresses as
#: ``-webkit-center``; the literal ``text-align:center`` is a different
#: value that centres inline content only. #125 paired them, which
#: un-centred the email in the window *and* inherited into every heading
#: and paragraph in every email — a change no golden could see, so the
#: guard that would have caught it lives in ``tests/test_screenshots.py``.
#: Exactly one such cell exists per rendered email; if a second appears,
#: decide whether it is really doing block alignment or has simply been
#: left half-done.
BLOCK_ALIGNING_CELLS_PER_EMAIL = 1

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

    def __init__(self, with_class: bool = False) -> None:
        super().__init__(convert_charrefs=True)
        self.with_class = with_class
        self.found: list[tuple[str, str | None, str | None]] = []
        self.classed: list[tuple[str, str, str | None, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        attribute = attributes.get("align")
        style = attributes.get("style") or ""
        match = _TEXT_ALIGN.search(style)
        declared = match.group(1) if match else None
        if attribute or declared:
            self.found.append((tag, attribute, declared))
            self.classed.append((tag, attributes.get("class") or "", attribute, declared))


def _aligned_elements(html: str) -> list[tuple[str, str, str | None, str | None]]:
    """
    ``(tag, class, align attribute, text-align value)`` for every element
    in a render that states an alignment. The class comes along because it
    is what tells a container's cells apart from a component's — the
    content cell is ``mobile-pad``, a KPI cell is ``kpi-cell``, and a
    section title cell carries none.
    """
    parser = _AlignmentAudit(with_class=True)
    parser.feed(html)
    return parser.classed


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
            block_aligned = 0
            for tag, attribute, declared in _audit(html):
                if tag in STYLE_ONLY_ELEMENTS:
                    continue
                if attribute and declared is None:
                    # The block-aligning cell, allowed once — see the note
                    # on BLOCK_ALIGNING_CELLS_PER_EMAIL.
                    block_aligned += 1
                    if block_aligned <= BLOCK_ALIGNING_CELLS_PER_EMAIL:
                        continue
                if attribute is None or declared is None:
                    missing = "the style" if declared is None else "the attribute"
                    lonely.setdefault(name, set()).add(f"{tag} is missing {missing}")
            if block_aligned != BLOCK_ALIGNING_CELLS_PER_EMAIL:
                lonely.setdefault(name, set()).add(
                    f"{block_aligned} attribute-only cells, expected "
                    f"{BLOCK_ALIGNING_CELLS_PER_EMAIL}"
                )
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


class TestContainerAlign:
    """
    #126: a section says where its copy sits.

    The mechanism is the CSS cascade, not a Python resolution chain —
    ``text-align`` is an inherited property, so a declaration on the
    container's cell reaches the prose inside it without anything being
    threaded down. See #124 for why that differs from the table's
    ``Column``/``Cell`` chain, which needs a *computed* value because
    ``textgen.table()`` reads it too.
    """

    META = {"email_subject": "Aligned", "firm_name": "F", "campaign_name": "c"}

    def _render(self, *sections) -> str:
        builder = EmailBuilder().metadata(dict(self.META))
        for section in sections:
            builder = builder.section(section)
        return builder.render()

    def test_unset_emits_nothing(self):
        """
        The whole byte-identity claim, at its smallest. Checked here as
        well as in the goldens because this is the assertion that says
        *why* the goldens did not move.
        """
        html = self._render(FullWidth(title="T", content=TextBlock("<p>x</p>")))
        assert 'class="mobile-pad" style=' in html, "no align attribute on an unset container"
        assert "text-align" not in html.split('class="mobile-pad"')[1].split(">")[0]

    @pytest.mark.parametrize("align", ["left", "center", "right"])
    def test_a_full_width_section_aligns_both_of_its_cells(self, align):
        """
        Both, not one. The title and the content are **sibling tables** in
        ``full-width.html``, not parent and child, so a declaration on the
        content cell alone leaves the heading where it was — which is what
        the prototype for #124 showed, and reads as a bug.
        """
        html = self._render(FullWidth(title="Heading", align=align, content=TextBlock("<p>x</p>")))
        aligned = [
            (tag, cls)
            for tag, cls, attribute, declared in _aligned_elements(html)
            if attribute == align and declared == align
        ]
        assert any(cls == "" for tag, cls in aligned), "the title cell did not take the alignment"
        assert any("mobile-pad" in cls for tag, cls in aligned), "the content cell did not"

    @pytest.mark.parametrize("align", ["left", "center", "right"])
    def test_a_split_aligns_its_title_and_every_column(self, align):
        """
        Asserts the *declaration* reaches every column cell, which is what
        this step delivers. It cannot assert the text visibly moves: a
        column cell shrink-wraps to its content rather than filling its
        column, so the alignment has no room to show whenever the copy is
        narrower than the column. That is pre-existing geometry — see the
        note on ``Container`` — and is filed as #129.
        """
        html = self._render(
            TwoColumn(
                ratio="50-50",
                title="Heading",
                align=align,
                left=TextBlock("<p>L</p>"),
                right=TextBlock("<p>R</p>"),
            )
        )
        columns = [
            cls
            for tag, cls, attribute, declared in _aligned_elements(html)
            if "mobile-pad" in cls and attribute == align and declared == align
        ]
        assert len(columns) == 2, f"expected both column cells aligned, got {len(columns)}"

    def test_a_section_without_a_title_still_aligns_its_content(self):
        html = self._render(FullWidth(align="right", content=TextBlock("<p>x</p>")))
        assert any(
            "mobile-pad" in cls and attribute == "right"
            for _, cls, attribute, _ in _aligned_elements(html)
        )

    def test_both_spellings_travel_together_here_too(self):
        """#125's invariant, applied to the declarations #126 adds."""
        html = self._render(
            FullWidth(title="T", align="center", content=TextBlock("<p>x</p>")),
            TwoColumn(ratio="30-70", align="right", title="U", left=TextBlock("<p>L</p>")),
        )
        unpaired = 0
        for tag, _, attribute, declared in _aligned_elements(html):
            if attribute and declared is None:
                unpaired += 1  # base.html's block-aligning cell
                continue
            assert attribute and declared and attribute == declared, (
                f"{tag} states its alignment only one way, or two ways that disagree"
            )
        assert unpaired == BLOCK_ALIGNING_CELLS_PER_EMAIL


class TestTheBoundaryHolds:
    """
    A container's alignment reaches its prose and stops at any component
    that declares its own. That is not arranged — it is what CSS
    inheritance does, and it works because every structural component
    already declares an alignment. These tests exist because a future
    template edit removing one of those declarations would silently let a
    section's alignment leak into a KPI strip or a data table.
    """

    META = {"email_subject": "Aligned", "firm_name": "F", "campaign_name": "c"}

    def _render(self, section) -> str:
        return EmailBuilder().metadata(dict(self.META)).section(section).render()

    def test_a_kpi_strip_keeps_its_own_centre(self):
        """
        The container is aligned **right** on purpose: a centred one could
        not tell "the KPI strip kept its own alignment" from "the KPI strip
        inherited the container's".
        """
        html = self._render(
            FullWidth(
                title="Snapshot",
                align="right",
                content=CardGroup([Card("A", "1"), Card("B", "2")], orientation="horizontal"),
            )
        )
        kpi = [
            (attribute, declared)
            for _, cls, attribute, declared in _aligned_elements(html)
            if "kpi-cell" in cls
        ]
        assert kpi, "the fixture rendered no KPI cells"
        assert all(a == "center" and d == "center" for a, d in kpi), (
            f"a right-aligned section leaked into the KPI strip: {kpi}"
        )

    def test_a_data_table_keeps_its_column_resolution(self):
        """
        Same shape for the other structural component. The table resolves
        its own alignment per column through ``kind`` (#117), which a
        section-level declaration must not override.
        """
        html = self._render(
            FullWidth(
                title="Factors",
                align="center",
                content=DataTable(
                    headers=["Factor", "1M"],
                    rows=[TableRow(["Value", "+1.8%"])],
                ),
            )
        )
        table = [
            (tag, attribute, declared)
            for tag, cls, attribute, declared in _aligned_elements(html)
            if tag in ("th", "td") and not cls
        ]
        # The label column resolves left and the numeric column right; a
        # leak would make every one of them centre.
        assert {"left", "right"} <= {a for _, a, _ in table}, (
            f"the table lost its own column alignment: {table}"
        )
