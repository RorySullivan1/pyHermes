"""
Email builder — the main orchestrator.

Provides two usage patterns:

1. Direct construction::

    email = Email(metadata={...})
    email.add_section(FullWidth(content=TextBlock("Hello"), title="Intro"))
    email.save(Path("out.html"))

2. Fluent builder::

    html = (EmailBuilder()
        .metadata({...})
        .section(FullWidth(content=TextBlock("Hello"), title="Intro"))
        .render())
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from svc.config import Config, get_config

from .containers import Container
from .engine import TemplateEngine
from .enums import EmbedStrategy
from .exceptions import SizeError
from .images import EmailImage, ImageAsset, dedupe_assets
from .models import EmailMetadata
from .regions import Footer, Header

# The shipped defaults, kept as module constants because they read as the
# thresholds themselves at a call site. The live values come from
# :func:`svc.config.get_config` at check time -- read those, not these, if
# you need what is actually in force.
_SIZE_LIMIT_KB = Config().size_limit_kb  # Gmail clips emails above this.
_SIZE_WARN_KB = Config().size_warn_kb


class Email:
    """
    Represents a complete, renderable email.

    The email is ``header | body | footer``: the metadata holds the facts,
    the two regions present them, and the body is the ordered section list.

    Args:
        metadata:     Dict or EmailMetadata with the email's facts.
        template_dir: Path to the ``templates/`` directory.  Defaults to
                      the copy packaged inside ``svc.builder``.
        header:       The masthead region. Defaults to the metadata's own
                      header, which the flat masthead keywords build — so an
                      email that never mentions a header is unchanged.
        footer:       The closing region, on exactly the same terms.

    Raises:
        ValidationError: If required metadata (``email_subject``, ``firm_name``,
            ``campaign_name``) is missing or empty.
    """

    def __init__(
        self,
        metadata: dict[str, Any] | EmailMetadata,
        template_dir: Path | None = None,
        header: Header | None = None,
        footer: Footer | None = None,
    ):
        self._engine = TemplateEngine(template_dir)

        if isinstance(metadata, dict):
            self._metadata = EmailMetadata(**metadata)
        else:
            self._metadata = metadata

        # Validation happens at construction time, not render time, so a
        # missing required field names itself instead of surfacing later as a
        # confusing render-time symptom.
        self._metadata.validate()

        self._header: Header = header if header is not None else self._metadata.header
        self._footer: Footer = footer if footer is not None else self._metadata.footer
        self._sections: list[Container] = []

    @property
    def metadata(self) -> EmailMetadata:
        """
        The email's own metadata — the facts it was built from.

        ``render()`` and ``assets()`` publish what the email *produces*; this
        publishes what it *knows*, so a consumer can read a fact rather than
        being told it twice. :func:`svc.delivery.build_message` uses it to
        default the ``Subject`` header.

        Read-only, and deliberately not a copy. Mutating the returned object
        after construction is unsupported: :meth:`validate` has already run,
        so a later edit is neither checked nor re-checked. A copy would be
        worse — mutating it would silently do nothing, which is a subtler
        trap than the one it closes. Note the object was never private in
        practice either: an ``Email`` built from an ``EmailMetadata``
        instance stores the caller's own object rather than a copy, so the
        caller already held this reference.
        """
        return self._metadata

    @property
    def header(self) -> Header:
        """
        The masthead region this email renders.

        Read-only for the same reasons as :attr:`metadata`; use
        :meth:`set_header` to swap it.
        """
        return self._header

    @property
    def footer(self) -> Footer:
        """
        The closing region this email renders.

        Read-only for the same reasons as :attr:`metadata`; use
        :meth:`set_footer` to swap it.
        """
        return self._footer

    # ------------------------------------------------------------------
    # Building
    # ------------------------------------------------------------------

    def set_header(self, header: Header) -> Email:
        """
        Replace the masthead region.

        Returns ``self`` for optional chaining.
        """
        self._header = header
        return self

    def set_footer(self, footer: Footer) -> Email:
        """
        Replace the closing region.

        Returns ``self`` for optional chaining.
        """
        self._footer = footer
        return self

    def add_section(self, container: Container) -> Email:
        """
        Append a section (container + component) to the email.

        Returns ``self`` for optional chaining.
        """
        self._sections.append(container)
        return self

    # ------------------------------------------------------------------
    # Image manifest
    # ------------------------------------------------------------------

    def images(self) -> list[EmailImage]:
        """
        Every image this email references: header, then sections in order,
        then footer.

        The footer participates even though no shipped variant carries an
        image. The slot has to exist or a variant that adds one — a signature
        block, a set of social icons — silently drops its bytes and renders a
        broken ``cid:`` reference, which is the failure the ``images()`` rule
        exists to prevent.
        """
        images = list(self._header.images())
        for section in self._sections:
            for component in section.components():
                images.extend(component.images())
        images.extend(self._footer.images())
        return images

    def assets(self) -> list[ImageAsset]:
        """
        The attachment manifest: the image parts a delivery layer must
        attach for this email to render.

        The builder composes the HTML and picks each image's ``src``, but it
        cannot attach a MIME part — that belongs to a delivery service
        (``svc/gmail``, ``svc/outlook``). This is the contract between them:
        for every ``src="cid:X"`` in the HTML, the entry describing what to
        attach as ``X``.

        Only ``CID`` images appear. Hosted images have no bytes to attach
        and data URIs carry their own, so both are absent by design. Repeat
        Content-IDs collapse to one entry, first-seen order preserved, so
        an image used in two sections is attached once.

        Returns:
            A list of :class:`~svc.builder.images.ImageAsset`, possibly empty.

        Example::

            html = email.render()
            for asset in email.assets():
                message.attach(asset.data, asset.mime_type,
                               cid=asset.content_id, filename=asset.filename)
        """
        assets = list(self._header.assets())
        for section in self._sections:
            assets.extend(section.assets())
        assets.extend(self._footer.assets())
        return dedupe_assets(assets)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render(self) -> str:
        """
        Render the complete email HTML.

        1. Render the header and footer regions into their skeleton slots.
        2. Render every section via its container.
        3. Inject all of it into the base skeleton.
        4. Validate final size against the 102 KB Gmail limit — on the
           *composed* document, so region bytes are inside the budget.

        Returns:
            Complete HTML string.

        Raises:
            SizeError: If the HTML exceeds 102 KB.
        """
        sections_html = "\n".join(section.render(self._engine) for section in self._sections)

        # Build skeleton context: the email's facts, plus one string per slot
        # each region fills. Every region goes through the same render path —
        # there is no separate "default footer" branch, because the default
        # *is* a default-constructed region.
        ctx = self._metadata.to_dict()
        ctx["sections_html"] = sections_html
        ctx.update(self._header.render_slots(self._engine, self._metadata.header_facts()))
        ctx.update(self._footer.render_slots(self._engine, self._metadata.footer_facts()))

        html = self._engine.render("base.html", ctx)

        # Size check
        self._validate_size(html, self._inline_image_hint())

        return html

    def save(self, output_path: str | Path) -> Path:
        """
        Render and write to disk.

        Args:
            output_path: Destination file path. A ``str`` is accepted -- the
                body has always coerced one, and :func:`svc.delivery.save_eml`
                takes the same union.

        Returns:
            The resolved output path.
        """
        html = self.render()
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8")
        return output_path

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_size(html: str, hint: str = "") -> None:
        """
        Check the rendered size against the Gmail clipping limit.

        Static, and takes the HTML as its only argument, so the size edges can
        be driven directly in tests. The thresholds come from the active
        :class:`~svc.config.Config` at call time, not import time.

        ``hint`` appends caller-supplied context to the failure message —
        ``render()`` uses it to name inlined images.
        """
        config = get_config()
        size_kb = len(html.encode("utf-8")) / 1024
        if size_kb > config.size_limit_kb:
            raise SizeError(
                f"Rendered email is {size_kb:.1f} KB, "
                f"exceeds {config.size_limit_kb} KB Gmail clipping limit.{hint}"
            )
        if size_kb > config.size_warn_kb:
            print(f"WARNING: Email size {size_kb:.1f} KB (target < {config.size_warn_kb} KB)")
        else:
            print(f"Email size: {size_kb:.1f} KB (OK)")

    def _inline_image_hint(self) -> str:
        """
        Name inlined images in a size failure when the email has any.

        A base64 data URI costs +33% on top of the raw bytes and lands
        entirely inside the HTML, so it is the usual reason an email that
        was comfortably under the limit suddenly is not.
        """
        inlined = [i for i in self.images() if i.strategy == EmbedStrategy.DATA_URI]
        if not inlined:
            return ""
        inline_kb = sum(len(i.data) for i in inlined) / 1024
        return (
            f" {len(inlined)} inlined image(s) contribute roughly "
            f"{inline_kb * 4 / 3:.1f} KB of base64 to that total; switching them to "
            f"EmailImage.attached() moves the bytes out of the HTML entirely."
        )


class EmailBuilder:
    """
    Fluent builder interface for constructing emails.

    Example::

        email = (EmailBuilder()
            .metadata({...})
            .section(FullWidth(content=CardGroup([...]), title="KPIs", highlight=True))
            .section(FullWidth(content=TextBlock("..."), title="Narrative"))
            .build())

        email.save(Path("output.html"))
    """

    def __init__(self, template_dir: Path | None = None):
        self._template_dir = template_dir
        self._email: Email | None = None

    def metadata(self, data: dict[str, Any] | EmailMetadata) -> EmailBuilder:
        """Set email metadata and initialise the Email instance."""
        self._email = Email(metadata=data, template_dir=self._template_dir)
        return self

    def header(self, header: Header) -> EmailBuilder:
        """
        Set the masthead region.

        Same sequencing rule as :meth:`section`: the email must exist first,
        so calling this before :meth:`metadata` is a programming error in the
        call sequence rather than rejected data.
        """
        if self._email is None:
            raise RuntimeError("Call .metadata() before setting the header.")
        self._email.set_header(header)
        return self

    def footer(self, footer: Footer) -> EmailBuilder:
        """
        Set the closing region.

        Same sequencing rule as :meth:`header`.
        """
        if self._email is None:
            raise RuntimeError("Call .metadata() before setting the footer.")
        self._email.set_footer(footer)
        return self

    def section(self, container: Container) -> EmailBuilder:
        """Append a section."""
        if self._email is None:
            raise RuntimeError("Call .metadata() before adding sections.")
        self._email.add_section(container)
        return self

    def build(self) -> Email:
        """Return the constructed Email object."""
        if self._email is None:
            raise RuntimeError("Call .metadata() before .build().")
        return self._email

    def assets(self) -> list[ImageAsset]:
        """Shortcut: the built email's attachment manifest."""
        return self.build().assets()

    def render(self) -> str:
        """Shortcut: build and render in one step."""
        return self.build().render()

    def save(self, path: str | Path) -> Path:
        """Shortcut: build, render, and save in one step."""
        return self.build().save(path)
