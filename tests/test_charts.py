"""
A matplotlib Figure becomes an EmailImage (#180). Skips cleanly without ``[charts]``.

Figures are built with ``matplotlib.figure.Figure`` and never through pyplot,
so no backend is selected and nothing here depends on a display.
"""

import struct

import pytest

pytest.importorskip("matplotlib", reason='the Figure adapter needs "pyhermes[charts]"')

from matplotlib.figure import Figure  # noqa: E402

from pyhermes.builder import (  # noqa: E402
    ChartBlock,
    EmailBuilder,
    FullWidth,
    SizeError,
    ValidationError,
)
from pyhermes.builder.enums import EmbedStrategy  # noqa: E402
from pyhermes.data import chart_from_figure, image_from_figure  # noqa: E402


def _figure(width_inches: float = 6.4, points: int = 3) -> Figure:
    figure = Figure(figsize=(width_inches, 3))
    figure.add_subplot().plot(range(points), [((i * 7) % 5) for i in range(points)])
    return figure


def _pixel_size(png: bytes) -> tuple[int, int]:
    """Width and height from the PNG header, which is where a viewer reads them."""
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", png[16:24])


class TestTheRenderedSize:
    @pytest.mark.parametrize("figure_width", [6.4, 3.3, 7.77])
    @pytest.mark.parametrize(("width", "scale"), [(320, 2), (616, 1), (333, 3)])
    def test_the_bytes_are_width_times_scale_pixels_wide(self, figure_width, width, scale):
        image = image_from_figure(_figure(figure_width), alt="Chart", width=width, scale=scale)
        assert _pixel_size(image.data)[0] == width * scale

    def test_the_attribute_is_the_display_width(self):
        """For a retina asset pass the *display* width, not the file's (builder-architecture.md)."""
        image = image_from_figure(_figure(), alt="Chart", width=320, scale=2)
        assert image.width == 320

    def test_the_aspect_ratio_is_the_figures(self):
        width, height = _pixel_size(image_from_figure(_figure(6.4), alt="C", width=320).data)
        assert height == pytest.approx(width * 3 / 6.4, abs=1)

    def test_the_figure_is_left_as_it_was(self):
        figure = _figure()
        dpi, size = figure.get_dpi(), tuple(figure.get_size_inches())
        image_from_figure(figure, alt="Chart", width=320, scale=3)
        assert (figure.get_dpi(), tuple(figure.get_size_inches())) == (dpi, size)

    def test_tight_crops_and_is_therefore_opt_in(self):
        exact = image_from_figure(_figure(), alt="C", width=320)
        tight = image_from_figure(_figure(), alt="C", width=320, tight=True)
        assert _pixel_size(tight.data)[0] < _pixel_size(exact.data)[0]


class TestHowItReachesTheReader:
    def test_cid_is_the_default_and_reaches_the_manifest(self):
        image = image_from_figure(_figure(), alt="Cumulative returns", width=320)
        assert image.strategy is EmbedStrategy.CID
        email = (
            EmailBuilder()
            .metadata({"email_subject": "S", "firm_name": "F", "campaign_name": "c"})
            .section(FullWidth(content=ChartBlock(image, source="Hermes")))
            .build()
        )
        assert [asset.content_id for asset in email.assets()] == [image.content_id]
        assert f'src="cid:{image.content_id}"' in email.render()

    def test_a_small_chart_can_be_inlined(self):
        image = image_from_figure(
            _figure(2, 3), alt="Spark", width=80, scale=1, strategy="data_uri"
        )
        assert image.src.startswith("data:image/png;base64,")

    def test_an_inlined_chart_over_the_cap_names_the_fix(self):
        """The existing inline cap applies, and its message already points at attached()."""
        big = Figure(figsize=(8, 8))
        big.add_subplot().scatter(range(4000), [(i * 7919) % 4001 for i in range(4000)], s=1)
        with pytest.raises(SizeError, match="attached"):
            image_from_figure(big, alt="Scatter", width=900, scale=2, strategy="data_uri")

    def test_remote_is_refused_because_a_render_has_no_host(self):
        with pytest.raises(ValidationError, match="no host"):
            image_from_figure(_figure(), alt="C", width=320, strategy="remote")


class TestDeterminism:
    def test_the_same_figure_gives_the_same_bytes_and_cid(self):
        """Content-IDs are sha256 of the bytes, so a drifting render would break every golden."""
        first = image_from_figure(_figure(), alt="C", width=320)
        second = image_from_figure(_figure(), alt="C", width=320)
        assert first.data == second.data
        assert first.content_id == second.content_id

    def test_the_matplotlib_version_is_not_in_the_bytes(self):
        import matplotlib

        data = image_from_figure(_figure(), alt="C", width=320).data
        assert matplotlib.__version__.encode() not in data


class TestWhatItRefuses:
    def test_a_non_figure_raises(self):
        with pytest.raises(ValidationError, match="Figure"):
            image_from_figure(object(), alt="C", width=320)

    @pytest.mark.parametrize(("name", "value"), [("width", 0), ("width", 1.5), ("scale", 0)])
    def test_a_bad_size_raises(self, name, value):
        kwargs = {"alt": "C", "width": 320, name: value}
        with pytest.raises(ValidationError, match=name):
            image_from_figure(_figure(), **kwargs)

    def test_alt_is_still_required(self):
        """A chart is never decorative (#149), so the builder's own alt rule holds."""
        with pytest.raises(ValidationError):
            image_from_figure(_figure(), alt="", width=320)


class TestChartFromFigure:
    def test_it_returns_a_chart_carrying_the_image_and_its_fine_print(self):
        chart = chart_from_figure(
            _figure(),
            alt="Cumulative returns",
            width=320,
            source="Hermes Research",
            subtitle="Indexed to 100",
            disclosure="Gross of fees.",
        )
        assert isinstance(chart, ChartBlock)
        assert chart.image.width == 320
        assert (chart.source, chart.subtitle, chart.disclosure) == (
            "Hermes Research",
            "Indexed to 100",
            "Gross of fees.",
        )
        assert chart.images() == [chart.image]
