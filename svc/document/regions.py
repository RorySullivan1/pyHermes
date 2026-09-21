"""
The regions a paged document has and an email never did.

A cover to open on, running margin boxes that repeat on every sheet, and a
back-matter page to close on. Each is an ordinary
:class:`~svc.builder.regions.Region`: it fills a named slot, presents facts
it is handed and cannot contradict one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

from svc.builder.exceptions import ValidationError
from svc.builder.models import _validate_align
from svc.builder.regions import BoxSurface, Region
from svc.builder.textgen import html_to_text, join_blocks, underline, wrap

if TYPE_CHECKING:  # pragma: no cover
    from svc.builder.images import EmailImage
    from svc.builder.theming import Theme

#: The ``@page`` margin boxes a running region may occupy. Closed, because a
#: name CSS does not define renders nothing and says nothing about why.
MARGIN_BOXES: tuple[str, ...] = (
    "top-left",
    "top-center",
    "top-right",
    "bottom-left",
    "bottom-center",
    "bottom-right",
)


@dataclass
class Cover(BoxSurface, Region):
    """
    The sheet a document opens on: its title, who wrote it, and when.

    The paged medium's masthead, and deliberately the same shape as
    :class:`~svc.builder.regions.Banner` rather than a second idea. ``title``
    and ``subtitle`` are free-form copy that **resolve to facts when unset**
    — ``firm_name`` and ``campaign_name`` — through the chain #91 built, and
    they resolve into keys of their own (``cover_title``, ``cover_subtitle``)
    because resolving in place would let a region shadow a fact. A test greps
    the template to keep it that way.

    Its box is :class:`~svc.builder.regions.BoxSurface`, the same three
    fields the email's two boxes take, so a caller learns one surface rather
    than a third.
    """

    CONTEXT_NAME: ClassVar[str] = "cover"
    SLOTS: ClassVar[tuple[str, ...]] = ("cover",)
    TEMPLATE_PATHS: ClassVar[dict[str, str]] = {"cover": "document/regions/cover.html"}
    IMAGE_FIELDS: ClassVar[tuple[str, ...]] = ("logo_url", "background_image_url")

    #: Logo width used when neither the cover nor the EmailImage sets one.
    DEFAULT_LOGO_WIDTH: ClassVar[int] = 140

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
            raise ValidationError(f"'cover.logo_width' must be positive, got: {self.logo_width}")

    def resolved_title(self, firm_name: str = "") -> str:
        """The cover's own headline, or the firm it comes from."""
        return self.title or firm_name

    def resolved_subtitle(self, campaign_name: str = "") -> str:
        """The cover's own standfirst, or the series it belongs to."""
        return self.subtitle or campaign_name

    def resolved_logo_alt(self, firm_name: str = "") -> str:
        """The logo's alt text, or the firm it depicts."""
        return self.logo_alt or firm_name

    def resolved_logo_width(self) -> int:
        """The logo's width, or this region's default."""
        return self.logo_width or self.DEFAULT_LOGO_WIDTH

    def context(self, facts: dict[str, Any]) -> dict[str, Any]:
        """The base context with the resolution chains applied; facts last."""
        firm_name = str(facts.get("firm_name", ""))
        campaign_name = str(facts.get("campaign_name", ""))
        resolved = {
            "cover_title": self.resolved_title(firm_name),
            "cover_subtitle": self.resolved_subtitle(campaign_name),
            "logo_alt": self.resolved_logo_alt(firm_name),
            "logo_width": self.resolved_logo_width(),
        }
        return {**super().context({}), **resolved, **facts}

    def theme_context(self, theme: Theme) -> dict[str, Any]:
        """The two colours the sheet draws, resolved under names of their own."""
        return {
            "cover_background": self.background_color or theme.palette.surface,
            "cover_text": self.text_color or theme.text.primary,
        }

    def _text(self, facts: dict[str, Any]) -> str:
        """
        The cover as plain text: the resolved headline, then the metadata.

        Read off the resolution chains rather than the fields, for
        ``Banner._text``'s reason — a document that renames itself says the
        new name in both projections.
        """
        meta = [str(facts.get(name, "")) for name in ("department", "date_range", "issue_label")]
        return join_blocks(
            underline(self.resolved_title(str(facts.get("firm_name", ""))), "="),
            wrap(
                "\n".join(
                    filter(
                        None,
                        [
                            self.resolved_subtitle(str(facts.get("campaign_name", ""))),
                            " · ".join(filter(None, meta)),
                        ],
                    )
                )
            ),
        )


@dataclass
class EmptyCover(Cover):
    """A document that opens straight into its body. Fills no slot."""

    TEMPLATE_PATHS: ClassVar[dict[str, str]] = {}


@dataclass
class RunningBox(Region):
    """
    Shared half of the two margin-box regions: where it sits and what it says.

    **These fill a slot inside the skeleton's ``style`` element, not its
    body.** A ``@page`` margin box is a CSS rule, so the region's template
    emits CSS — which is why every value it interpolates goes through
    ``css_string`` rather than ``escape_html``. The two are not
    interchangeable: HTML escaping inside a stylesheet would render the
    entities literally, and neither would stop a ``</style>`` closing the
    block early.

    ``label`` is presentation and falls back to a fact, resolving into
    ``running_label`` under the chain the cover and the masthead both use.
    """

    #: Which fact this region's label falls back to. Subclasses set it.
    LABEL_FACT: ClassVar[str] = "firm_name"

    #: Where in the page margin this box sits, by default.
    DEFAULT_BOX: ClassVar[str] = "top-left"

    label: str = ""
    box: str = ""
    show_page_number: bool = False

    def validate(self) -> None:
        super().validate()
        if self.box and self.box not in MARGIN_BOXES:
            raise ValidationError(
                f"'{self.CONTEXT_NAME}.box' must be one of {list(MARGIN_BOXES)}, got: {self.box!r}"
            )

    def resolved_box(self) -> str:
        """Where this box sits, or this region's default corner."""
        return self.box or self.DEFAULT_BOX

    def resolved_label(self, fact: str = "") -> str:
        """This box's own copy, or the fact it falls back to."""
        return self.label or fact

    def context(self, facts: dict[str, Any]) -> dict[str, Any]:
        """The base context with the box and the label resolved; facts last."""
        resolved = {
            "running_box": self.resolved_box(),
            "running_label": self.resolved_label(str(facts.get(self.LABEL_FACT, ""))),
        }
        return {**super().context({}), **resolved, **facts}

    def _text(self, facts: dict[str, Any]) -> str:
        """
        Nothing, deliberately.

        A running box is chrome: it repeats copy the cover already carries,
        and a page number counts sheets that plain text does not have. So the
        projection is empty **by decision** rather than by omission — which
        is why it is implemented rather than left to raise.
        """
        return ""


@dataclass
class RunningHeader(RunningBox):
    """The line repeated in the top margin of every sheet."""

    CONTEXT_NAME: ClassVar[str] = "running_header"
    SLOTS: ClassVar[tuple[str, ...]] = ("running_header",)
    TEMPLATE_PATHS: ClassVar[dict[str, str]] = {
        "running_header": "document/regions/running-box.html"
    }
    LABEL_FACT: ClassVar[str] = "campaign_name"
    DEFAULT_BOX: ClassVar[str] = "top-left"


@dataclass
class RunningFooter(RunningBox):
    """The line repeated in the bottom margin, usually carrying the folio."""

    CONTEXT_NAME: ClassVar[str] = "running_footer"
    SLOTS: ClassVar[tuple[str, ...]] = ("running_footer",)
    TEMPLATE_PATHS: ClassVar[dict[str, str]] = {
        "running_footer": "document/regions/running-box.html"
    }
    LABEL_FACT: ClassVar[str] = "firm_name"
    DEFAULT_BOX: ClassVar[str] = "bottom-center"

    show_page_number: bool = True


@dataclass
class EmptyRunningHeader(RunningHeader):
    """No line in the top margin. Fills no slot."""

    TEMPLATE_PATHS: ClassVar[dict[str, str]] = {}


@dataclass
class EmptyRunningFooter(RunningFooter):
    """No line in the bottom margin. Fills no slot."""

    TEMPLATE_PATHS: ClassVar[dict[str, str]] = {}


@dataclass
class BackMatter(Region):
    """
    The sheet a document closes on, carrying its disclosures.

    **The copy is a fact, not a field.** ``header_disclaimer`` already
    belongs to the document — #161 put it on ``DocumentMetadata`` for exactly
    this reason — so this region decides how the closing page presents it and
    owns none of the wording. That is also what keeps the blessed raw-HTML
    set closed at five: this adds no sixth surface, it gives an existing one
    a second place to render.

    Like every raw-HTML field here, it is emitted inside a ``div`` and never
    a ``p``, and escaping untrusted text in it is the caller's job.
    """

    CONTEXT_NAME: ClassVar[str] = "back_matter"
    SLOTS: ClassVar[tuple[str, ...]] = ("back_matter",)
    TEMPLATE_PATHS: ClassVar[dict[str, str]] = {"back_matter": "document/regions/back-matter.html"}

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
class EmptyBackMatter(BackMatter):
    """A document that ends with its last section. Fills no slot."""

    TEMPLATE_PATHS: ClassVar[dict[str, str]] = {}


__all__ = [
    "MARGIN_BOXES",
    "BackMatter",
    "Cover",
    "EmptyBackMatter",
    "EmptyCover",
    "EmptyRunningFooter",
    "EmptyRunningHeader",
    "RunningBox",
    "RunningFooter",
    "RunningHeader",
]
