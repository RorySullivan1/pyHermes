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

import dataclasses
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import NamedTuple

import pytest

from pyhermes.builder import (
    AuthorBlock,
    Button,
    CardGroup,
    ChartBlock,
    Component,
    ContactBlock,
    Contents,
    DataTable,
    EmailBuilder,
    FullWidth,
    NumberedList,
    PullQuote,
    TextBlock,
    TwoColumn,
    ValidationError,
)
from pyhermes.builder.components import CopyAlignment
from pyhermes.builder.models import Card, NumberedItem, TableRow
from qa.fixtures import all_fixtures

TEMPLATE_DIR = Path("pyhermes/builder/templates")

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

#: Alignments a **template** fixes, which no caller can reach and which are
#: therefore not part of #124's three-value axis.
#:
#: ``justify`` sets the per-exhibit disclosure (#154), and the non-goal it
#: looks like it breaks does not apply: ``TextAlign`` omits justify because
#: it "does nothing to a single short line", and a disclosure is the one
#: place in the package that renders multi-sentence prose narrow enough for
#: it to do something. The caller-facing vocabulary stays three values, and
#: ``test_the_caller_facing_vocabulary_still_excludes_justify`` is what keeps
#: this from being read as permission to widen it.
_TEMPLATE_FIXED_ALIGNMENTS = frozenset({"justify"})
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


class Aligned(NamedTuple):
    """One element that states an alignment, and how it states it."""

    tag: str
    css_class: str
    attribute: str | None
    declared: str | None
    style: str


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
        self.classed: list[Aligned] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        attribute = attributes.get("align")
        style = attributes.get("style") or ""
        match = _TEXT_ALIGN.search(style)
        declared = match.group(1) if match else None
        if attribute or declared:
            self.found.append((tag, attribute, declared))
            self.classed.append(
                Aligned(tag, attributes.get("class") or "", attribute, declared, style)
            )


def _aligned_elements(html: str) -> list[Aligned]:
    """
    Every element in a render that states an alignment.

    The class and the style come along because they are what tell one
    aligned element from another: a container's content cell is
    ``mobile-pad``, a KPI cell is ``kpi-cell``, a section title cell
    carries neither, and a component's subtitle is the italic paragraph.
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
            if value is not None
            and value not in _ALIGNMENTS
            and value not in _TEMPLATE_FIXED_ALIGNMENTS
        }
        assert not strays, f"alignment values outside the vocabulary: {sorted(strays)}"

    def test_the_caller_facing_vocabulary_still_excludes_justify(self):
        """
        The other half of ``_TEMPLATE_FIXED_ALIGNMENTS``, and the reason
        widening the audit above is not a hole. A template may fix an
        alignment the axis does not offer; a **caller** may not reach one.
        Without this, admitting ``justify`` to the audit would quietly become
        permission to add it to the enum.
        """
        from pyhermes.builder.enums import TextAlign

        assert "justify" not in {member.value for member in TextAlign}
        assert "justify" not in _ALIGNMENTS


class TestTheStyleOnlyElementsAreDeliberate:
    """
    An exception with no recorded reason is an exception someone deletes
    for looking like an oversight — the lesson the closed colour list is
    built on. So both are named, and both say why in the template.
    """

    @pytest.mark.parametrize(
        ("template", "element"),
        [("analysis/data-table.html", "caption"), ("common/cta.html", "a")],
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
            element
            for element in _aligned_elements(html)
            if element.attribute == align and element.declared == align
        ]
        assert any(e.css_class == "" for e in aligned), "the title cell did not take the alignment"
        assert any("mobile-pad" in e.css_class for e in aligned), "the content cell did not"

    @pytest.mark.parametrize("align", ["left", "center", "right"])
    def test_a_split_aligns_its_title_and_every_column(self, align):
        """
        Asserts the *declaration* reaches every column cell. That the cell
        is then wide enough for the alignment to show is #129's business
        and is measured in ``tests/test_screenshots.py`` — a width is not
        something markup can assert.
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
            e
            for e in _aligned_elements(html)
            if "mobile-pad" in e.css_class and e.attribute == align and e.declared == align
        ]
        assert len(columns) == 2, f"expected both column cells aligned, got {len(columns)}"

    def test_a_section_without_a_title_still_aligns_its_content(self):
        html = self._render(FullWidth(align="right", content=TextBlock("<p>x</p>")))
        assert any(
            "mobile-pad" in e.css_class and e.attribute == "right" for e in _aligned_elements(html)
        )

    def test_both_spellings_travel_together_here_too(self):
        """#125's invariant, applied to the declarations #126 adds."""
        html = self._render(
            FullWidth(title="T", align="center", content=TextBlock("<p>x</p>")),
            TwoColumn(ratio="30-70", align="right", title="U", left=TextBlock("<p>L</p>")),
        )
        unpaired = 0
        for element in _aligned_elements(html):
            if element.attribute and element.declared is None:
                unpaired += 1  # base.html's block-aligning cell
                continue
            assert element.attribute and element.declared == element.attribute, (
                f"{element.tag} states its alignment only one way, or two that disagree"
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
            (e.attribute, e.declared) for e in _aligned_elements(html) if "kpi-cell" in e.css_class
        ]
        assert kpi, "the fixture rendered no KPI cells"
        assert all(a == "center" and d == "center" for a, d in kpi), (
            f"a right-aligned section leaked into the KPI strip: {kpi}"
        )

    def test_a_contents_list_keeps_its_own_left(self):
        """The third structural shape: a centred entry would leave its leader."""
        html = self._render(FullWidth(title="Inside", align="center", content=Contents()))
        contents = [
            (e.attribute, e.declared) for e in _aligned_elements(html) if "contents" in e.css_class
        ]
        assert contents == [("left", "left")], f"the section leaked into the list: {contents}"

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
            (e.tag, e.attribute, e.declared)
            for e in _aligned_elements(html)
            if e.tag in ("th", "td") and not e.css_class
        ]
        # The label column resolves left and the numeric column right; a
        # leak would make every one of them centre.
        assert {"left", "right"} <= {a for _, a, _ in table}, (
            f"the table lost its own column alignment: {table}"
        )


PROSE_COMPONENTS = (
    TextBlock,
    NumberedList,
    AuthorBlock,
    ContactBlock,
    ChartBlock,
    PullQuote,
    Button,
)

#: Components that deliberately do **not** take an ``align``, each with the
#: reason, because an exclusion whose justification lives only in an issue
#: is one somebody deletes for looking like an oversight.
STRUCTURALLY_ALIGNED = {
    "CardGroup": "a KPI cell is centred because it is a KPI cell",
    "KpiStrip": "the deprecated alias of CardGroup",
    "DataTable": "columns and cells resolve their own alignment (#117, #118)",
    "ImageBlock": "already has an align, and that one places a block (ImageAlign)",
    "MathBlock": "an equation is an image, placed as a block like ImageBlock (#229)",
    "Contents": "an entry is a title, a leader and a page number, left to right (#183)",
    "Stack": "it holds blocks; each keeps its own align and inherits the section's (#262)",
    "Columns": "a split: each block keeps its own align and inherits the section's (#263)",
    "Callout": "it boxes one block, which keeps its own align and inherits the section's (#268)",
    "Divider": "a rule has no copy to align (#269)",
    "Bibliography": "an entry's hanging indent is its shape, so it fixes its own left (#310)",
    "Glossary": "a term sits beside its definition, so the list fixes its own left (#311)",
    "Only": "it shows one block or none; the block keeps its own align (#365)",
}


class TestOnlyProseComponentsTakeAnAlignment:
    """
    Which components take an ``align`` is **structural**, not a convention.

    ``BoxSurface``'s shape and ``TestTheTwoBoxesShareOneSurface``'s
    reasoning: a claim with an enforcing test is a rule, one without is a
    wish. This reads the class hierarchy rather than a hand-written list,
    so a component added later is covered without anyone remembering.
    """

    def test_every_prose_component_mixes_the_alignment_in(self):
        for component in PROSE_COMPONENTS:
            assert issubclass(component, CopyAlignment), (
                f"{component.__name__} carries prose but does not take an align"
            )

    def test_the_structural_components_deliberately_do_not(self):
        import pyhermes.builder as api

        for name, reason in STRUCTURALLY_ALIGNED.items():
            component = getattr(api, name)
            assert not issubclass(component, CopyAlignment), (
                f"{name} grew an align, but {reason}. If that is intended, the "
                "reasoning on CopyAlignment needs revisiting first — the two "
                "answers to 'where does this cell's text sit' would compete."
            )

    def test_the_split_is_exhaustive(self):
        """
        Every public component is on exactly one side. A component that is
        neither prose nor named as structural is one nobody has decided
        about, which is how a field silently goes missing.
        """
        import pyhermes.builder as api

        public = {
            name
            for name in api.__all__
            if isinstance(getattr(api, name), type)
            and issubclass(getattr(api, name), Component)
            and getattr(api, name) is not Component
        }
        decided = {c.__name__ for c in PROSE_COMPONENTS} | set(STRUCTURALLY_ALIGNED)
        assert public == decided, (
            f"undecided components: {sorted(public - decided)}; "
            f"named but not public: {sorted(decided - public)}"
        )

    def test_the_reason_for_each_exclusion_is_written_down(self):
        """
        In the code, not only here — ``CopyAlignment``'s docstring is what
        the next reader meets.
        """
        doc = CopyAlignment.__doc__ or ""
        for name in ("CardGroup", "DataTable", "ImageBlock", "Contents"):
            assert name in doc, f"{name}'s exclusion is undocumented on CopyAlignment"


class TestComponentAlign:
    META = {"email_subject": "Aligned", "firm_name": "F", "campaign_name": "c"}

    def _render(self, component, **container) -> str:
        return (
            EmailBuilder()
            .metadata(dict(self.META))
            .section(FullWidth(content=component, **container))
            .render()
        )

    @pytest.mark.parametrize("align", ["left", "center", "right"])
    def test_a_component_declares_its_own_alignment(self, align):
        html = self._render(TextBlock("<p>x</p>", align=align))
        body = [
            (e.attribute, e.declared) for e in _aligned_elements(html) if "body-text" in e.css_class
        ]
        assert body == [(align, align)], body

    def test_unset_emits_nothing(self):
        html = self._render(TextBlock("<p>x</p>"))
        assert not [e for e in _aligned_elements(html) if "body-text" in e.css_class], (
            "an unset component declared an alignment"
        )

    def test_a_component_overrides_its_container(self):
        """
        By ordinary CSS cascade — the component's declaration sits on a
        descendant of the cell carrying the container's, and inheritance is
        the weakest source. No Python resolves this.
        """
        html = self._render(TextBlock("<p>x</p>", align="right"), align="center")
        body = [
            (e.attribute, e.declared) for e in _aligned_elements(html) if "body-text" in e.css_class
        ]
        assert body == [("right", "right")], body

    @pytest.mark.parametrize(
        "component",
        [
            TextBlock("<p>x</p>", subtitle="Standfirst", align="center"),
            NumberedList([NumberedItem("01", "T", "b")], subtitle="S", align="center"),
            AuthorBlock("A. Analyst", subtitle="S", align="center"),
            ChartBlock("https://example.com/c.png", alt_text="C", subtitle="S", align="center"),
        ],
        ids=["text", "numbered", "author", "chart"],
    )
    def test_the_subtitle_takes_the_component_s_alignment(self, component):
        """
        The subtitle is part of the component's prose. A centred block with
        a left-aligned italic standfirst above it is the half-applied
        result that makes a feature look broken.
        """
        html = self._render(component)
        subtitles = [
            element
            for element in _aligned_elements(html)
            if element.tag == "p" and "font-style: italic" in element.style
        ]
        assert subtitles, "the component rendered no aligned subtitle"
        for element in subtitles:
            assert (element.attribute, element.declared) == ("center", "center"), element

    def test_every_prose_component_accepts_the_parameter(self):
        """A per-class smoke test, so none is wired in name only."""
        built = [
            TextBlock("<p>x</p>", align="right"),
            NumberedList([NumberedItem("01", "T", "b")], align="right"),
            AuthorBlock("A", align="right"),
            ContactBlock("H", cta_url="https://example.com", align="right"),
            ChartBlock("https://example.com/c.png", alt_text="C", align="right"),
        ]
        for component in built:
            assert component.align == "right"
            html = self._render(component)
            assert 'align="right"' in html, f"{type(component).__name__} did not emit it"

    @pytest.mark.parametrize(
        "component",
        [TextBlock, NumberedList, AuthorBlock, ContactBlock, ChartBlock],
    )
    def test_a_bad_alignment_raises_naming_the_component(self, component):
        arguments = {
            TextBlock: {"content": "<p>x</p>"},
            NumberedList: {"items": [NumberedItem("01", "T", "b")]},
            AuthorBlock: {"name": "A"},
            ContactBlock: {"heading": "H", "cta_url": "https://example.com"},
            ChartBlock: {"image_url": "https://example.com/c.png"},
        }[component]
        with pytest.raises(ValidationError, match=component.__name__.lower()):
            component(**arguments, align="middle")


class TestAlignmentIsGeometryNotADesignAxis:
    """
    The epic's conceptual claim, pinned so nobody has to re-derive it.

    Colour, density and typeface each became an email-level *theme* with
    no per-call-site knob, because a ``font_size=`` or a ``title_color=``
    would dissolve the design system one component at a time. Alignment is
    not of that kind: it is layout geometry, the same category as
    ``TwoColumn(ratio=...)`` and ``CardGroup(orientation=...)``, which have
    always been per-call-site parameters. So there is no ``align_theme``,
    no entry in the closed colour list, and nothing to widen in
    ``TestTheCallerFacingSurfaceStaysClosed``.
    """

    def test_alignment_sits_beside_ratio_and_orientation(self):
        import inspect

        geometry = {
            "TwoColumn": "ratio",
            "ThreeColumn": "ratio",
            "CardGroup": "orientation",
            "FullWidth": "align",
            "TextBlock": "align",
        }
        import pyhermes.builder as api

        for name, parameter in geometry.items():
            parameters = inspect.signature(getattr(api, name)).parameters
            assert parameter in parameters, f"{name} lost its {parameter} parameter"

    def test_there_is_no_alignment_theme(self):
        """
        The failure mode this guards against is someone adding a fourth
        shared value to the bound engine for something that is not an
        email-level voice. A section's alignment varies *per section* —
        that is the whole point — so it can never be one.
        """
        from pyhermes.builder.models import EmailMetadata

        fields = {f.name for f in dataclasses.fields(EmailMetadata)}
        assert not {name for name in fields if "align" in name}, (
            "an alignment reached EmailMetadata. Alignment is per-section geometry, "
            "not an email-level theme like colour, density and typeface."
        )


class TestCallerWrappedContentIsStyledToo:
    """
    #130, which #127 surfaced and this replaces.

    ``TextBlock.content`` is a raw-HTML field whose documented shape is the
    caller's own paragraph tags. A ``p`` cannot contain a ``p``, so while
    the styling wrapper *was* a paragraph the parser auto-closed it, the
    copy became its sibling, and it inherited from the containing cell —
    the label typeface, not the body one, and no alignment. The wrapper is
    a ``div`` now, as ``Card.body`` and ``Footer.disclaimer`` already were.

    The class this used to assert as a *limitation* is gone: its docstring
    said the fix should make it fail and that the failure was the signal to
    delete it rather than widen it. It failed, and it is deleted.
    """

    META = {"email_subject": "Aligned", "firm_name": "F", "campaign_name": "c"}

    def _render(self, component) -> str:
        return (
            EmailBuilder().metadata(dict(self.META)).section(FullWidth(content=component)).render()
        )

    @pytest.mark.parametrize(
        "content",
        [
            "Prose with no markup.",
            "Prose with <strong>emphasis</strong>.",
            "<p>Prose the caller wrapped.</p>",
            "<p>First paragraph.</p><p>Second paragraph.</p>",
        ],
        ids=["plain", "inline", "wrapped", "two-paragraphs"],
    )
    def test_the_styling_wrapper_is_an_ancestor_of_the_copy(self, content):
        """
        The structural claim, checkable without a browser: whatever the
        caller passed must sit *inside* the element carrying the
        component's styling, not beside it.
        """
        html = self._render(TextBlock(content, align="right"))
        wrapper = html[html.index('<div class="body-text"') :]
        wrapper = wrapper[: wrapper.index("</div>")]
        assert "Prose" in wrapper or "First paragraph" in wrapper, (
            "the caller's copy is not inside the styled wrapper"
        )

    def test_every_raw_html_surface_lands_in_a_div(self):
        """
        All five, named and checked structurally. ``Card.body`` and
        ``Footer.disclaimer`` were already right; #130 brought the other
        three into line, and this is what keeps a sixth from being added
        wrongly.

        The rule is worth stating plainly, because it is the cheap
        invariant that would have caught #130 at the time: **a raw-HTML
        field may not be emitted inside a p.** Whatever the caller passes,
        a paragraph inside a paragraph is auto-closed, and everything the
        wrapper was styling escapes.
        """
        surfaces = {
            # Both emitted through the footnote macro since #182, raw all the same.
            "text/text-block.html": "{{ marked(text_parts, true) | prose }}",
            "text/numbered-list.html": "{{ marked(item.body_parts, true) | prose }}",
            "regions/header-bar.html": "{{header_disclaimer}}",
            "analysis/card-group.html": "{{ card.body | prose }}",
            "regions/footer.html": "{{ disclaimer }}",
        }
        for name, expression in surfaces.items():
            source = (TEMPLATE_DIR / name).read_text(encoding="utf-8")
            before = source[: source.index(expression)]
            tag = before[before.rindex("<") :].split()[0].split(">")[0]
            assert tag == "<div", (
                f"{name}: the raw-HTML field {expression} sits directly in {tag}, not a div. "
                "A p cannot contain a p — see #130."
            )
