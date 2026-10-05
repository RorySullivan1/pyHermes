"""
``Email`` — a :class:`~pyhermes.builder.document.Document` with a masthead.

Two construction patterns, the fluent one preferred::

    email = (EmailBuilder()
        .metadata({...})
        .section(FullWidth(content=TextBlock("Hello"), title="Intro"))
        .build())

Everything generic — the three projections, the binder, the section tree —
is ``Document``'s. What is an email's and nothing else's lives here: the
four-slot skeleton's regions, and the facts each is handed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

from pyhermes.config import Config
from pyhermes.email import EMAIL_MEDIUM

from .containers import Container
from .document import Document, RegionFacts
from .engine import TemplateOverlay
from .exceptions import ValidationError
from .images import ImageAsset
from .medium import Medium
from .models import EmailMetadata
from .regions import Banner, Footer, Header


class Email(Document):
    """
    A document read in a mail client: ``strip | masthead | body | footer``.

    The metadata holds the facts, the three regions present them, and the
    body is the ordered section list. Everything generic is
    :class:`~pyhermes.builder.document.Document`'s; what is here is the region
    set and the facts each one is handed.

    Args:
        metadata:     Dict or EmailMetadata with the email's facts.
        template_dir: Path to the ``templates/`` directory.  Defaults to
                      the copy packaged inside ``pyhermes.builder``.
        header:       The strip at the top. Defaults to the metadata's own,
                      which the flat masthead keywords build — so an email
                      that never mentions a header is unchanged.
        banner:       The masthead, on the same terms.
        footer:       The closing region, on the same terms.
        medium:       Where this is read. An ``Email`` pins the email medium;
                      the argument exists so a test can drive a different
                      constraint set.
        config, template_overlay: As ``Document`` takes them.

    Raises:
        ValidationError: If required metadata (``email_subject``, ``firm_name``,
            ``campaign_name``) is missing or empty.
    """

    METADATA: ClassVar[type[EmailMetadata]] = EmailMetadata

    #: Narrows what ``Document`` stores. An ``Email`` is constructed through
    #: :attr:`METADATA`, so the facts it holds are always an
    #: :class:`~pyhermes.builder.models.EmailMetadata` — the annotation says so
    #: rather than every reader asserting it.
    _metadata: EmailMetadata

    def __init__(
        self,
        metadata: dict[str, Any] | EmailMetadata,
        template_dir: Path | None = None,
        header: Header | None = None,
        banner: Banner | None = None,
        footer: Footer | None = None,
        medium: Medium | None = None,
        *,
        config: Config | None = None,
        template_overlay: TemplateOverlay = None,
    ):
        super().__init__(
            metadata,
            template_dir,
            medium if medium is not None else EMAIL_MEDIUM,
            config=config,
            template_overlay=template_overlay,
        )
        self._header: Header = header if header is not None else self._metadata.header
        self._banner: Banner = banner if banner is not None else self._metadata.banner
        self._footer: Footer = footer if footer is not None else self._metadata.footer

    @property
    def metadata(self) -> EmailMetadata:
        """The email's own facts. See :attr:`Document.metadata`."""
        return self._metadata

    @property
    def header(self) -> Header:
        """
        The strip at the top of the email.

        Read-only for the same reasons as :attr:`metadata`; use
        :meth:`set_header` to swap it.
        """
        return self._header

    @property
    def banner(self) -> Banner:
        """
        The masthead region this email renders.

        Read-only for the same reasons as :attr:`metadata`; use
        :meth:`set_banner` to swap it.
        """
        return self._banner

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
        Replace the strip at the top of the email.

        Returns ``self`` for optional chaining.
        """
        self._header = header
        return self

    def set_banner(self, banner: Banner) -> Email:
        """
        Replace the masthead region.

        Returns ``self`` for optional chaining.
        """
        self._banner = banner
        return self

    def set_footer(self, footer: Footer) -> Email:
        """
        Replace the closing region.

        Returns ``self`` for optional chaining.
        """
        self._footer = footer
        return self

    def validate(self) -> None:
        """
        As :meth:`Document.validate`, and a stamp has its strip.

        An email sets its stamp in the header strip (#342), so an ``EmptyHeader``
        would drop a DRAFT silently: that is refused, naming the fix.
        """
        super().validate()
        if self._metadata.stamp and not self._header.TEMPLATE_PATHS:
            raise ValidationError(
                f"this email is stamped {self._metadata.stamp!r}, and an email shows its "
                "stamp in the header strip, which an EmptyHeader omits. Use a Header."
            )

    def leading_regions(self) -> tuple[RegionFacts, ...]:
        """The strip and the masthead, each with the facts it renders."""
        return (
            (self._header, self._metadata.header_facts()),
            (self._banner, self._metadata.banner_facts()),
        )

    def trailing_regions(self) -> tuple[RegionFacts, ...]:
        """The closing block, on the same terms."""
        return ((self._footer, self._metadata.footer_facts()),)


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

    def __init__(
        self,
        template_dir: Path | None = None,
        *,
        config: Config | None = None,
        template_overlay: TemplateOverlay = None,
    ):
        self._template_dir = template_dir
        self._config = config
        self._template_overlay = template_overlay
        self._email: Email | None = None

    def metadata(self, data: dict[str, Any] | EmailMetadata) -> EmailBuilder:
        """Set email metadata and initialise the Email instance."""
        self._email = Email(
            metadata=data,
            template_dir=self._template_dir,
            config=self._config,
            template_overlay=self._template_overlay,
        )
        return self

    def header(self, header: Header) -> EmailBuilder:
        """
        Set the strip at the top of the email.

        Same sequencing rule as :meth:`section`: the email must exist first,
        so calling this before :meth:`metadata` is a programming error in the
        call sequence rather than rejected data.
        """
        if self._email is None:
            raise RuntimeError("Call .metadata() before setting the header.")
        self._email.set_header(header)
        return self

    def banner(self, banner: Banner) -> EmailBuilder:
        """
        Set the masthead region.

        Same sequencing rule as :meth:`header`.
        """
        if self._email is None:
            raise RuntimeError("Call .metadata() before setting the banner.")
        self._email.set_banner(banner)
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

    def text(self) -> str:
        """Terminal: build and return the plain-text projection."""
        return self.build().text()

    def render(self) -> str:
        """Shortcut: build and render in one step."""
        return self.build().render()

    def save(self, path: str | Path) -> Path:
        """Shortcut: build, render, and save in one step."""
        return self.build().save(path)
