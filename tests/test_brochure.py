"""
The brochure medium (#172): fold geometry, the panel, imposition and the proof.

Everything here runs on ``[dev]`` alone. What only the print engine can
answer, where each panel lands on the sheet, is in ``test_brochure_pdf.py``.
"""

from __future__ import annotations

import warnings

import pytest

from pyhermes.brochure import (
    BI_FOLD_LETTER,
    BROCHURE_MEDIUM,
    FACE_NAMES,
    FOLD_FORMATS,
    GATE_FOLD_A4,
    IMPOSITION,
    TRI_FOLD_LETTER,
    Z_FOLD_LETTER,
    Brochure,
    FoldFormat,
    FoldKind,
    Panel,
    brochure_medium,
    impose,
)
from pyhermes.brochure.fold import A4_SHEET, LETTER_SHEET
from pyhermes.builder import EmailBuilder, FullWidth, TextBlock, TwoColumn
from pyhermes.builder.exceptions import PrintQualityWarning, ValidationError
from pyhermes.builder.sizing import A4_PORTRAIT, PageFormat
from pyhermes.document import Page, PagedDocument
from qa.fixtures import all_brochure_fixtures, tri_fold_letter
from qa.goldens import artifacts, check_fixture
from qa.lint import errors, lint_document

BROCHURE_NAMES = sorted(all_brochure_fixtures())


def _facts() -> dict[str, str]:
    return {"firm_name": "Hermes", "campaign_name": "Brochure"}


def _panels(count: int, copy: str = "Copy") -> list[Panel]:
    return [
        Panel([FullWidth(TextBlock(f"<p>{copy} {n}</p>"), title=f"Face {n}")], title=f"P{n}")
        for n in range(1, count + 1)
    ]


# ----------------------------------------------------------------------
# #186 — fold geometry
# ----------------------------------------------------------------------


class TestEveryPresetsWidths:
    """Pinned per preset, tuck deficit included, and summing to the sheet exactly."""

    @pytest.mark.parametrize(
        ("fold", "widths"),
        [
            (BI_FOLD_LETTER, (528, 528)),
            # 356 + 356 + 344: the tuck panel is 12px (1/8in) short.
            (TRI_FOLD_LETTER, (344, 356, 356)),
            (Z_FOLD_LETTER, (352, 352, 352)),
            # Flaps 277 over a 569 centre: each flap is 7.5px (2mm) short of half.
            (GATE_FOLD_A4, (277, 569, 277)),
        ],
    )
    def test_the_widths_are_pinned(self, fold, widths):
        assert fold.widths == widths
        assert all(isinstance(width, int) for width in fold.widths)

    @pytest.mark.parametrize("name", sorted(FOLD_FORMATS))
    def test_the_widths_sum_to_the_sheet(self, name):
        fold = FOLD_FORMATS[name]
        assert sum(fold.side_widths(1)) == sum(fold.side_widths(2)) == fold.sheet.width

    def test_the_c_folds_tuck_panel_is_short_by_exactly_the_tuck(self):
        tuck_panel, full, _ = TRI_FOLD_LETTER.widths
        assert full - tuck_panel == TRI_FOLD_LETTER.tuck

    def test_the_gate_flaps_meet_short_of_the_middle_by_the_tuck(self):
        flap, centre, _ = GATE_FOLD_A4.widths
        assert centre / 2 - flap == GATE_FOLD_A4.tuck

    def test_side_two_is_side_one_turned_over(self):
        assert TRI_FOLD_LETTER.side_widths(2) == (356, 356, 344)

    def test_offsets_are_the_running_edges(self):
        assert TRI_FOLD_LETTER.offsets(1) == (0, 344, 700)
        assert TRI_FOLD_LETTER.offsets(2) == (0, 356, 712)

    def test_a_non_whole_width_stays_a_float(self):
        fold = FoldFormat(sheet=PageFormat(width=1000, height=700), kind=FoldKind.Z)
        assert fold.widths == (1000 / 3, 1000 / 3, 1000 - 2 * (1000 / 3))

    def test_panels_are_derived_from_the_kind(self):
        assert (BI_FOLD_LETTER.panels, TRI_FOLD_LETTER.panels) == (2, 3)
        assert (BI_FOLD_LETTER.faces, TRI_FOLD_LETTER.faces) == (4, 6)


class TestAFoldRefuses:
    def test_a_portrait_sheet(self):
        with pytest.raises(ValidationError, match="landscape"):
            FoldFormat(sheet=PageFormat(width=816, height=1056), kind=FoldKind.C)

    def test_a_continuous_sheet(self):
        with pytest.raises(ValidationError, match="height"):
            FoldFormat(sheet=PageFormat(width=816), kind=FoldKind.C)

    def test_a_sheet_with_a_margin(self):
        with pytest.raises(ValidationError, match="margin"):
            sheet = PageFormat(width=1123, height=794, margin=A4_PORTRAIT.margin)
            FoldFormat(sheet=sheet, kind=FoldKind.C)

    @pytest.mark.parametrize("kind", [FoldKind.BI, FoldKind.Z])
    def test_a_tuck_on_a_fold_with_nothing_to_tuck(self, kind):
        with pytest.raises(ValidationError, match="tuck"):
            FoldFormat(sheet=LETTER_SHEET, kind=kind, tuck=6)

    def test_an_unknown_kind(self):
        with pytest.raises(ValidationError, match="fold.kind"):
            FoldFormat(sheet=LETTER_SHEET, kind="accordion")  # type: ignore[arg-type]

    def test_a_tuck_that_leaves_no_panel(self):
        with pytest.raises(ValidationError, match="no width"):
            FoldFormat(sheet=A4_SHEET, kind=FoldKind.GATE, tuck=600)

    @pytest.mark.parametrize("value", [-1, True, "24"])
    def test_a_bad_inset(self, value):
        with pytest.raises(ValidationError, match="inset"):
            FoldFormat(sheet=LETTER_SHEET, kind=FoldKind.C, inset=value)


class TestThePanel:
    def test_it_refuses_to_be_empty(self):
        with pytest.raises(ValidationError, match="at least one section"):
            Panel([])

    def test_it_refuses_a_panel_inside(self):
        with pytest.raises(ValidationError, match="may not contain a panel"):
            Panel([Panel([FullWidth(TextBlock("<p>x</p>"))])], title="Outer")

    def test_it_refuses_a_page_inside(self):
        with pytest.raises(ValidationError, match="may not contain a page"):
            Panel([Page([FullWidth(TextBlock("<p>x</p>"))])])

    @pytest.mark.parametrize("kind", ["slide", "divider"])
    def test_it_refuses_a_slide_inside(self, kind):
        # #317: a slide is a sheet of its own, and inside a panel its anchor
        # pointed nowhere while its titled sections went unregistered.
        from pyhermes.deck import DividerSlide, Slide

        slide = Slide([FullWidth(TextBlock("<p>x</p>"))]) if kind == "slide" else DividerSlide("P")
        with pytest.raises(ValidationError, match="may not contain a (slide|dividerslide)"):
            Panel([slide])

    def test_it_holds_containers_only(self):
        with pytest.raises(ValidationError, match="holds containers"):
            Panel([TextBlock("<p>x</p>")])  # type: ignore[list-item]

    def test_errors_name_the_panel(self):
        with pytest.raises(ValidationError, match="the panel titled 'Cover'"):
            Panel([], title="Cover")

    @pytest.mark.parametrize("value", [-3, True, "12"])
    def test_a_bad_inset(self, value):
        with pytest.raises(ValidationError, match="inset"):
            Panel([FullWidth(TextBlock("<p>x</p>"))], inset=value)

    def test_its_text_is_its_title_then_its_sections(self):
        panel = Panel([FullWidth(TextBlock("<p>Body</p>"), title="Heading")], title="Cover")
        assert panel.text().splitlines()[:2] == ["Cover", "-----"]
        assert "Body" in panel.text()


class TestAPanelFlattensOutsideTheBrochure:
    """
    One tree, three media: wrapping sections in a ``Panel`` moves no byte of
    an email or a paged document. The same claim ``Page`` makes.
    """

    def _sections(self):
        return [
            FullWidth(TextBlock("<p>First</p>"), title="One"),
            TwoColumn(left=TextBlock("<p>Left</p>"), right=TextBlock("<p>Right</p>")),
        ]

    def test_an_email_renders_identically(self):
        bare = EmailBuilder().metadata(_facts() | {"email_subject": "S"})
        for section in self._sections():
            bare = bare.section(section)
        wrapped = (
            EmailBuilder()
            .metadata(_facts() | {"email_subject": "S"})
            .section(Panel(self._sections(), title="Panel", inset=40))
        )
        assert wrapped.build().render() == bare.build().render()

        # The text differs by the panel's own heading and nothing else: a
        # panel joins its sections as a Page does, one blank line apart.
        def lines(text: str) -> list[str]:
            return [line for line in text.splitlines() if line]

        assert (
            lines(wrapped.build().text())
            == lines(bare.build().text())[:3]
            + [
                "Panel",
                "-----",
            ]
            + lines(bare.build().text())[3:]
        )

    def test_a_paged_document_renders_identically(self):
        bare = PagedDocument(_facts())
        for section in self._sections():
            bare.add_section(section)
        wrapped = PagedDocument(_facts()).add_section(Panel(self._sections()))
        assert wrapped.render() == bare.render()

    def test_the_email_and_paged_goldens_are_unaffected(self):
        """Nothing in either gallery is a Panel, and the goldens still hold."""
        from qa.fixtures import all_fixtures, all_paged_fixtures

        for name, build in {**all_fixtures(), **all_paged_fixtures()}.items():
            assert not check_fixture(name, build()), name


class TestTheMedium:
    def test_it_is_paged_and_not_an_email(self):
        assert BROCHURE_MEDIUM.paged and not BROCHURE_MEDIUM.email

    def test_it_searches_its_own_templates_then_the_paged_mediums(self):
        assert BROCHURE_MEDIUM.template_search_path == ("brochure", "document")

    def test_it_has_no_regions(self):
        """Every face is a panel; a Cover region would be a second way to fill the first."""
        assert BROCHURE_MEDIUM.region_types == ()

    def test_it_takes_the_folds_sheet(self):
        assert brochure_medium(GATE_FOLD_A4).page_format == A4_SHEET


# ----------------------------------------------------------------------
# #187 — imposition
# ----------------------------------------------------------------------


class TestImposition:
    @pytest.mark.parametrize("kind", list(FoldKind))
    def test_every_reader_panel_lands_exactly_once(self, kind):
        side_one, side_two = IMPOSITION[kind]
        faces = 2 * len(side_one)
        assert sorted(side_one + side_two) == list(range(1, faces + 1))
        assert len(side_one) == len(side_two)
        assert len(FACE_NAMES[kind]) == faces

    def test_the_c_fold_matches_the_issue(self):
        """Side 1: inside flap, back cover, front cover. Side 2: the inside spread."""
        assert IMPOSITION[FoldKind.C] == ((6, 5, 1), (2, 3, 4))

    @pytest.mark.parametrize("name", sorted(FOLD_FORMATS))
    def test_each_panel_has_the_same_width_on_both_faces(self, name):
        """
        A face on side 1 and the face behind it are one physical panel.

        Side 1's position ``p`` backs side 2's ``n + 1 - p``, so the boxes at
        those two positions must be the same width: the check that the tables
        and the width arithmetic agree about which panel is narrow.
        """
        fold = FOLD_FORMATS[name]
        boxes = impose(fold)
        by_place = {(box.side, box.position): box for box in boxes}
        for position in range(1, fold.panels + 1):
            front = by_place[(1, position)]
            back = by_place[(2, fold.panels + 1 - position)]
            assert front.width == back.width

    def test_the_boxes_come_back_in_reader_order(self):
        boxes = impose(TRI_FOLD_LETTER)
        assert [box.reader for box in boxes] == [1, 2, 3, 4, 5, 6]
        cover = boxes[0]
        assert (cover.side, cover.position, cover.left, cover.width) == (1, 3, 700, 356)
        assert boxes[3].width == 344  # inside right: the panel that folds in


class TestTheBrochure:
    def test_a_wrong_panel_count_names_the_fold_and_the_count(self):
        with pytest.raises(ValidationError, match=r"c-fold has 6 panels, 3 a side; got 5"):
            Brochure(_facts(), _panels(5))

    def test_the_error_lists_the_faces_in_reader_order(self):
        with pytest.raises(ValidationError, match="front cover, inside left, inside right"):
            Brochure(_facts(), _panels(3), fold=BI_FOLD_LETTER)

    def test_every_face_must_be_a_panel(self):
        panels: list = _panels(6)
        panels[2] = FullWidth(TextBlock("<p>x</p>"))
        with pytest.raises(ValidationError, match="inside centre must be a Panel"):
            Brochure(_facts(), panels)

    def test_add_section_is_refused(self):
        brochure = Brochure(_facts(), _panels(6))
        with pytest.raises(ValidationError, match="given at construction"):
            brochure.add_section(FullWidth(TextBlock("<p>x</p>")))

    def test_footnotes_are_refused(self):
        panels = _panels(6)
        panels[1] = Panel([FullWidth(TextBlock("<p>Noted.[^1]</p>", notes=["A note."]))])
        with pytest.raises(ValidationError, match="cannot carry footnotes"):
            Brochure(_facts(), panels)

    def test_the_text_is_reader_order(self):
        text = Brochure(_facts(), _panels(6)).text()
        positions = [text.index(f"Copy {n}") for n in range(1, 7)]
        assert positions == sorted(positions)

    def test_the_html_is_printer_order(self):
        html = Brochure(_facts(), _panels(6)).render()
        positions = [html.index(f"Copy {n}<") for n in (6, 5, 1, 2, 3, 4)]
        assert positions == sorted(positions)

    def test_two_sides_one_page_each(self):
        html = Brochure(_facts(), _panels(6)).render()
        assert html.count('<div class="side"') == 2

    def test_each_panel_renders_against_its_own_width(self):
        """A section inside a panel is sized to the panel, not the sheet."""
        html = Brochure(_facts(), _panels(6)).render()
        assert 'width="344" cellpadding="0"' in html
        assert 'width="1056" cellpadding' not in html

    def test_a_panels_own_inset_wins_over_the_folds(self):
        panels = _panels(6)
        panels[0] = Panel([FullWidth(TextBlock("<p>x</p>"))], inset=40)
        brochure = Brochure(_facts(), panels)
        assert brochure.inset(brochure.panels[0]) == 40
        assert brochure.inset(brochure.panels[1]) == TRI_FOLD_LETTER.inset
        assert "padding:40px 0;" in brochure.render()

    def test_a_panels_ground_is_its_sections_surface(self):
        panels = _panels(6)
        panels[0] = Panel([FullWidth(TextBlock("<p>x</p>"))], background_color="#EEF2F5")
        html = Brochure(_facts(), panels).render()
        cover = html[html.index('data-reader="1"') :]
        cover = cover[: cover.index('class="panel-ground"')]
        assert "#FFFFFF" not in cover.upper()
        assert "#EEF2F5" in cover


class TestTheProof:
    def test_production_output_carries_no_guides_or_labels(self):
        html = Brochure(_facts(), _panels(6)).render()
        assert "proof-fold" not in html.split("</style>", 1)[1]
        assert "proof-label" not in html.split("</style>", 1)[1]

    def test_a_proof_draws_a_guide_on_every_fold(self):
        html = Brochure(_facts(), _panels(6)).render(proof=True)
        body = html.split("</style>", 1)[1]
        assert body.count('class="proof-fold"') == 4
        assert 'class="proof-fold" style="left:344px;' in body
        assert 'class="proof-fold" style="left:712px;' in body

    def test_a_proof_labels_every_panel_with_its_reader_index(self):
        body = Brochure(_facts(), _panels(6)).render(proof=True).split("</style>", 1)[1]
        assert "1 &middot; front cover" in body
        assert "6 &middot; inside flap" in body

    def test_a_proof_leaves_the_next_render_clean(self):
        brochure = Brochure(_facts(), _panels(6))
        brochure.render(proof=True)
        assert 'class="proof-fold"' not in brochure.render()


# ----------------------------------------------------------------------
# The gallery
# ----------------------------------------------------------------------


@pytest.fixture(params=BROCHURE_NAMES)
def brochure_name(request: pytest.FixtureRequest) -> str:
    return str(request.param)


class TestEveryBrochureFixtureMatchesItsGolden:
    def test_every_artifact_is_unchanged(self, brochure_name, request):
        document = all_brochure_fixtures()[brochure_name]()
        if request.config.getoption("--update-goldens"):
            from qa.goldens import write_fixture

            written = write_fixture(brochure_name, document)
            pytest.skip(f"regenerated {', '.join(p.name for p in written)}")
        mismatches = check_fixture(brochure_name, document)
        assert not mismatches, "\n\n".join(str(m) for m in mismatches)

    def test_every_golden_is_checked_in(self, brochure_name):
        document = all_brochure_fixtures()[brochure_name]()
        for _, path, _ in artifacts(brochure_name, document):
            assert path.is_file(), f"{path} is missing; run `pytest --update-goldens`."
            assert path.parent.name == "brochure"

    def test_every_fixture_lints_clean(self, brochure_name):
        assert errors(lint_document(all_brochure_fixtures()[brochure_name]())) == []


class TestEveryPanelFieldIsExercised:
    """Standing rule 9, for the brochure's one new container."""

    def test_each_field_is_set_away_from_its_default_somewhere(self):
        panels = tri_fold_letter.panels()
        assert any(panel.title for panel in panels)
        assert any(panel.background_color for panel in panels)
        assert any(panel.align for panel in panels)
        assert any(panel.inset is not None for panel in panels)

    def test_every_face_opens_on_its_own_marker(self):
        text = tri_fold_letter.build().text()
        for marker in tri_fold_letter.MARKERS:
            assert text.count(marker) == 1, marker


class TestAProofIsACopy:
    def test_the_proof_renders_with_guides(self):
        brochure = Brochure(_facts(), _panels(6))
        assert 'class="proof-fold"' in brochure.proof().render()

    def test_the_original_never_does(self):
        brochure = Brochure(_facts(), _panels(6))
        brochure.proof()
        assert 'class="proof-fold"' not in brochure.render()

    def test_a_proof_can_still_render_clean_when_asked(self):
        proof = Brochure(_facts(), _panels(6)).proof()
        assert 'class="proof-fold"' not in proof.render(proof=False)
        assert 'class="proof-fold"' in proof.render()


def test_the_brochure_imports_the_exporter_only_to_check_a_fit():
    """``pyhermes.brochure`` renders on ``[dev]`` alone; only the overflow check needs ``[pdf]``."""
    import ast
    import pathlib

    for path in sorted(pathlib.Path("pyhermes/brochure").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        top = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
        modules = {getattr(n, "module", None) or n.names[0].name for n in top}
        assert not any(m and m.startswith("pyhermes.pdf") for m in modules), path


# ----------------------------------------------------------------------
# #188 — print preparation
# ----------------------------------------------------------------------


class TestTheSafeArea:
    def test_a_panel_inside_the_safe_distance_raises_naming_it(self):
        panels = _panels(6)
        panels[3] = Panel([FullWidth(TextBlock("<p>x</p>"))], title="Positions", inset=8)
        with pytest.raises(ValidationError, match=r"inside right \('Positions'\).*8px.*12px"):
            Brochure(_facts(), panels)

    def test_exactly_the_safe_distance_is_allowed(self):
        panels = _panels(6)
        panels[3] = Panel([FullWidth(TextBlock("<p>x</p>"))], inset=TRI_FOLD_LETTER.safe)
        Brochure(_facts(), panels)

    def test_a_fold_whose_default_inset_is_unsafe_is_refused(self):
        with pytest.raises(ValidationError, match="safe distance"):
            FoldFormat(sheet=LETTER_SHEET, kind=FoldKind.Z, inset=6)

    @pytest.mark.parametrize("name", ["safe", "bleed", "slug"])
    def test_each_distance_is_a_number_of_px(self, name):
        with pytest.raises(ValidationError, match=name):
            FoldFormat(sheet=LETTER_SHEET, kind=FoldKind.Z, **{name: -1})


class TestImageResolution:
    """300 dpi on paper: a 300px display width needs 938 source pixels."""

    def _with_image(self, pixels: int, display: int) -> Brochure:
        from pyhermes.builder import ImageBlock
        from pyhermes.builder.images import EmailImage
        from qa.fixtures._png import solid_png

        image = EmailImage.attached(solid_png(pixels, 10, (1, 2, 3)), alt="Chart", width=display)
        panels = _panels(6)
        panels[2] = Panel([FullWidth(ImageBlock(image))])
        return Brochure(_facts(), panels)

    def test_enough_pixels_is_silent(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error", PrintQualityWarning)
            self._with_image(938, 300)

    def test_below_the_target_warns_naming_the_width_it_needs(self):
        with pytest.warns(
            PrintQualityWarning, match="'Chart' is 600px wide and needs 938px to print at 300 dpi"
        ):
            self._with_image(600, 300)

    def test_below_half_the_target_raises_naming_the_width_it_needs(self):
        with pytest.raises(ValidationError, match=r"'Chart' is 400px wide.*needs 938px"):
            self._with_image(400, 300)

    def test_the_target_is_the_configs(self):
        from pyhermes.config import config_override

        with config_override(print_dpi=150):
            self._with_image(469, 300)


class TestThePrintMarkup:
    def test_the_page_declares_bleed_and_slug_and_marks(self):
        html = Brochure(_facts(), _panels(6)).render()
        assert "bleed: 36px;" in html and "marks: crop cross;" in html

    def test_an_outer_panels_ground_runs_into_the_bleed_on_three_sides(self):
        html = Brochure(_facts(), _panels(6)).render()
        # Side 1's left panel: the flap, 344px, bled left, top and bottom.
        assert (
            'class="panel-ground" style="left:-12px; top:-12px; width:356px; height:840px;' in html
        )

    def test_an_inner_panels_ground_crosses_no_fold(self):
        html = Brochure(_facts(), _panels(6)).render()
        assert (
            'class="panel-ground" style="left:344px; top:-12px; width:356px; height:840px;' in html
        )

    def test_the_brochure_lints_one_info_finding_and_no_error(self):
        from qa.lint import Severity

        findings = lint_document(Brochure(_facts(), _panels(6)))
        assert [(f.rule_id, f.severity) for f in findings] == [("rgb-only", Severity.INFO)]

    def test_a_skeleton_without_marks_is_an_error(self):
        from qa.lint import lint_html

        html = Brochure(_facts(), _panels(6)).render().replace("marks: crop cross;", "")
        assert "print-marks" in {f.rule_id for f in lint_html(html, "brochure")}


# ----------------------------------------------------------------------
# #189 — the full-bleed panel
# ----------------------------------------------------------------------


class TestTheFullBleedPanel:
    @staticmethod
    def _image(pixels: int = 1150):
        from pyhermes.builder.images import EmailImage
        from qa.fixtures._png import solid_png

        return EmailImage.attached(solid_png(pixels, 20, (9, 9, 9)), alt="Ground")

    def _brochure(self, image) -> Brochure:
        panels = _panels(6)
        panels[0] = Panel([FullWidth(TextBlock("<p>Cover</p>"))], background_image=image)
        return Brochure(_facts(), panels)

    def test_the_image_fills_the_ground_to_the_bleed(self):
        image = self._image()
        html = self._brochure(image).render()
        ground = html[html.index('class="panel-ground" style="left:700px;') :]
        assert f"background-image:url('cid:{image.content_id}'); background-size:cover;" in ground

    def test_the_sections_go_clear_over_it(self):
        html = self._brochure(self._image()).render()
        assert '<div class="panel panel-imaged" data-reader="1"' in html
        assert ".panel-imaged table, .panel-imaged td { background-color: transparent" in html

    def test_it_is_declared_and_reaches_the_manifest_first(self):
        """Standing rule 7: the panel names the field, and the bytes are attached."""
        image = self._image()
        brochure = self._brochure(image)
        assert Panel.IMAGE_FIELDS == ("background_image",)
        assert brochure.panels[0].images()[0] is image
        assert image.content_id in [asset.content_id for asset in brochure.assets()]

    def test_the_print_check_measures_the_ground_not_the_image(self):
        """The cover's ground is 368px with its bleed: 1,150 pixels, and half is refused."""
        with pytest.raises(ValidationError, match=r"'Ground' is 500px wide.*needs 1150px"):
            self._brochure(self._image(500))

    def test_a_hosted_image_is_refused(self):
        from pyhermes.builder.images import EmailImage

        with pytest.raises(ValidationError, match="attach it"):
            Panel(
                [FullWidth(TextBlock("<p>x</p>"))],
                background_image=EmailImage.hosted("https://example.com/a.png", alt="A"),
            )

    def test_it_must_be_an_email_image(self):
        with pytest.raises(ValidationError, match="must be an EmailImage"):
            Panel([FullWidth(TextBlock("<p>x</p>"))], background_image="a.png")  # type: ignore[arg-type]

    def test_the_gallery_sets_one(self):
        assert any(panel.background_image for panel in tri_fold_letter.panels())
