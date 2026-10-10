"""
``content_width`` names the width a block is rendered into, so a caller never types one.

The claim is agreement with the render, not a table of numbers: a probe block
records the width its section actually binds, and the helper must report the
same for every density, every preset and a set of weights.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from pyhermes.builder import (
    SIZE_SCHEMES,
    Component,
    EmailBuilder,
    FourColumn,
    FullWidth,
    SizeTheme,
    ThreeColumn,
    ThreeColumnRatio,
    TwoColumn,
    TwoColumnRatio,
    ValidationError,
    content_width,
)
from pyhermes.builder.engine import cell_width_of
from pyhermes.builder.sizing import A4_PORTRAIT, LETTER_PORTRAIT, resolve_size_scheme

EMAIL_DENSITIES = [SizeTheme.COMPACT, SizeTheme.STANDARD, SizeTheme.SPACIOUS]


class _Probe(Component):
    """A block that records the width its cell was bound to, and draws nothing."""

    def __init__(self, seen: list[int]):
        super().__init__()
        self.seen = seen

    def render(self, engine):
        self.seen.append(cell_width_of(engine))
        return ""

    def text(self) -> str:
        return ""


def _bound(size_theme, section_of) -> list[int]:
    """The widths the probes in one section were rendered into, in column order."""
    seen: list[int] = []
    (
        EmailBuilder()
        .metadata(
            {
                "email_subject": "Widths",
                "firm_name": "Hermes Research",
                "campaign_name": "widths",
                "size_theme": size_theme,
            }
        )
        .section(section_of(lambda: _Probe(seen)))
        .build()
        .render()
    )
    return seen


class TestItAgreesWithTheRender:
    @pytest.mark.parametrize("size_theme", EMAIL_DENSITIES)
    def test_the_body(self, size_theme):
        assert _bound(size_theme, lambda probe: FullWidth(probe())) == [content_width(size_theme)]

    @pytest.mark.parametrize("size_theme", EMAIL_DENSITIES)
    @pytest.mark.parametrize("ratio", list(TwoColumnRatio))
    def test_each_two_column_preset(self, size_theme, ratio):
        bound = _bound(size_theme, lambda p: TwoColumn(left=p(), right=p(), ratio=ratio))
        assert bound == content_width(size_theme, ratio)

    @pytest.mark.parametrize("size_theme", EMAIL_DENSITIES)
    @pytest.mark.parametrize("ratio", list(ThreeColumnRatio))
    def test_each_three_column_preset(self, size_theme, ratio):
        bound = _bound(size_theme, lambda p: ThreeColumn(ratio, left=p(), center=p(), right=p()))
        assert bound == content_width(size_theme, ratio)

    def test_four_across(self):
        bound = _bound(SizeTheme.STANDARD, lambda p: FourColumn([p(), p(), p(), p()]))
        assert bound == content_width(SizeTheme.STANDARD, "25-25-25-25")

    @pytest.mark.parametrize("weights", [(3, 2), (1, 1, 2), (2, 1, 1, 1)])
    def test_weights(self, weights):
        split = {2: TwoColumn, 3: ThreeColumn}.get(len(weights))
        if split is TwoColumn:
            bound = _bound("standard", lambda p: TwoColumn(left=p(), right=p(), ratio=weights))
        elif split is ThreeColumn:
            bound = _bound(
                "standard", lambda p: ThreeColumn(weights, left=p(), center=p(), right=p())
            )
        else:
            bound = _bound("standard", lambda p: FourColumn([p(), p(), p(), p()], ratio=weights))
        assert bound == content_width("standard", weights)


class TestItReadsTheDensityAndThePage:
    def test_the_default_is_the_standard_email_body(self):
        assert content_width() == resolve_size_scheme(SizeTheme.STANDARD).frame.inner

    @pytest.mark.parametrize("name", sorted(SIZE_SCHEMES))
    def test_every_density_by_name_member_or_scheme(self, name):
        scheme = SIZE_SCHEMES[name]
        assert content_width(name) == content_width(SizeTheme(name)) == content_width(scheme)
        assert content_width(name) == scheme.frame.inner

    @pytest.mark.parametrize("page", [A4_PORTRAIT, LETTER_PORTRAIT], ids=["a4", "letter"])
    def test_a_page_lays_the_density_over_its_sheet(self, page):
        expected = resolve_size_scheme(SizeTheme.DENSE).with_page(page).frame.inner
        assert content_width(SizeTheme.DENSE, page=page) == expected
        assert content_width(SizeTheme.DENSE, page=page) != content_width(SizeTheme.DENSE)


class TestItRefusesWhatASplitRefuses:
    def test_an_unknown_preset_names_the_presets(self):
        with pytest.raises(ValidationError, match="50-50"):
            content_width("standard", "60-40")

    @pytest.mark.parametrize("weights", [(1,), (1, 1, 1, 1, 1)])
    def test_a_count_no_split_takes(self, weights):
        with pytest.raises(ValidationError, match="2 to 4 weights"):
            content_width("standard", weights)

    def test_weights_below_the_column_floor(self):
        with pytest.raises(ValidationError, match="min_column_px"):
            content_width("standard", (20, 1))


REPO = Path(__file__).resolve().parent.parent

#: Where a reader learns to size a picture: every example, the manual and the README.
#: The gallery is not here; its fixtures pin deliberate sizes as test data.
USER_FACING = sorted(REPO.glob("examples/*/*.py")) + sorted(REPO.glob("docs/manual/*.md"))
USER_FACING.append(REPO / "README.md")

#: A px width typed inline: ``width=616``, ``logo_width=120``. A relative weight
#: (``width=3``) or a share (``width=0.6``) is not a pixel and is not matched.
TYPED_WIDTH = re.compile(r"\b(?:\w+_)?width\s*=\s*\d{2,}(?![\d.])")


class TestNoWidthIsTypedWhereUsersLearn:
    """
    Standing rule 13: a width comes from ``content_width()`` or a named constant.

    A typed 616 is right at one density on one medium and silently wrong at the
    rest; the factsheet's charts said 690 on a page whose body is 648.
    """

    def test_the_scope_is_not_empty(self):
        assert len(USER_FACING) > 5 and all(path.exists() for path in USER_FACING)

    @pytest.mark.parametrize("path", USER_FACING, ids=lambda p: str(p.relative_to(REPO)))
    def test_no_width_is_typed(self, path):
        offenders = [
            f"{path.relative_to(REPO)}:{number}: {line.strip()}"
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
            if TYPED_WIDTH.search(line)
        ]
        assert not offenders, (
            "a px width is typed; use content_width() for a layout width or a named "
            "constant for an asset's own size:\n" + "\n".join(offenders)
        )
