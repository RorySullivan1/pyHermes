"""
Blocks that set content apart: a boxed block, a button, a rule (#265), a row of tags (#327),
an aside the prose wraps round on paper (#343), and a QR code back to the web (#344).

Each draws on a surface the theme owns, so a caller names a tone or nothing,
never a colour. `.claude/rules/design-axes.md` records why.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .apparatus import CITATION, MARKER
from .components import CellShare, Component, CopyAlignment, TextBlock
from .engine import Renderer, cell_width_of, own_surface, rebind, respaced, scheme_of
from .enums import EmbedStrategy
from .exceptions import ValidationError
from .filters import escape_html
from .images import EmailImage
from .medium import PAGED_MEDIA, walking_medium
from .models import Badge, _validate_url
from .sizing import Spacing
from .textgen import LINE_WIDTH, link_line, wrap

#: The semantic tones a callout may take; ``None`` is the highlight tint.
TONES = ("positive", "negative", "neutral")

_RULE = "-" * LINE_WIDTH


class Callout(CellShare, Component):
    """
    One block boxed inside a section: a key takeaway, what changed, a risk note.

    The box is a table cell, so its padding survives Outlook's Word engine,
    where a ``div``'s does not. Its fill is the theme's highlight tint, or a
    light tint of a semantic colour when a ``tone`` is named, and its frame is
    the theme's rule or that colour. It paints its own surface, so on a
    section's dark ground the block inside keeps the theme's dark type.

    Args:
        content: The block to box; any component, a ``Stack`` included.
        tone:    ``"positive"``, ``"negative"`` or ``"neutral"``; unset for the highlight tint.
        label:   A small heading above the block, such as "Key takeaway".
        border:  Whether the box is framed.
        spacing: Moves ``callout_pad_y`` and ``callout_pad_x``, the box's padding, and
                 ``caption_gap``, the space under the label.
        width:   A share of the cell, 0.3 to 1.0, placed by the section's align (#357).
    """

    OWN_SURFACE = True

    template_path = "text/callout.html"

    SPACING_TOKENS = ("callout_pad_y", "callout_pad_x", "caption_gap")

    def __init__(
        self,
        content: Component,
        tone: str | None = None,
        label: str | None = None,
        border: bool = True,
        spacing: Spacing | Mapping[str, int | float] | None = None,
        *,
        width: float | None = None,
    ):
        self.spacing = self._coerce_spacing(spacing)
        self.width = self.validate_share(width)
        if not isinstance(content, Component):
            raise ValidationError(
                f"Callout holds one component, got {type(content).__name__}. "
                "Put several in a Stack."
            )
        if tone is not None and tone not in TONES:
            raise ValidationError(f"Callout tone must be one of {TONES} or None, got: {tone!r}")
        self.content = content
        self.tone = tone
        self.label = label
        self.border = border

    def children(self) -> list[Component]:
        return [self.content]

    def images(self) -> list[EmailImage]:
        return self.content.images()

    def text(self) -> str:
        """The label and the block between two rules, so the text part keeps the emphasis."""
        label = wrap(self.label.upper()) if self.label else ""
        return self._with_subtitle(_RULE, label, self.content.text(), _RULE)

    def context(self) -> dict[str, Any]:
        raise NotImplementedError("Callout renders its block first; see render().")

    def _fill(self, engine: Renderer) -> str:
        engine = respaced(own_surface(engine), self.spacing, type(self).__name__)
        component = scheme_of(engine).component
        inset = 2 * component.callout_pad_x + (2 if self.border else 0)
        inner = rebind(engine, cell_width=int(cell_width_of(engine) - inset))
        context = {
            "content": self.content.render(inner),
            "label": self.label or "",
            "tone": self.tone or "",
            "border": self.border,
        }
        return engine.render(self.template_path, context)


class Button(CopyAlignment, Component):
    """
    A call-to-action button on its own, anywhere a block goes.

    The same Outlook ``v:roundrect`` and styled link ``ContactBlock`` draws,
    from one shared partial, in the theme's accent and at the scheme's
    ``cta_width`` and ``cta_height``. The URL passes the scheme check.

    Args:
        label:   The button's words, plain text.
        url:     Where it goes: ``http``, ``https``, ``mailto`` or relative.
        align:   ``left``, ``center`` or ``right``; unset inherits the section's.
        spacing: Takes no token: the button has no spacing of its own.
    """

    template_path = "text/button.html"

    def __init__(
        self,
        label: str,
        url: str,
        align: str | None = None,
        spacing: Spacing | Mapping[str, int | float] | None = None,
    ):
        self.spacing = self._coerce_spacing(spacing)
        if not label:
            raise ValidationError("Button requires a label.")
        if not url:
            raise ValidationError("Button requires a url.")
        _validate_url(url, "Button.url")
        self.label = label
        self.url = url
        self.align = self.validate_alignment(align)

    def text(self) -> str:
        return self._with_subtitle(wrap(link_line(self.label, self.url)))

    def context(self) -> dict[str, Any]:
        return {"button_label": self.label, "button_url": self.url, **self.alignment_context()}


class Divider(Component):
    """
    A horizontal rule between blocks, in the theme's rule colour.

    A bordered cell rather than an ``hr``, which Outlook draws at its own
    weight and colour. ``block_gap`` above and below it.

    Args:
        spacing: Moves ``block_gap``, the space either side of the rule.
    """

    template_path = "text/divider.html"

    SPACING_TOKENS = ("block_gap",)

    def __init__(self, spacing: Spacing | Mapping[str, int | float] | None = None):
        self.spacing = self._coerce_spacing(spacing)

    def text(self) -> str:
        return self._with_subtitle(_RULE)

    def context(self) -> dict[str, Any]:
        return {}


class TagRow(Component):
    """
    Two to twelve neutral tags along one line, wrapping: *Rates · Credit · FX* (#327).

    Each tag is a :class:`~pyhermes.builder.models.Badge` in the neutral tone,
    drawn by the badge partial, so a tag and a badge cannot drift. The row is
    a run of inline elements, so it wraps on a phone and on paper without a
    stacking rule. A tag labels; it does not link.

    Args:
        tags:    The labels, plain text, each within ``Config.badge_max_chars``.
        spacing: Moves ``badge_pad_y`` and ``badge_pad_x``, inside each tag, and
                 ``caption_gap``, between tags and between wrapped lines.
    """

    template_path = "text/tag-row.html"

    SPACING_TOKENS = ("badge_pad_y", "badge_pad_x", "caption_gap")

    #: The fewest and the most tags a row takes.
    BOUNDS = (2, 12)

    def __init__(self, tags: list[str], spacing: Spacing | Mapping[str, int | float] | None = None):
        self.spacing = self._coerce_spacing(spacing)
        low, high = self.BOUNDS
        if not isinstance(tags, (list, tuple)) or not low <= len(tags) <= high:
            count = len(tags) if isinstance(tags, (list, tuple)) else type(tags).__name__
            raise ValidationError(f"TagRow takes {low} to {high} tags, got: {count}")
        self.tags = [Badge(tag) for tag in tags]
        for index, tag in enumerate(self.tags):
            tag.validate(f"tag_row.tags[{index}]")

    def text(self) -> str:
        return self._with_subtitle(wrap("Tags: " + ", ".join(tag.label for tag in self.tags)))

    def context(self) -> dict[str, Any]:
        return {"tags": [tag.drawn() for tag in self.tags]}


#: The sides an aside floats to on paper.
ASIDE_SIDES = ("left", "right")


@dataclass(frozen=True)
class Aside:
    """
    A boxout the prose wraps round on paper (#343): a definition, a key number, a method note.

    A second kind of float a :class:`~pyhermes.builder.components.TextBlock`
    hosts, beside ``figure``, not a new layout model: on paper it floats to
    ``side`` at about a third of the column, and in an email it is the same
    :class:`Callout` set above the prose, its stated degradation. Its copy is
    plain text, escaped, so the raw-HTML set stays at five; and it is
    unnumbered, so a note or a citation in it is refused, as a hosted figure's
    are: the document numbers what it walks, and it walks the text block.

    Args:
        body:  The aside's copy, plain text.
        title: A small heading above it, the callout's label.
        side:  ``"left"`` or ``"right"``, where it floats on paper.
        tone:  ``"positive"``, ``"negative"`` or ``"neutral"``; unset for the highlight tint.
    """

    body: str
    title: str | None = None
    side: str = "right"
    tone: str | None = None
    callout: Callout = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.body, str) or not self.body.strip():
            raise ValidationError("an Aside requires a body of plain text")
        if self.side not in ASIDE_SIDES:
            raise ValidationError(
                f"an Aside's side must be one of {ASIDE_SIDES}, got: {self.side!r}"
            )
        if MARKER.search(self.body) or CITATION.search(self.body):
            raise ValidationError(
                "an Aside cannot call a note or cite: the document numbers what it walks, "
                "and it walks the text block that hosts the aside, not the aside"
            )
        boxed = TextBlock(f"<p>{escape_html(self.body)}</p>")
        object.__setattr__(self, "callout", Callout(boxed, tone=self.tone, label=self.title))

    def render(self, engine: Renderer, width: int) -> str:
        """The callout, laid out for a column ``width`` px wide."""
        return self.callout.render(rebind(engine, cell_width=width))

    def text(self) -> str:
        """The title and body between two rules, the callout's own projection."""
        return self.callout.text()


#: A QR code's printed size by default: one inch, which a phone reads at arm's length.
QR_SIZE = 96

#: The smallest a code may print, three quarters of an inch.
QR_MIN_SIZE = 72

#: What the email's button says when the code has no caption.
QR_LABEL = "View online"


def check_qr_url(url: str) -> None:
    """
    Raise unless ``url`` is one a phone can open from a printed code.

    Raises:
        ValidationError: On a scheme the builder refuses, or a relative or ``cid:`` URL.
    """
    _validate_url(url, "QrCode.url")
    if not url.lower().startswith(("http://", "https://", "mailto:")):
        raise ValidationError(
            f"a QrCode encodes an http, https or mailto URL a phone can open, got: {url!r}"
        )


class QrCode(CopyAlignment, Component):
    """
    A way back from paper to the web (#344): a printed QR code and the URL it encodes.

    **The component takes bytes; the ``[qr]`` extra renders them**, as
    ``MathBlock`` takes an equation's (`math.md`), so the builder imports no
    backend: ``pyhermes.qr.qr_code(url)`` makes one. On paper it prints the
    image at ``size`` px, with the caption and the URL beneath. In an email
    the reader is already online, so it draws the link as a :class:`Button`
    instead, and no image reaches the manifest.

    Args:
        image:   The code as PNG bytes, or an attached ``EmailImage``.
        url:     What it encodes: an ``http``, ``https`` or ``mailto`` URL.
        caption: A line beneath the code, and the email's button label.
        size:    The printed width in px, at least :data:`QR_MIN_SIZE`.
        align:   ``left``, ``center`` or ``right``; unset inherits the section's.
        spacing: Moves ``caption_gap``, the space under the code on paper.
    """

    template_path = "media/qr-code.html"

    SPACING_TOKENS = ("caption_gap",)

    def __init__(
        self,
        image: bytes | EmailImage,
        url: str,
        caption: str | None = None,
        *,
        size: int = QR_SIZE,
        align: str | None = None,
        spacing: Spacing | Mapping[str, int | float] | None = None,
    ):
        self.spacing = self._coerce_spacing(spacing)
        check_qr_url(url)
        if isinstance(size, bool) or not isinstance(size, int) or size < QR_MIN_SIZE:
            raise ValidationError(
                f"a QrCode prints at least {QR_MIN_SIZE}px wide to scan, got: {size!r}"
            )
        alt = f"QR code for {url}"
        if isinstance(image, bytes):
            image = EmailImage.attached(image, alt=alt, width=size)
        if not isinstance(image, EmailImage):
            raise ValidationError(
                f"QrCode.image takes PNG bytes or an EmailImage, got: {type(image).__name__}"
            )
        if image.strategy is EmbedStrategy.REMOTE:
            raise ValidationError(
                "a QrCode's image is hosted, and the PDF exporter fetches nothing: "
                "pass its bytes, or attach it with EmailImage.attached()"
            )
        self.image = image
        self.url = url
        self.caption = caption
        self.size = size
        self.align = self.validate_alignment(align)

    def button(self) -> Button:
        """The email's form: the link as a button, labelled by the caption."""
        return Button(self.caption or QR_LABEL, self.url, align=self.align)

    def images(self) -> list[EmailImage]:
        """The code, except in a walk for a medium that prints none (standing rule 7)."""
        medium = walking_medium()
        return [self.image] if medium is None or medium in PAGED_MEDIA else []

    def render(self, engine: Renderer) -> str:
        """The code at its printed size on paper; :meth:`button` anywhere else."""
        if not engine.medium.paged:
            return self.button().render(engine)
        return super().render(engine)

    def text(self) -> str:
        """The URL, behind the caption when there is one."""
        line = link_line(self.caption, self.url) if self.caption else self.url
        return self._with_subtitle(wrap(line))

    def context(self) -> dict[str, Any]:
        return {
            "image_src": self.image.src,
            "image_alt": self.image.alt,
            "qr_size": self.size,
            "url": self.url,
            "caption": self.caption or "",
            **self.alignment_context(),
        }
