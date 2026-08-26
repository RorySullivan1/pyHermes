"""
Regions — the layer between the skeleton and the containers.

The composition model is ``skeleton ← regions (header | body) ← containers
← components``. A *region* is a named area of the email that renders itself
from its own template and declares its own images, the way a
:class:`~svc.builder.components.Component` already does for a content block.

Two rules give the layer its shape:

**Facts flow down.** ``firm_name``, ``campaign_name``, ``date_range``,
``issue_label`` and ``header_disclaimer`` are facts about the *email*; they
live on :class:`~svc.builder.models.EmailMetadata` and are passed into the
region at render time. A region presents them — it cannot own or contradict
them, which :meth:`Header.context` enforces by layering the facts *over* its
own keys rather than under them.

**The design system is not a parameter.** Fonts, palette, padding and the
680px geometry stay in the templates, exactly as for containers and
components. A region varies the *structure* of the masthead, not its look.

The body region is deliberately not a class: it *is* the email's ordered
section list, and wrapping that in an object would add a layer with no
behaviour. The footer is deliberately still in ``base.html`` — the same kind
of candidate, but the seam is proven on the header first.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

from .exceptions import ValidationError
from .models import _validate_url

if TYPE_CHECKING:  # pragma: no cover - import cycle: images imports _validate_url
    from .engine import TemplateEngine
    from .images import EmailImage, ImageAsset


@dataclass
class Header:
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

    #: The template this region renders. A variant overrides it.
    template_path: ClassVar[str] = "regions/header.html"

    #: Fields that may hold an EmailImage instead of a bare URL.
    IMAGE_FIELDS: ClassVar[tuple[str, ...]] = ("logo_url", "background_image_url")

    #: Logo width used when neither the header nor the EmailImage sets one.
    DEFAULT_LOGO_WIDTH: ClassVar[int] = 90

    background_image_url: str | EmailImage = ""
    logo_url: str | EmailImage = ""
    logo_alt: str = ""
    logo_width: int | None = None

    def __post_init__(self) -> None:
        self.validate()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> None:
        """Raise :class:`ValidationError` if a URL carries an unsafe scheme."""
        from .images import EmailImage

        for fname in self.IMAGE_FIELDS:
            value = getattr(self, fname)
            # An EmailImage validated its own URL (or its own bytes) at
            # construction; only a bare string still needs checking here.
            if isinstance(value, str):
                _validate_url(value, f"header.{fname}")
            elif not isinstance(value, EmailImage):
                raise ValidationError(
                    f"'header.{fname}' must be a URL string or an EmailImage, "
                    f"got: {type(value).__name__}"
                )
        if self.logo_width is not None and self.logo_width <= 0:
            raise ValidationError(f"'header.logo_width' must be positive, got: {self.logo_width}")

    # ------------------------------------------------------------------
    # Image manifest
    # ------------------------------------------------------------------

    def images(self) -> list[EmailImage]:
        """
        The EmailImages this region references.

        A region that carries images **must** override this, or its bytes
        never reach :meth:`svc.builder.email.Email.assets` and its ``cid:``
        reference renders as a broken image — the same rule components have.
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

        firm_name = str(facts.get("firm_name", ""))
        presentation: dict[str, Any] = {
            fname: value.src if isinstance(value := getattr(self, fname), EmailImage) else value
            for fname in self.IMAGE_FIELDS
        }
        presentation["logo_alt"] = self.resolved_logo_alt(firm_name)
        presentation["logo_width"] = self.resolved_logo_width()
        return {**presentation, **facts}

    def render(self, engine: TemplateEngine, facts: dict[str, Any]) -> str:
        """Render this region's template with the merged context."""
        return engine.render(self.template_path, self.context(facts))

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
