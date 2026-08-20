"""
Jinja2 template engine for the email builder.

Manages the Jinja2 environment, template loading, caching, and custom
filter registration. All template rendering flows through this class.
"""

from importlib import resources
from pathlib import Path
from typing import Any, Dict, Optional

import jinja2

from .exceptions import TemplateError
from .filters import register_all


def _packaged_template_dir() -> Path:
    """
    Locate the ``templates/`` directory shipped inside this package.

    Resolved via ``importlib.resources`` rather than by walking parent
    directories, so it works identically for an editable install (where it
    resolves into the source tree) and a real wheel install (where it
    resolves into site-packages).  The old ``parent.parent.parent`` walk
    only ever worked from a source checkout.

    Assumes an unpacked install — which is also what Jinja2's
    ``FileSystemLoader`` requires, since it needs a real filesystem path.
    """
    return Path(str(resources.files(__package__) / "templates"))


class TemplateEngine:
    """
    Wraps a Jinja2 Environment configured for HTML email templates.

    The engine is initialised with a template directory and provides
    methods to load and render templates. Custom filters for color
    validation, size checking, etc. are registered automatically.

    Args:
        template_dir: Root directory containing all templates.
                      Defaults to the ``templates/`` directory packaged
                      inside ``svc.builder``.
    """

    def __init__(self, template_dir: Optional[Path] = None):
        if template_dir is None:
            template_dir = _packaged_template_dir()
        self._template_dir = Path(template_dir).resolve()

        if not self._template_dir.is_dir():
            raise TemplateError(f"Template directory not found: {self._template_dir}")

        self._env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(self._template_dir)),
            autoescape=False,  # HTML emails need raw output
            trim_blocks=True,  # Strip newline after block tags
            lstrip_blocks=True,  # Strip leading whitespace before block tags
            keep_trailing_newline=True,
            undefined=jinja2.StrictUndefined,  # Fail on missing vars
        )

        # Register custom filters & tests
        register_all(self._env)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def environment(self) -> jinja2.Environment:
        """Return the underlying Jinja2 Environment."""
        return self._env

    @property
    def template_dir(self) -> Path:
        """Return the resolved template directory path."""
        return self._template_dir

    def get_template(self, name: str) -> jinja2.Template:
        """
        Load a template by name (relative to template_dir).

        Args:
            name: Template path, e.g. ``"base.html"`` or
                  ``"common/containers/full-width.html"``.

        Returns:
            Compiled Jinja2 Template.

        Raises:
            TemplateError: If the template file is not found.
        """
        try:
            return self._env.get_template(name)
        except jinja2.TemplateNotFound as exc:
            raise TemplateError(f"Template not found: {name}") from exc

    def render(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Load a template and render it with the given context.

        Args:
            template_name: Template path relative to template_dir.
            context: Dictionary of variables passed to the template.

        Returns:
            Rendered HTML string.

        Raises:
            TemplateError: If the template cannot be loaded or rendered.
        """
        try:
            tpl = self.get_template(template_name)
            return tpl.render(**context)
        except jinja2.TemplateError as exc:
            raise TemplateError(f"Error rendering {template_name}: {exc}") from exc

    def render_string(self, source: str, context: Dict[str, Any]) -> str:
        """
        Render a raw Jinja2 string (not from a file).

        Useful for one-off rendering of dynamic content.

        Args:
            source: Jinja2 template string.
            context: Dictionary of variables.

        Returns:
            Rendered string.
        """
        try:
            tpl = self._env.from_string(source)
            return tpl.render(**context)
        except jinja2.TemplateError as exc:
            raise TemplateError(f"Error rendering string template: {exc}") from exc
