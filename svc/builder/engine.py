"""
Jinja2 template engine for the email builder.

Manages the Jinja2 environment, template loading, caching, and custom
filter registration. All template rendering flows through this class.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import jinja2

from .exceptions import TemplateError
from .filters import register_all
from .theming import DEFAULT_THEME


@runtime_checkable
class Renderer(Protocol):
    """
    What a container, component or region actually needs from an engine.

    Only :meth:`render` — which is why a :class:`BoundEngine` can stand in
    for a :class:`TemplateEngine` anywhere in the section tree without a
    single call site changing.
    """

    def render(self, template_name: str, context: dict[str, Any]) -> str: ...


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

    def __init__(self, template_dir: Path | None = None):
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

    def bound(self, **shared: Any) -> "BoundEngine":
        """
        A view of this engine that adds ``shared`` to every render context.

        Used once per :meth:`svc.builder.email.Email.render` to carry the
        resolved theme down the section tree. See :class:`BoundEngine` for
        why this rather than a threaded argument or an environment global.
        """
        return BoundEngine(self, dict(shared))

    def render(self, template_name: str, context: dict[str, Any]) -> str:
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
            # Every template reads colours from ``theme`` since #49, so the
            # engine guarantees one is present: rendering a component on its
            # own stays a one-liner, and it renders in the shipped palette.
            # The *choice* of theme belongs to Email.render(), which binds a
            # resolved one — and because the caller's context is layered on
            # top here, that binding always wins over this floor.
            return tpl.render(**{"theme": DEFAULT_THEME, **context})
        except jinja2.TemplateError as exc:
            raise TemplateError(f"Error rendering {template_name}: {exc}") from exc

    def render_string(self, source: str, context: dict[str, Any]) -> str:
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
            # Same theme floor as render(); see the note there.
            return tpl.render(**{"theme": DEFAULT_THEME, **context})
        except jinja2.TemplateError as exc:
            raise TemplateError(f"Error rendering string template: {exc}") from exc


@dataclass(frozen=True)
class BoundEngine:
    """
    An engine view that merges email-level values into every render context.

    The problem it solves: a value owned by the *email* — the resolved theme —
    has to reach every template in the tree, including component templates
    several layers down that know nothing about it. Threading it through
    every ``render()`` signature would change containers, components and
    regions alike; setting it on the Jinja environment would make the engine
    stateful, and two emails with different themes sharing an engine could
    then interleave.

    A binder avoids both. :meth:`TemplateEngine.bound` returns one per
    ``Email.render()`` call, so the shared values cannot leak between renders,
    and everything downstream keeps calling ``engine.render(path, ctx)``
    unchanged — it is simply handed the view instead of the engine.

    **Shared values are layered over the caller's context, not under it**,
    the same way :meth:`svc.builder.regions.Region.context` layers the email's
    facts over a region's own keys: what the email owns cannot be shadowed
    from below, even by accident.
    """

    engine: TemplateEngine
    shared: Mapping[str, Any]

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        """Render with ``shared`` layered over ``context``."""
        return self.engine.render(template_name, {**context, **self.shared})

    @property
    def template_dir(self) -> Path:
        """The underlying engine's template directory."""
        return self.engine.template_dir
