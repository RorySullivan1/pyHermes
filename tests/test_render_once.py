"""
Epic #419: the render path does each expensive step once.

A check pass lays a document out once and warns once per kept section that
split (#426); a render builds the size-failure hint only when the size check
fails (#427); a message is serialised once per send (#428). Each test counts
the work itself, by patching the call that does it.
"""

from __future__ import annotations

import inspect
import warnings
from email.message import EmailMessage
from unittest import mock

import pytest

from pyhermes.builder import Banner, FullWidth, PrintQualityWarning, TextBlock
from pyhermes.builder.document import Document
from pyhermes.builder.exceptions import SizeError
from pyhermes.builder.images import EmailImage
from pyhermes.builder.medium import LazyHint
from pyhermes.delivery import build_message, save_eml
from pyhermes.delivery.message import to_wire_bytes
from pyhermes.document import EmptyBackMatter, EmptyCover, PagedDocument
from pyhermes.gmail import send_message as gmail_send
from pyhermes.outlook import send_message as outlook_send
from pyhermes.pdf import available
from qa.fixtures import all_fixtures, all_paged_fixtures

requires_pdf = pytest.mark.skipif(
    not available(), reason='no WeasyPrint; the PDF exporter is the optional "[pdf]" extra'
)

ENVELOPE = {"sender": "research@example.com", "to": "reader@example.com"}
LOREM = "The long end did the work this quarter, and the term premium explains the move. " * 3


def _tall_kept() -> PagedDocument:
    """A document whose kept section is taller than a sheet, so it splits and warns."""
    document = PagedDocument(
        {"firm_name": "F", "campaign_name": "C"}, cover=EmptyCover(), back_matter=EmptyBackMatter()
    )
    document.add_section(
        FullWidth(TextBlock(f"<p>{LOREM}</p>" * 40), title="Too tall", keep_together=True)
    )
    return document


@requires_pdf
class TestADocumentIsLaidOutOnce:
    """#426: ``layout()`` is the one place a document meets the engine."""

    @pytest.fixture
    def engine_calls(self):
        import weasyprint

        calls: list[int] = []
        original = weasyprint.HTML.render

        def counting(self, *args, **kwargs):
            calls.append(1)
            return original(self, *args, **kwargs)

        with mock.patch.object(weasyprint.HTML, "render", counting):
            yield calls

    def test_render_pdf_lays_out_once_and_warns_once(self, engine_calls):
        from pyhermes.pdf import render_pdf

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            render_pdf(_tall_kept())
        assert len(engine_calls) == 1
        assert [w.category for w in caught] == [PrintQualityWarning]

    def test_a_held_layout_is_queried_without_the_engine_or_a_warning(self, engine_calls):
        from pyhermes.pdf import anchor_tops, layout, page_count, render_layout

        with pytest.warns(PrintQualityWarning):
            laid_out = layout(_tall_kept())
        with warnings.catch_warnings():
            warnings.simplefilter("error", PrintQualityWarning)
            sheets = page_count(laid_out)
            anchor_tops(laid_out)
            pdf = render_layout(laid_out)
        assert len(engine_calls) == 1
        assert sheets > 1 and pdf.startswith(b"%PDF")

    def test_a_document_is_still_laid_out_when_passed(self, engine_calls):
        from pyhermes.pdf import page_count

        assert page_count(all_paged_fixtures()["a4_portrait"]()) > 0
        assert len(engine_calls) == 1

    def test_render_pdf_has_one_path_and_no_options_of_its_own(self):
        from pyhermes.pdf import exporter

        assert "DEFAULT_OPTIONS" not in inspect.getsource(exporter)


class TestTheHintIsBuiltOnlyOnFailure:
    """#427: a render walks no images for a hint it does not use."""

    @pytest.fixture
    def walks(self):
        calls: list[int] = []
        original = Document.images

        def counting(self, *args, **kwargs):
            calls.append(1)
            return original(self, *args, **kwargs)

        with mock.patch.object(Document, "images", counting):
            yield calls

    @pytest.mark.parametrize(
        ("registry", "name"),
        [(all_paged_fixtures, "a4_portrait"), (all_fixtures, "kitchen_sink")],
    )
    def test_a_passing_render_walks_no_images_for_the_hint(self, walks, registry, name):
        # Before #427 every render walked them once, for a hint only a failure reads.
        registry()[name]().render()
        assert walks == []

    def test_a_failing_email_still_names_its_inlined_images(self, valid_metadata, png_bytes):
        from pyhermes.builder import Email

        email = Email(valid_metadata)
        email.set_banner(Banner(logo_url=EmailImage.inline(png_bytes, alt="Logo", width=100)))
        email.add_section(FullWidth(TextBlock("<p>" + "x" * 110 * 1024 + "</p>")))
        with pytest.raises(SizeError) as raised:
            email.render()
        hint = email._inline_image_hint()
        assert hint.startswith(" 1 inlined image(s) contribute roughly")
        assert str(raised.value).endswith(f"Gmail clipping limit.{hint}")

    def test_the_hint_is_built_once_however_often_it_is_read(self):
        built: list[int] = []
        hint = LazyHint(lambda: built.append(1) or " text")
        assert (str(hint), f"{hint}", built) == (" text", " text", [1])


class _Gmail:
    def send_raw(self, raw: str, *, user_id: str = "me") -> dict:
        return {"id": "m-1"}


class _Graph:
    def send_mime(self, encoded: str, *, user_id: str = "me") -> None:
        return None


class TestAMessageIsSerialisedOnce:
    """#428: the budget, the adapter and ``save_eml`` read the same bytes."""

    @pytest.fixture
    def serialisations(self):
        calls: list[int] = []
        original = EmailMessage.as_bytes

        def counting(self, *args, **kwargs):
            calls.append(1)
            return original(self, *args, **kwargs)

        with mock.patch.object(EmailMessage, "as_bytes", counting):
            yield calls

    @pytest.fixture
    def email(self):
        return all_fixtures()["kitchen_sink"]()

    @pytest.mark.parametrize(
        ("send", "transport"),
        [(gmail_send, _Gmail), (outlook_send, _Graph)],
        ids=["gmail", "outlook"],
    )
    def test_a_build_and_a_send_serialise_once(self, serialisations, email, send, transport):
        send(build_message(email, **ENVELOPE), transport=transport())
        assert len(serialisations) == 1

    def test_save_eml_writes_the_bytes_the_adapter_sends(self, serialisations, email, tmp_path):
        message = build_message(email, **ENVELOPE)
        sent = to_wire_bytes(message)
        assert save_eml(message, tmp_path / "m.eml").read_bytes() == sent
        assert len(serialisations) == 1

    def test_a_changed_message_is_serialised_again(self, serialisations, email):
        message = build_message(email, **ENVELOPE)
        message.replace_header("Subject", "A different subject")
        assert b"A different subject" in to_wire_bytes(message)
        assert len(serialisations) == 2

    def test_an_added_part_is_serialised_again(self, email):
        message = build_message(email, **ENVELOPE)
        before = to_wire_bytes(message)
        message.add_attachment(b"late", maintype="text", subtype="plain", filename="late.txt")
        after = to_wire_bytes(message)
        assert after != before and b"late.txt" in after
