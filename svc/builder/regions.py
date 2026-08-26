"""
Regions — the layer between the skeleton and the containers.

The composition model is ``skeleton ← regions (header | body | footer) ←
containers ← components``. A *region* is a named area of the email that
renders itself from its own template(s) and declares its own images, the way
a :class:`~svc.builder.components.Component` already does for a content
block.

Two rules give the layer its shape:

**Facts flow down.** The firm's name, the campaign, the dates, the
disclaimers and the outbound URLs are facts about the *email*; they live on
:class:`~svc.builder.models.EmailMetadata` and are passed into the region at
render time. A region presents them — it cannot own or contradict them,
which :meth:`Region.context` enforces by layering the facts *over* its own
keys rather than under them.

**The design system is not a parameter.** Fonts, palette, padding and the
680px geometry stay in the templates, exactly as for containers and
components. A region varies the *structure* of the masthead, not its look.

**A region fills one or more named slots.** The header fills one
(``{{ header_html }}``); the footer fills two, because its contact card is a
``<tr>`` inside the body table while its legal block is a sibling table
below — one fragment spanning both would have to close a tag the skeleton
opened. :meth:`Region.render_slots` is the contract the skeleton consumes,
and a slot a variant leaves unfilled renders empty, which is how a variant
*omits* a block rather than conditionalising it away.

The body region is deliberately not a class: it *is* the email's ordered
section list, and wrapping that in an object would add a layer with no
behaviour. The preheader stays skeleton plumbing for the same reason —
header, body and footer are the complete set.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import TYPE_CHECKING, Any, ClassVar

from .exceptions import ValidationError
from .models import _validate_url

if TYPE_CHECKING:  # pragma: no cover - import cycle: images imports _validate_url
    from .engine import TemplateEngine
    from .images import EmailImage, ImageAsset


@dataclass
class Region:
    """
    The shared half of a region: validation, images and the render contract.

    A region owns *presentation*; the email owns the *facts* and hands them
    over at render time. Everything below is the part header and footer do
    identically — :meth:`context` layering facts over presentation,
    :meth:`images` feeding the asset manifest, and :meth:`render_slots`
    turning the region into the one-or-more HTML strings the skeleton needs.
    A subclass declares its slots, its templates and its fields; the
    mechanism is not re-derived per region.

    Attributes are dataclass fields on the subclass. Every one of them
    reaches the template under its own name, so adding a field to a region is
    a one-line change on both sides.
    """

    #: Prefix for this region's validation messages, e.g. ``header.logo_url``.
    #: A caller reading the error should learn *where the field lives*.
    CONTEXT_NAME: ClassVar[str] = "region"

    #: Every slot in the skeleton this kind of region can fill, in skeleton
    #: order. Fixed by the skeleton's shape, so a variant does not override
    #: it — a variant varies :attr:`TEMPLATE_PATHS` instead.
    SLOTS: ClassVar[tuple[str, ...]] = ()

    #: Slot → template. A variant may omit a slot, which then renders empty.
    TEMPLATE_PATHS: ClassVar[dict[str, str]] = {}

    #: Slots a variant may **not** leave unfilled. Empty for a region with
    #: nothing to protect; the footer uses it as a compliance floor.
    REQUIRED_SLOTS: ClassVar[tuple[str, ...]] = ()

    #: Fields that may hold an EmailImage instead of a bare URL.
    IMAGE_FIELDS: ClassVar[tuple[str, ...]] = ()

    def __post_init__(self) -> None:
        self.validate()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> None:
        """
        Raise :class:`ValidationError` if this region is not renderable.

        Two rules, both structural: every image field holds a URL with a safe
        scheme or an :class:`~svc.builder.images.EmailImage`, and every
        required slot has a template. A subclass extends this; it does not
        replace it.
        """
        from .images import EmailImage

        for fname in self.IMAGE_FIELDS:
            value = getattr(self, fname)
            # An EmailImage validated its own URL (or its own bytes) at
            # construction; only a bare string still needs checking here.
            if isinstance(value, str):
                _validate_url(value, f"{self.CONTEXT_NAME}.{fname}")
            elif not isinstance(value, EmailImage):
                raise ValidationError(
                    f"'{self.CONTEXT_NAME}.{fname}' must be a URL string or an "
                    f"EmailImage, got: {type(value).__name__}"
                )
        missing = [slot for slot in self.REQUIRED_SLOTS if slot not in self.TEMPLATE_PATHS]
        if missing:
            raise ValidationError(
                f"{type(self).__name__} leaves required slot(s) {sorted(missing)} "
                f"unfilled. A variant may drop an optional block, but not one the "
                f"region declares as required."
            )

    # ------------------------------------------------------------------
    # Image manifest
    # ------------------------------------------------------------------

    def images(self) -> list[EmailImage]:
        """
        The EmailImages this region references.

        Driven by :attr:`IMAGE_FIELDS`, so a region that carries images
        declares them rather than overriding this — but a region that
        sources bytes some other way **must** override it, or they never
        reach :meth:`svc.builder.email.Email.assets` and the ``cid:``
        reference renders as a broken image. Same rule components have.
        """
        from .images import EmailImage

        return [
            value
            for fname in self.IMAGE_FIELDS
            if isinstance(value := getattr(self, fname), EmailImage)
        ]

    def assets(self) -> list[ImageAsset]:
        """The attachment manifest entries for this region's images."""
        return [image.asset for image in self.images() if image.asset is not None]

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def context(self, facts: dict[str, Any]) -> dict[str, Any]:
        """
        The render context: this region's presentation, under the email's facts.

        ``facts`` is layered *over* the presentation keys, not under them, so
        a region cannot shadow a fact the email owns even by accident. The
        two key sets are disjoint today and a test keeps them that way; the
        ordering is what makes the ownership rule mechanical rather than a
        convention to remember.

        Image fields collapse to their resolved ``src`` — the template wants
        a string for an attribute, and the bytes behind a ``cid:`` reference
        travel through the asset manifest instead.
        """
        from .images import EmailImage

        presentation: dict[str, Any] = {
            f.name: value.src if isinstance(value := getattr(self, f.name), EmailImage) else value
            for f in fields(self)
        }
        return {**presentation, **facts}

    def render_slots(self, engine: TemplateEngine, facts: dict[str, Any]) -> dict[str, str]:
        """
        Render this region into the skeleton variables it fills.

        Returns ``{"<slot>_html": html}`` for **every** slot in
        :attr:`SLOTS`, filled or not: the skeleton names them unconditionally
        and the engine runs under ``StrictUndefined``, so an omitted key is a
        render failure rather than a missing block. An unfilled slot renders
        as the empty string — that is what makes dropping a block an
        omission rather than a conditional in the template.
        """
        ctx = self.context(facts)
        return {
            f"{slot}_html": (
                engine.render(self.TEMPLATE_PATHS[slot], ctx) if slot in self.TEMPLATE_PATHS else ""
            )
            for slot in self.SLOTS
        }


@dataclass
class Header(Region):
    """
    The masthead: how an email presents the facts it holds.

    Owns presentation only — the background image, the logo and the logo's
    resolution chains. The wording it displays (firm name, campaign name,
    date range, issue label, disclaimer) belongs to the email and arrives
    through :meth:`context`.

    Attributes:
        background_image_url: Hero background. A CSS background cannot carry
            alt text, so it is decorative by construction. Accepts an
            :class:`~svc.builder.images.EmailImage` or a bare URL.
        logo_url:   Masthead logo. Same union.
        logo_alt:   Explicit alt text. Falls back to the ``EmailImage``'s own
                    ``alt``, then to the email's ``firm_name`` — the logo is
                    never left unlabelled.
        logo_width: Display width in px, emitted as the HTML attribute
                    because Outlook's Word engine ignores ``max-width``.
                    Falls back to the ``EmailImage``'s own ``width``, then to
                    :data:`DEFAULT_LOGO_WIDTH`.

    Validates at construction, like every model here.
    """

    CONTEXT_NAME: ClassVar[str] = "header"

    #: The masthead fills a single slot: ``{{ header_html }}``.
    SLOTS: ClassVar[tuple[str, ...]] = ("header",)

    TEMPLATE_PATHS: ClassVar[dict[str, str]] = {"header": "regions/header.html"}

    #: Fields that may hold an EmailImage instead of a bare URL.
    IMAGE_FIELDS: ClassVar[tuple[str, ...]] = ("logo_url", "background_image_url")

    #: Logo width used when neither the header nor the EmailImage sets one.
    DEFAULT_LOGO_WIDTH: ClassVar[int] = 90

    background_image_url: str | EmailImage = ""
    logo_url: str | EmailImage = ""
    logo_alt: str = ""
    logo_width: int | None = None

    def validate(self) -> None:
        super().validate()
        if self.logo_width is not None and self.logo_width <= 0:
            raise ValidationError(f"'header.logo_width' must be positive, got: {self.logo_width}")

    def context(self, facts: dict[str, Any]) -> dict[str, Any]:
        """
        The base context, with the logo's resolution chains applied.

        ``logo_alt`` and ``logo_width`` reach the template resolved rather
        than raw, and ``facts`` still lands last — the ownership rule holds
        through the override.
        """
        firm_name = str(facts.get("firm_name", ""))
        resolved = {
            "logo_alt": self.resolved_logo_alt(firm_name),
            "logo_width": self.resolved_logo_width(),
        }
        return {**super().context({}), **resolved, **facts}

    def render(self, engine: TemplateEngine, facts: dict[str, Any]) -> str:
        """
        The masthead HTML.

        A convenience over :meth:`render_slots` for the single-slot case, and
        deliberately a delegation rather than a second call to ``engine`` —
        one rendering path is the whole point.
        """
        return self.render_slots(engine, facts)["header_html"]

    # ------------------------------------------------------------------
    # Resolution chains
    # ------------------------------------------------------------------

    def resolved_logo_alt(self, firm_name: str = "") -> str:
        """
        The alt text the logo actually renders with.

        Explicit ``logo_alt`` wins; otherwise an ``EmailImage`` logo supplies
        its own ``alt``; otherwise the firm name, which is what the skeleton
        hardcoded before this was configurable. ``firm_name`` is a parameter
        rather than a field because it is a fact about the email — the header
        is handed it, it does not hold it.
        """
        from .images import EmailImage

        if self.logo_alt:
            return self.logo_alt
        if isinstance(self.logo_url, EmailImage) and self.logo_url.alt:
            return self.logo_url.alt
        return firm_name

    def resolved_logo_width(self) -> int:
        """The logo width actually rendered: header, then image, then default."""
        from .images import EmailImage

        if self.logo_width is not None:
            return self.logo_width
        if isinstance(self.logo_url, EmailImage) and self.logo_url.width is not None:
            return self.logo_url.width
        return self.DEFAULT_LOGO_WIDTH


@dataclass
class MinimalHeader(Header):
    """
    A masthead with no background image and no VML.

    The variant that proves the seam: a caller picks it with
    ``Email(header=MinimalHeader(...))``, and nothing about the skeleton, the
    body or the email's facts changes. Same logo resolution chains, same
    facts flowing down — a flat ``#2C3E50`` band instead of a photograph with
    a scrim over it.

    Dropping the image removes the ``v:rect``/``v:fill``/``v:textbox`` block,
    which is the most fragile markup in the repo: there is nothing left to
    frame. That is the point of the variant, so a background image is
    rejected at construction rather than silently ignored.
    """

    TEMPLATE_PATHS: ClassVar[dict[str, str]] = {"header": "regions/header-minimal.html"}

    def validate(self) -> None:
        if self.background_image_url:
            raise ValidationError(
                "'header.background_image_url' is not supported by MinimalHeader — "
                "the variant exists to render a flat band with no VML. Use Header "
                "for a background image."
            )
        super().validate()


@dataclass
class Footer(Region):
    """
    The closing region: how an email says the things it is obliged to say.

    Owns the *wording* — the contact card's heading, description and button
    label, and the two link labels in the legal line. It owns none of the
    substance: the disclaimer, the copyright year, the firm's name and the
    three outbound URLs are facts about the email, arrive through
    :meth:`context`, and cannot be contradicted here.

    That line is drawn where #38 drew the header's. The URLs stay facts —
    unlike the header's ``logo_url``, which is an image the *region* chose,
    an unsubscribe address is a property of the mailing, and
    :meth:`svc.builder.models.EmailMetadata.validate` already checks all
    three schemes.

    The footer fills two slots because its blocks sit in different parents;
    see the module docstring. A variant may drop the contact slot, but not
    the legal one — :attr:`REQUIRED_SLOTS` makes the compliance floor a rule
    rather than a convention.

    Attributes:
        contact_heading:      Bold line above the contact card's copy.
        contact_description:  Prose under it. Escaped by the template.
        contact_cta_label:    The button's text, emitted **twice** — once in
                              the Outlook ``v:roundrect``, once in the anchor
                              everyone else sees.
        unsubscribe_label:    Text of the unsubscribe link.
        view_in_browser_label: Text of the view-in-browser link.

    Defaults reproduce the strings ``base.html`` used to hardcode, so an
    email that never mentions a footer renders unchanged.
    """

    CONTEXT_NAME: ClassVar[str] = "footer"

    SLOTS: ClassVar[tuple[str, ...]] = ("footer_contact", "footer_legal")

    TEMPLATE_PATHS: ClassVar[dict[str, str]] = {
        "footer_contact": "regions/footer-contact.html",
        "footer_legal": "regions/footer-legal.html",
    }

    contact_heading: str = "Questions or feedback?"
    contact_description: str = ""
    contact_cta_label: str = "Contact Us"
    unsubscribe_label: str = "Unsubscribe"
    view_in_browser_label: str = "View in browser"
