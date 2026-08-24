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

# The shipped defaults, kept as module constants because they read as the
# thresholds themselves at a call site. The live values come from
# :func:`svc.config.get_config` at check time -- read those, not these, if
# you need what is actually in force.
_SIZE_LIMIT_KB = Config().size_limit_kb  # Gmail clips emails above this.
_SIZE_WARN_KB = Config().size_warn_kb


class Email:
    """
    Represents a complete, renderable email.

    Args:
        metadata:     Dict or EmailMetadata with skeleton-level variables.
        template_dir: Path to the ``templates/`` directory.  Defaults to
                      the copy packaged inside ``svc.builder``.

    Raises:
        ValidationError: If required metadata (``email_subject``, ``firm_name``,
            ``campaign_name``) is missing or empty.
    """

    def __init__(
        self,
        metadata: dict[str, Any] | EmailMetadata,
        template_dir: Path | None = None,
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

    # ------------------------------------------------------------------
    # Building
    # ------------------------------------------------------------------

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
        Every image this email references, metadata first, then sections
        in order.
        """
        images = list(self._metadata.images())
        for section in self._sections:
            for component in section.components():
                images.extend(component.images())
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
        assets = list(self._metadata.assets())
        for section in self._sections:
            assets.extend(section.assets())
        return dedupe_assets(assets)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render(self) -> str:
        """
        Render the complete email HTML.

        1. Render every section via its container.
        2. Inject rendered sections into the base skeleton.
        3. Validate final size against the 102 KB Gmail limit.

        Returns:
            Complete HTML string.

        Raises:
            SizeError: If the HTML exceeds 102 KB.
        """
        # Render sections
        sections_html = "\n".join(section.render(self._engine) for section in self._sections)

        # Build skeleton context
        ctx = self._metadata.to_dict()
        ctx["sections_html"] = sections_html

        html = self._engine.render("base.html", ctx)

        # Size check
        self._validate_size(html, self._inline_image_hint())

        return html

    def save(self, output_path: Path) -> Path:
        """
        Render and write to disk.

        Args:
            output_path: Destination file path.

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

    def save(self, path: Path) -> Path:
        """Shortcut: build, render, and save in one step."""
        return self.build().save(path)
