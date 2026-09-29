"""
Centralized enum vocabulary for the builder.

These are ``StrEnum``s on purpose: each member *is* its wire string, so a
caller can pass either ``TwoColumnRatio.EQUAL`` or the bare ``"50-50"`` and
the containers treat them identically. The tests below pin both the values
and that string-equivalence, because the whole backward-compatibility story
rests on it.
"""

from pyhermes.builder.enums import CardOrientation, ThreeColumnRatio, TwoColumnRatio


class TestTwoColumnRatio:
    def test_values(self):
        assert TwoColumnRatio.EQUAL == "50-50"
        assert TwoColumnRatio.NARROW_WIDE == "30-70"
        assert TwoColumnRatio.WIDE_NARROW == "70-30"

    def test_members_are_strings(self):
        # StrEnum: a member is usable anywhere a str is, and hashes as one.
        assert isinstance(TwoColumnRatio.EQUAL, str)
        assert TwoColumnRatio.EQUAL in {"50-50": 1}

    def test_covers_exactly_the_supported_ratios(self):
        assert {r.value for r in TwoColumnRatio} == {"50-50", "30-70", "70-30"}


class TestThreeColumnRatio:
    def test_values(self):
        assert ThreeColumnRatio.EQUAL == "33-33-33"
        assert ThreeColumnRatio.WIDE_LEFT == "50-25-25"
        assert ThreeColumnRatio.WIDE_CENTER == "25-50-25"
        assert ThreeColumnRatio.WIDE_RIGHT == "25-25-50"

    def test_members_are_strings(self):
        assert isinstance(ThreeColumnRatio.EQUAL, str)
        assert ThreeColumnRatio.EQUAL in {"33-33-33": 1}

    def test_covers_exactly_the_supported_ratios(self):
        assert {r.value for r in ThreeColumnRatio} == {
            "33-33-33",
            "50-25-25",
            "25-50-25",
            "25-25-50",
        }


class TestCardOrientation:
    def test_values(self):
        assert CardOrientation.HORIZONTAL == "horizontal"
        assert CardOrientation.VERTICAL == "vertical"

    def test_members_are_strings(self):
        assert isinstance(CardOrientation.HORIZONTAL, str)
        assert CardOrientation.VERTICAL in {"vertical": 1}
