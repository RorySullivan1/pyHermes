"""
Email assembly, the 102 KB Gmail size gate, and the EmailBuilder state machine.

The size-limit edges are driven through validate_gmail_size directly: it is
the single runtime check that matters most, and calling it with crafted
strings pins the exact boundary without having to build a ~102 KB email.
"""

import warnings
from pathlib import Path

import pytest

from pyhermes.builder import Email, EmailBuilder, FullWidth
from pyhermes.builder.exceptions import (
    EmailBuilderError,
    SizeError,
    SizeWarning,
    ValidationError,
)
from pyhermes.builder.models import EmailMetadata
from pyhermes.email.medium import _SIZE_LIMIT_KB, _SIZE_WARN_KB, validate_gmail_size


def html_of_kb(kb: float) -> str:
    """An ASCII string weighing exactly `kb` kilobytes."""
    return "x" * int(kb * 1024)


class TestMetadataValidation:
    def test_valid_metadata_constructs(self, valid_metadata):
        Email(metadata=valid_metadata)

    @pytest.mark.parametrize("field", ["email_subject", "firm_name", "campaign_name"])
    def test_missing_required_metadata_raises_at_construction(self, valid_metadata, field):
        # Regression: #7 — EmailMetadata.validate() existed but was never
        # called, so this constructed fine and failed confusingly later.
        del valid_metadata[field]
        with pytest.raises(ValidationError, match=field):
            Email(metadata=valid_metadata)

    def test_accepts_an_emailmetadata_instance(self, valid_metadata):
        Email(metadata=EmailMetadata(**valid_metadata))

    def test_validates_an_emailmetadata_instance_too(self):
        with pytest.raises(ValidationError):
            Email(metadata=EmailMetadata(firm_name="Acme"))


class TestSizeLimit:
    def test_just_under_the_limit_passes(self):
        validate_gmail_size(html_of_kb(_SIZE_LIMIT_KB - 0.1))

    def test_exactly_at_the_limit_passes(self):
        # The check is strictly greater-than, so 102.0 KB is allowed.
        validate_gmail_size(html_of_kb(_SIZE_LIMIT_KB))

    def test_over_the_limit_raises(self):
        with pytest.raises(SizeError, match="exceeds"):
            validate_gmail_size(html_of_kb(_SIZE_LIMIT_KB + 0.1))

    def test_size_error_reports_the_actual_size(self):
        with pytest.raises(SizeError, match="103"):
            validate_gmail_size(html_of_kb(103))

    def test_size_error_is_catchable_as_the_base_class(self):
        with pytest.raises(EmailBuilderError):
            validate_gmail_size(html_of_kb(_SIZE_LIMIT_KB + 1))

    def test_above_the_warn_threshold_warns_but_passes(self):
        with pytest.warns(SizeWarning, match=rf"target < {_SIZE_WARN_KB} KB"):
            validate_gmail_size(html_of_kb(_SIZE_WARN_KB + 1))

    def test_below_the_warn_threshold_is_silent(self, capsys):
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            validate_gmail_size(html_of_kb(10))
        assert capsys.readouterr().out == ""

    def test_size_is_measured_in_utf8_bytes(self):
        # A multi-byte body under the limit by character count but over it
        # by encoded size must still be rejected.
        with pytest.raises(SizeError):
            validate_gmail_size("é" * int(_SIZE_LIMIT_KB * 1024 * 0.75))


class TestRendering:
    def test_renders_a_complete_document(self, valid_metadata, text_block):
        email = Email(metadata=valid_metadata)
        email.add_section(FullWidth(content=text_block, title="Intro"))
        html = email.render()
        assert html.lstrip().lower().startswith("<!doctype html")
        assert "Narrative prose." in html
        assert "Intro" in html

    def test_metadata_reaches_the_skeleton(self, valid_metadata, text_block):
        email = Email(metadata=valid_metadata)
        email.add_section(FullWidth(content=text_block))
        assert valid_metadata["firm_name"] in email.render()

    def test_sections_render_in_order(self, valid_metadata, engine):
        from pyhermes.builder import TextBlock

        email = Email(metadata=valid_metadata)
        email.add_section(FullWidth(content=TextBlock("<p>FIRST</p>")))
        email.add_section(FullWidth(content=TextBlock("<p>SECOND</p>")))
        html = email.render()
        assert html.index("FIRST") < html.index("SECOND")

    def test_add_section_returns_self_for_chaining(self, valid_metadata, text_block):
        email = Email(metadata=valid_metadata)
        assert email.add_section(FullWidth(content=text_block)) is email

    def test_save_writes_the_rendered_html(self, valid_metadata, text_block, tmp_path):
        email = Email(metadata=valid_metadata)
        email.add_section(FullWidth(content=text_block))
        out = email.save(tmp_path / "nested" / "out.html")
        assert out.is_file()
        assert "Narrative prose." in out.read_text(encoding="utf-8")

    def test_save_accepts_a_str_path(self, valid_metadata, text_block, tmp_path):
        """The body coerces with Path(), and save_eml() takes the same union."""
        email = Email(metadata=valid_metadata)
        email.add_section(FullWidth(content=text_block))
        out = email.save(str(tmp_path / "out.html"))
        assert isinstance(out, Path)
        assert out.is_file()


class TestEmailBuilder:
    def test_fluent_chain_builds_an_email(self, valid_metadata, text_block):
        html = (
            EmailBuilder()
            .metadata(valid_metadata)
            .section(FullWidth(content=text_block, title="Intro"))
            .render()
        )
        assert "Narrative prose." in html

    def test_section_before_metadata_raises(self, text_block):
        with pytest.raises(RuntimeError, match="metadata"):
            EmailBuilder().section(FullWidth(content=text_block))

    def test_build_before_metadata_raises(self):
        with pytest.raises(RuntimeError, match="metadata"):
            EmailBuilder().build()

    def test_a_second_metadata_call_raises_rather_than_dropping_sections(
        self, valid_metadata, text_block
    ):
        # #432: it used to start a fresh email, and build() returned no sections.
        builder = EmailBuilder().metadata(valid_metadata).section(FullWidth(content=text_block))
        corrected = {**valid_metadata, "email_subject": "corrected"}
        with pytest.raises(EmailBuilderError, match=r"\.metadata\(\) was already called"):
            builder.metadata(corrected)
        assert "Narrative prose." in builder.render()

    def test_build_returns_the_underlying_email(self, valid_metadata):
        assert isinstance(EmailBuilder().metadata(valid_metadata).build(), Email)

    def test_metadata_validation_applies_through_the_builder(self):
        with pytest.raises(ValidationError):
            EmailBuilder().metadata({"firm_name": "Acme"})

    def test_save_shortcut(self, valid_metadata, text_block, tmp_path):
        out = (
            EmailBuilder()
            .metadata(valid_metadata)
            .section(FullWidth(content=text_block))
            .save(str(tmp_path / "out.html"))
        )
        assert out.is_file()


class TestMetadataAccessor:
    """`Email.metadata` — the read side of the builder's contract (#72)."""

    def test_exposes_the_facts_the_email_was_built_from(self, valid_metadata, text_block):
        email = Email(metadata=valid_metadata)
        email.add_section(FullWidth(content=text_block))
        assert email.metadata.email_subject == valid_metadata["email_subject"]
        assert email.metadata.firm_name == valid_metadata["firm_name"]

    def test_is_read_only(self, valid_metadata):
        # A consumer may read the facts; it may not swap them out from under
        # an email whose validate() has already run.
        email = Email(metadata=valid_metadata)
        with pytest.raises(AttributeError):
            email.metadata = EmailMetadata(**valid_metadata)  # type: ignore[misc]

    def test_returns_the_callers_own_object_not_a_copy(self, valid_metadata):
        # Documents reality rather than aspiration: Email stores the instance
        # it was given, so the caller already held this reference. A copy
        # would be worse -- mutating it would silently do nothing.
        supplied = EmailMetadata(**valid_metadata)
        assert Email(metadata=supplied).metadata is supplied

    def test_a_dict_built_email_still_exposes_metadata(self, valid_metadata):
        assert isinstance(Email(metadata=valid_metadata).metadata, EmailMetadata)
