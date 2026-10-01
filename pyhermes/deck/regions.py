"""
The slides a deck opens and closes on, as regions: the title slide and the disclosures.

Each is an ordinary :class:`~pyhermes.builder.regions.Region` with an ``Empty``
variant: it fills a named slot and presents facts it is handed. The deck
also hands each the sheet's bands, ``deck_box``, as the paged medium hands a
contents sheet its entries, so both draw the same frame as every slide.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

from pyhermes.builder.exceptions import ValidationError
from pyhermes.builder.models import _validate_align
from pyhermes.builder.regions import BoxSurface, Region
from pyhermes.builder.textgen import html_to_text, join_blocks, underline, wrap

if TYPE_CHECKING:  # pragma: no cover
    from pyhermes.builder.images import EmailImage
    from pyhermes.builder.theming import Theme


@dataclass
class TitleSlide(BoxSurface, Region):
    """
    The slide a deck opens on: what it is, who it is from, and when.

    The deck's counterpart to the paged ``Cover``, and the same shape: free
    copy that **resolves to facts when unset**, into keys of its own so a
    region never shadows a fact. The headline falls back to
    ``campaign_name`` and the line under it to ``firm_name``, because a deck
    is titled by its subject; ``department`` and ``date_range`` follow.
    """

    CONTEXT_NAME: ClassVar[str] = "title_slide"
    SLOTS: ClassVar[tuple[str, ...]] = ("title_slide",)
    TEMPLATE_PATHS: ClassVar[dict[str, str]] = {"title_slide": "deck/regions/title-slide.html"}
    IMAGE_FIELDS: ClassVar[tuple[str, ...]] = ("logo_url", "background_image_url")

    #: Logo width used when neither the slide nor the EmailImage sets one.
    DEFAULT_LOGO_WIDTH: ClassVar[int] = 160

    #: Left, unlike the cover's centre: the title slide's copy sits level with
    #: every slide's title after it.
    align: str = "left"
    title: str = ""
    subtitle: str = ""
    logo_url: str | EmailImage = ""
    logo_alt: str = ""
    logo_width: int | None = None
    background_image_url: str | EmailImage = ""

    def validate(self) -> None:
        super().validate()
        self.validate_box_surface(self.CONTEXT_NAME)
        if self.logo_width is not None and self.logo_width <= 0:
            raise ValidationError(
                f"'title_slide.logo_width' must be positive, got: {self.logo_width}"
            )

    def resolved_title(self, campaign_name: str = "") -> str:
        """The slide's own headline, or the deck's subject."""
        return self.title or campaign_name

    def resolved_subtitle(self, firm_name: str = "") -> str:
        """The line under the headline, or the firm the deck comes from."""
        return self.subtitle or firm_name

    def resolved_logo_alt(self, firm_name: str = "") -> str:
        """The logo's alt text, or the firm it depicts."""
        return self.logo_alt or firm_name

    def context(self, facts: dict[str, Any]) -> dict[str, Any]:
        """The base context with the resolution chains applied; facts last."""
        firm_name = str(facts.get("firm_name", ""))
        resolved = {
            "headline": self.resolved_title(str(facts.get("campaign_name", ""))),
            "standfirst": self.resolved_subtitle(firm_name),
            "resolved_logo_alt": self.resolved_logo_alt(firm_name),
            "resolved_logo_width": self.logo_width or self.DEFAULT_LOGO_WIDTH,
        }
        return {**super().context({}), **resolved, **facts}

    def theme_context(self, theme: Theme) -> dict[str, Any]:
        """The sheet's two colours, resolved under names of their own."""
        return {
            "title_slide_background": self.background_color or theme.palette.surface,
            "title_slide_text": self.text_color or theme.text.heading,
        }

    def _text(self, facts: dict[str, Any]) -> str:
        """The resolved headline, then the line under it and the meta line."""
        meta = " · ".join(
            filter(None, (str(facts.get(n, "")) for n in ("department", "date_range")))
        )
        return join_blocks(
            underline(self.resolved_title(str(facts.get("campaign_name", ""))), "="),
            wrap(
                "\n".join(
                    filter(None, [self.resolved_subtitle(str(facts.get("firm_name", ""))), meta])
                )
            ),
        )


@dataclass
class EmptyTitleSlide(TitleSlide):
    """A deck that opens straight on its first slide. Fills no slot."""

    TEMPLATE_PATHS: ClassVar[dict[str, str]] = {}


@dataclass
class ClosingSlide(Region):
    """
    The slide a deck closes on, carrying its disclosures.

    ``BackMatter``'s terms exactly: the copy is ``header_disclaimer``, a fact
    the document owns, so this region decides only how the last slide
    presents it and the raw-HTML set stays closed at five.
    """

    CONTEXT_NAME: ClassVar[str] = "closing_slide"
    SLOTS: ClassVar[tuple[str, ...]] = ("closing_slide",)
    TEMPLATE_PATHS: ClassVar[dict[str, str]] = {"closing_slide": "deck/regions/closing-slide.html"}

    heading: str = "Disclosures"
    align: str = ""

    def validate(self) -> None:
        super().validate()
        _validate_align(self.align or "", f"{self.CONTEXT_NAME}.align")

    def _text(self, facts: dict[str, Any]) -> str:
        """The heading, then the disclosure copy degraded from its HTML."""
        return join_blocks(
            underline(self.heading or ""),
            wrap(html_to_text(str(facts.get("header_disclaimer", "")))),
        )


@dataclass
class EmptyClosingSlide(ClosingSlide):
    """A deck that ends on its last slide. Fills no slot."""

    TEMPLATE_PATHS: ClassVar[dict[str, str]] = {}


__all__ = ["ClosingSlide", "EmptyClosingSlide", "EmptyTitleSlide", "TitleSlide"]
