"""
Jinja2 template engine for the email builder.

Manages the Jinja2 environment, template loading, caching, and custom
filter registration. All template rendering flows through this class.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import jinja2

from .exceptions import TemplateError
from .filters import register_all
from .medium import DEFAULT_MEDIUM, Medium
from .sizing import STANDARD_SIZES, SizeScheme, Spacing
from .theming import DEFAULT_THEME, Theme
from .typography import DEFAULT_FONTS


@runtime_checkable
class Renderer(Protocol):
    """
    What a container, component or region actually needs from an engine.

    :meth:`render`, and the theme in force — which is why a
    :class:`BoundEngine` can stand in for a :class:`TemplateEngine` anywhere
    in the section tree without a single call site changing.

    :attr:`medium` joined it in #163 on the same terms: a
    :class:`~pyhermes.document.page.Page` renders a page break for a paged medium
    and flattens for every other, which is a decision it can only make in
    Python. It was deliberately left off this protocol in #158, when nothing
    needed it — the bar for adding to a contract every container, component
    and region shares is a reader, not a plausible future one.

    :attr:`theme` exists because one consumer needs the theme as an *object*
    rather than as context: :class:`~pyhermes.builder.regions.Banner` resolves a
    :class:`~pyhermes.builder.theming.BannerPalette` against it in Python, so that
    the template reads one total palette instead of eight fallbacks. Reading
    it here rather than threading it through ``render_slots`` is what keeps
    that signature the one every region shares.
    """

    def render(self, template_name: str, context: dict[str, Any]) -> str: ...

    @property
    def theme(self) -> "Theme": ...

    @property
    def medium(self) -> "Medium": ...


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

    Initialised with a template directory; the custom filters for colour
    validation, size checking and the rest are registered automatically.

    **A medium may fork one template without forking the tree.**
    ``search_path`` names directories searched *before* the root, so a file
    at ``<medium>/text/text-block.html`` shadows ``text/text-block.html``
    for that medium and is invisible to every other. Nothing moves to turn
    this on: a medium with no forks has no directory at all, and every
    lookup falls through to the shared tree.

    How to fork one, and a caller's overlay searched ahead of it, are in
    `.claude/rules/media.md`.

    Args:
        template_dir: Root directory containing all templates.
                      Defaults to the ``templates/`` directory packaged
                      inside ``pyhermes.builder``.
        search_path:  Directories, relative to the root, searched ahead of
                      it in order. A name with no directory behind it is
                      not an error; it is what a medium that has forked
                      nothing looks like.
        overlays:     The caller's own directories, searched ahead of both.
                      Each must exist: unlike a medium's, a missing one is a
                      mistake.
    """

    def __init__(
        self,
        template_dir: Path | None = None,
        *,
        search_path: tuple[str, ...] = (),
        overlays: Sequence[Path | str] = (),
    ):
        if template_dir is None:
            template_dir = _packaged_template_dir()
        self._template_dir = Path(template_dir).resolve()

        if not self._template_dir.is_dir():
            raise TemplateError(f"Template directory not found: {self._template_dir}")

        self._overlays = tuple(Path(overlay).resolve() for overlay in overlays)
        for overlay in self._overlays:
            if not overlay.is_dir():
                raise TemplateError(f"Template overlay not found: {overlay}")

        self._search_path = tuple(search_path)
        # The caller's overlays, then the medium's forks, then the shared tree.
        # A FileSystemLoader over a medium directory that does not exist finds
        # nothing and raises nothing, the fall-through an unforked medium needs.
        loaders = [jinja2.FileSystemLoader(str(overlay)) for overlay in self._overlays]
        loaders.extend(
            jinja2.FileSystemLoader(str(self._template_dir / sub)) for sub in self._search_path
        )
        loaders.append(jinja2.FileSystemLoader(str(self._template_dir)))

        self._env = jinja2.Environment(
            loader=jinja2.ChoiceLoader(loaders),
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

    @property
    def search_path(self) -> tuple[str, ...]:
        """The directories searched ahead of the root, in order."""
        return self._search_path

    @property
    def overlays(self) -> tuple[Path, ...]:
        """The caller's directories, searched ahead of everything, resolved."""
        return self._overlays

    @property
    def medium(self) -> Medium:
        """The medium an unbound render gets, which is plain HTML."""
        return DEFAULT_MEDIUM

    @property
    def theme(self) -> Theme:
        """
        The theme an unbound render gets, which is the default.

        The floor :meth:`render` already guarantees by layering
        ``DEFAULT_THEME`` under the caller's context, stated as an object so
        a consumer that needs the theme itself does not have to re-derive it.
        """
        return DEFAULT_THEME

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

        Used once per :meth:`pyhermes.builder.email.Email.render` to carry the
        resolved theme and size scheme down the section tree. See
        :class:`BoundEngine` for why this rather than a threaded argument or
        an environment global — and note that the size epic (#45) rides this
        binder rather than building a second one, which is the whole reason
        it is keyword-general instead of theme-shaped.
        """
        return BoundEngine(self, dict(shared))

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        """
        Load a template and render it with the given context.

        Args:
            template_name: Template path relative to template_dir.
            context: Dictionary of variables passed to the template.

        The four shared namespaces are layered **under** ``context``: the
        engine guarantees a theme, a size scheme, a set of typefaces and a
        medium, and the document chooses each by binding its own over them
        (:meth:`bound`). That floor is what keeps rendering a component on its
        own a one-liner.

        Returns:
            Rendered HTML string.

        Raises:
            TemplateError: If the template cannot be loaded or rendered.
        """
        try:
            tpl = self.get_template(template_name)
            # The four namespaces every template reads have a floor here, so
            # rendering one component alone stays a one-liner. Email.render()
            # binds the resolved ones, and the caller's context is layered on
            # top, so that binding always wins over this floor.
            return tpl.render(
                **{
                    "theme": DEFAULT_THEME,
                    "size": STANDARD_SIZES,
                    "font": DEFAULT_FONTS,
                    "medium": DEFAULT_MEDIUM,
                    **context,
                }
            )
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
            # Same four-namespace floor as render(); see the note there.
            return tpl.render(
                **{
                    "theme": DEFAULT_THEME,
                    "size": STANDARD_SIZES,
                    "font": DEFAULT_FONTS,
                    "medium": DEFAULT_MEDIUM,
                    **context,
                }
            )
        except jinja2.TemplateError as exc:
            raise TemplateError(f"Error rendering string template: {exc}") from exc


@dataclass(frozen=True)
class BoundEngine:
    """
    An engine view that merges email-level values into every render context.

    The problem it solves: a value owned by the *email* — the resolved theme,
    the resolved size scheme — has to reach every template in the tree,
    including component templates several layers down that know nothing
    about it. Threading it through
    every ``render()`` signature would change containers, components and
    regions alike; setting it on the Jinja environment would make the engine
    stateful, and two emails with different themes sharing an engine could
    then interleave.

    A binder avoids both. :meth:`TemplateEngine.bound` returns one per
    ``Email.render()`` call, so the shared values cannot leak between renders,
    and everything downstream keeps calling ``engine.render(path, ctx)``
    unchanged — it is simply handed the view instead of the engine.

    **Shared values are layered over the caller's context, not under it**,
    the same way :meth:`pyhermes.builder.regions.Region.context` layers the email's
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

    @property
    def medium(self) -> "Medium":
        """The medium this render is bound to, falling through to the engine's."""
        bound = self.shared.get("medium")
        return bound if isinstance(bound, Medium) else self.engine.medium

    @property
    def theme(self) -> "Theme":
        """
        The theme this render is bound to, falling through to the engine's.

        Same precedence as :meth:`render` applies to the context: a bound
        theme wins, and an engine bound without one still guarantees the
        default rather than ``None``.
        """
        bound = self.shared.get("theme")
        return bound if isinstance(bound, Theme) else self.engine.theme


def scheme_of(engine: Renderer) -> SizeScheme:
    """The size scheme ``engine`` is bound to, or the shipped floor."""
    shared = getattr(engine, "shared", {})
    scheme = shared.get("size") if isinstance(shared, Mapping) else None
    return scheme if isinstance(scheme, SizeScheme) else STANDARD_SIZES


def cell_width_of(engine: Renderer) -> int:
    """The width of the cell ``engine`` is rendering into, or the frame's content width (#263)."""
    shared = getattr(engine, "shared", {})
    width = shared.get("cell_width") if isinstance(shared, Mapping) else None
    return width if isinstance(width, int) else int(scheme_of(engine).frame.inner)


def _surface_theme(engine: Renderer) -> Theme | None:
    """The theme a section's own ground replaced, or ``None`` off such a ground."""
    shared = getattr(engine, "shared", {})
    theme = shared.get("surface_theme") if isinstance(shared, Mapping) else None
    return theme if isinstance(theme, Theme) else None


def grounded(engine: Renderer, ink: Theme | None) -> Renderer:
    """``engine`` rendering type in ``ink``, a section's ground (#266); itself for ``None``."""
    if ink is None:
        return engine
    return rebind(engine, theme=ink, surface_theme=_surface_theme(engine) or engine.theme)


def on_ground(engine: Renderer) -> bool:
    """Whether ``engine`` renders onto a section's own ground rather than the theme's."""
    return _surface_theme(engine) is not None


def own_surface(engine: Renderer) -> Renderer:
    """``engine`` back on the theme's type, for a block that paints its own surface."""
    surface = _surface_theme(engine)
    return engine if surface is None else rebind(engine, theme=surface, surface_theme=None)


def rebind(engine: Renderer, **shared: Any) -> Renderer:
    """``engine`` with ``shared`` bound over whatever it already had."""
    if isinstance(engine, BoundEngine):
        return BoundEngine(engine.engine, {**engine.shared, **shared})
    if isinstance(engine, TemplateEngine):
        return engine.bound(**shared)
    raise TypeError(f"cannot bind onto {type(engine).__name__}")


def respaced(engine: Renderer, spacing: Spacing | None, owner: str) -> Renderer:
    """
    ``engine`` with ``owner``'s spacing applied to the bound scheme, for its subtree.

    ``None`` returns ``engine`` itself, so an object without an override
    renders exactly as it did before the mechanism existed.

    Raises:
        ValidationError: If a token here is unsafe on this medium.
    """
    if spacing is None:
        return engine
    spacing.check_medium(engine.medium.paged, engine.medium.name, owner)
    return rebind(engine, size=spacing.applied_to(scheme_of(engine)))


#: What ``template_overlay=`` takes: one directory, or several in search order.
TemplateOverlay = Path | str | Sequence[Path | str] | None


def overlay_dirs(overlay: TemplateOverlay) -> tuple[Path | str, ...]:
    """``template_overlay`` as the sequence :class:`TemplateEngine` takes."""
    if overlay is None:
        return ()
    if isinstance(overlay, (str, Path)):
        return (overlay,)
    return tuple(overlay)
