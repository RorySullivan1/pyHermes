"""
The regions a paged document has and an email never did.

A cover to open on, running margin boxes that repeat on every sheet, and a
back-matter page to close on. Each is an ordinary
:class:`~pyhermes.builder.regions.Region`: it fills a named slot, presents facts
it is handed and cannot contradict one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

from pyhermes.builder.components import check_listing
from pyhermes.builder.exceptions import ValidationError
from pyhermes.builder.models import _validate_align
from pyhermes.builder.regions import BoxSurface, Region
from pyhermes.builder.textgen import html_to_text, join_blocks, underline, wrap

if TYPE_CHECKING:  # pragma: no cover
    from pyhermes.builder.images import EmailImage
    from pyhermes.builder.theming import Theme

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
    :class:`~pyhermes.builder.regions.Banner` rather than a second idea. ``title``
    and ``subtitle`` are free-form copy that **resolve to facts when unset**
    — ``firm_name`` and ``campaign_name`` — through the chain #91 built, and
    they resolve into keys of their own (``cover_title``, ``cover_subtitle``)
    because resolving in place would let a region shadow a fact. A test greps
    the template to keep it that way.

    Its box is :class:`~pyhermes.builder.regions.BoxSurface`, the same three
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
class ContentsPage(Region):
    """
    The sheet after the cover that lists every section and the page it starts on.

    **The titles are handed down, never held.** The document passes its
    sections' titles and anchors as ``contents_entries``, layered over this
    region's fields like any fact, so the list cannot restate a title the
    body spells differently. The page numbers are the one figure Python
    cannot know: the paged skeleton's stylesheet asks the print engine for
    each through ``target-counter``, on the partial the email's
    :class:`~pyhermes.builder.components.Contents` component shares.

    ``of="exhibits"`` lists the numbered exhibits instead, as the email's
    component does (#308); :class:`ExhibitsPage` is the same sheet in a slot
    of its own, for a document that wants both lists.

    Its heading is deliberately not a section title, so it never becomes the
    section a running header follows (#185). There is no ``align``: the list
    fixes its own, since an entry's shape — title, leader, page — is its
    alignment.
    """

    CONTEXT_NAME: ClassVar[str] = "contents"
    SLOTS: ClassVar[tuple[str, ...]] = ("contents",)
    TEMPLATE_PATHS: ClassVar[dict[str, str]] = {"contents": "document/regions/contents.html"}

    heading: str = "Contents"
    of: str = "sections"
    label: str | None = None

    def validate(self) -> None:
        """The base rules, then a listing :func:`check_listing` accepts."""
        super().validate()
        check_listing(self.of, self.label, type(self).__name__)

    def _text(self, facts: dict[str, Any]) -> str:
        """The heading, then the titles one per line: plain text has no page numbers."""
        titles = [entry["title"] for entry in facts.get("contents_entries", [])]
        return join_blocks(underline(self.heading or ""), wrap("\n".join(titles)))


@dataclass
class EmptyContentsPage(ContentsPage):
    """No contents sheet: the body follows the cover. Fills no slot."""

    TEMPLATE_PATHS: ClassVar[dict[str, str]] = {}


@dataclass
class ExhibitsPage(ContentsPage):
    """
    The list of exhibits on a sheet of its own, after the contents (#308).

    A :class:`ContentsPage` in a second slot, so a research note can open on
    both lists; the skeleton prints the two slots back to back.
    """

    CONTEXT_NAME: ClassVar[str] = "exhibits"
    SLOTS: ClassVar[tuple[str, ...]] = ("exhibits",)
    TEMPLATE_PATHS: ClassVar[dict[str, str]] = {"exhibits": "document/regions/contents.html"}

    heading: str = "Exhibits"
    of: str = "exhibits"

    def validate(self) -> None:
        """The contents sheet's rules, and a listing of exhibits only."""
        super().validate()
        if self.of != "exhibits":
            raise ValidationError(
                f"{type(self).__name__} lists exhibits; a list of sections is ContentsPage."
            )


@dataclass
class EmptyExhibitsPage(ExhibitsPage):
    """No list of exhibits. Fills no slot, and the default."""

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

    ``follow="section"`` prints the current section's title instead (#185),
    with ``label`` as the fallback for sheets before the first one. The title
    reaches the margin through the print engine's named strings, not the
    facts: which section a sheet holds is the page's own knowledge.

    ``skip_first=True`` leaves the box off the document's first sheet (#400),
    as a deck's title slide carries no bands. The count is unchanged, so the
    second sheet still reads 2.
    """

    #: What a box may follow instead of its fixed label. Closed, like the boxes.
    FOLLOWS: ClassVar[tuple[str, ...]] = ("section",)

    #: Which fact this region's label falls back to. Subclasses set it.
    LABEL_FACT: ClassVar[str] = "firm_name"

    #: Where in the page margin this box sits, by default.
    DEFAULT_BOX: ClassVar[str] = "top-left"

    label: str = ""
    box: str = ""
    show_page_number: bool = False
    follow: str | None = None
    skip_first: bool = False

    def validate(self) -> None:
        super().validate()
        if self.follow is not None and self.follow not in self.FOLLOWS:
            raise ValidationError(
                f"'{self.CONTEXT_NAME}.follow' must be one of {list(self.FOLLOWS)} or None, "
                f"got: {self.follow!r}"
            )
        if not isinstance(self.skip_first, bool):
            raise ValidationError(
                f"'{self.CONTEXT_NAME}.skip_first' is True or False, got: {self.skip_first!r}"
            )
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
            "running_string": self.CONTEXT_NAME.replace("_", "-"),
            "skip_first": self.skip_first,
        }
        return {**super().context({}), **resolved, **facts}

    def _text(self, facts: dict[str, Any]) -> str:
        """
        Nothing, deliberately.

        A running box is chrome: it repeats copy the cover already carries,
        and a page number counts sheets that plain text does not have. So the
        projection is empty **by decision** rather than by omission — which
        is why it is implemented rather than left to raise. A box following
        the section is the same kind of thing: plain text has no sheets to head.
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
    "ContentsPage",
    "Cover",
    "EmptyBackMatter",
    "EmptyContentsPage",
    "EmptyCover",
    "EmptyRunningFooter",
    "EmptyRunningHeader",
    "RunningBox",
    "RunningFooter",
    "RunningHeader",
]
