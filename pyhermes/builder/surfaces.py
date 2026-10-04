"""
Blocks that set content apart: a boxed block, a button, a rule (#265).

Each draws on a surface the theme owns, so a caller names a tone or nothing,
never a colour. `.claude/rules/design-axes.md` records why.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .components import CellShare, Component, CopyAlignment
from .engine import Renderer, cell_width_of, own_surface, rebind, respaced, scheme_of
from .exceptions import ValidationError
from .images import EmailImage
from .models import _validate_url
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
