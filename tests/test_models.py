"""
Model validation — required fields and hex-color enforcement.

Validation is expected at construction time (see CLAUDE.md), so these
tests assert on the exception raised by .validate(), which the components
call from their own __init__.
"""

import pytest

from svc.builder.exceptions import EmailBuilderError, ValidationError
from svc.builder.models import (
    EmailMetadata,
    KpiItem,
    NumberedItem,
    SectionConfig,
    TableRow,
)


class TestKpiItem:
    def test_valid_item_passes(self):
        KpiItem(label="S&P 500", value="5,234", color="#4A7C59").validate()

    @pytest.mark.parametrize("field", ["label", "value"])
    def test_missing_required_field_raises(self, field):
        kwargs = {"label": "S&P 500", "value": "5,234"}
        kwargs[field] = ""
        with pytest.raises(ValidationError, match=field):
            KpiItem(**kwargs).validate()

    def test_whitespace_only_is_not_a_value(self):
        with pytest.raises(ValidationError, match="label"):
            KpiItem(label="   ", value="5,234").validate()

    @pytest.mark.parametrize(
        "color", ["4A7C59", "#4A7C5", "#4A7C599", "#GGGGGG", "red", "#4a7c59ff"]
    )
    def test_non_hex_color_raises(self, color):
        with pytest.raises(ValidationError, match="hex color"):
            KpiItem(label="L", value="V", color=color).validate()

    def test_an_unset_color_is_allowed_and_means_the_theme_s_neutral(self):
        """
        Empty stopped being invalid in #49: a construction-time default
        cannot see a render-time theme, so unset is how a card says "use the
        palette". An explicit value is still checked, exactly as above.
        """
        KpiItem(label="L", value="V", color="").validate()

    @pytest.mark.parametrize("color", ["#4A7C59", "#4a7c59", "#000000", "#FFFFFF"])
    def test_hex_color_accepts_both_cases(self, color):
        KpiItem(label="L", value="V", color=color).validate()

    def test_default_color_is_valid(self):
        KpiItem(label="L", value="V").validate()


class TestTableRow:
    def test_colors_may_be_empty(self):
        TableRow(cells=["a", "b"]).validate()

    def test_colors_matching_cells_pass(self):
        TableRow(cells=["a", "b"], colors=["#000000", "#FFFFFF"]).validate()

    def test_empty_string_color_is_skipped(self):
        # "" means "use the template default" for that cell, not "invalid".
        TableRow(cells=["a", "b"], colors=["", "#FFFFFF"]).validate()

    @pytest.mark.parametrize("colors", [["#000000"], ["#000000"] * 3])
    def test_colors_length_mismatch_raises(self, colors):
        # Regression: #6 — the template indexes colors directly, so a
        # mismatched list crashed the render under StrictUndefined.
        with pytest.raises(ValidationError, match="same length"):
            TableRow(cells=["a", "b"], colors=colors).validate()

    def test_invalid_color_raises(self):
        with pytest.raises(ValidationError, match="hex color"):
            TableRow(cells=["a"], colors=["nope"]).validate()


class TestNumberedItem:
    def test_valid_item_passes(self):
        NumberedItem(number="01", title="T", body="B").validate()

    @pytest.mark.parametrize("field", ["title", "body"])
    def test_missing_required_field_raises(self, field):
        kwargs = {"number": "01", "title": "T", "body": "B"}
        kwargs[field] = ""
        with pytest.raises(ValidationError, match=field):
            NumberedItem(**kwargs).validate()


class TestEmailMetadata:
    def test_valid_metadata_passes(self, valid_metadata):
        EmailMetadata(**valid_metadata).validate()

    @pytest.mark.parametrize("field", ["email_subject", "firm_name", "campaign_name"])
    def test_each_required_field_is_enforced(self, valid_metadata, field):
        valid_metadata[field] = ""
        with pytest.raises(ValidationError, match=field):
            EmailMetadata(**valid_metadata).validate()

    def test_optional_fields_may_stay_empty(self, valid_metadata):
        # Only the three above are required; the rest default to "".
        EmailMetadata(**valid_metadata).validate()


class TestSectionConfig:
    def test_valid_config_passes(self):
        SectionConfig(container="full-width", component="analysis/kpi-strip").validate()

    @pytest.mark.parametrize("field", ["container", "component"])
    def test_missing_required_field_raises(self, field):
        kwargs = {"container": "full-width", "component": "analysis/kpi-strip"}
        kwargs[field] = ""
        with pytest.raises(ValidationError, match=field):
            SectionConfig(**kwargs).validate()

    def test_invalid_background_color_raises(self):
        with pytest.raises(ValidationError, match="hex color"):
            SectionConfig(
                container="full-width",
                component="analysis/kpi-strip",
                background_color="not-a-color",
            ).validate()


def test_validation_errors_are_catchable_as_the_base_class():
    # CLAUDE.md: "catch the base class for anything the builder rejected".
    with pytest.raises(EmailBuilderError):
        KpiItem(label="", value="V").validate()


class TestTheLanguageFact:
    """
    #115: the document language is a fact the caller can state.

    The default is ``"en"`` rather than empty for a reason worth keeping:
    every pre-existing email renders byte-identically, and an *absent*
    ``lang`` is worse for the reader than a stated one — a screen reader
    with nothing to go on guesses from the client's locale, which is the
    recipient's language, not the email's.
    """

    def test_it_defaults_to_english(self):
        assert EmailMetadata().language == "en"

    @pytest.mark.parametrize("tag", ["en", "fr", "en-GB", "zh-Hant-TW", "de-DE-1996"])
    def test_a_well_shaped_tag_is_accepted(self, valid_metadata, tag):
        assert EmailMetadata(**valid_metadata, language=tag).language == tag

    @pytest.mark.parametrize(
        "tag",
        [
            "",  # the field is required, unlike every optional URL
            "   ",
            "en_GB",  # underscore is the POSIX locale spelling, not BCP 47
            "en-",  # the three malformations string-building actually
            "-en",  # produces, and the three a bare character class
            "en--GB",  # would wave through
            "en GB",
            "en;charset=utf-8",
        ],
    )
    def test_a_malformed_tag_raises_naming_the_field(self, valid_metadata, tag):
        with pytest.raises(ValidationError, match="metadata.language"):
            EmailMetadata(**valid_metadata, language=tag)

    def test_it_is_rejected_at_construction_not_at_validate(self, valid_metadata):
        """
        The repo's philosophy, and the direction #91 already moved the
        masthead's URLs: by the time ``render()`` runs, the shape is known
        good. A check that only ran in ``validate()`` would let a bad tag
        live in an object for as long as the caller held it.
        """
        with pytest.raises(ValidationError):
            EmailMetadata(**valid_metadata, language="en_GB")

    def test_it_reaches_the_skeleton(self, valid_metadata):
        """It travels by ``to_dict()`` like every other fact — no plumbing."""
        assert EmailMetadata(**valid_metadata, language="fr-CA").to_dict()["language"] == "fr-CA"
