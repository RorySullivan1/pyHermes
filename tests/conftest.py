"""
Shared fixtures for the pyHermes builder test suite.

Everything here is deliberately minimal-but-valid: each fixture is the
smallest object that passes construction, so a test that fails is failing
on the thing it names rather than on incidental fixture data.
"""

import pytest

from svc.builder import TextBlock
from svc.builder.engine import TemplateEngine
from svc.builder.models import KpiItem, NumberedItem, TableRow


@pytest.fixture(scope="session")
def engine() -> TemplateEngine:
    """A TemplateEngine pointed at the templates/ packaged in svc.builder.

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
