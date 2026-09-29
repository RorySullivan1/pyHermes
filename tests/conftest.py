"""
Shared fixtures for the pyHermes builder test suite.

Everything here is deliberately minimal-but-valid: each fixture is the
smallest object that passes construction, so a test that fails is failing
on the thing it names rather than on incidental fixture data.
"""

from pathlib import Path

import pytest

from pyhermes.builder import TextBlock
from pyhermes.builder.engine import TemplateEngine
from pyhermes.builder.models import KpiItem, NumberedItem, TableRow


@pytest.fixture(scope="session")
def engine() -> TemplateEngine:
    """A TemplateEngine pointed at the templates/ packaged in pyhermes.builder.

    Session-scoped: the engine is stateless for our purposes and Jinja2
    caches compiled templates, so sharing it keeps the suite fast.
    """
    return TemplateEngine()


@pytest.fixture
def valid_metadata() -> dict:
    """The minimum metadata EmailMetadata.validate() accepts."""
    return {
        "email_subject": "Weekly Market Wrap",
        "firm_name": "Test Capital",
        "campaign_name": "weekly-wrap",
    }


@pytest.fixture
def kpi_items() -> list:
    return [
        KpiItem(label="S&amp;P 500", value="5,234", color="#4A7C59", sublabel="+1.42%"),
        KpiItem(label="10Y Yield", value="4.21%", color="#A63D40", sublabel="-6 bps"),
    ]


@pytest.fixture
def table_rows() -> list:
    return [
        TableRow(cells=["Equities", "+1.4%", "+8.2%"], colors=["", "#4A7C59", "#4A7C59"]),
        TableRow(cells=["Bonds", "-0.3%", "+1.1%"], colors=["", "#A63D40", "#4A7C59"]),
    ]


@pytest.fixture
def numbered_items() -> list:
    return [
        NumberedItem(number="01", title="Rates", body="The curve steepened."),
        NumberedItem(number="02", title="Credit", body="Spreads tightened."),
    ]


@pytest.fixture
def text_block() -> TextBlock:
    """A trivially valid Component, for tests about containers rather than content."""
    return TextBlock("<p>Narrative prose.</p>")


# ──────────────────────────────────────────────────────────────────────
# Image fixtures
# ──────────────────────────────────────────────────────────────────────
#
# Real magic bytes, because sniff_image_type() reads the bytes rather than
# trusting an extension — a fixture of fake bytes would test nothing. The
# PNG is a genuine 1x1 file; the JPEG and GIF carry real signatures with
# filler bodies, which is all the builder ever inspects.


def _one_pixel_png() -> bytes:
    """A valid 1x1 red PNG, built rather than checked in as a binary blob."""
    import struct
    import zlib

    def chunk(kind: bytes, payload: bytes) -> bytes:
        body = kind + payload
        return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body))

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00"))
        + chunk(b"IEND", b"")
    )


@pytest.fixture(scope="session")
def png_bytes() -> bytes:
    return _one_pixel_png()


@pytest.fixture(scope="session")
def other_png_bytes() -> bytes:
    """A second, distinct PNG — so Content-ID dedupe has something to tell apart."""
    return _one_pixel_png() + b"\x00trailing"


@pytest.fixture(scope="session")
def jpeg_bytes() -> bytes:
    return b"\xff\xd8\xff\xe0" + b"\x00" * 32


@pytest.fixture(scope="session")
def gif_bytes() -> bytes:
    return b"GIF89a" + b"\x00" * 32


@pytest.fixture
def png_file(tmp_path, png_bytes) -> Path:
    """The PNG written to disk, for the path-reading code path."""
    path = tmp_path / "chart.png"
    path.write_bytes(png_bytes)
    return path
