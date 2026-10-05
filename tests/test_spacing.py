"""
Epic #209: a print density, a custom scheme, and spacing per object.

#211 ships ``dense`` and gates it off the email medium; #212 lets
``size_theme`` take a :class:`SizeScheme`; #213 is :class:`Spacing` and the
subtree rebind; #214 and #215 put it on the containers and the components.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from typing import Any

import pytest

from pyhermes.brochure import Brochure, Panel
from pyhermes.builder import (
    COMPACT_SIZES,
    DENSE_SIZES,
    STANDARD_SIZES,
    Appendices,
    AuthorBlock,
    BarList,
    Bibliography,
    Button,
    Callout,
    CardGroup,
    ChartBlock,
    Columns,
    ContactBlock,
    Contents,
    DataTable,
    Divider,
    Email,
    EmailBuilder,
    FactList,
    FlowedColumns,
    FourColumn,
    FullWidth,
    Glossary,
    HeroStat,
    ImageBlock,
    MathBlock,
    NumberedList,
    Only,
    OnlySections,
    PullQuote,
    Reference,
    Spacing,
    Sparkline,
    Stack,
    TagRow,
    Teaser,
    TeaserList,
    Term,
    TextBlock,
    ThreeColumn,
    Timeline,
    TwoColumn,
)
from pyhermes.builder import engine as engine_module
from pyhermes.builder.components import Component, descendants
from pyhermes.builder.containers import Container, section_spacing_tokens
from pyhermes.builder.document import Document
from pyhermes.builder.engine import Renderer, TemplateEngine
from pyhermes.builder.enums import CardOrientation, SizeTheme
from pyhermes.builder.exceptions import ValidationError
from pyhermes.builder.images import EmailImage
from pyhermes.builder.models import Card, KpiItem, NumberedItem, TableRow
from pyhermes.builder.sizing import (
    LETTER_LANDSCAPE,
    LETTER_PORTRAIT,
    TOKEN_LAYERS,
    UNPAGED_UNSAFE_TOKENS,
    WIDTH_TOKENS,
    SizeScheme,
)
from pyhermes.config import Config, config_override
from pyhermes.document import Page, PagedDocument, paged_medium
from pyhermes.pdf import available
from qa.fixtures import all_brochure_fixtures, all_fixtures, all_paged_fixtures, letter_dense
from qa.fixtures._png import solid_png

requires_pdf = pytest.mark.skipif(
    not available() or importlib.util.find_spec("pypdfium2") is None,
    reason='reading a sheet back needs the "[pdf]" and "[qa]" extras',
)

PAPER_FACTS = {"firm_name": "Hermes", "campaign_name": "Review"}
EMAIL_FACTS = {"email_subject": "Subject", **PAPER_FACTS}
CARDS = [Card("A", "1"), Card("B", "2")]
HOUSE = COMPACT_SIZES.derive(space={"content_top": 8}, component={"table_cell_pad": 5})

#: A value no preset holds, so finding it in markup can only mean the override.
SENTINEL = 7.25
MARK = f"{SENTINEL}px"

TEMPLATES = Path(__file__).resolve().parent.parent / "pyhermes" / "builder" / "templates"


#: Every tag a prose field is styled on, so each prose token is read (#280).
PROSE = "<h3>H</h3><ul><li>a</li><li>b</li></ul><blockquote>q</blockquote><hr>"


def _panels(count: int = 6) -> list[Panel]:
    return [
        Panel([FullWidth(content=TextBlock(f"<p>Face {n}.</p>"))], title=f"Face {n}")
        for n in range(1, count + 1)
    ]


# ----------------------------------------------------------------------
# #211 — dense, and the gate that keeps it off the email
# ----------------------------------------------------------------------


class TestDenseIsAPrintDensity:
    def test_it_is_a_shipped_density(self) -> None:
        assert SizeTheme.DENSE == "dense"
        from pyhermes.builder.sizing import SIZE_SCHEMES

        assert SIZE_SCHEMES[SizeTheme.DENSE] is DENSE_SIZES

    def test_an_email_refuses_it_and_says_why(self) -> None:
        with pytest.raises(ValidationError, match="not been rendered in an email client"):
            Email({**EMAIL_FACTS, "size_theme": "dense"})

    def test_the_builder_refuses_it_too(self) -> None:
        with pytest.raises(ValidationError, match="print density 'dense'"):
            EmailBuilder().metadata({**EMAIL_FACTS, "size_theme": SizeTheme.DENSE}).build()

    def test_a_paged_document_takes_it(self) -> None:
        document = PagedDocument({**PAPER_FACTS, "size_theme": "dense"})
        document.add_section(FullWidth(title="A", content=TextBlock("<p>x</p>")))
        assert f"font-size:{DENSE_SIZES.type.section}px" in document.render()

    def test_a_brochure_takes_it(self) -> None:
        brochure = Brochure({**PAPER_FACTS, "size_theme": "dense"}, _panels())
        assert f"{DENSE_SIZES.type.body}px" in brochure.render()

    def test_plain_html_takes_it(self) -> None:
        # The gate is the email medium's: plain HTML is never read in Outlook.
        from pyhermes.builder.models import EmailMetadata

        Document(EmailMetadata(**EMAIL_FACTS, size_theme="dense"))

    def test_the_switch_lets_an_email_take_it(self) -> None:
        with config_override(allow_custom_email_density=True):
            Email({**EMAIL_FACTS, "size_theme": "dense"}).render()


class TestTheDenseFixture:
    def test_it_is_in_the_paged_gallery_at_letter_portrait(self) -> None:
        document = all_paged_fixtures()["letter_dense"]()
        assert document.metadata.size_theme == "dense"
        assert document.medium.page_format == LETTER_PORTRAIT

    @requires_pdf
    def test_it_lays_out_to_its_sheets(self) -> None:
        from pyhermes.pdf import page_count

        assert page_count(letter_dense.build()) == letter_dense.SHEETS == 2

    @requires_pdf
    def test_it_is_photographed_one_image_per_sheet(self, tmp_path: Path) -> None:
        from qa.screenshots import capture_pages

        shots, _ = capture_pages({"letter_dense": letter_dense.build()}, tmp_path)
        assert len(shots) == letter_dense.SHEETS
        for shot in shots:
            assert (shot.width, shot.height) == (LETTER_PORTRAIT.width, LETTER_PORTRAIT.height)


# ----------------------------------------------------------------------
# #212 — size_theme accepts a SizeScheme, and the email gates it
# ----------------------------------------------------------------------


class TestACustomScheme:
    def test_a_paged_document_renders_it(self) -> None:
        document = PagedDocument({**PAPER_FACTS, "size_theme": HOUSE})
        document.add_section(FullWidth(content=DataTable(["A"], [TableRow(["1"])])))
        html = document.render()
        assert "padding:8px" in html and "padding: 5px" in html

    def test_a_brochure_renders_it(self) -> None:
        Brochure({**PAPER_FACTS, "size_theme": HOUSE}, _panels()).render()

    def test_an_email_refuses_it_by_default(self) -> None:
        with pytest.raises(
            ValidationError, match="a custom SizeScheme.*allow_custom_email_density"
        ):
            Email({**EMAIL_FACTS, "size_theme": HOUSE})

    def test_an_email_takes_it_behind_the_switch(self) -> None:
        with config_override(allow_custom_email_density=True):
            html = (
                Email({**EMAIL_FACTS, "size_theme": HOUSE})
                .add_section(FullWidth(content=TextBlock("<p>x</p>")))
                .render()
            )
        assert "padding:8px" in html

    def test_a_scheme_equal_to_a_preset_renders_as_its_name(self) -> None:
        def build(size_theme: Any) -> str:
            email = Email({**EMAIL_FACTS, "size_theme": size_theme})
            return email.add_section(FullWidth(content=TextBlock("<p>x</p>"))).render()

        with config_override(allow_custom_email_density=True):
            assert build(STANDARD_SIZES.derive()) == build("standard")

    def test_a_bad_scheme_fails_before_any_template_loads(self) -> None:
        with pytest.raises(ValidationError, match="content_top"):
            COMPACT_SIZES.derive(space={"content_top": 0})

    def test_it_is_still_not_in_the_skeleton_context(self) -> None:
        from pyhermes.builder.models import EmailMetadata

        assert "size_theme" not in EmailMetadata(size_theme=HOUSE).to_dict()


class TestTheSwitchIsAConfigField:
    def test_it_is_off_by_default(self) -> None:
        assert Config().allow_custom_email_density is False

    @pytest.mark.parametrize(
        ("raw", "expected"), [("1", True), ("true", True), ("On", True), ("no", False)]
    )
    def test_the_environment_sets_it(
        self, monkeypatch: pytest.MonkeyPatch, raw: str, expected: bool
    ) -> None:
        monkeypatch.setenv("PYHERMES_ALLOW_CUSTOM_EMAIL_DENSITY", raw)
        assert Config.from_env().allow_custom_email_density is expected

    def test_a_misspelt_value_names_its_variable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PYHERMES_ALLOW_CUSTOM_EMAIL_DENSITY", "maybe")
        with pytest.raises(ValueError, match="PYHERMES_ALLOW_CUSTOM_EMAIL_DENSITY"):
            Config.from_env()

    def test_it_must_be_a_bool(self) -> None:
        with pytest.raises(ValueError, match="must be a bool"):
            Config(allow_custom_email_density=1)  # type: ignore[arg-type]


# ----------------------------------------------------------------------
# #213 — Spacing, and the rebind
# ----------------------------------------------------------------------


class TestSpacingNamesTokens:
    def test_a_flat_name_finds_its_layer(self) -> None:
        spacing = Spacing(content_top=6, table_cell_pad=3, pad_x=10)
        assert spacing.by_layer() == {
            "space": {"content_top": 6},
            "component": {"table_cell_pad": 3},
            "frame": {"pad_x": 10},
        }

    def test_a_mapping_and_keywords_are_one_spacing(self) -> None:
        assert Spacing({"content_top": 6}) == Spacing(content_top=6)
        assert hash(Spacing({"content_top": 6})) == hash(Spacing(content_top=6))

    def test_no_token_name_is_ambiguous_today(self) -> None:
        assert all(len(layers) == 1 for layers in TOKEN_LAYERS.values())

    def test_an_ambiguous_name_is_refused(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from pyhermes.builder import sizing

        monkeypatch.setitem(sizing.TOKEN_LAYERS, "gutter", ("space", "frame"))
        with pytest.raises(ValidationError, match="ambiguous"):
            Spacing(gutter=4)

    @pytest.mark.parametrize("name", sorted(WIDTH_TOKENS))
    def test_the_width_is_never_a_spacing_token(self, name: str) -> None:
        with pytest.raises(ValidationError, match="medium's width"):
            Spacing({name: 300})

    @pytest.mark.parametrize("name", ["body", "section", "body_line", "kpi_value", "legal_line"])
    def test_type_is_never_a_spacing_token(self, name: str) -> None:
        with pytest.raises(ValidationError, match="is type, not spacing"):
            Spacing({name: 2})

    @pytest.mark.parametrize("name", ["cta_width", "cta_height", "list_ordinal_width"])
    def test_a_box_size_is_never_a_spacing_token(self, name: str) -> None:
        with pytest.raises(ValidationError, match="sizes a box"):
            Spacing({name: 20})

    def test_an_unknown_name_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="unknown spacing token 'padding'"):
            Spacing(padding=4)

    def test_an_empty_spacing_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="at least one token"):
            Spacing()

    @pytest.mark.parametrize("bad", [0, -1, True, 4.0, "4px"])
    def test_a_bad_value_fails_as_a_preset_would(self, bad: object) -> None:
        with pytest.raises(ValidationError, match="content_top"):
            Spacing(content_top=bad)  # type: ignore[arg-type]

    def test_a_non_mapping_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="mapping"):
            Spacing(["content_top"])  # type: ignore[arg-type]

    def test_no_caller_writes_css(self) -> None:
        with pytest.raises(ValidationError):
            FullWidth(content=TextBlock("x"), spacing={"padding": "4px 8px"})


class TestAnOverrideMovesOnlyWhatItsObjectReads:
    def test_a_token_the_class_does_not_read_is_refused_by_name(self) -> None:
        with pytest.raises(ValidationError, match="TextBlock reads no 'table_cell_pad'"):
            TextBlock("<p>x</p>", spacing={"table_cell_pad": 3})

    def test_a_container_names_itself_by_its_title(self) -> None:
        with pytest.raises(ValidationError, match="FullWidth 'Rates' reads no 'gutter'"):
            FullWidth(title="Rates", content=TextBlock("x"), spacing={"gutter": 3})

    def test_a_page_may_move_any_token_a_section_reads(self) -> None:
        assert Page.spacing_tokens() == section_spacing_tokens()
        assert {"table_cell_pad", "content_top", "column_bottom"} <= set(Page.spacing_tokens())


class TestTheEmailRefusesTokensItsCollapseReads:
    """
    The ``@media`` block reads the document's scheme, never a subtree's, so
    a token it also reads cannot be moved for one section of an email.
    """

    def test_every_token_the_media_block_reads_is_named(self) -> None:
        source = (TEMPLATES / "base.html").read_text(encoding="utf-8")
        block = source[source.index("@media only screen") : source.index(":root")]
        read = set(re.findall(r"size\.\w+\.(\w+)", block))
        type_tokens = {name for name, layers in TOKEN_LAYERS.items() if layers[0] == "type"}
        assert read - type_tokens - WIDTH_TOKENS <= UNPAGED_UNSAFE_TOKENS

    @pytest.mark.parametrize(
        "section",
        [
            lambda: FullWidth(content=TextBlock("x"), spacing={"pad_x": 10}),
            lambda: TwoColumn(left=TextBlock("x"), spacing={"pad_x": 10}),
            lambda: FullWidth(content=CardGroup(CARDS, spacing={"card_pad_y": 4})),
            lambda: FullWidth(content=CardGroup(CARDS, spacing={"card_pad_x": 4})),
            lambda: Page([FullWidth(content=TextBlock("x"))], spacing={"pad_x": 10}),
        ],
    )
    def test_an_email_refuses_each_when_the_section_is_added(self, section: Any) -> None:
        with pytest.raises(ValidationError, match="mobile collapse"):
            Email(EMAIL_FACTS).add_section(section())

    def test_a_refused_section_leaves_the_email_as_it_was(self) -> None:
        email = Email(EMAIL_FACTS)
        with pytest.raises(ValidationError):
            email.add_section(FullWidth(content=TextBlock("x"), spacing={"pad_x": 10}))
        assert email.text() == Email(EMAIL_FACTS).text()

    def test_a_direct_render_on_a_non_paged_engine_refuses_too(self) -> None:
        section = FullWidth(content=TextBlock("x"), spacing={"pad_x": 10})
        with pytest.raises(ValidationError, match="'html' medium"):
            section.render(TemplateEngine())

    def test_a_paged_document_applies_each(self) -> None:
        document = PagedDocument(PAPER_FACTS)
        document.add_section(
            FullWidth(
                title="T",
                content=CardGroup(
                    [Card("A", "1")],
                    orientation=CardOrientation.VERTICAL,
                    spacing={"card_pad_y": SENTINEL},
                ),
                spacing={"pad_x": 9.5},
            )
        )
        html = document.render()
        assert MARK in html and "9.5px" in html


class TestTheRebindCostsNothingUnused:
    @staticmethod
    def _strip(document: Document) -> Document:
        for section in document._sections:
            held = descendants(section.components())  # a Stack's blocks too (#261)
            for node in [section, *getattr(section, "sections", ()), *held]:
                node.spacing = None
                # A section's own ground rebinds the theme (#266): a colour, not a spacing cost.
                for ground in ("background_color", "text_color"):
                    if hasattr(node, ground):
                        setattr(node, ground, None)
        return document

    @pytest.mark.parametrize(
        "build",
        [
            *all_fixtures().values(),
            *all_paged_fixtures().values(),
            *all_brochure_fixtures().values(),
        ],
    )
    def test_nothing_is_rebound_without_an_override(
        self, build: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def refuse(*_: object, **__: object) -> None:
            raise AssertionError("rebound with no override")

        document = self._strip(build())
        monkeypatch.setattr(engine_module, "rebind", refuse)
        document.render()

    def test_restating_the_bound_value_is_byte_identical(self) -> None:
        def build(spacing: Any) -> str:
            email = Email(EMAIL_FACTS)
            table = DataTable(["A"], [TableRow(["1"])], spacing=spacing)
            return email.add_section(FullWidth(title="T", content=table)).render()

        restated = {"table_cell_pad": STANDARD_SIZES.component.table_cell_pad}
        assert build(restated) == build(None)

    def test_an_override_has_no_plain_text_projection(self) -> None:
        from qa.fixtures import kitchen_sink

        assert self._strip(kitchen_sink.build()).text() == kitchen_sink.build().text()


class TestOverridesNest:
    def _paged(self, *sections: Container) -> str:
        document = PagedDocument(PAPER_FACTS)
        for section in sections:
            document.add_section(section)
        return document.render()

    def test_a_component_derives_from_its_containers_override(self) -> None:
        html = self._paged(
            FullWidth(
                title="T",
                spacing={"content_top": 5.5},
                content=TextBlock("<p>a</p><p>b</p>", spacing={"block_gap": 3.5}),
            )
        )
        assert "padding:5.5px" in html and "3.5px" in html

    def test_a_page_reaches_every_section_on_it(self) -> None:
        html = self._paged(
            Page(
                [FullWidth(content=DataTable(["A"], [TableRow(["1"])]))],
                spacing={"table_cell_pad": 2.5},
            )
        )
        assert "padding: 2.5px" in html

    def test_the_nearer_override_wins(self) -> None:
        table = DataTable(["A"], [TableRow(["1"])], spacing={"table_cell_pad": 3.5})
        html = self._paged(Page([FullWidth(content=table)], spacing={"table_cell_pad": 2.5}))
        assert "padding: 3.5px" in html and "padding: 2.5px" not in html


# ----------------------------------------------------------------------
# #214 / #215 — every class's SPACING_TOKENS is what its template reads
# ----------------------------------------------------------------------


class _Stub(Component):
    """Content that reads no token, so a container's markup is the container's own."""

    def render(self, engine: Renderer) -> str:
        return "<p>stub</p>"

    def text(self) -> str:
        return "stub"


def _image() -> EmailImage:
    return EmailImage.hosted("https://example.com/c.png", alt="Chart", width=300)


#: Each class, built so that every branch its template has is taken.
INSTANCES: dict[type, list[Any]] = {
    FullWidth: [lambda s: FullWidth(title="T", kicker="K", content=_Stub(), spacing=s)],
    FlowedColumns: [lambda s: FlowedColumns(title="T", kicker="K", content=_Stub(), spacing=s)],
    TwoColumn: [
        lambda s: TwoColumn("30-70", title="T", kicker="K", left=_Stub(), right=_Stub(), spacing=s)
    ],
    ThreeColumn: [
        lambda s: ThreeColumn(
            "50-25-25",
            title="T",
            kicker="K",
            left=_Stub(),
            center=_Stub(),
            right=_Stub(),
            spacing=s,
        )
    ],
    CardGroup: [
        lambda s: CardGroup([KpiItem("A", "1"), KpiItem("B", "2")], subtitle="S", spacing=s),
        lambda s: CardGroup(
            [Card("A", "1", body=PROSE), Card("B", "2", body="<p>c</p>")],
            orientation=CardOrientation.VERTICAL,
            subtitle="S",
            spacing=s,
        ),
    ],
    DataTable: [
        lambda s: DataTable(
            ["A", "B"],
            [TableRow(["x", "1"])],
            source="Src",
            as_of="Today",
            subtitle="S",
            caption="Cap",
            disclosure="Fine print.",
            spacing=s,
        )
    ],
    ChartBlock: [
        lambda s: ChartBlock(
            _image(), source="Src", subtitle="S", caption="Cap", disclosure="Fine.", spacing=s
        )
    ],
    ImageBlock: [
        lambda s: ImageBlock(_image(), caption="Cap", subtitle="S", disclosure="Fine.", spacing=s)
    ],
    MathBlock: [
        lambda s: MathBlock(
            solid_png(40, 12, (0, 0, 0)), latex="x^2", caption="Cap", disclosure="Fine.", spacing=s
        )
    ],
    TextBlock: [lambda s: TextBlock("<p>a</p>" + PROSE, subtitle="S", spacing=s)],
    PullQuote: [lambda s: PullQuote("Quoted.", attribution="Someone", spacing=s)],
    ContactBlock: [
        lambda s: ContactBlock(
            heading="H", description="D", cta_label="Go", cta_url="https://example.com", spacing=s
        )
    ],
    NumberedList: [
        lambda s: NumberedList(
            [NumberedItem("1", "One", PROSE), NumberedItem("2", "Two", "<p>b</p>")],
            subtitle="S",
            spacing=s,
        )
    ],
    AuthorBlock: [
        lambda s: AuthorBlock(
            "Name", job_title="Title", email="a@example.com", subtitle="S", spacing=s
        )
    ],
    Contents: [lambda s: _with_entries(Contents(subtitle="S", spacing=s))],
    Stack: [lambda s: Stack([_Stub(), _Stub()], spacing=s)],
    Columns: [lambda s: Columns([_Stub(), _Stub()], spacing=s)],
    FourColumn: [
        lambda s: FourColumn([_Stub(), _Stub(), None, _Stub()], title="T", kicker="K", spacing=s)
    ],
    Callout: [lambda s: Callout(_Stub(), tone="positive", label="L", spacing=s)],
    Button: [lambda s: Button("Go", "https://example.com", spacing=s)],
    Divider: [lambda s: Divider(spacing=s)],
    TagRow: [lambda s: TagRow(["Rates", "Credit", "FX"], spacing=s)],
    FactList: [
        lambda s: FactList({"A": "1", "B": 2}, columns=2, title="T", subtitle="S", spacing=s)
    ],
    Timeline: [lambda s: Timeline([("1 Oct", "A", "B"), ("2 Oct", "C")], subtitle="S", spacing=s)],
    TeaserList: [
        lambda s: TeaserList(
            [Teaser("T", "https://example.com", "1 Oct", "Sum.", image=_image(), tags=["Rates"])],
            subtitle="S",
            spacing=s,
        )
    ],
    Bibliography: [
        lambda s: Bibliography(
            [Reference("k", ["A, B."], 2020, "T", "V", url="https://example.com")],
            style="numeric",
            title="R",
            spacing=s,
        )
    ],
    Glossary: [lambda s: Glossary([Term("T", "D")], title="G", spacing=s)],
    BarList: [
        lambda s: BarList([("A", 2), ("B", -1)], diverging=True, title="T", subtitle="S", spacing=s)
    ],
    Sparkline: [lambda s: Sparkline([1, 2, 3], subtitle="S", spacing=s)],
    HeroStat: [lambda s: HeroStat("1", "Label", "Context", spacing=s)],
    Appendices: [lambda s: Appendices([FullWidth(title="T", content=_Stub())], spacing=s)],
    Only: [lambda s: Only(_Stub(), "html", spacing=s)],
    OnlySections: [
        lambda s: OnlySections([FullWidth(title="T", content=_Stub())], "html", spacing=s)
    ],
}


def _with_entries(contents: Contents) -> Contents:
    contents.entries = [("First", "first"), ("Second", "second")]
    return contents


def _eligible() -> list[str]:
    """Every token a Spacing may name at all."""
    names = []
    for name in TOKEN_LAYERS:
        try:
            Spacing({name: 7})
        except ValidationError:
            continue
        names.append(name)
    return names


def _engine(scheme: SizeScheme = STANDARD_SIZES) -> Renderer:
    medium = paged_medium(LETTER_LANDSCAPE)
    return TemplateEngine(search_path=medium.template_search_path).bound(
        size=scheme.with_page(medium.page_format), medium=medium
    )


def _render(cls: type, spacing: Any, scheme: SizeScheme = STANDARD_SIZES) -> str:
    return "\n".join(build(spacing).render(_engine(scheme)) for build in INSTANCES[cls])


def test_every_public_component_and_container_is_covered() -> None:
    import pyhermes.builder as api

    public = {
        obj
        for name in api.__all__
        if isinstance(obj := getattr(api, name), type)
        and issubclass(obj, (Component, Container))
        and obj not in (Component, Container)
        and name != "KpiStrip"
    }
    assert public == set(INSTANCES)


@pytest.mark.parametrize(
    ("cls", "token"),
    [(cls, token) for cls in INSTANCES for token in cls.SPACING_TOKENS],
    ids=lambda value: getattr(value, "__name__", value),
)
def test_every_declared_token_reaches_the_markup(cls: type, token: str) -> None:
    assert MARK not in _render(cls, None)
    assert MARK in _render(cls, {token: SENTINEL}), (
        f"{cls.__name__} declares {token} and never reads it"
    )


#: Tokens a class reads only when rendered outside any cell, each with why it does.
FALLBACK_READS: dict[type, dict[str, str]] = {
    Columns: {
        "pad_x": "alone it splits the frame's content width; in a cell it splits the cell's (#263)"
    },
    FactList: {"pad_x": "alone its columns share the frame's content width; in a cell, the cell's"},
}


def _declared(cls: type) -> tuple[str, ...]:
    """What a spacing on ``cls`` may move: a holder of sections reaches every one's (#213)."""
    return cls.spacing_tokens() if issubclass(cls, Container) else cls.SPACING_TOKENS


@pytest.mark.parametrize("cls", list(INSTANCES), ids=lambda cls: cls.__name__)
def test_every_token_the_markup_reads_is_declared(cls: type) -> None:
    baseline = _render(cls, None)
    undeclared = []
    for token in _eligible():
        if token in _declared(cls) or token in FALLBACK_READS.get(cls, {}):
            continue
        layer = TOKEN_LAYERS[token][0]
        perturbed = STANDARD_SIZES.derive(**{layer: {token: SENTINEL}})
        if _render(cls, None, perturbed) != baseline:
            undeclared.append(token)
    assert not undeclared, f"{cls.__name__} reads {undeclared} without declaring them"


@pytest.mark.parametrize("cls", list(INSTANCES), ids=lambda cls: cls.__name__)
def test_a_token_outside_the_tuple_is_refused(cls: type) -> None:
    outside = next(token for token in _eligible() if token not in _declared(cls))
    with pytest.raises(ValidationError, match="reads no"):
        INSTANCES[cls][0]({outside: 4})


@pytest.mark.parametrize("cls", list(INSTANCES), ids=lambda cls: cls.__name__)
def test_every_class_takes_spacing_as_a_keyword(cls: type) -> None:
    import inspect

    assert "spacing" in inspect.signature(cls.__init__).parameters


# ----------------------------------------------------------------------
# #215 — a tightened table still breaks cleanly across sheets
# ----------------------------------------------------------------------


@requires_pdf
def test_a_tightened_table_repeats_its_header_on_every_sheet() -> None:
    import pypdfium2

    from pyhermes.pdf import render_pdf

    headers = ["Issue", "Sector", "Weight"]
    rows = [TableRow([f"Bond {n:03d}", "Rates", f"{n / 10:.1f}"]) for n in range(1, 121)]
    document = PagedDocument({**PAPER_FACTS, "size_theme": "dense"})
    document.add_section(FullWidth(content=DataTable(headers, rows, spacing={"table_cell_pad": 3})))
    pdf = pypdfium2.PdfDocument(render_pdf(document))
    sheets = [sheet.get_textpage().get_text_range() for sheet in pdf]
    holding = [text for text in sheets if "Bond " in text]
    assert len(holding) >= 2, "the table did not cross a sheet"
    for text in holding:
        assert all(header.upper() in text for header in headers)
    for text in holding:
        # A row split across a sheet would leave a label without its figure.
        for label in re.findall(r"Bond \d{3}", text):
            number = int(label.split()[1])
            assert f"{number / 10:.1f}" in text
