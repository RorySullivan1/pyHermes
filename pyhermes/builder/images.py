"""
Image sources and embed strategies for HTML email.

An image carries two independent facts: **where the bytes live** (a URL, a
file, bytes in memory) and **how they reach the reader** (hosted, attached by
``cid:``, or inlined as a data URI). This module owns both.

The builder decides the strategy and emits the correct ``src``, but it cannot
*perform* a CID embed — attaching a MIME part is a transport act. So it
**declares**: :meth:`Email.assets` returns the manifest, and
:mod:`pyhermes.delivery` turns it into parts.

A component that carries images must declare them in ``IMAGE_FIELDS`` or by
overriding ``images()``, or the bytes never reach the manifest.
`.claude/rules/builder-architecture.md` carries the strategy table.
"""

from __future__ import annotations

import base64
import hashlib
import re
import struct
from dataclasses import dataclass, field
from pathlib import Path

from pyhermes.config import Config, get_config

from .enums import EmbedStrategy
from .exceptions import SizeError, SizeWarning, ValidationError, warn_caller

# ──────────────────────────────────────────────────────────────────────
# Format detection
# ──────────────────────────────────────────────────────────────────────

# Magic-byte signatures, checked instead of trusting a file extension: the
# extension is a claim by the caller, the bytes are the fact.
_SIGNATURES: tuple[tuple[bytes, str, str], ...] = (
    (b"\x89PNG\r\n\x1a\n", "image/png", ".png"),
    (b"\xff\xd8\xff", "image/jpeg", ".jpg"),
    (b"GIF87a", "image/gif", ".gif"),
    (b"GIF89a", "image/gif", ".gif"),
)

#: Formats mail clients render reliably. Keyed by MIME type -> extension.
SUPPORTED_IMAGE_TYPES: dict[str, str] = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
}

# A single inlined image may not exceed this, so that one image cannot eat
# the whole email.  The Gmail clipping limit is 102 KB for the *entire*
# rendered document (see Email._validate_size); base64 costs +33% on top of
# the raw bytes, so this cap keeps a single data URI under roughly half the
# budget and leaves room for the skeleton and the rest of the content.
#: The *default* per-image inline cap, kept as a name because tests build
#: payloads relative to it. Mirrors :class:`pyhermes.config.Config`'s default;
#: the value enforced is read from the active config at call time, so an
#: override installed via ``set_config`` is honoured.
INLINE_LIMIT_KB = Config().inline_image_limit_kb

# Safe as both a `cid:` URL and a MIME Content-ID token.
_CONTENT_ID_RE = re.compile(r"^[A-Za-z0-9._+-]{1,128}$")


def sniff_image_type(data: bytes) -> tuple[str, str]:
    """
    Identify image bytes by their magic-byte signature.

    Args:
        data: The raw image bytes.

    Returns:
        A ``(mime_type, extension)`` pair, e.g. ``("image/png", ".png")``.

    Raises:
        ValidationError: If the bytes are empty, or are not a PNG, JPEG or
            GIF.  WebP and SVG are detected specifically so the message can
            explain that no mail client renders them dependably (and that
            SVG can additionally carry script).
    """
    if not data:
        raise ValidationError("image data is empty; nothing to embed.")

    for signature, mime_type, extension in _SIGNATURES:
        if data.startswith(signature):
            return mime_type, extension

    # Recognised-but-unsupported, so the error can name the actual problem
    # rather than a generic "unknown format".
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        raise ValidationError(
            "WebP images are not supported: Outlook's Word rendering engine "
            "cannot display them. Convert to PNG or JPEG."
        )
    if data[:5].lower() == b"<?xml" or data[:4].lower() == b"<svg":
        raise ValidationError(
            "SVG images are not supported: mail clients do not render them "
            "dependably, and SVG can carry script. Rasterise to PNG."
        )

    raise ValidationError(
        f"Unrecognised image format (first bytes: {data[:8]!r}). "
        f"Supported: {', '.join(sorted(SUPPORTED_IMAGE_TYPES))}."
    )


def pixel_size(data: bytes) -> tuple[int, int] | None:
    """
    ``(width, height)`` in pixels, read from a PNG, JPEG or GIF header.

    ``None`` when the header does not say, such as a truncated file or a JPEG
    whose frame header is missing: a caller treats that as unknown, never as zero.
    """
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        return struct.unpack(">II", data[16:24])
    if data[:6] in (b"GIF87a", b"GIF89a") and len(data) >= 10:
        return struct.unpack("<HH", data[6:10])
    if data.startswith(b"\xff\xd8"):
        offset = 2
        while offset + 9 <= len(data) and data[offset] == 0xFF:
            marker = data[offset + 1]
            length = struct.unpack(">H", data[offset + 2 : offset + 4])[0]
            # SOF0..SOF15 carry the frame size; C4, C8 and CC are other tables.
            if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                height, width = struct.unpack(">HH", data[offset + 5 : offset + 9])
                return width, height
            offset += 2 + length
    return None


def _read_source(source: str | Path | bytes) -> tuple[bytes, str]:
    """
    Resolve an image source to ``(data, original_filename)``.

    ``bytes`` are taken as-is with no filename; a ``str``/``Path`` is read
    from disk.

    Raises:
        ValidationError: If the path does not exist or cannot be read.
    """
    if isinstance(source, bytes):
        return source, ""

    path = Path(source)
    try:
        return path.read_bytes(), path.name
    except OSError as exc:
        raise ValidationError(f"cannot read image file '{path}': {exc}") from exc


def _validate_content_id(value: str) -> None:
    """Raise if a Content-ID could not sit safely in a ``cid:`` URL."""
    if not _CONTENT_ID_RE.match(value):
        raise ValidationError(
            f"'content_id' must be 1-128 characters of [A-Za-z0-9._+-], got: {value!r}. "
            "The 'cid:' prefix (HTML) and the angle brackets (MIME header) are added by "
            "whichever consumer needs them. '@' and whitespace are not permitted at all: "
            "RFC 2392 makes a cid: URL the Content-ID with only its brackets stripped, so "
            "a qualified id would no longer match the reference the builder emits."
        )


# ──────────────────────────────────────────────────────────────────────
# The manifest entry
# ──────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ImageAsset:
    """
    One image the delivery layer must attach to the outgoing message.

    This is the builder's half of a CID embed: the HTML says
    ``src="cid:<content_id>"``, and this says what to attach under that ID.
    A delivery service turns it into a MIME part with
    ``Content-ID: <{content_id}>`` and ``Content-Disposition: inline``.

    Attributes:
        content_id: Bare Content-ID, *without* the angle brackets a MIME
            header needs and without the ``cid:`` prefix the HTML needs —
            each consumer adds its own.
        data:       The raw image bytes.
        mime_type:  Sniffed from the bytes, e.g. ``"image/png"``.
        filename:   Suggested attachment filename.
    """

    content_id: str
    data: bytes
    mime_type: str
    filename: str

    @property
    def size_kb(self) -> float:
        """Size of the attached bytes in kilobytes."""
        return len(self.data) / 1024


# ──────────────────────────────────────────────────────────────────────
# The image reference
# ──────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class EmailImage:
    """
    An image plus the strategy for getting it in front of the reader.

    Build one with :meth:`hosted`, :meth:`attached` or :meth:`inline` rather
    than the constructor — the factories read the file, sniff the format,
    derive the Content-ID, and make the valid field combinations unmissable.

    Validation runs at construction: by the time a component holds an
    ``EmailImage``, the bytes are read and the format is known good.

    Attributes:
        strategy:  How the bytes reach the reader.
        alt:       Alt text. Required — it is what the reader sees whenever
            images are blocked, which for Outlook desktop is the default.
        decorative: The image carries no information, so a screen reader
            should skip it. Emits ``alt=""`` — a positive assertion, not an
            absent attribute — and the only case where ``alt`` may be empty.
        url:       The hosted URL. ``REMOTE`` only.
        data:      The raw bytes. ``CID`` and ``DATA_URI`` only.
        mime_type: Sniffed from ``data``. ``CID`` and ``DATA_URI`` only.
        content_id: Bare Content-ID. ``CID`` only.
        filename:  Suggested attachment filename. ``CID`` only.
        width:     Display width in px, emitted as the ``width`` attribute
            because Outlook's Word engine ignores CSS ``max-width``. For a
            retina asset pass the *display* width, not the file's. ``None``
            renders full-width.
    """

    strategy: EmbedStrategy
    alt: str = ""
    decorative: bool = False
    url: str = ""
    data: bytes = b""
    mime_type: str = ""
    content_id: str = ""
    filename: str = ""
    width: int | None = field(default=None)

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------

    @classmethod
    def hosted(
        cls, url: str, alt: str = "", width: int | None = None, *, decorative: bool = False
    ) -> EmailImage:
        """
        Reference a publicly hosted image by URL.

        The default strategy, and the only one that costs nothing. The
        caller owns the host: this validates the URL's *scheme* only, not
        that it resolves.

        Args:
            url:   Absolute or relative image URL.
            alt:   Alt text; shown wherever images are blocked.
            width: Display width in px. ``None`` renders full-width.
            decorative: The image carries no information; emit ``alt=""``.

        Raises:
            ValidationError: On an empty/unsafe URL, or on alt text that is
                empty without ``decorative`` or supplied with it.
        """
        from .models import _validate_url  # local: models imports nothing from here

        if not url:
            raise ValidationError("EmailImage.hosted() requires a url.")
        _validate_url(url, "image.url")
        return cls(
            strategy=EmbedStrategy.REMOTE,
            alt=alt,
            decorative=decorative,
            url=url,
            width=_check_width(width),
        )

    @classmethod
    def attached(
        cls,
        source: str | Path | bytes,
        alt: str = "",
        width: int | None = None,
        content_id: str = "",
        filename: str = "",
        *,
        decorative: bool = False,
    ) -> EmailImage:
        """
        Embed by attaching the bytes as a MIME part, referenced by ``cid:``.

        The strategy that renders without the reader clicking anything. The
        bytes are read and sniffed now; the resulting :class:`ImageAsset`
        surfaces in the email's manifest for the delivery layer to attach.
        Costs message size but *not* HTML size, so it does not push the
        email toward Gmail's 102 KB clipping limit.

        Args:
            source:     Path to an image file, or raw image bytes.
            alt:        Alt text; shown until the image loads.
            width:      Display width in px. ``None`` renders full-width.
            content_id: Bare Content-ID. Defaults to a hash of the bytes,
                so the same image used twice is attached once.
            filename:   Attachment filename. Defaults to the source file's
                name, or ``<content_id><ext>`` for raw bytes.
            decorative: The image carries no information; emit ``alt=""``.

        Raises:
            ValidationError: On unreadable files, unsupported formats, an
                unsafe ``content_id``, or an alt/``decorative`` mismatch.
        """
        data, original_name = _read_source(source)
        mime_type, extension = sniff_image_type(data)

        # Content-addressed by default: identical bytes collapse to one
        # attachment, and the same input always yields the same output.
        resolved_id = content_id or hashlib.sha256(data).hexdigest()[:16]
        _validate_content_id(resolved_id)

        return cls(
            strategy=EmbedStrategy.CID,
            alt=alt,
            decorative=decorative,
            data=data,
            mime_type=mime_type,
            content_id=resolved_id,
            filename=filename or original_name or f"{resolved_id}{extension}",
            width=_check_width(width),
        )

    @classmethod
    def inline(
        cls,
        source: str | Path | bytes,
        alt: str = "",
        width: int | None = None,
        *,
        decorative: bool = False,
    ) -> EmailImage:
        """
        Inline the bytes as a base64 ``data:`` URI.

        **Gmail strips data URIs and Outlook's Word engine will not render
        them.** For browser preview or a known non-Gmail, non-Outlook-desktop
        channel — never a general default.

        Args:
            source: Path to an image file, or raw image bytes.
            alt:    Alt text; shown wherever the URI is stripped.
            width:  Display width in px. ``None`` renders full-width.
            decorative: Carries no information; emit ``alt=""``.

        Raises:
            ValidationError: On unreadable files or unsupported formats.
            SizeError: If the base64 payload exceeds
                :data:`INLINE_LIMIT_KB`, leaving too little of the budget.
        """
        data, _ = _read_source(source)
        mime_type, _ = sniff_image_type(data)

        # base64 encodes 3 bytes as 4 characters, rounded up to a 4-char
        # block — checked here so the failure names the image, rather than
        # surfacing later as a whole-email SizeError that doesn't.
        encoded_kb = (-(-len(data) // 3) * 4) / 1024
        config = get_config()
        limit_kb = config.inline_image_limit_kb
        if encoded_kb > limit_kb:
            raise SizeError(
                f"Inlined image is {encoded_kb:.1f} KB once base64-encoded, over the "
                f"{limit_kb} KB per-image cap (the whole email must stay under "
                f"{config.size_limit_kb} KB). Attach it instead with "
                "EmailImage.attached(), or host it."
            )

        return cls(
            strategy=EmbedStrategy.DATA_URI,
            alt=alt,
            decorative=decorative,
            data=data,
            mime_type=mime_type,
            width=_check_width(width),
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def __post_init__(self) -> None:
        if self.decorative and self.alt:
            raise ValidationError(
                f"a decorative image cannot also carry alt text, got: {self.alt!r}. "
                "Decorative means a screen reader should skip it; text means it has "
                "something to say. Drop one."
            )
        if not self.decorative and (not self.alt or not self.alt.strip()):
            raise ValidationError(
                "'image.alt' is required and cannot be empty: it is what the reader "
                "sees whenever images are blocked, which is Outlook's default. If the "
                "image is purely decorative, say so with decorative=True, which emits "
                'alt="" so a screen reader skips it.'
            )
        if self.strategy == EmbedStrategy.REMOTE:
            if not self.url:
                raise ValidationError("a REMOTE image requires a 'url'.")
        elif not self.data:
            raise ValidationError(f"a {self.strategy.upper()} image requires 'data'.")

        if self.strategy == EmbedStrategy.CID and not self.content_id:
            raise ValidationError("a CID image requires a 'content_id'.")
        self._check_weight()

    def _check_weight(self) -> None:
        """Warn when the bytes are far wider than the image is shown (#276); hosted is unread."""
        if not self.data or not self.width:
            return
        size = pixel_size(self.data)
        ratio = get_config().oversize_image_ratio
        if size is None or size[0] <= ratio * self.width:
            return
        name = self.alt or self.filename or "a decorative image"
        warn_caller(
            f"{name!r} is {size[0]}x{size[1]}px but shown {self.width}px wide, "
            f"{size[0] / self.width:.1f} times its display width. Export it at "
            f"{2 * self.width}px wide for a screen, or {round(3.125 * self.width)}px for "
            f"print at 300 dpi, to cut its weight. Config.oversize_image_ratio ({ratio:g}) "
            "sets this threshold.",
            SizeWarning,
        )

    # ------------------------------------------------------------------
    # Rendering / manifest
    # ------------------------------------------------------------------

    @property
    def src(self) -> str:
        """
        The value for the ``src`` attribute, per this image's strategy.

        Templates escape it on the way out, as they do every attribute.
        """
        if self.strategy == EmbedStrategy.REMOTE:
            return self.url
        if self.strategy == EmbedStrategy.CID:
            return f"cid:{self.content_id}"
        encoded = base64.b64encode(self.data).decode("ascii")
        return f"data:{self.mime_type};base64,{encoded}"

    @property
    def asset(self) -> ImageAsset | None:
        """
        The manifest entry for this image, or ``None`` if it needs none.

        Only ``CID`` images produce one: a remote image has no bytes to
        attach, and a data URI carries its own inside the HTML.
        """
        if self.strategy != EmbedStrategy.CID:
            return None
        return ImageAsset(
            content_id=self.content_id,
            data=self.data,
            mime_type=self.mime_type,
            filename=self.filename,
        )


def _displayed_height(data: bytes | None, width: int | None) -> int | None:
    """
    How tall ``width`` pixels of ``data`` render, or ``None`` if unknowable.

    Needed only where a box must be given a height rather than taking one
    from the image it contains — a CSS background, which is how a paged
    render draws a decorative image so the print engine marks it an artifact
    (#202). An ``img`` never needs this: it keeps its own aspect.

    ``None`` for a hosted image, whose bytes this package never sees, and for
    a header that does not say. The caller falls back to an ``img`` rather
    than guessing: a wrong height crops or letterboxes the mark, and a
    decorative rule that is visibly the wrong shape is worse than one a
    screen reader has to skip.
    """
    if not data or not width:
        return None
    size = pixel_size(data)
    if size is None:
        return None
    intrinsic_width, intrinsic_height = size
    if not intrinsic_width:
        return None
    return max(1, round(width * intrinsic_height / intrinsic_width))


def _check_width(width: int | None) -> int | None:
    """Raise if a display width is not a positive integer."""
    if width is None:
        return None
    if not isinstance(width, int) or isinstance(width, bool) or width <= 0:
        raise ValidationError(f"'image.width' must be a positive integer of pixels, got: {width!r}")
    return width


def coerce_image(
    value: str | EmailImage,
    alt: str,
    field_name: str,
    width: int | None = None,
    decorative: bool = False,
) -> EmailImage:
    """
    Accept either an :class:`EmailImage` or a bare URL string.

    Lets every image-taking API keep working with the plain URLs it took
    before this module existed, while accepting a full ``EmailImage``.

    Args:
        value:      An ``EmailImage``, or a URL string to wrap as ``REMOTE``.
        alt:        Alt text. Used only when wrapping a bare string — an
            ``EmailImage`` carries its own.
        field_name: Name used in the error message.
        width:      Display width in px. Used only when wrapping a bare
            string, for the same reason.
        decorative: Emit ``alt=""``. Bare-string only, for the same reason.

    Raises:
        ValidationError: If ``value`` is empty or of an unsupported type.
    """
    if isinstance(value, EmailImage):
        return value
    if isinstance(value, str):
        if not value:
            raise ValidationError(f"'{field_name}' is required and cannot be empty.")
        # Validated here as well as inside hosted(), so the message names the
        # field the caller actually passed rather than the generic 'image.url'.
        from .models import _validate_url

        _validate_url(value, field_name)
        return EmailImage.hosted(value, alt=alt, width=width, decorative=decorative)
    raise ValidationError(
        f"'{field_name}' must be a URL string or an EmailImage, got {type(value).__name__}."
    )


def dedupe_assets(assets: list[ImageAsset]) -> list[ImageAsset]:
    """
    Drop repeat Content-IDs, keeping first-seen order.

    The same image used in two sections should be attached once. Order is
    preserved so a rendered email and its manifest stay diffable.

    Raises:
        ValidationError: One Content-ID carries two different payloads, which
            would ship the first and show it at both references (#430).
    """
    seen: dict[str, ImageAsset] = {}
    for asset in assets:
        first = seen.setdefault(asset.content_id, asset)
        if first.data != asset.data:
            raise ValidationError(
                f"Content-ID {asset.content_id!r} names two different images "
                f"({first.filename!r} and {asset.filename!r}); give each its own content_id."
            )
    return list(seen.values())
