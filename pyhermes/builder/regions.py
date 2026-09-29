"""
Regions — the layer between the skeleton and the containers.

The composition model is ``skeleton <- regions (header | banner | body |
footer) <- containers <- components``. A region is a named area that renders
itself from its own template(s) and declares its own images, the way a
:class:`~pyhermes.builder.components.Component` does for a content block.

Two rules give the layer its shape: **each region owns exactly one skeleton
slot**, and **facts flow down** — a region receives the email's facts and
layers them *over* its own context, so what the email owns cannot be shadowed
from below.

`.claude/rules/builder-architecture.md` carries the four-region model, the
``BoxSurface`` mixin the header and footer share, and ``theme_context()``.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import TYPE_CHECKING, Any, ClassVar

from .enums import TextAlign
from .exceptions import ValidationError
from .models import FooterLink, LinkRow, _validate_color, _validate_url
from .textgen import html_to_text, join_blocks, link_line, underline, wrap

if TYPE_CHECKING:  # pragma: no cover - import cycle: images imports _validate_url
    from .engine import Renderer
    from .images import EmailImage, ImageAsset
    from .theming import BannerPalette, Theme


@dataclass
class Region:
    """
    The shared half of a region: validation, images and the render contract.

    A region owns *presentation*; the email owns the *facts* and hands them
    over at render time. Everything below is the part banner and footer do
    identically — :meth:`context` layering facts over presentation,
    :meth:`images` feeding the asset manifest, and :meth:`render_slots`
    turning the region into the one-or-more HTML strings the skeleton needs.
    A subclass declares its slots, its templates and its fields; the
    mechanism is not re-derived per region.

    Attributes are dataclass fields on the subclass. Every one of them
    reaches the template under its own name, so adding a field to a region is
    a one-line change on both sides.
    """

    #: Prefix for this region's validation messages, e.g. ``banner.logo_url``.
    #: A caller reading the error should learn *where the field lives*.
    CONTEXT_NAME: ClassVar[str] = "region"

    #: Every slot in the skeleton this kind of region can fill, in skeleton
    #: order. Fixed by the skeleton's shape, so a variant does not override
    #: it — a variant varies :attr:`TEMPLATE_PATHS` instead.
    SLOTS: ClassVar[tuple[str, ...]] = ()

    #: Slot → template. A variant may omit a slot, which then renders empty.
    TEMPLATE_PATHS: ClassVar[dict[str, str]] = {}

    #: Slots a variant may **not** leave unfilled. Empty for a region whose
    #: whole box is optional (the header); named by one whose block is
    #: structural (the footer).
    #:
    #: **This is a rule about variants, never about callers.** It says a
    #: subclass may not silently drop a block the region is *made of*; it
    #: says nothing about what a caller must put in one. pyHermes does not
    #: require disclaimer language, an unsubscribe link, or any other
    #: content — it cannot know whether an email is a commercial newsletter,
    #: an internal note or a receipt, and each answers that differently. The
    #: two are easy to conflate, and this attribute was described as a
    #: "compliance floor" until #100, which over-claimed in exactly that
    #: direction.
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
        scheme or an :class:`~pyhermes.builder.images.EmailImage`, and every
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
        reach :meth:`pyhermes.builder.email.Email.assets` and the ``cid:``
        reference renders as a broken image. Same rule components have.
        """
        from .images import EmailImage

        return [
            value
            for fname in self.IMAGE_FIELDS
            if isinstance(value := getattr(self, fname), EmailImage)
        ]

    def raw_html(self) -> list[str]:
        """The caller markup this region emits raw, for the document's link check."""
        return []

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

    def theme_context(self, theme: Theme) -> dict[str, Any]:
        """
        Keys this region resolves against the email's theme. Empty by default.

        The hook a region overrides when one of its presentation fields means
        *"the theme's token, unless I say otherwise"*. It exists because the
        theme is neither a fact nor a field: it reaches the templates through
        the bound engine, and a region only has it at render time — so
        resolving in :meth:`context`, which has no engine, is impossible.

        What comes back is layered **with the facts**, over the region's own
        keys, so a resolved value cannot be shadowed by the raw field it was
        resolved from. That is why a resolved key takes a *different name*
        than the field: ``Header.background_color`` is what the caller set
        (possibly nothing), ``header_background`` is what actually renders,
        and the template reads only the second.

        Generalised rather than duplicated: the banner needed it first for
        its :class:`~pyhermes.builder.theming.BannerPalette`, the header for its
        colour pair, and #98's footer box for the same two tokens.
        """
        return {}

    def text(self, facts: dict[str, Any]) -> str:
        """
        This region's plain-text projection (#109).

        **A variant that fills no slot projects nothing**, checked here rather
        than overridden per variant — it is the same rule
        :meth:`render_slots` applies, read once for the whole region:
        :class:`EmptyHeader` omits the strip from the HTML by declaring no
        templates, and the text part has to agree without anybody remembering
        to make it.

        What a region projects is its **resolved** state — the same accessors
        the HTML templates read, never the raw fields — so the two parts
        cannot come to disagree about what the email says.
        """
        if not self.TEMPLATE_PATHS:
            return ""
        return self._text(facts)

    def _text(self, facts: dict[str, Any]) -> str:
        """The projection itself, once :meth:`text` has established there is one."""
        raise NotImplementedError(
            f"{type(self).__name__} has no _text() projection. Every region needs "
            "one, or its content disappears from the plain-text part."
        )

    def render_slots(self, engine: Renderer, facts: dict[str, Any]) -> dict[str, str]:
        """
        Render this region into the skeleton variables it fills.

        Returns ``{"<slot>_html": html}`` for **every** slot in
        :attr:`SLOTS`, filled or not: the skeleton names them unconditionally
        and the engine runs under ``StrictUndefined``, so an omitted key is a
        render failure rather than a missing block. An unfilled slot renders
        as the empty string — that is what makes dropping a block an
        omission rather than a conditional in the template.
        """
        ctx = self.context({**facts, **self.theme_context(engine.theme)})
        return {
            f"{slot}_html": (
                engine.render(self.TEMPLATE_PATHS[slot], ctx) if slot in self.TEMPLATE_PATHS else ""
            )
            for slot in self.SLOTS
        }


@dataclass
class BoxSurface:
    """
    The three fields the email's two outer boxes share.

    The header strip and the footer's legal block are the customisable boxes
    that bracket the body, and the requirement behind them is that they be
    *similar*: two boxes that behave alike should cost one API to learn, not
    two. So the surface is declared once and mixed into both, which makes the
    parity structural rather than a convention a test has to keep catching
    after the fact. (The test exists anyway — it is what stops a third region
    redeclaring these by hand instead of inheriting them.)

    A region mixes this in beside :class:`Region` and keeps its own
    :meth:`Region.theme_context`: the *fields* are shared, the tokens they
    fall back to are not. The footer's box draws type in two theme tokens and
    the header's in one, and pretending otherwise would be parity as
    costume.

    Attributes:
        align:            ``left``, ``center`` or ``right``.
        background_color: Hex; unset means the region's own theme token.
        text_color:       Hex; unset means the region's own theme token. It
                          ships with the background rather than alone,
                          because a ground the caller chose makes the theme's
                          type on it a guess — :class:`BannerPalette`'s
                          reasoning at the size these boxes need.
    """

    #: The alignments that make sense for a band of copy — read off
    #: :class:`~pyhermes.builder.enums.TextAlign`, which is the same vocabulary
    #: the body's containers take (#126). One source rather than two copies
    #: of the same three strings: a box and a section align the same thing,
    #: and the moment they disagree an email's header and its first section
    #: mean different things by the same word.
    ALIGNMENTS: ClassVar[frozenset[str]] = frozenset(TextAlign)

    align: str = "center"
    background_color: str = ""
    text_color: str = ""

    def validate_box_surface(self, context_name: str) -> None:
        """Validate the three shared fields, naming the owning region."""
        if self.align not in self.ALIGNMENTS:
            raise ValidationError(
                f"'{context_name}.align' must be one of {sorted(self.ALIGNMENTS)}, "
                f"got: {self.align!r}"
            )
        for name in ("background_color", "text_color"):
            value = getattr(self, name)
            if value:
                _validate_color(value, f"{context_name}.{name}")


@dataclass
class Banner(Region):
    """
    The masthead: how an email presents the facts it holds.

    Owns presentation only — the background image, the logo, the headline
    copy, and the resolution chains behind each. The facts it displays (firm
    name, campaign name, date range, issue label, disclaimer) belong to the
    email and arrive through :meth:`context`.

    **The headline is presentation, and that is not a contradiction.** Until
    #91 the masthead's large type *was* ``firm_name`` and its second line
    *was* ``campaign_name``, so an email that wanted to lead with *"Q3
    Outlook"* had to lie about who sent it. The facts-over-presentation
    layering makes shadowing a fact impossible by design — correctly — so
    the escape is the one the logo's alt text already uses: a presentation
    field with a resolution chain, landing in a key of its *own*
    (``banner_title``, ``banner_subtitle``) that the template reads instead
    of the fact. The fact still flows down untouched, which is why the
    footer's copyright line is unaffected by a banner that renames itself.

    Attributes:
        background_image_url: Hero background. A CSS background cannot carry
            alt text, so it is decorative by construction. Accepts an
            :class:`~pyhermes.builder.images.EmailImage` or a bare URL.
        logo_url:   Masthead logo. Same union.
        logo_alt:   Explicit alt text. Falls back to the ``EmailImage``'s own
                    ``alt``, then to the email's ``firm_name`` — the logo is
                    never left unlabelled.
        logo_width: Display width in px, emitted as the HTML attribute
                    because Outlook's Word engine ignores ``max-width``.
                    Falls back to the ``EmailImage``'s own ``width``, then to
                    :data:`DEFAULT_LOGO_WIDTH`.
        title:      Free-form headline. Falls back to the email's
                    ``firm_name``. Plain text, escaped on the way out —
                    "free form" means arbitrary *copy*, not markup, and the
                    raw-HTML surface stays where it already is (the
                    disclaimers, ``TextBlock.content``).
        subtitle:   Free-form second line. Falls back to ``campaign_name``,
                    escaped the same way.
        palette:    Optional :class:`~pyhermes.builder.theming.BannerPalette` —
                    the one place in the builder a caller may move a colour
                    without replacing the whole :class:`Theme`, because it is
                    the one place the *caller* supplies the surface being
                    rendered on. Unset roles take the theme's tokens. See the
                    class for why this does not generalise to other regions.

    Validates at construction, like every model here.
    """

    CONTEXT_NAME: ClassVar[str] = "banner"

    #: One slot. The strip at the top of the email lived here between #89 and
    #: #95 — separate template, separate slot, but rendered by this class —
    #: and #95 gave it :class:`Header`. The skeleton's slot set never changed
    #: across either step, which is what made the split a change of *owner*
    #: rather than of markup.
    SLOTS: ClassVar[tuple[str, ...]] = ("banner",)

    TEMPLATE_PATHS: ClassVar[dict[str, str]] = {"banner": "regions/banner.html"}

    #: Fields that may hold an EmailImage instead of a bare URL.
    IMAGE_FIELDS: ClassVar[tuple[str, ...]] = ("logo_url", "background_image_url")

    #: Logo width used when neither the banner nor the EmailImage sets one.
    DEFAULT_LOGO_WIDTH: ClassVar[int] = 90

    background_image_url: str | EmailImage = ""
    logo_url: str | EmailImage = ""
    logo_alt: str = ""
    logo_width: int | None = None
    title: str = ""
    subtitle: str = ""
    palette: BannerPalette | None = None

    def validate(self) -> None:
        super().validate()
        if self.logo_width is not None and self.logo_width <= 0:
            raise ValidationError(f"'banner.logo_width' must be positive, got: {self.logo_width}")

    def context(self, facts: dict[str, Any]) -> dict[str, Any]:
        """
        The base context, with this region's resolution chains applied.

        Four keys arrive resolved rather than raw, and ``facts`` still lands
        *last* — the ownership rule holds through the override rather than
        being carved out of.

        ``logo_alt`` and ``logo_width`` resolve in place, because no fact
        answers to either name. ``title`` and ``subtitle`` cannot: their
        chains end at ``firm_name`` and ``campaign_name``, which are facts
        the email owns and which land after this dict. So they resolve into
        ``banner_title`` and ``banner_subtitle``, names no fact uses, and the
        template reads *those*. A test greps the templates to keep it that
        way — reading ``{{ firm_name }}`` again would work, silently, and
        make the field unreachable.
        """
        firm_name = str(facts.get("firm_name", ""))
        campaign_name = str(facts.get("campaign_name", ""))
        resolved = {
            "logo_alt": self.resolved_logo_alt(firm_name),
            "logo_width": self.resolved_logo_width(),
            "banner_title": self.resolved_title(firm_name),
            "banner_subtitle": self.resolved_subtitle(campaign_name),
        }
        return {**super().context({}), **resolved, **facts}

    def theme_context(self, theme: Theme) -> dict[str, Any]:
        """
        A **total** :class:`~pyhermes.builder.theming.BannerPalette`, as
        ``banner_palette``.

        Total by construction, so the template reads one object for every
        colour it draws and an override is indistinguishable from an
        inherited token by the time the markup sees it.
        """
        from .theming import BannerPalette

        return {"banner_palette": (self.palette or BannerPalette()).resolved(theme)}

    def _text(self, facts: dict[str, Any]) -> str:
        """
        The masthead as plain text: the resolved headline, then the metadata.

        Read off the **resolution chains**, not the fields — an email whose
        banner renames itself says the new name in both parts, and one that
        does not falls back to ``firm_name`` in both. Reading ``title``
        directly would work for every email that sets it and quietly print
        nothing for every email that does not.

        The logo and the background image project to nothing: both are
        chrome, and the logo's alt text resolves to ``firm_name``, which the
        headline already carries.
        """
        title = self.resolved_title(str(facts.get("firm_name", "")))
        meta = [str(facts.get(name, "")) for name in ("department", "date_range", "issue_label")]
        return join_blocks(
            underline(title, "="),
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

    def render(self, engine: Renderer, facts: dict[str, Any]) -> str:
        """
        Every slot this region fills, in skeleton order, as one string.

        A convenience over :meth:`render_slots`, and deliberately a
        delegation rather than a second call to ``engine`` — one rendering
        path is the whole point.
        """
        slots = self.render_slots(engine, facts)
        return "\n".join(slots[f"{slot}_html"] for slot in self.SLOTS)

    # ------------------------------------------------------------------
    # Resolution chains
    # ------------------------------------------------------------------

    def resolved_logo_alt(self, firm_name: str = "") -> str:
        """
        The alt text the logo actually renders with.

        Explicit ``logo_alt`` wins; otherwise an ``EmailImage`` logo supplies
        its own ``alt``; otherwise the firm name, which is what the skeleton
        hardcoded before this was configurable. ``firm_name`` is a parameter
        rather than a field because it is a fact about the email — the banner
        is handed it, it does not hold it.
        """
        from .images import EmailImage

        if self.logo_alt:
            return self.logo_alt
        if isinstance(self.logo_url, EmailImage) and self.logo_url.alt:
            return self.logo_url.alt
        return firm_name

    def resolved_logo_width(self) -> int:
        """The logo width actually rendered: banner, then image, then default."""
        from .images import EmailImage

        if self.logo_width is not None:
            return self.logo_width
        if isinstance(self.logo_url, EmailImage) and self.logo_url.width is not None:
            return self.logo_url.width
        return self.DEFAULT_LOGO_WIDTH

    def resolved_title(self, firm_name: str = "") -> str:
        """
        The headline the masthead actually renders: explicit, then the firm.

        ``firm_name`` is a parameter rather than a field for the reason
        :meth:`resolved_logo_alt` gives — it is a fact about the email, and
        the banner is handed it rather than holding it.
        """
        return self.title or firm_name

    def resolved_subtitle(self, campaign_name: str = "") -> str:
        """The second line: explicit, then the campaign name. Same shape."""
        return self.subtitle or campaign_name


@dataclass
class MinimalBanner(Banner):
    """
    A masthead with no background image and no VML.

    The variant that proves the seam: a caller picks it with
    ``Email(banner=MinimalBanner(...))``, and nothing about the skeleton, the
    body or the email's facts changes. Same logo resolution chains, same
    facts flowing down — a flat ``#2C3E50`` band instead of a photograph with
    a scrim over it.

    Dropping the image removes the ``v:rect``/``v:fill``/``v:textbox`` block,
    which is the most fragile markup in the repo: there is nothing left to
    frame. That is the point of the variant, so a background image is
    rejected at construction rather than silently ignored.
    """

    #: Composed rather than restated. It reads as a no-op today, because #95
    #: left the banner one slot and the variant differs in that one — but the
    #: form is the point: a variant that overrides only what it changes
    #: cannot drift from the parent on a slot they share, and the duplicated
    #: strip template #89 removed is what that drift looked like.
    TEMPLATE_PATHS: ClassVar[dict[str, str]] = {
        **Banner.TEMPLATE_PATHS,
        "banner": "regions/banner-minimal.html",
    }

    def validate(self) -> None:
        if self.background_image_url:
            raise ValidationError(
                "'banner.background_image_url' is not supported by MinimalBanner — "
                "the variant exists to render a flat band with no VML. Use Banner "
                "for a background image."
            )
        super().validate()


@dataclass
class Header(BoxSurface, Region):
    """
    The strip at the very top of the email: one band of centred copy.

    The email's outermost box above the body, and deliberately symmetric with
    :class:`Footer` below it — the two are the customisable boxes that bracket
    the sections, and #98 gives the footer's box these same three field names,
    so a caller learns one surface rather than two.

    **The name meant the masthead until #95.** ``Header`` was renamed to
    :class:`Banner` in #90 precisely so it could be reused here, with no
    deprecated alias in between: an old-style ``Header(logo_url=…)`` now fails
    at construction, because this class has no such field. That is loud, at the
    call site, which is the point — a name that quietly changed meaning would
    keep running and be wrong.

    **Its copy is raw HTML, and that is a footgun nobody has been warned
    about.** ``header_disclaimer`` is emitted unescaped, as it always has
    been, and as the other disclaimers are: escaping it now would break every
    caller passing markup. So the contract is kept and stated instead —
    **escaping untrusted text in it is the caller's job**, with
    :func:`~pyhermes.builder.filters.escape_html` the tool. The copy itself stays
    on :class:`~pyhermes.builder.models.EmailMetadata`: it is legal wording that
    belongs to the *email*, and this region only decides how the box presents
    it.

    Its presentation is :class:`BoxSurface` — ``align``, ``background_color``
    and ``text_color``, shared with the footer's box so the two cost one API
    to learn. Unset, the background is the theme's band
    (``palette.header_bg``) and the text its ``text.on_dark_muted``.

    Validates at construction, like every model here.
    """

    CONTEXT_NAME: ClassVar[str] = "header"
    SLOTS: ClassVar[tuple[str, ...]] = ("header_bar",)
    TEMPLATE_PATHS: ClassVar[dict[str, str]] = {"header_bar": "regions/header-bar.html"}

    def validate(self) -> None:
        super().validate()
        self.validate_box_surface(self.CONTEXT_NAME)

    def _text(self, facts: dict[str, Any]) -> str:
        """
        The strip's copy, through #108's degrader.

        ``header_disclaimer`` is a fact the email owns and one of the five
        raw-HTML surfaces, so it arrives as markup and leaves as text. The
        box's colours and alignment project to nothing.
        """
        return html_to_text(str(facts.get("header_disclaimer", "")))

    def theme_context(self, theme: Theme) -> dict[str, Any]:
        """
        The two colours the band actually draws, resolved.

        Under names of their own — ``header_background``, ``header_text`` —
        rather than in place, so the template reads what *renders* and never
        the raw field, which is empty for the caller who set nothing. Same
        shape as ``banner_palette``, at the size this box needs.
        """
        return {
            "header_background": self.background_color or theme.palette.header_bg,
            "header_text": self.text_color or theme.text.on_dark_muted,
        }


@dataclass
class EmptyHeader(Header):
    """
    A header that renders nothing at all — no band, no empty ``<tr>``.

    Not every email carries a strip, and the slot mechanism already supports
    true omission: an unfilled slot renders as the empty string, so the
    skeleton needs no conditional. This gives that a name. A class rather
    than a flag (``Header(visible=False)``) because variants are classes
    here, and a class is what an introspecting test can find.

    **An empty ``header_disclaimer`` on a plain ``Header`` still renders the
    band, and that is deliberate.** It is tempting to auto-collapse — but the
    presence of the *box* would then depend on a fact the email owns rather
    than on the region, which inverts the rule the whole layer rests on: a
    region decides how it renders and whether it renders; a fact is only its
    content. The footer already draws the line in the same place, with
    ``Footer.disclaimer`` empty omitting the fine-print *line* while the
    footer itself still renders. "I have no copy" and "I do not want this
    box" are different statements, and this class is the second one.

    What a blank default actually looks like is worth knowing before
    reaching for it: on the theme's own colours the band is `#2C3E50` sitting
    directly above the masthead's identical `#2C3E50`, so it is invisible —
    14px of extra navy. It only reads as a mistake once #95 let the header
    carry a background of its own, and a caller who colours a box they put
    nothing in wants this class.

    **The asymmetry with `Footer` is not a lower standard.**
    :attr:`Region.REQUIRED_SLOTS` is a rule about *variants not silently
    dropping structure*, never about a caller supplying content — pyHermes
    does not require disclaimer language, and whether an email needs one is
    the sender's judgement. ``Footer`` names its slot required because a
    footer that renders nothing is a footer that failed; ``Header`` names
    none because its whole box is genuinely optional.
    """

    TEMPLATE_PATHS: ClassVar[dict[str, str]] = {}


@dataclass
class Footer(BoxSurface, Region):
    """
    The closing region: a structured, partially-flexible block.

    The caller controls its background, an optional full-box border, an
    optional sign-off image, the disclaimer text, and the two link labels.
    It does not control fonts or geometry. The copyright year, firm name and
    the two outbound URLs are facts about the email and arrive via
    :meth:`context`. The disclaimer is optional — an empty one omits the
    fine-print line; the copyright + links line always renders.

    Its box presentation is :class:`BoxSurface` — ``align``,
    ``background_color`` and ``text_color``, the same three the header strip
    takes, so the email's two outer boxes cost one API to learn rather than
    two. Everything below is the footer's own.

    Attributes:
        border:           Draw a full box around the footer.
        border_color:     Hex; empty falls back to the theme rule colour.
        image:            Optional sign-off mark (URL or EmailImage). The box
                          stacks **image → disclaimer → copyright row**, so
                          this sits above the disclaimer, not in place of it.
                          All three are independently optional and each
                          collapses when unset, closing the gap rather than
                          leaving one.
        image_alt:        Alt text; falls back to the EmailImage's own alt.
        image_width:      Display width in px; falls back to the EmailImage's
                          own width, then to :data:`DEFAULT_IMAGE_WIDTH`.
        disclaimer:       Free-form HTML, emitted **raw and unwrapped**.
        unsubscribe_label / view_in_browser_label: link wording.
    """

    CONTEXT_NAME: ClassVar[str] = "footer"
    SLOTS: ClassVar[tuple[str, ...]] = ("footer",)
    TEMPLATE_PATHS: ClassVar[dict[str, str]] = {"footer": "regions/footer.html"}
    REQUIRED_SLOTS: ClassVar[tuple[str, ...]] = ("footer",)
    IMAGE_FIELDS: ClassVar[tuple[str, ...]] = ("image",)
    DEFAULT_IMAGE_WIDTH: ClassVar[int] = 120

    border: bool = False
    border_color: str = ""
    image: str | EmailImage = ""
    image_alt: str = ""
    image_width: int | None = None
    disclaimer: str = ""
    unsubscribe_label: str = "Unsubscribe"
    view_in_browser_label: str = "View in browser"
    link_row: LinkRow | None = None

    def validate(self) -> None:
        super().validate()
        self.validate_box_surface(self.CONTEXT_NAME)
        if self.border_color:
            _validate_color(self.border_color, "footer.border_color")
        if self.image_width is not None and self.image_width <= 0:
            raise ValidationError(f"'footer.image_width' must be positive, got: {self.image_width}")

    def context(self, facts: dict[str, Any]) -> dict[str, Any]:
        resolved = {
            "image_alt": self.resolved_image_alt(),
            "image_width": self.resolved_image_width(),
            "copyright_html": self.resolved_copyright_html(facts),
            "footer_links": self.resolved_links(facts),
        }
        return {**super().context({}), **resolved, **facts}

    def raw_html(self) -> list[str]:
        return [self.disclaimer] if self.disclaimer else []

    def _text(self, facts: dict[str, Any]) -> str:
        """
        The closing block: disclaimer, copyright, then the links.

        The copyright line is **degraded back to text** from
        :meth:`resolved_copyright_html`, which is the shortest way to say why
        the entity/character question inverts between the two parts: that
        method emits ``&copy;`` on purpose, because a bare U+00A9 mis-decoded
        as latin-1 is mojibake in an HTML client that guesses the charset
        wrong. Here the MIME part declares its charset, so the character is
        correct and the entity would be the bug — and running it back through
        the degrader means one source of truth produces both spellings rather
        than two branches drifting apart.

        The sign-off image projects to nothing: chrome, like the masthead's
        logo.
        """
        links = [link_line(link.label, link.url) for link in self.resolved_links(facts)]
        return join_blocks(
            wrap(html_to_text(self.disclaimer)),
            wrap(html_to_text(self.resolved_copyright_html(facts))),
            wrap("\n".join(links)),
        )

    def resolved_copyright_html(self, facts: dict[str, Any]) -> str:
        """
        The copyright line, as HTML the builder produced.

        Two paths, one key, because the alternative is a conditional in the
        markup and therefore two rendering paths. Both escape through
        :func:`~pyhermes.builder.filters.escape_html_ascii`, so both spell a
        non-ASCII character as a reference: the default's ``&copy;`` was
        always written that way — a bare ``©`` mis-decoded as latin-1
        renders as ``Â©`` — and #148 was that the caller's path did not
        agree, leaving them to choose between an entity that escaped to
        literal text and a character the decision had already ruled out.
        The key is named ``_html`` because it *is* HTML by the time the
        template sees it — produced by the builder, never by the caller.
        """
        from .filters import escape_html_ascii

        row = self.link_row or LinkRow()
        if row.copyright:
            return escape_html_ascii(row.copyright)
        year = escape_html_ascii(str(facts.get("current_year", "")))
        firm = escape_html_ascii(str(facts.get("firm_name", "")))
        return f"&copy; {year} {firm}"

    def resolved_links(self, facts: dict[str, Any]) -> list[FooterLink]:
        """
        The links the row actually renders.

        ``link_row=None`` and ``LinkRow(links=None)`` both mean *the default
        pair*, built from the email's two URL facts and this footer's own
        labels — which is what keeps #64's label parameters working and an
        unset row byte-identical. An explicit list is taken exactly as given,
        **including an empty one**: which links an email carries is the
        caller's judgement, not this library's.
        """
        row = self.link_row or LinkRow()
        if row.links is not None:
            return list(row.links)
        pairs = (
            (self.unsubscribe_label, facts.get("unsubscribe_url", "")),
            (self.view_in_browser_label, facts.get("view_in_browser_url", "")),
        )
        return [FooterLink(label, str(url)) for label, url in pairs]

    def theme_context(self, theme: Theme) -> dict[str, Any]:
        """
        The box's colours, resolved — the same mechanism the header uses.

        The fallbacks are this region's own, which is why the mixin shares
        the *fields* and not this: the box draws type in **two** theme
        tokens, ``text.fine_print`` for the disclaimer and the lighter
        ``text.light`` for the copyright row, and the header's box draws it
        in one.

        **``text_color`` is deliberately coarser than the theme**: set, it
        collapses those two into one. That is the right trade rather than a
        shortcut — a caller sets it *because* they set a background, and a
        knob that recoloured only one of the two rows would leave the other
        illegible on the new ground. Unset, the two stay distinct.

        Link colour stays ``palette.accent``: the links are anchors, not box
        text, and per-link colour is an explicit non-goal.
        """
        return {
            "footer_background": self.background_color or theme.palette.wrapper_bg,
            "footer_text": self.text_color or theme.text.fine_print,
            "footer_text_muted": self.text_color or theme.text.light,
            "footer_border": self.border_color or theme.palette.rule,
        }

    def resolved_image_alt(self) -> str:
        from .images import EmailImage

        if self.image_alt:
            return self.image_alt
        if isinstance(self.image, EmailImage) and self.image.alt:
            return self.image.alt
        return ""

    def resolved_image_width(self) -> int:
        from .images import EmailImage

        if self.image_width is not None:
            return self.image_width
        if isinstance(self.image, EmailImage) and self.image.width is not None:
            return self.image.width
        return self.DEFAULT_IMAGE_WIDTH
