"""
Put an assembled message into classic Outlook's drafts on Windows, through COM (#279).

For a desk user with Outlook open and no Graph token. It owns the desktop
client's object model and never credentials, like the other adapters, and it
never sends: the draft opens for a person to review and send.

    from pyhermes.delivery import build_message
    from pyhermes.outlook.desktop import create_draft

    create_draft(build_message(email, sender=..., to=[...]))
"""

from __future__ import annotations

import importlib
import sys
import tempfile
from dataclasses import dataclass
from email.message import EmailMessage, Message
from pathlib import Path
from typing import Any

from pyhermes.delivery.exceptions import MessageError, TransportError

#: ``PR_ATTACH_CONTENT_ID``: the id an HTML body's ``cid:`` reference resolves against.
PR_ATTACH_CONTENT_ID = "http://schemas.microsoft.com/mapi/proptag/0x3712001F"

#: ``PR_ATTACHMENT_HIDDEN``: keeps an inline picture out of the attachment well.
PR_ATTACHMENT_HIDDEN = "http://schemas.microsoft.com/mapi/proptag/0x7FFE000B"

#: ``olMailItem`` in ``Application.CreateItem``.
OL_MAIL_ITEM = 0

#: ``olByValue`` in ``Attachments.Add``: Outlook keeps its own copy of the bytes.
OL_BY_VALUE = 1


class BackendMissingError(TransportError):
    """Classic Outlook's COM surface is unavailable: not Windows, or no pywin32."""


@dataclass(frozen=True)
class _Part:
    """One attachment as Outlook will be handed it."""

    filename: str
    data: bytes
    content_id: str = ""


def outlook_application() -> Any:
    """
    The running classic Outlook, through pywin32.

    Raises:
        BackendMissingError: Off Windows, or without the ``[outlook-desktop]`` extra.
    """
    if sys.platform != "win32":
        raise BackendMissingError(
            "A desktop Outlook draft needs Windows and classic Outlook. Elsewhere, save the "
            "message with pyhermes.delivery.save_eml, or send it through pyhermes.outlook (Graph)."
        )
    try:
        client = importlib.import_module("win32com.client")
    except ImportError as exc:
        raise BackendMissingError(
            'pywin32 is missing: install the "[outlook-desktop]" extra, '
            'pip install "pyhermes[outlook-desktop]".'
        ) from exc
    return client.Dispatch("Outlook.Application")


def create_draft(message: EmailMessage, *, display: bool = True, outlook: Any = None) -> Any:
    """
    Save ``message`` as a draft in classic Outlook, and open it unless ``display`` is false.

    The subject, To and Cc, the HTML body, every ``cid:`` image as a hidden
    attachment carrying its Content-ID, and every file attachment. The draft is
    from the Outlook profile's own account, whatever ``From`` the message names.
    ``outlook`` is the ``Outlook.Application`` to use; unset, the running one.

    Returns:
        The saved ``MailItem``.

    Raises:
        MessageError: The message has no HTML part.
        BackendMissingError: No Outlook to reach; see :func:`outlook_application`.
        TransportError: Outlook refused a step, with its own error chained.
    """
    html_part = message.get_body(preferencelist=("html",))
    if html_part is None:
        raise MessageError("The message has no HTML part to put in an Outlook draft.")
    html = html_part.get_content()
    inline, files = _parts(message)
    application = outlook if outlook is not None else outlook_application()
    try:
        mail = application.CreateItem(OL_MAIL_ITEM)
        mail.Subject = str(message.get("Subject", ""))
        mail.To = _recipients(message, "To")
        mail.CC = _recipients(message, "Cc")
        with tempfile.TemporaryDirectory(prefix="pyhermes-draft-") as folder:
            for index, part in enumerate([*inline, *files]):
                path = Path(folder, str(index), part.filename)
                path.parent.mkdir()
                path.write_bytes(part.data)
                attachment = mail.Attachments.Add(str(path), OL_BY_VALUE)
                if part.content_id:
                    accessor = attachment.PropertyAccessor
                    accessor.SetProperty(PR_ATTACH_CONTENT_ID, part.content_id)
                    accessor.SetProperty(PR_ATTACHMENT_HIDDEN, True)
            mail.HTMLBody = html
            mail.Save()
        if display:
            mail.Display(False)
    except Exception as exc:
        raise TransportError(f"Outlook refused the draft: {exc}") from exc
    return mail


def _recipients(message: Message, header: str) -> str:
    """A header's addresses in Outlook's separator."""
    return "; ".join(
        address.strip()
        for value in message.get_all(header, [])
        for address in str(value).split(",")
        if address.strip()
    )


def _parts(message: EmailMessage) -> tuple[list[_Part], list[_Part]]:
    """The inline images, by Content-ID, and the file attachments, in message order."""
    inline: list[_Part] = []
    files: list[_Part] = []
    for part in message.walk():
        if part.is_multipart():
            continue
        content_id = str(part.get("Content-ID", "")).strip().strip("<>")
        data = part.get_payload(decode=True)
        if not isinstance(data, bytes):
            continue
        if part.get_content_disposition() == "attachment":
            files.append(_Part(part.get_filename() or f"attachment-{len(files) + 1}", data))
        elif content_id:
            name = part.get_filename() or f"{content_id}.{part.get_content_subtype()}"
            inline.append(_Part(name, data, content_id))
    return inline, files
