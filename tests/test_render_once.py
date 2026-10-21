"""
Epic #419: the render path does each expensive step once.

A check pass lays a document out once and warns once per kept section that
split (#426); a render builds the size-failure hint only when the size check
fails (#427); a message is serialised once per send (#428). Each test counts
the work itself, by patching the call that does it. The memo of #428 lives
on the message, so a dropped message takes its bytes with it (#443); a layout
carries its profile (#445); and one preview run lays out once (#446).
"""

from __future__ import annotations

import copy
import gc
import importlib.util
import inspect
import warnings
import weakref
from email.message import EmailMessage
from unittest import mock

import pytest

from pyhermes.builder import Banner, FullWidth, PrintQualityWarning, TextBlock
from pyhermes.builder.document import Document
from pyhermes.builder.exceptions import SizeError
from pyhermes.builder.images import EmailImage
from pyhermes.builder.medium import Constraint, Medium
from pyhermes.config import config_override
from pyhermes.delivery import Attachment, MessageError, build_message, save_eml
from pyhermes.delivery import message as message_module
from pyhermes.delivery.message import to_wire_bytes
from pyhermes.document import EmptyBackMatter, EmptyCover, PagedDocument
from pyhermes.gmail import send_message as gmail_send
from pyhermes.outlook import send_message as outlook_send
from pyhermes.pdf import available
from qa.fixtures import all_fixtures, all_paged_fixtures

requires_pdf = pytest.mark.skipif(
    not available(), reason='no WeasyPrint; the PDF exporter is the optional "[pdf]" extra'
)
requires_raster = pytest.mark.skipif(
    importlib.util.find_spec("pypdfium2") is None,
    reason='no pypdfium2; rastering a PDF is the optional "[qa]" extra',
)


@pytest.fixture
def engine_calls():
    """Every time the print engine lays a document out, counted."""
    import weasyprint

    calls: list[int] = []
    original = weasyprint.HTML.render

    def counting(self, *args, **kwargs):
        calls.append(1)
        return original(self, *args, **kwargs)

    with mock.patch.object(weasyprint.HTML, "render", counting):
        yield calls


@pytest.fixture
def pinned_clock():
    """
    fontTools' clock, held still, so two renders compare byte for byte.

    Without HarfBuzz-Subset WeasyPrint subsets fonts through fontTools, which
    stamps the time into each font's ``head`` table (``digital-pdf.md``).
    """
    from fontTools.ttLib.tables import _h_e_a_d

    with mock.patch.object(_h_e_a_d, "timestampNow", lambda: 0):
        yield


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


@requires_pdf
class TestALayoutIsWrittenUnderItsOwnProfile:
    """#445: a layout carries the profile it was laid out under, and nothing else is one."""

    def test_a_tagged_layout_is_written_tagged_with_no_profile_repeated(self, pinned_clock):
        from pyhermes.pdf import PRINT, TAGGED, layout, render_layout, render_pdf

        document = all_paged_fixtures()["a4_portrait"]()
        laid_out = layout(document, TAGGED)
        assert laid_out.profile is TAGGED and laid_out.document is document
        written = render_layout(laid_out)
        assert written == render_pdf(document, TAGGED)
        assert written != render_pdf(document, PRINT)

    def test_save_pdf_writes_through_the_layout(self, tmp_path, pinned_clock):
        from pyhermes.pdf import SCREEN, layout, render_layout, save_layout, save_pdf

        document = all_paged_fixtures()["a4_portrait"]()
        saved = save_pdf(document, tmp_path / "deep" / "a.pdf", SCREEN)
        assert saved.read_bytes() == render_layout(layout(document, SCREEN))
        assert save_layout(layout(document, SCREEN), tmp_path / "b.pdf").read_bytes() == (
            saved.read_bytes()
        )

    def test_render_layout_takes_no_profile_to_drift(self):
        from pyhermes.pdf import render_layout

        assert list(inspect.signature(render_layout).parameters) == ["laid_out"]

    @pytest.mark.parametrize("name", ["page_count", "anchor_tops", "render_layout"])
    def test_anything_else_is_refused_by_name(self, name):
        import pyhermes.pdf

        with pytest.raises(TypeError, match="got str"):
            getattr(pyhermes.pdf, name)("not a document")

    def test_a_fit_check_refuses_a_layout_of_another_document(self):
        from pyhermes.brochure import overflowing_panels
        from pyhermes.deck import overflowing_slides
        from pyhermes.pdf import layout
        from qa.fixtures import all_brochure_fixtures, all_deck_fixtures

        deck = all_deck_fixtures()["pitch_16_9"]()
        brochure = all_brochure_fixtures()["tri_fold_letter"]()
        other = layout(all_paged_fixtures()["a4_portrait"]())
        with pytest.raises(ValueError, match="another document"):
            overflowing_slides(deck, other)
        with pytest.raises(ValueError, match="another document"):
            overflowing_panels(brochure, other)
        assert overflowing_panels(brochure, layout(brochure)) == overflowing_panels(brochure)


@requires_pdf
class TestAPreviewRunLaysOutOnce:
    """#446: one ``python -m qa.preview`` run meets the print engine once, whatever the flags."""

    @requires_raster
    def test_a_paged_document_linted_and_photographed(self, engine_calls, tmp_path):
        from qa.preview import main

        main(["a4_portrait", "--lint", "--screenshot", "--out", str(tmp_path)])
        assert len(engine_calls) == 1
        assert (tmp_path / "a4_portrait.pdf").read_bytes().startswith(b"%PDF")
        assert (tmp_path / "screenshots" / "a4_portrait-page-1.png").exists()

    def test_a_deck_linted(self, tmp_path):
        # The handout is a second document (#459's notes rule lays it out), so each is counted.
        from pyhermes.pdf import exporter
        from qa.preview import main

        laid: list[str] = []
        original = exporter._html

        def recording(weasyprint, html, fetcher):
            laid.append(html)
            return original(weasyprint, html, fetcher)

        with mock.patch.object(exporter, "_html", recording):
            main(["pitch_16_9", "--lint", "--out", str(tmp_path)])
        assert len(laid) == len(set(laid)) == 2

    def test_preview_writes_its_pdf_through_the_exporter(self):
        from qa import preview

        source = inspect.getsource(preview)
        assert "save_layout(" in source
        assert "write_bytes" not in source and "render_layout" not in source


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


class _HostSizeError(SizeError):
    pass


def _host_constraint(html: str, hint: str = "") -> None:
    # Written to the contract before #427: it treats its hint as a str.
    if hint:
        raise AssertionError("a document passes no hint")
    if len(html) > 1024:
        raise _HostSizeError("too big" + hint.strip() + f"{hint:>0}")


class TestAConstraintReceivesAString:
    """#444: the protocol is ``hint: str`` again, and the hint is the document's to add."""

    def test_a_host_constraint_typed_for_a_string_runs(self, valid_metadata, png_bytes):
        from pyhermes.builder import Email

        medium = Medium(name="host", skeleton="base.html", constraints=(_host_constraint,))
        email = Email(valid_metadata, medium=medium)
        email.set_banner(Banner(logo_url=EmailImage.inline(png_bytes, alt="Logo", width=100)))
        with pytest.raises(_HostSizeError) as raised:
            email.render()
        assert str(raised.value) == "too big" + email._inline_image_hint()

    def test_a_host_constraint_typed_for_a_string_type_checks(self, tmp_path):
        from mypy import api

        probe = tmp_path / "probe.py"
        probe.write_text(
            "from pyhermes.builder import Constraint, Medium\n"
            "def check(html: str, hint: str = '') -> None:\n"
            "    if len(html) > 10:\n"
            "        raise ValueError('too big' + hint.strip())\n"
            "constraint: Constraint = check\n"
            "Medium(name='host', skeleton='base.html', constraints=(check,))\n",
            encoding="utf-8",
        )
        out, err, status = api.run([str(probe), "--strict", "--no-incremental"])
        assert status == 0, out + err

    def test_the_constraint_protocol_names_a_string(self):
        assert inspect.signature(Constraint.__call__).parameters["hint"].annotation == "str"


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


class TestTheBytesLiveAndDieWithTheMessage:
    """#443: nothing outside a message keeps it, or its bytes, alive."""

    @pytest.fixture
    def email(self):
        return all_fixtures()["minimal"]()

    def test_a_built_message_once_dropped_is_freed(self, email):
        attachment = Attachment(b"\0" * 2_000_000, "large.bin", "application/octet-stream")
        message = build_message(email, **ENVELOPE, attachments=[attachment])
        to_wire_bytes(message)
        ref = weakref.ref(message)
        del message
        gc.collect()
        assert ref() is None

    def test_a_dropped_message_is_freed_without_the_collector(self, email):
        message = build_message(email, **ENVELOPE)
        ref = weakref.ref(message)
        gc.disable()
        try:
            del message
            assert ref() is None
        finally:
            gc.enable()

    def test_a_refused_build_leaves_nothing_behind(self, email):
        refs: list[weakref.ref[EmailMessage]] = []
        measure = message_module.to_wire_bytes

        def recording(message):
            refs.append(weakref.ref(message))
            return measure(message)

        with (
            mock.patch.object(message_module, "to_wire_bytes", recording),
            config_override(attachment_limit_kb=1, attachment_warn_kb=1),
            pytest.raises(MessageError),
        ):
            build_message(email, **ENVELOPE)
        gc.collect()
        assert len(refs) == 1 and refs[0]() is None

    def test_a_copied_message_is_sent_with_its_own_changes(self, email):
        message = build_message(email, **ENVELOPE)
        sent = to_wire_bytes(message)
        changed = copy.deepcopy(message)
        changed.replace_header("Subject", "A copied subject")
        assert b"A copied subject" in to_wire_bytes(changed)
        assert to_wire_bytes(message) == sent
