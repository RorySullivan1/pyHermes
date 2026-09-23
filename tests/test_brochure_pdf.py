"""
Where each panel lands on the printed sheet: what only the print engine can answer.

Needs ``[pdf]`` and ``[qa]``, and skips without either. Positions are read back
from the PDF by pypdfium2 in points and converted to px at 96 dpi, the unit
every fold width is written in.
"""

from __future__ import annotations

import importlib.util

import pytest

from qa.fixtures import tri_fold_letter
from svc.brochure import (
    BI_FOLD_LETTER,
    TRI_FOLD_LETTER,
    Brochure,
    Panel,
    impose,
    overflowing_panels,
)
from svc.builder import FullWidth, TextBlock
from svc.pdf import available, render_pdf

pytestmark = pytest.mark.skipif(
    not available() or importlib.util.find_spec("pypdfium2") is None,
    reason='the brochure PDF tests need the "[pdf]" and "[qa]" extras',
)

#: PDF points to px: a point is 1/72in and a px 1/96in.
PX_PER_POINT = 96 / 72


def _pdf(document):
    import pypdfium2

    return pypdfium2.PdfDocument(render_pdf(document))


def _left_px(sheet, text: str) -> float | None:
    """The px from the sheet's left edge where ``text`` first starts, or ``None``."""
    textpage = sheet.get_textpage()
    match = textpage.search(text).get_next()
    if not match:
        return None
    left, _, _, _ = textpage.get_charbox(match[0])
    return float(left) * PX_PER_POINT


def _position(fold, side: int, x: float) -> int:
    """Which panel, from 1 at the left, the px ``x`` falls in on ``side``."""
    edges = (*fold.offsets(side), fold.width)
    return next(n for n in range(1, fold.panels + 1) if edges[n - 1] <= x < edges[n])


class TestTheImpositionOnPaper:
    """The #187 done-when: each side carries the right three panels in the right places."""

    @pytest.fixture(scope="class")
    def pdf(self):
        return _pdf(tri_fold_letter.build())

    def test_two_sides(self, pdf):
        assert len(pdf) == 2

    #: Reader index to (side, position), written out rather than read from
    #: the imposition table, so a wrong table cannot agree with itself: side 1
    #: is the inside flap, the back cover and the front cover, and side 2 the
    #: inside spread, as #187 specifies.
    WHERE = {1: (1, 3), 2: (2, 1), 3: (2, 2), 4: (2, 3), 5: (1, 2), 6: (1, 1)}

    @pytest.mark.parametrize(("reader", "place"), sorted(WHERE.items()))
    def test_every_panel_lands_on_its_side_at_its_position(self, pdf, reader, place):
        side, position = place
        marker = tri_fold_letter.MARKERS[reader - 1]
        x = _left_px(pdf[side - 1], marker)
        assert x is not None, f"{marker!r} is not on side {side}"
        assert _position(TRI_FOLD_LETTER, side, x) == position
        assert _left_px(pdf[2 - side], marker) is None, f"{marker!r} is on both sides"

    def test_the_trim_is_the_folds_sheet(self, pdf):
        for sheet in pdf:
            left, bottom, right, top = (v * PX_PER_POINT for v in sheet.get_trimbox())
            assert (round(left), round(bottom), round(right), round(top)) == (0, 0, 1056, 816)


class TestPrintPreparation:
    """The #188 done-when, read off the PDF's own page boxes."""

    @pytest.fixture(scope="class")
    def pdf(self):
        return _pdf(tri_fold_letter.build())

    def test_the_media_box_is_the_trim_plus_bleed_and_slug(self, pdf):
        grow = TRI_FOLD_LETTER.bleed + TRI_FOLD_LETTER.slug
        for sheet in pdf:
            left, bottom, right, top = (v * PX_PER_POINT for v in sheet.get_mediabox())
            assert (round(left), round(bottom)) == (-grow, -grow)
            assert (round(right), round(top)) == (1056 + grow, 816 + grow)

    def test_the_bleed_box_reaches_past_the_trim(self, pdf):
        for sheet in pdf:
            left, bottom, right, top = (v * PX_PER_POINT for v in sheet.get_bleedbox())
            assert left <= -TRI_FOLD_LETTER.bleed and right >= 1056 + TRI_FOLD_LETTER.bleed

    @staticmethod
    def _raster(sheet):
        """The sheet at 96 dpi, and the px offset of the trim's top-left corner in it."""
        image = sheet.render(scale=PX_PER_POINT).to_pil().convert("RGB")
        left, _, _, top = sheet.get_mediabox()
        _, _, _, trim_top = sheet.get_trimbox()
        return image, round(-left * PX_PER_POINT), round((top - trim_top) * PX_PER_POINT)

    def test_the_covers_ground_runs_past_the_trim(self, pdf):
        """The cover is side 1's right panel: its tint reaches into the bleed, right and top."""
        image, x0, y0 = self._raster(pdf[0])
        tint = (0xEE, 0xF2, 0xF5)
        inside_bleed = (x0 + 1056 + TRI_FOLD_LETTER.bleed // 2, y0 + 400)
        above_trim = (x0 + 900, y0 - TRI_FOLD_LETTER.bleed // 2)
        for point in (inside_bleed, above_trim):
            assert max(abs(a - b) for a, b in zip(image.getpixel(point), tint, strict=True)) <= 2, (
                point
            )

    def test_the_ground_stops_at_the_bleed_and_leaves_the_slug_for_marks(self, pdf):
        image, x0, y0 = self._raster(pdf[0])
        slug = (x0 + 1056 + TRI_FOLD_LETTER.bleed + 4, y0 + 400)
        assert image.getpixel(slug) == (255, 255, 255)

    def test_crop_marks_are_drawn_in_the_slug(self, pdf):
        """A crop mark runs out from each trim corner; the top-left one crosses the slug."""
        image, x0, y0 = self._raster(pdf[0])
        # A hairline, antialiased across the two pixels either side of the edge.
        band = [
            image.getpixel((x, y))
            for x in (x0 - 2, x0 - 1, x0, x0 + 1)
            for y in range(0, y0 - TRI_FOLD_LETTER.bleed)
        ]
        assert sum(1 for pixel in band if max(pixel) < 200) >= 10


class TestTheProofOnPaper:
    """The proof raster shows the guides and indices; the production raster shows neither."""

    @staticmethod
    def _dark_pixels_on(document, side: int, x: int) -> int:
        """Dark pixels in a column of the sheet, well below any copy."""
        sheet = _pdf(document)[side - 1]
        image = sheet.render(scale=PX_PER_POINT).to_pil().convert("L")
        # The raster is the media box; the trim sits the bleed and slug in.
        left, _, _, top = sheet.get_mediabox()
        _, _, _, trim_top = sheet.get_trimbox()
        x0, y0 = round(-left * PX_PER_POINT), round((top - trim_top) * PX_PER_POINT)
        return sum(1 for y in range(500, 780) if image.getpixel((x0 + x, y0 + y)) < 200)

    def test_the_proof_draws_every_fold(self):
        proof = tri_fold_letter.build().proof()
        for side in (1, 2):
            for fold in TRI_FOLD_LETTER.offsets(side)[1:]:
                assert self._dark_pixels_on(proof, side, fold) > 50, (side, fold)

    def test_production_draws_none(self):
        brochure = tri_fold_letter.build()
        for side in (1, 2):
            for fold in TRI_FOLD_LETTER.offsets(side)[1:]:
                assert self._dark_pixels_on(brochure, side, fold) == 0, (side, fold)

    def test_the_proof_labels_every_panel_and_production_none(self):
        proof, production = _pdf(tri_fold_letter.build().proof()), _pdf(tri_fold_letter.build())
        for box in impose(TRI_FOLD_LETTER):
            label = f"{box.reader} · "
            assert _left_px(proof[box.side - 1], label) is not None, label
            assert _left_px(production[box.side - 1], label) is None, label


class TestOverflowIsLoud:
    """The prototype's answer, as a test: a clipped panel is named, not lost silently."""

    def test_the_gallery_fits(self):
        assert overflowing_panels(tri_fold_letter.build()) == []

    def _brochure(self, copy_for_panel_three: str) -> Brochure:
        panels = [
            Panel([FullWidth(TextBlock(f"<p>Face {n}</p>"))], title=f"P{n}") for n in range(1, 7)
        ]
        panels[2] = Panel([FullWidth(TextBlock(copy_for_panel_three))], title="Overlong")
        return Brochure({"firm_name": "F", "campaign_name": "C"}, panels)

    @staticmethod
    def _deep_inset(repeats: int) -> Brochure:
        """
        A bi-fold whose inside left keeps a 120px inset, so its safe line is at
        696px and the band between it and the sheet's edge is 120px deep: room
        for copy to overflow the panel and still land on the sheet.
        """
        copy = "<p>" + " ".join(["The curve steepened again."] * repeats) + "</p>"
        panels = [Panel([FullWidth(TextBlock(f"<p>Face {n}</p>"))]) for n in range(1, 5)]
        panels[1] = Panel([FullWidth(TextBlock(copy))], inset=120)
        return Brochure({"firm_name": "F", "campaign_name": "C"}, panels, fold=BI_FOLD_LETTER)

    def test_copy_past_the_safe_line_is_named(self):
        """Overflow that stays on the sheet: the sentinel lands, below the safe line (~735px)."""
        assert overflowing_panels(self._deep_inset(40)) == ["panel 2 (inside left)"]

    def test_copy_inside_the_safe_line_is_not(self):
        """The same panel a third shorter (~540px): the check is not trigger-happy."""
        assert overflowing_panels(self._deep_inset(26)) == []

    def test_copy_off_the_sheet_is_named(self):
        """Overflow past the sheet: the engine records no position for the sentinel at all."""
        long = "<p>" + " ".join(["The curve steepened again."] * 900) + "</p>"
        assert overflowing_panels(self._brochure(long)) == ["panel 3 (inside centre)"]

    def test_an_overlong_panel_stays_on_its_side(self):
        """The table-cell design carried a side onto five more sheets; this one does not."""
        long = "<p>" + " ".join(["The curve steepened again."] * 900) + "</p>"
        assert len(_pdf(self._brochure(long))) == 2
