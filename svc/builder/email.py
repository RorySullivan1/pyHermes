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
from typing import Any, Dict, List, Optional, Union

from .engine import TemplateEngine
from .containers import Container
from .models import EmailMetadata
from .exceptions import SizeError


# Gmail clips emails above this threshold (bytes).
_SIZE_LIMIT_KB = 102
_SIZE_WARN_KB = 90


class Email:
    """
    Represents a complete, renderable email.

    Args:
        metadata:     Dict or EmailMetadata with skeleton-level variables.
        template_dir: Path to the ``templates/`` directory.  Defaults to
                      ``<project_root>/templates/``.
    """

    def __init__(
        self,
        metadata: Union[Dict[str, Any], EmailMetadata],
        template_dir: Optional[Path] = None,
    ):
        self._engine = TemplateEngine(template_dir)

        if isinstance(metadata, dict):
            self._metadata = EmailMetadata(**metadata)
        else:
            self._metadata = metadata

        self._sections: List[Container] = []

    # ------------------------------------------------------------------
    # Building
    # ------------------------------------------------------------------

    def add_section(self, container: Container) -> "Email":
        """
        Append a section (container + component) to the email.

        Returns ``self`` for optional chaining.
        """
        self._sections.append(container)
        return self

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
        sections_html = "\n".join(
            section.render(self._engine) for section in self._sections
        )

        # Build skeleton context
        ctx = self._metadata.to_dict()
        ctx["sections_html"] = sections_html

        html = self._engine.render("base.html", ctx)

        # Size check
        self._validate_size(html)

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
    def _validate_size(html: str) -> None:
        size_kb = len(html.encode("utf-8")) / 1024
        if size_kb > _SIZE_LIMIT_KB:
            raise SizeError(
                f"Rendered email is {size_kb:.1f} KB, "
                f"exceeds {_SIZE_LIMIT_KB} KB Gmail clipping limit."
            )
        if size_kb > _SIZE_WARN_KB:
            print(f"WARNING: Email size {size_kb:.1f} KB (target < {_SIZE_WARN_KB} KB)")
        else:
            print(f"Email size: {size_kb:.1f} KB (OK)")


class EmailBuilder:
    """
    Fluent builder interface for constructing emails.

    Example::

        email = (EmailBuilder()
            .metadata({...})
            .section(Highlight(content=KpiStrip([...]), title="KPIs"))
            .section(FullWidth(content=TextBlock("..."), title="Narrative"))
            .build())

        email.save(Path("output.html"))
    """

    def __init__(self, template_dir: Optional[Path] = None):
        self._template_dir = template_dir
        self._email: Optional[Email] = None

    def metadata(self, data: Union[Dict[str, Any], EmailMetadata]) -> "EmailBuilder":
        """Set email metadata and initialise the Email instance."""
        self._email = Email(metadata=data, template_dir=self._template_dir)
        return self

    def section(self, container: Container) -> "EmailBuilder":
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

    def render(self) -> str:
        """Shortcut: build and render in one step."""
        return self.build().render()

    def save(self, path: Path) -> Path:
        """Shortcut: build, render, and save in one step."""
        return self.build().save(path)
