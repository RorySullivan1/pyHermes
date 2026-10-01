"""
Classic Outlook's drafts through COM (#279), driven against a recording fake of its object model.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import pyhermes.outlook.desktop as desktop
from pyhermes.builder import Email, FullWidth, ImageBlock, TextBlock
from pyhermes.builder.images import EmailImage
from pyhermes.delivery import build_message
from pyhermes.delivery.exceptions import MessageError, TransportError
from pyhermes.delivery.message import Attachment
from pyhermes.outlook.desktop import (
    PR_ATTACH_CONTENT_ID,
    PR_ATTACHMENT_HIDDEN,
    BackendMissingError,
    create_draft,
)
from qa.fixtures._png import solid_png

FACTS = {"email_subject": "Morning Note", "firm_name": "F", "campaign_name": "C"}


class _Accessor:
    def __init__(self) -> None:
        self.properties: dict[str, object] = {}

    def SetProperty(self, name: str, value: object) -> None:  # noqa: N802 — COM's spelling
        self.properties[name] = value


class _Attachment:
    def __init__(self, path: str) -> None:
        self.name = Path(path).name
        self.data = Path(path).read_bytes()
        self.PropertyAccessor = _Accessor()


class _Attachments(list):
    def Add(self, path: str, kind: int) -> _Attachment:  # noqa: N802
        assert kind == desktop.OL_BY_VALUE
        attachment = _Attachment(path)
        self.append(attachment)
        return attachment


class _MailItem:
    def __init__(self) -> None:
        self.Subject = self.To = self.CC = self.HTMLBody = ""
        self.Attachments = _Attachments()
        self.calls: list[str] = []

    def Save(self) -> None:  # noqa: N802
        self.calls.append("Save")

    def Display(self, modal: bool) -> None:  # noqa: N802
        self.calls.append(f"Display({modal})")

    def Send(self) -> None:  # noqa: N802
        self.calls.append("Send")


class _Outlook:
    def __init__(self) -> None:
        self.items: list[_MailItem] = []

    def CreateItem(self, kind: int) -> _MailItem:  # noqa: N802
        assert kind == desktop.OL_MAIL_ITEM
        self.items.append(_MailItem())
        return self.items[-1]


def _message(*, attachments=()):
    image = EmailImage.attached(solid_png(20, 10, (1, 2, 3)), alt="Mark", width=20)
    email = Email(FACTS)
    email.add_section(FullWidth(TextBlock("<p>Body copy.</p>")))
    email.add_section(FullWidth(ImageBlock(image)))
    message = build_message(
        email,
        sender="desk@example.com",
        to=["a@example.com", "b@example.com"],
        cc="c@example.com",
        attachments=attachments,
    )
    return message, image


class TestADraft:
    def test_it_carries_the_envelope_and_the_body(self):
        outlook = _Outlook()
        message, _ = _message()
        mail = create_draft(message, outlook=outlook)
        assert mail is outlook.items[0]
        assert mail.Subject == "Morning Note"
        assert mail.To == "a@example.com; b@example.com"
        assert mail.CC == "c@example.com"
        assert "Body copy." in mail.HTMLBody

    def test_each_cid_image_is_a_hidden_attachment_with_its_content_id(self):
        message, image = _message()
        mail = create_draft(message, outlook=_Outlook())
        (attachment,) = mail.Attachments
        assert attachment.PropertyAccessor.properties == {
            PR_ATTACH_CONTENT_ID: image.content_id,
            PR_ATTACHMENT_HIDDEN: True,
        }
        assert attachment.data == image.asset.data
        assert f'src="cid:{image.content_id}"' in mail.HTMLBody

    def test_a_file_attachment_is_a_visible_one(self):
        report = Attachment(b"%PDF-1.7 fake", "report.pdf", "application/pdf")
        message, _ = _message(attachments=[report])
        mail = create_draft(message, outlook=_Outlook())
        visible = [a for a in mail.Attachments if not a.PropertyAccessor.properties]
        assert [(a.name, a.data) for a in visible] == [("report.pdf", b"%PDF-1.7 fake")]

    def test_it_is_saved_and_opened_and_never_sent(self):
        message, _ = _message()
        mail = create_draft(message, outlook=_Outlook())
        assert mail.calls == ["Save", "Display(False)"]

    def test_display_false_saves_it_quietly(self):
        message, _ = _message()
        mail = create_draft(message, display=False, outlook=_Outlook())
        assert mail.calls == ["Save"]


class TestFailures:
    def test_a_message_with_no_html_is_refused(self):
        message, _ = _message()
        plain = message.get_body(preferencelist=("plain",))
        with pytest.raises(MessageError, match="no HTML part"):
            create_draft(plain, outlook=_Outlook())

    def test_outlooks_own_error_is_chained(self):
        class Refusing(_Outlook):
            def CreateItem(self, kind):  # noqa: N802
                raise RuntimeError("The operation failed.")

        message, _ = _message()
        with pytest.raises(TransportError, match="The operation failed.") as caught:
            create_draft(message, outlook=Refusing())
        assert isinstance(caught.value.__cause__, RuntimeError)

    def test_off_windows_it_says_what_to_use_instead(self, monkeypatch):
        monkeypatch.setattr(desktop.sys, "platform", "linux")
        with pytest.raises(BackendMissingError, match="save_eml"):
            desktop.outlook_application()

    def test_without_pywin32_it_names_the_extra(self, monkeypatch):
        monkeypatch.setattr(desktop.sys, "platform", "win32")

        def missing(name):
            raise ImportError(name)

        monkeypatch.setattr(desktop.importlib, "import_module", missing)
        with pytest.raises(BackendMissingError, match=r"\[outlook-desktop\]"):
            desktop.outlook_application()


def test_the_adapter_never_calls_send():
    """Drafts only: the human stays the sender. Parsed, so a docstring cannot trip it."""
    tree = ast.parse(Path(desktop.__file__).read_text(encoding="utf-8"))
    calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert "Send" not in calls
