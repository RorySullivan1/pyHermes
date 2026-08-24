"""
Transport-neutral MIME assembly for a built email.

The builder composes and *declares*; this module assembles.
:meth:`~svc.builder.email.Email.render` gives the HTML and
:meth:`~svc.builder.email.Email.assets` gives the manifest of images that
HTML references as ``cid:`` — this turns that pair into an
:class:`~email.message.EmailMessage` an adapter can hand to a transport.

Nothing here authenticates, opens a socket, or reads the clock. Assembly is
pure: testable without credentials, and byte-identical for the same input.
Everything that varies per send — ``Date``, ``Message-ID``, envelope
recipients — belongs to the adapter that sends.

Structure produced::

    text/html                        (an email with no CID images)

    multipart/related                (an email with CID images)
    ├── text/html
    └── image/*  × N    Content-ID: <id>, Content-Disposition: inline

When plain-text generation lands, the HTML part becomes one half of a
``multipart/alternative`` and this structure nests inside it unchanged.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Sequence
from email.message import EmailMessage
from html.parser import HTMLParser
from pathlib import Path
from typing import Protocol

from svc.builder.images import ImageAsset

from .exceptions import MessageError

__all__ = ["RenderableEmail", "build_message", "collect_cid_references", "save_eml"]

CID_SCHEME = "cid:"

# A cid: reference inside a CSS url(), e.g.
# style="background-image:url(cid:abc)". EmailMetadata.header_bg_image_url is
# a CSS background, so checking whether an attribute *value* starts with
# "cid:" would miss it entirely. This scans an already-parsed attribute value
# — the parse-don't-grep rule is about HTML structure, and CSS sitting inside
# an attribute has no parser of its own here.
_CSS_URL_CID = re.compile(r"url\(\s*['\"]?\s*cid:([^)'\"\s]+)", re.IGNORECASE)

# Deliberately narrow: CR/LF is what turns an envelope field into a header
# injection (a "Subject" containing "\nBcc: ..." forges an extra header).
# This is not address-format validation -- no RFC 5322 addr-spec parsing, no
# deliverability checks -- just the characters that let a value break out of
# the single header line it is meant to occupy.
_CONTROL_CHARS = re.compile(r"[\r\n]")


class RenderableEmail(Protocol):
    """What assembly needs from the builder: the HTML, and the manifest.

    A structural type rather than a base class, so both
    :class:`~svc.builder.email.Email` and
    :class:`~svc.builder.email.EmailBuilder` satisfy it as they are — the
    delivery layer never imports or subclasses builder classes.
    """

    def render(self) -> str: ...

    def assets(self) -> list[ImageAsset]: ...


class _CidReferenceCollector(HTMLParser):
    """Collects every ``cid:`` reference in any attribute of any tag."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.content_ids: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for _name, value in attrs:
            if value:
                self.content_ids.extend(_cids_in(value))


def _cids_in(value: str) -> Iterator[str]:
    """Every Content-ID referenced by one attribute value."""
    stripped = value.strip()
    if stripped.lower().startswith(CID_SCHEME):
        candidate = stripped[len(CID_SCHEME) :].strip().strip("\"'")
        if candidate:
            yield candidate
    for match in _CSS_URL_CID.finditer(value):
        candidate = match.group(1).strip()
        if candidate:
            yield candidate


def collect_cid_references(html: str) -> list[str]:
    """
    Every Content-ID the HTML references, deduped, in first-seen order.

    Finds both ``src="cid:X"`` style attributes and ``url(cid:X)`` inside a
    CSS value. The returned ids are **bare** — no ``cid:`` prefix, no angle
    brackets — matching :attr:`~svc.builder.images.ImageAsset.content_id`.
    """
    collector = _CidReferenceCollector()
    collector.feed(html)
    collector.close()
    return list(dict.fromkeys(collector.content_ids))


def _as_list(value: str | Sequence[str] | None) -> list[str]:
    """One address or many, normalised to a list with blanks dropped."""
    if value is None:
        return []
    items = [value] if isinstance(value, str) else list(value)
    return [item.strip() for item in items if item and item.strip()]


def _reject_control_chars(value: str, field: str) -> None:
    """
    Raise MessageError if `value` carries a CR or LF.

    Without this, a poisoned field (e.g. subject="a\\nBcc: x@evil.test")
    sails past the blankness check here and only fails later, at header
    assignment, as a bare ValueError from email.policy -- which a caller
    following exceptions.py's documented "catch DeliveryError" contract does
    not catch. Checking here, before any header is set, keeps every envelope
    rejection inside this module's own exception hierarchy.
    """
    if _CONTROL_CHARS.search(value):
        raise MessageError(f"{field} must not contain a line break: {value!r}")


def _verify_cid_manifest(html: str, assets: Sequence[ImageAsset]) -> None:
    """
    Check the builder's seam actually holds for this email.

    The contract is that for every ``src="cid:X"`` in the HTML there is an
    ``ImageAsset`` for ``X``. Until now that was documented but never
    verified; a mismatch either way is a bug worth failing on rather than
    mailing out.
    """
    referenced = set(collect_cid_references(html))
    attached = {asset.content_id for asset in assets}

    missing = sorted(referenced - attached)
    if missing:
        raise MessageError(
            f"the HTML references Content-IDs with nothing to attach: {', '.join(missing)}. "
            'Every src="cid:X" needs an ImageAsset for X in Email.assets() — a component '
            "carrying images must override images(), or its bytes never reach the manifest."
        )

    unreferenced = sorted(attached - referenced)
    if unreferenced:
        raise MessageError(
            "the asset manifest carries images the HTML never references: "
            f"{', '.join(unreferenced)}. Attaching them would add dead weight to the "
            "message, and it usually means a component reported an image it did not render."
        )


def build_message(
    email: RenderableEmail,
    *,
    subject: str,
    sender: str,
    to: str | Sequence[str],
    cc: str | Sequence[str] | None = None,
    reply_to: str | None = None,
) -> EmailMessage:
    """
    Assemble a built email into a sendable MIME message.

    Args:
        email:    Anything with ``render()`` and ``assets()`` — an ``Email``
            or an ``EmailBuilder``.
        subject:  Subject header. Required: the builder's ``email_subject``
            is not reachable from here (see issue #72), and the envelope is
            arguably the sender's business rather than the content's.
        sender:   ``From`` header.
        to:       One recipient address or a sequence of them.
        cc:       Optional carbon-copy recipients.
        reply_to: Optional ``Reply-To`` header.

    Returns:
        An :class:`~email.message.EmailMessage`: ``text/html`` when the email
        has no CID images, ``multipart/related`` when it does.

    Raises:
        MessageError: On a missing subject, sender or recipient; on a
            control character (CR or LF) in any envelope field; on an asset
            with an unusable MIME type; or when the HTML's ``cid:``
            references and the asset manifest disagree.
        EmailBuilderError: Propagated unchanged from ``render()`` — a build
            failure is not a delivery failure.

    Note:
        No ``Date`` or ``Message-ID`` is stamped, keeping assembly pure and
        deterministic; the transport adds them. ``Bcc`` is deliberately not
        accepted — a ``Bcc`` header travels with the message and leaks the
        blind-copy list, so blind copy is an envelope concern for adapters.

    Example::

        message = build_message(
            email, subject="Weekly Market Wrap",
            sender="research@example.com", to=["reader@example.com"],
        )
        save_eml(message, "output/preview.eml")
    """
    recipients = _as_list(to)
    cc_recipients = _as_list(cc)

    if not subject.strip():
        raise MessageError("subject is required: an outgoing message needs a Subject header.")
    if not sender.strip():
        raise MessageError("sender is required: an outgoing message needs a From header.")
    if not recipients:
        raise MessageError("at least one recipient is required in `to`.")

    _reject_control_chars(subject, "subject")
    _reject_control_chars(sender, "sender")
    for address in recipients:
        _reject_control_chars(address, "to")
    for address in cc_recipients:
        _reject_control_chars(address, "cc")
    if reply_to:
        _reject_control_chars(reply_to, "reply_to")

    html = email.render()
    assets = email.assets()
    _verify_cid_manifest(html, assets)

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    if cc_recipients:
        message["Cc"] = ", ".join(cc_recipients)
    if reply_to:
        message["Reply-To"] = reply_to

    message.set_content(html, subtype="html")

    if assets:
        # Promote the html part to multipart/related, then hang each image
        # off it. Only reached when there is something to relate to.
        message.make_related()
        for asset in assets:
            maintype, _, subtype = asset.mime_type.partition("/")
            if not maintype or not subtype:
                raise MessageError(
                    f"asset {asset.content_id!r} has an unusable MIME type "
                    f"{asset.mime_type!r}; expected 'type/subtype'."
                )
            message.add_related(
                asset.data,
                maintype=maintype,
                subtype=subtype,
                # Brackets are this consumer's job: ImageAsset.content_id is
                # bare, and add_related() stores whatever it is given, so a
                # bare id would emit an RFC-invalid Content-ID header.
                cid=f"<{asset.content_id}>",
                filename=asset.filename,
                # Without this, supplying a filename yields
                # Content-Disposition: attachment, and inline art shows up as
                # a paperclip instead of rendering in place.
                disposition="inline",
            )

    return message


def save_eml(message: EmailMessage, output_path: str | Path) -> Path:
    """
    Write an assembled message to a ``.eml`` file for inspection.

    The dry-run path: no transport, no credentials. The result opens in any
    mail client and round-trips through :func:`email.message_from_bytes`,
    which is how the CID seam is verified end to end.

    Args:
        message:     An assembled message from :func:`build_message`.
        output_path: Destination path; parent directories are created.

    Returns:
        The path written.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(message.as_bytes())
    return path
