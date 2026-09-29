"""
Transport-neutral MIME assembly for a built email.

The builder composes and *declares*; this module assembles.
:meth:`~pyhermes.builder.email.Email.render` gives the HTML and
:meth:`~pyhermes.builder.email.Email.assets` the manifest of images that HTML
references as ``cid:``. This turns that pair into an
:class:`~email.message.EmailMessage` an adapter can hand to a transport.

Nothing here authenticates, opens a socket, or reads the clock. The result is
**not** byte-identical between calls, because the stdlib generates a random
MIME boundary per part — normalise every one before comparing.

`.claude/rules/delivery.md` carries the part ordering and its reasons.
"""

from __future__ import annotations

import re
import warnings
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from email.message import EmailMessage
from html.parser import HTMLParser
from pathlib import Path
from typing import Protocol, cast

from pyhermes.builder.exceptions import SizeWarning, warn_caller
from pyhermes.builder.images import ImageAsset
from pyhermes.config import Config, config_override, get_config

from .exceptions import MessageError

__all__ = [
    "Attachment",
    "RenderableEmail",
    "build_message",
    "collect_cid_references",
    "save_eml",
    "to_wire_bytes",
]

CID_SCHEME = "cid:"

# A cid: reference inside a CSS url(), e.g.
# style="background-image:url(cid:abc)". Banner.background_image_url is
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

#: ``type/subtype``, each an RFC 2045 token: what a Content-Type can carry.
_MIME_TYPE = re.compile(r"[A-Za-z0-9!#$&^_.+-]+/[A-Za-z0-9!#$&^_.+-]+")


@dataclass(frozen=True)
class Attachment:
    """
    A file carried after the email, validated at construction.

    A sibling of :class:`~pyhermes.builder.images.ImageAsset`, and deliberately
    not the same class: an asset is referenced by ``cid:`` from inside the
    HTML and rendered in place, while an attachment is referenced by nothing
    and shown as a file. Sharing one type would let either be passed where
    the other belongs, and each would then be delivered wrong.

    ``size_hint`` is what the producer knows would make the file smaller.
    The size budget quotes it when a message is over, so the delivery layer
    can point at a remedy without knowing what made the bytes.
    """

    data: bytes
    filename: str
    mime_type: str
    size_hint: str = ""

    def __post_init__(self) -> None:
        if not self.data:
            raise MessageError(f"attachment data is empty for {self.filename!r}")
        name = self.filename
        if not name.strip() or name.strip() in {".", ".."}:
            raise MessageError(f"attachment filename must name a file, got {name!r}")
        if "/" in name or "\\" in name:
            raise MessageError(f"attachment filename must not contain a path separator: {name!r}")
        _reject_control_chars(name, "attachment filename")
        if not _MIME_TYPE.fullmatch(self.mime_type):
            raise MessageError(
                f"attachment mime_type must be 'type/subtype', got {self.mime_type!r} for {name!r}"
            )


class RenderableEmail(Protocol):
    """What assembly needs from the builder: the HTML, and the manifest.

    A structural type rather than a base class, so both
    :class:`~pyhermes.builder.email.Email` and
    :class:`~pyhermes.builder.email.EmailBuilder` satisfy it as they are — the
    delivery layer never imports or subclasses builder classes.
    """

    def render(self) -> str: ...

    def text(self) -> str: ...

    def assets(self) -> list[ImageAsset]: ...


class _CidReferenceCollector(HTMLParser):
    """Collects every ``cid:`` reference in a fetching tag attribute, a
    ``<style>`` block's text, or markup hidden inside a comment.

    A bare ``HTMLParser`` only calls ``handle_starttag`` -- it treats
    ``<style>`` content as opaque CDATA text and a ``<!--...-->`` comment as
    opaque too. Both carry real ``cid:`` references in this codebase: the
    header background can be styled via a ``<style>`` rule, and Outlook's
    VML fill (``<v:fill src="cid:X"/>``) only renders inside an
    ``<!--[if mso]>...<![endif]-->`` conditional comment.
    """

    _CDATA_TAGS = frozenset({"style", "script"})

    # Positive allowlist of attributes that actually make a client *fetch*
    # a resource -- the ones a real cid: reference can live in. Everything
    # else (alt, title, aria-label, ...) is caller-supplied prose that a
    # denylist would just be a standing promise to keep enumerating; a
    # "cid:"-looking string there is not a reference, it is text. `style`
    # is included for its CSS `url(cid:X)` form, `xlink:href` for SVG/VML
    # <use>-style references, and `background`/`poster` for the legacy HTML
    # attributes email clients (notably Outlook) still honour.
    _FETCHING_ATTRS = frozenset(
        {"src", "href", "xlink:href", "background", "poster", "srcset", "style"}
    )

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.content_ids: list[str] = []
        self._cdata_tag: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if value and name in self._FETCHING_ATTRS:
                self.content_ids.extend(_cids_in(value))
        if tag in self._CDATA_TAGS:
            self._cdata_tag = tag

    def handle_endtag(self, tag: str) -> None:
        if tag == self._cdata_tag:
            self._cdata_tag = None

    def handle_data(self, data: str) -> None:
        # Only <style>/<script> text is CSS/JS rather than prose; scanning
        # it with the same CSS url() regex used on attribute values is
        # "parse, don't grep" for structure -- the parser already told us
        # this span is CDATA, so all that's left is a CSS-value scan.
        if self._cdata_tag:
            for match in _CSS_URL_CID.finditer(data):
                candidate = match.group(1).strip()
                if candidate:
                    self.content_ids.append(candidate)

    def handle_comment(self, data: str) -> None:
        # A conditional comment's interior is real markup a client parses
        # (e.g. Outlook's VML), not prose -- hand it back through a fresh
        # instance of this same parser rather than grepping the raw text.
        nested = _CidReferenceCollector()
        nested.feed(data)
        nested.close()
        self.content_ids.extend(nested.content_ids)


def _cids_in(value: str) -> Iterator[str]:
    """Every Content-ID referenced by one attribute value.

    Handles a plain ``cid:X`` value, ``url(cid:X)`` inside a CSS value, and
    the ``srcset`` grammar -- a comma-separated list of ``<url>
    <descriptor>?`` candidates (e.g. ``srcset="cid:a 1x, cid:b 2x"``), where
    only the leading url token of each candidate is a candidate id. Handling
    the grammar generically means a plain single-value attribute (no comma)
    falls out as the one-candidate case, with nothing attribute-name-specific.
    """
    for candidate in value.split(","):
        candidate = candidate.strip()
        if not candidate:
            continue
        url = candidate.split(maxsplit=1)[0]
        if url.lower().startswith(CID_SCHEME):
            content_id = url[len(CID_SCHEME) :].strip("\"'")
            if content_id:
                yield content_id
    for match in _CSS_URL_CID.finditer(value):
        content_id = match.group(1).strip()
        if content_id:
            yield content_id


def collect_cid_references(html: str) -> list[str]:
    """
    Every Content-ID the HTML references, deduped, in first-seen order.

    Finds both ``src="cid:X"`` style attributes and ``url(cid:X)`` inside a
    CSS value. The returned ids are **bare** — no ``cid:`` prefix, no angle
    brackets — matching :attr:`~pyhermes.builder.images.ImageAsset.content_id`.
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


def _subject_from(email: RenderableEmail) -> str:
    """
    The email's own subject, when it exposes readable metadata.

    Duck-typed rather than declared on :class:`RenderableEmail`, because
    ``EmailBuilder`` already uses ``metadata`` as a fluent *setter* method —
    putting it in the protocol would make a perfectly valid input stop
    satisfying it. An unbuilt builder therefore falls through to "subject is
    required", which is the honest answer.
    """
    subject = getattr(getattr(email, "metadata", None), "email_subject", None)
    return subject if isinstance(subject, str) else ""


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
    ``ImageAsset`` for ``X``. The two directions are not equally severe,
    though: a reference with nothing to attach is a broken image the
    reader will actually see, so it stays fatal. An attached-but-unreferenced
    asset only costs message weight -- and treating it as fatal would turn
    any gap in the collector above (there will always be markup shapes it
    doesn't know about yet) into a false rejection of a valid email, so it
    is a warning rather than a raise.
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
        warnings.warn(
            "the asset manifest carries images the HTML never references: "
            f"{', '.join(unreferenced)}. Attaching them adds dead weight to the message, "
            "and it usually means a component reported an image it did not render.",
            UserWarning,
            stacklevel=3,
        )


def build_message(
    email: RenderableEmail,
    *,
    subject: str | None = None,
    sender: str,
    to: str | Sequence[str],
    cc: str | Sequence[str] | None = None,
    reply_to: str | None = None,
    attachments: Sequence[Attachment] = (),
    config: Config | None = None,
) -> EmailMessage:
    """
    Assemble a built email into a sendable MIME message.

    Args:
        email:    Anything with ``render()`` and ``assets()``.
        subject:  ``Subject``. Omitted, falls back to the email's own
            ``email_subject``, which ``validate()`` already requires.
        sender:   ``From`` header.
        to:       One recipient address or a sequence of them.
        cc:       Optional carbon-copy recipients.
        reply_to: Optional ``Reply-To`` header.
        attachments: Files carried after the email, each an :class:`Attachment`.
        config:   Limits for this message alone, in force while it renders the
            email and checks the budget; ``None`` reads the ambient one.

    Returns:
        A ``multipart/alternative``, its HTML ``multipart/related`` with CID
        images, inside a ``multipart/mixed`` when there are attachments.

    Raises:
        MessageError: On a missing subject, sender or recipient; a control
            character in an envelope field; an asset with an unusable MIME
            type; ``cid:`` references disagreeing with the manifest.
        EmailBuilderError: Propagated unchanged.

    ``Bcc`` is deliberately not accepted; see the module docstring.
    """
    if config is not None:
        with config_override(config):
            return build_message(
                email,
                subject=subject,
                sender=sender,
                to=to,
                cc=cc,
                reply_to=reply_to,
                attachments=attachments,
            )
    recipients = _as_list(to)
    cc_recipients = _as_list(cc)
    # An explicit subject always wins; only its absence consults the email.
    # `subject=""` is therefore still an error rather than a silent fallback,
    # because a caller who passed something meant it.
    resolved_subject = subject if subject is not None else _subject_from(email)

    if not resolved_subject.strip():
        raise MessageError(
            "subject is required: pass subject=, or build from an Email whose metadata "
            "carries email_subject (an EmailBuilder must be .build()-ed first)."
        )
    if not sender.strip():
        raise MessageError("sender is required: an outgoing message needs a From header.")
    if not recipients:
        raise MessageError("at least one recipient is required in `to`.")

    _reject_control_chars(resolved_subject, "subject")
    _reject_control_chars(sender, "sender")
    for address in recipients:
        _reject_control_chars(address, "to")
    for address in cc_recipients:
        _reject_control_chars(address, "cc")
    if reply_to:
        _reject_control_chars(reply_to, "reply_to")

    html = email.render()
    text = email.text()
    assets = email.assets()
    # Scoped to the HTML deliberately: the text part carries URLs as text and
    # never a cid: reference, so a plain-text body that happens to mention
    # "cid:" -- documentation copy, say -- must not be read as one.
    _verify_cid_manifest(html, assets)

    message = EmailMessage()
    message["Subject"] = resolved_subject
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    if cc_recipients:
        message["Cc"] = ", ".join(cc_recipients)
    if reply_to:
        message["Reply-To"] = reply_to

    # Text first, HTML second: RFC 2046 §5.1.4 orders an alternative's parts
    # by *increasing* preference. Reversing these two is a silent bug -- every
    # graphical client still shows the HTML, and only the readers who need the
    # fallback ever see the wrong thing.
    message.set_content(text)
    message.add_alternative(html, subtype="html")

    if assets:
        # Promote the *html* part to multipart/related and hang each image off
        # it -- not the top-level message, which is now the alternative. The
        # images are resources of the HTML alternative specifically; relating
        # them to the alternative would attach them to the text part as well,
        # which is both wrong and how a text-only reader ends up with a
        # paperclip for art they cannot see.
        # ``get_payload()`` is typed as the union of every payload shape a
        # legacy ``Message`` can hold — a string for a leaf part, a list for
        # a multipart. This message is the multipart ``add_alternative()``
        # just made three lines up, and its last part is the HTML: a stdlib
        # invariant a type checker has no way to see.
        html_part = cast(list[EmailMessage], message.get_payload())[-1]
        html_part.make_related()
        # RFC 2387 requires 'type' to name the root part's media type, so a
        # strict client knows text/html is the thing to render and the
        # image/* parts are its resources. make_related() does not set this
        # on its own -- without it, a client with no other way to pick a
        # root part can fall back to listing every part as an attachment,
        # which is the exact paperclip failure disposition="inline" below
        # exists to avoid.
        html_part.set_param("type", "text/html")
        for asset in assets:
            maintype, _, subtype = asset.mime_type.partition("/")
            if not maintype or not subtype:
                raise MessageError(
                    f"asset {asset.content_id!r} has an unusable MIME type "
                    f"{asset.mime_type!r}; expected 'type/subtype'."
                )
            html_part.add_related(
                asset.data,
                maintype=maintype,
                subtype=subtype,
                # Brackets are this consumer's job -- ImageAsset.content_id is
                # bare and add_related() stores what it is given -- but the id
                # is deliberately NOT qualified with "@domain": the builder has
                # already written src="cid:<bare-id>" into the HTML, so
                # qualifying only the header would break every embedded image.
                cid=f"<{asset.content_id}>",
                filename=asset.filename,
                # Without this, supplying a filename yields
                # Content-Disposition: attachment, and inline art shows up as
                # a paperclip instead of rendering in place.
                disposition="inline",
            )

    _attach(message, attachments)
    if attachments:
        _check_attachment_budget(message, attachments)
    return message


def _attach(message: EmailMessage, attachments: Sequence[Attachment]) -> None:
    """
    Carry each attachment after the email, in order, as a file.

    The first ``add_attachment`` makes the message ``multipart/mixed`` with
    the alternative as its first part, so the related subtree keeps its
    structure one level deeper. With none, the message is left untouched.
    """
    for attachment in attachments:
        if not isinstance(attachment, Attachment):
            raise MessageError(
                f"attachments must be Attachment instances, got {type(attachment).__name__}"
            )
        maintype, _, subtype = attachment.mime_type.partition("/")
        message.add_attachment(
            attachment.data, maintype=maintype, subtype=subtype, filename=attachment.filename
        )


def _check_attachment_budget(message: EmailMessage, attachments: Sequence[Attachment]) -> None:
    """
    Refuse a message a mail server would refuse, and warn short of it.

    Measured over the encoded wire bytes, since that is what a server counts:
    base64 makes a 16 MB file a 22 MB message. Both thresholds come from the
    active :class:`~pyhermes.config.Config`. The 102 KB check is a separate fact
    about the HTML part and Gmail's clipping, and this one leaves it alone.
    """
    config = get_config()
    size_kb = len(to_wire_bytes(message)) / 1024
    if size_kb > config.attachment_limit_kb:
        files = "; ".join(
            f"{a.filename} is {len(a.data) / 1024:,.1f} KB"
            + (f" ({a.size_hint})" if a.size_hint else "")
            for a in attachments
        )
        raise MessageError(
            f"the message is {size_kb:,.1f} KB on the wire, over the "
            f"{config.attachment_limit_kb:,} KB attachment limit that mail servers "
            f"enforce: {files}."
        )
    if size_kb > config.attachment_warn_kb:
        warn_caller(
            f"Message size {size_kb:,.1f} KB with attachments "
            f"(target < {config.attachment_warn_kb:,} KB)",
            SizeWarning,
        )


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
    path.write_bytes(to_wire_bytes(message))
    return path


def to_wire_bytes(message: EmailMessage) -> bytes:
    """
    Serialise a message with RFC 5322 CRLF line endings.

    The default policy generates bare LF, which a strict client is entitled
    to reject even though the bytes round-trip fine through Python's own
    parser. Cloning the policy with ``linesep="\r\n"`` is what makes the
    generator normalise both headers and body content to CRLF --
    ``.as_bytes()`` otherwise leaves it as written.

    Every consumer that puts a message on the wire or on disk goes through
    here, so the ``.eml`` written by :func:`save_eml` for inspection is
    byte-identical to what an adapter transmits. That correspondence is what
    makes the dry run worth trusting.

    Args:
        message: An assembled message from :func:`build_message`.

    Returns:
        The serialised message, CRLF throughout.
    """
    return message.as_bytes(policy=message.policy.clone(linesep="\r\n"))
