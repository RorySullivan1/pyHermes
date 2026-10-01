"""
A headline figure built from a number (#274): formatted once, toned by what the move means.
"""

from __future__ import annotations

from functools import partial

import pytest

from pyhermes.builder import DEFAULT_THEME, CardGroup, Email, FullWidth
from pyhermes.builder.enums import Tone
from pyhermes.builder.exceptions import ValidationError
from pyhermes.builder.formats import bps, pct
from pyhermes.builder.models import Card, KpiItem

signed_pct = partial(pct, sign=True)


def test_the_issues_own_case():
    item = KpiItem.from_number("UST 10Y", 0.0428, pct, change=0.0006, change_fmt=bps, good="down")
    assert (item.value, item.sublabel, item.tone) == ("4.28%", "+6 bps", Tone.NEGATIVE)
    assert isinstance(item, KpiItem)


@pytest.mark.parametrize(
    ("change", "good", "tone"),
    [
        (0.0006, "up", Tone.POSITIVE),
        (-0.0006, "up", Tone.NEGATIVE),
        (0.0006, "down", Tone.NEGATIVE),
        (-0.0006, "down", Tone.POSITIVE),
        (0.0, "up", Tone.NEUTRAL),
        (0.0, "down", Tone.NEUTRAL),
    ],
)
def test_the_tone_follows_the_change_and_what_good_means(change, good, tone):
    item = KpiItem.from_number("Yield", 0.0428, pct, change=change, change_fmt=bps, good=good)
    assert item.tone == tone


def test_a_change_that_rounds_to_zero_is_not_coloured():
    """`tone_of` reads the formatted string: 0.00% is neutral whatever the raw sign."""
    item = KpiItem.from_number("Index", 5234.1, change=0.00001, change_fmt=signed_pct)
    assert (item.sublabel, item.tone) == ("0.00%", Tone.NEUTRAL)


def test_with_no_change_the_value_carries_the_tone():
    item = KpiItem.from_number("Week", -0.0142, signed_pct)
    assert (item.value, item.sublabel, item.tone) == ("-1.42%", "", Tone.NEGATIVE)


def test_an_explicit_tone_wins():
    item = KpiItem.from_number("VIX", 14.32, change=-2.18, tone=Tone.NEUTRAL)
    assert item.tone == Tone.NEUTRAL


def test_the_change_takes_the_value_format_by_default():
    item = KpiItem.from_number("Spread", 125, change=-5)
    assert (item.value, item.sublabel) == ("125", "-5")


def test_a_card_takes_it_too_with_a_body():
    card = Card.from_number(
        "Breadth", 0.62, pct, change=0.04, change_fmt=signed_pct, body="<p>x</p>"
    )
    assert isinstance(card, Card) and not isinstance(card, KpiItem)
    assert (card.value, card.sublabel, card.tone, card.body) == (
        "62.00%",
        "+4.00%",
        "positive",
        "<p>x</p>",
    )


@pytest.mark.parametrize("good", ["higher", "", None])
def test_good_is_up_or_down(good):
    with pytest.raises(ValidationError, match="good must be"):
        KpiItem.from_number("x", 1, good=good)


def test_both_parts_say_the_same_thing():
    items = [
        KpiItem.from_number("UST 10Y", 0.0428, pct, change=0.0006, change_fmt=bps, good="down"),
        KpiItem.from_number("S&P 500", 5234.1, change=0.0142, change_fmt=signed_pct),
    ]
    email = Email({"email_subject": "S", "firm_name": "F", "campaign_name": "C"})
    email.add_section(FullWidth(CardGroup(items)))
    html, text = email.render(), email.text()
    for figure in ("4.28%", "+6 bps", "5,234", "+1.42%"):
        assert figure in html and figure in text
    assert DEFAULT_THEME.semantic.negative in html and DEFAULT_THEME.semantic.positive in html
