"""
Model validation — required fields and hex-color enforcement.

Validation is expected at construction time (see CLAUDE.md), so these
tests assert on the exception raised by .validate(), which the components
call from their own __init__.
"""

import dataclasses

import pytest

from pyhermes.builder.exceptions import EmailBuilderError, ValidationError
from pyhermes.builder.models import (
    DocumentMetadata,
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


class TestTheDocumentFactsSplitFromTheEmailOnes:
    """
    #161: a paged document reuses the facts without a subject line.

    The split is only real if the base stands alone -- validating, rejecting
    a bad language tag, and requiring nothing an email happens to need.
    """

    def test_an_email_is_a_document(self):
        assert issubclass(EmailMetadata, DocumentMetadata)
        assert isinstance(EmailMetadata(), DocumentMetadata)

    def test_an_email_adds_fields_and_removes_none(self):
        document = {f.name for f in dataclasses.fields(DocumentMetadata)}
        email = {f.name for f in dataclasses.fields(EmailMetadata)}
        assert document < email, "an email must be a strict superset of a document"

    def test_the_shared_facts_are_the_medium_neutral_ones(self):
        # Named rather than derived: which side of the line a fact falls on
        # is a decision, and a decision that nothing pins gets re-made.
        assert {f.name for f in dataclasses.fields(DocumentMetadata)} == {
            "language",
            "header_disclaimer",
            "firm_name",
            "campaign_name",
            "department",
            "date_range",
            "issue_label",
            "current_year",
            "theme",
            "size_theme",
            "font_theme",
        }

    def test_the_email_only_facts_are_the_ones_a_document_cannot_have(self):
        document = {f.name for f in dataclasses.fields(DocumentMetadata)}
        added = {f.name for f in dataclasses.fields(EmailMetadata)} - document
        assert added == {
            "email_subject",
            "preheader_text",
            "unsubscribe_url",
            "view_in_browser_url",
            "header",
            "banner",
            "footer",
        }

    def test_a_document_validates_on_its_own(self):
        DocumentMetadata(firm_name="F", campaign_name="C").validate()

    def test_a_document_does_not_need_a_subject(self):
        # The whole point: a printed page has no subject line, so requiring
        # one on the base would make the split decorative.
        assert not hasattr(DocumentMetadata(), "email_subject")

    @pytest.mark.parametrize("field", ["firm_name", "campaign_name"])
    def test_a_document_still_requires_who_and_what(self, field):
        values = {"firm_name": "F", "campaign_name": "C"}
        values[field] = ""
        with pytest.raises(ValidationError, match=field):
            DocumentMetadata(**values).validate()

    def test_a_document_validates_its_language_tag(self):
        with pytest.raises(ValidationError, match="language"):
            DocumentMetadata(language="en--GB")

    def test_a_document_checks_its_presets_at_construction(self):
        with pytest.raises(ValidationError):
            DocumentMetadata(size_theme="not-a-density")

    def test_a_flat_keyword_conflict_is_reported_before_a_bad_language(self, png_bytes):
        # Error precedence is behaviour too: hydration runs before the base's
        # checks, and it did before the split.
        from pyhermes.builder.regions import Banner

        with pytest.raises(ValidationError, match="flat banner field"):
            EmailMetadata(
                language="en--GB",
                banner=Banner(logo_url="https://example.com/a.png"),
                logo_url="https://example.com/b.png",
            )


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
