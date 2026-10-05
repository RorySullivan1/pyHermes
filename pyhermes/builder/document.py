"""
``Document`` — the medium-neutral product: metadata, regions, a section tree.

What every destination has in common. Three projections of one tree —
:meth:`render` to markup, :meth:`text` to the plain-text part and
:meth:`assets` to the images a delivery layer must carry — plus the one
resolution point where the theme, density, typefaces and medium are bound.

A subclass supplies its regions through :meth:`leading_regions` and
:meth:`trailing_regions`; :class:`~pyhermes.builder.email.Email` is the worked
example. `.claude/rules/builder-architecture.md` carries the layer model.
"""

from __future__ import annotations

import functools
import math
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager, nullcontext
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Concatenate, ParamSpec, Self, TypeVar

from pyhermes.config import Config, config_override, get_config

from .apparatus import (
    UNRESOLVED,
    check_unique,
    cited_keys,
    note_anchor,
    note_ref_anchor,
    references,
)
from .components import Component, Contents, Endnotes, Exhibit, descendants, leaves
from .containers import Appendices, Container, FullWidth, OnlySections
from .engine import Renderer, TemplateEngine, TemplateOverlay, overlay_dirs, scheme_of
from .enums import EmbedStrategy, SizeTheme
from .exceptions import ValidationError
from .exhibits import legends
from .images import EmailImage, ImageAsset, dedupe_assets
from .medium import DEFAULT_MEDIUM, Medium, walking_in
from .models import DocumentMetadata, Footnote
from .research import Bibliography
from .sizing import (
    MEDIUM_DENSITIES,
    PRINT_DENSITIES,
    FrameGeometry,
    SizeScheme,
    Spacing,
    resolve_size_scheme,
)
from .textgen import join_sections
from .theming import resolve_theme
from .typography import resolve_font_theme

if TYPE_CHECKING:  # pragma: no cover - regions imports models, which imports this
    from .regions import Region

#: One region and the facts handed down to it. Ordered pairs rather than a
#: mapping, because the skeleton's order is part of the contract.
RegionFacts = tuple["Region", dict[str, Any]]

_P = ParamSpec("_P")
_R = TypeVar("_R")
_D = TypeVar("_D", bound="Document")


def _under_own_config(
    method: Callable[Concatenate[_D, _P], _R],
) -> Callable[Concatenate[_D, _P], _R]:
    """Run ``method`` with the document's own config in force, when it has one."""

    @functools.wraps(method)
    def wrapper(self: _D, /, *args: _P.args, **kwargs: _P.kwargs) -> _R:
        with self.configured():
            return method(self, *args, **kwargs)

    return wrapper


class Document:
    """
    A renderable document: its facts, its sections, and where it is read.

    Construct with a mapping of facts or a :class:`~pyhermes.builder.models.
    DocumentMetadata`, add sections in order, then render. The medium decides
    the skeleton, the page and the checks the composed document must pass; a
    document that never mentions one gets plain HTML.

    **Regions are a subclass's business.** This class knows only that some
    render before the body and some after — enough to fill their slots, walk
    their images and project their text in the right order, and not enough to
    care that an email has a masthead and a paged document has a cover.

    Args:
        metadata:     Mapping of facts, or a metadata instance.
        template_dir: Root of the templates. Defaults to the packaged copy.
        medium:       Where this is going to be read.
        config:       Limits and policy for this document alone, in force while
                      it validates and renders; ``None`` reads the ambient one.
        template_overlay: Your own template directories, searched before the
                      medium's and the packaged ones: a forked template, or
                      the template of a component you defined.

    Raises:
        ValidationError: If a required fact is missing or empty.
    """

    #: What a mapping of facts is coerced into. A subclass narrows it.
    METADATA: ClassVar[type[DocumentMetadata]] = DocumentMetadata

    def __init__(
        self,
        metadata: dict[str, Any] | DocumentMetadata,
        template_dir: Path | None = None,
        medium: Medium | None = None,
        *,
        config: Config | None = None,
        template_overlay: TemplateOverlay = None,
    ):
        if config is not None and not isinstance(config, Config):
            raise TypeError(f"config must be a Config, got {type(config).__name__}")
        self._config = config
        # The medium is settled first: it names the templates this engine
        # searches before the shared tree.
        self._medium: Medium = medium if medium is not None else DEFAULT_MEDIUM
        self._engine = TemplateEngine(
            template_dir,
            search_path=self._medium.template_search_path,
            overlays=overlay_dirs(template_overlay),
        )

        if isinstance(metadata, dict):
            self._metadata: DocumentMetadata = self.METADATA(**metadata)
        else:
            self._metadata = metadata

        # Validation happens at construction time, not render time, so a
        # missing required field names itself instead of surfacing later as a
        # confusing render-time symptom.
        with self.configured():
            self._metadata.validate()
            check_density(self._metadata.size_theme, self._medium)
        self._sections: list[Container] = []

    # ------------------------------------------------------------------
    # What it knows
    # ------------------------------------------------------------------

    @property
    def metadata(self) -> DocumentMetadata:
        """
        The facts this document was built from.

        Read-only, and deliberately not a copy: :meth:`validate` has already
        run, so a later edit is neither checked nor re-checked, and a copy
        would make mutating it silently do nothing — a subtler trap than the
        one it closes.
        """
        return self._metadata

    @property
    def config(self) -> Config | None:
        """The config this document pins, or ``None`` when it reads the ambient one."""
        return self._config

    def configured(self) -> AbstractContextManager[object]:
        """
        A context with this document's config in force, and its tree walked as its medium.

        The medium is what ``Only`` and ``OnlySections`` read (#365), so every
        projection sees the blocks its medium shows and no others.
        """
        return self._scoped()

    @contextmanager
    def _scoped(self) -> Iterator[None]:
        config = config_override(self._config) if self._config is not None else nullcontext()
        with config, walking_in(self._medium.name):
            yield

    @property
    def medium(self) -> Medium:
        """
        Where this document is going to be read.

        Read-only: a medium decides the skeleton and the checks, so swapping
        one mid-life would leave a document that had already validated
        against rules it no longer runs.
        """
        return self._medium

    def leading_regions(self) -> tuple[RegionFacts, ...]:
        """The regions rendered before the body, in skeleton order."""
        return ()

    def trailing_regions(self) -> tuple[RegionFacts, ...]:
        """The regions rendered after the body, in skeleton order."""
        return ()

    def add_section(self, container: Container) -> Self:
        """
        Append a section. Returns ``self`` for optional chaining.

        Raises:
            ValidationError: If ``container`` is not a section, or if it claims an
                anchor the document already has; the document is left as it was.
        """
        if not isinstance(container, Container):
            hint = (
                "Wrap a block in a section, e.g. FullWidth(...)."
                if isinstance(container, Component)
                else "Pass a section such as FullWidth(...)."
            )
            raise ValidationError(
                f"add_section takes a section, got {type(container).__name__}. {hint}"
            )
        with self.configured():
            self._add(container)
        return self

    def _add(self, container: Container) -> None:
        """Append ``container`` once its subtree passes this medium's checks, or leave things be."""
        for owner, spacing in _spacings(container):
            spacing.check_medium(self._medium.paged, self._medium.name, owner)
        if self._medium.email and (aligned := _valigned(container)):
            raise ValidationError(
                f"{aligned[0]} sets valign={aligned[1]!r}, which an email refuses: a split's "
                "columns align at the top until an Outlook check shows the Word engine honours "
                "valign on the ghost table (#356). It is accepted on paper."
            )
        for legend in legends(_held(container)):
            legend.check_theme(self._metadata.theme)
        if isinstance(container, Appendices) and any(
            isinstance(section, Appendices) for section in self._sections
        ):
            raise ValidationError(
                "a document has one Appendices; a second would letter its own from A again."
            )
        self._sections.append(container)
        try:
            self._walk()
            self._check_one_bibliography()
            check_unique(self._anchors())
        except ValidationError:
            self._sections.pop()
            self._walk()
            raise

    def _flat_sections(self) -> list[Container]:
        """
        Every section in reading order, a page's own flattened in.

        A :class:`~pyhermes.document.page.Page` is a sheet boundary, not a section a
        reader navigates to, so the sections inside it stand in for it.
        """
        return [inner for section in self._sections for inner in _flatten(section)]

    @_under_own_config
    def validate(self) -> None:
        """
        Check what only the finished tree can answer, before any template loads.

        Every ``#fragment`` in caller markup must land on an anchor this
        document defines, and every ``[@key]`` on a reference its bibliography
        lists. It runs at the start of each projection rather than in
        :meth:`add_section`, because a reference may name a section not yet
        added; call it directly to check sooner.

        Raises:
            ValidationError: Naming the first dangling reference or citation and who made it.
        """
        self._walk()
        listed = bibliography.keys if (bibliography := self._bibliography()) else set()
        for owner, _, marked in self._marked():
            for key in (k for copy in marked for k in cited_keys(copy)):
                if key not in listed:
                    raise ValidationError(
                        f"{owner} cites [@{key}], which no Bibliography "
                        "in this document lists. Check the key, or add the Reference."
                    )
        defined = {anchor for anchor, _ in self._anchors()}
        for owner, html in self._raw_html():
            for target in references(html):
                if target not in defined:
                    raise ValidationError(
                        f"{owner} links to #{target}, which nothing in this document "
                        "defines. Check the anchor, or the numbering it assumed."
                    )

    # ------------------------------------------------------------------
    # The three projections
    # ------------------------------------------------------------------

    @_under_own_config
    def images(self) -> list[EmailImage]:
        """
        Every image this document references, in render order.

        Leading regions, then sections, then trailing ones. A region with no
        image today still participates: the slot has to exist, or a variant
        that adds one silently drops its bytes and renders a broken
        reference, which is the failure the ``images()`` rule exists to
        prevent.
        """
        images = [image for region, _ in self.leading_regions() for image in region.images()]
        for section in self._sections:
            images.extend(section.images())
        images.extend(image for region, _ in self.trailing_regions() for image in region.images())
        return images

    @_under_own_config
    def assets(self) -> list[ImageAsset]:
        """
        The attachment manifest: what a delivery layer must carry.

        Only ``CID`` images appear — hosted ones have no bytes to attach and
        data URIs carry their own. Repeat Content-IDs collapse to one entry,
        first-seen order preserved.
        """
        assets = [asset for region, _ in self.leading_regions() for asset in region.assets()]
        for section in self._sections:
            assets.extend(section.assets())
        assets.extend(asset for region, _ in self.trailing_regions() for asset in region.assets())
        return dedupe_assets(assets)

    @_under_own_config
    def render(self) -> str:
        """
        Render the complete document.

        Resolve the theme, density, typefaces and page once and bind them;
        render each region into the slots it fills and every section through
        its container; drop all of it into the medium's skeleton; then run
        the medium's constraints over the *composed* document, so region
        bytes are inside whatever budget it sets.
        """
        self.validate()
        engine = self._bound_engine()
        ctx = self._metadata.to_dict()
        ctx.update(self._body_context(engine, self._body_sections()))
        for region, facts in self.leading_regions() + self.trailing_regions():
            ctx.update(region.render_slots(engine, facts))

        if self._metadata.stamp:
            ctx["stamp_type"] = stamp_type(self._metadata.stamp, scheme_of(engine).frame)
        html = engine.render(self._medium.skeleton, ctx)
        self._medium.validate(html, self._inline_image_hint())
        return html

    @_under_own_config
    def text(self) -> str:
        """
        The plain-text projection: a second projection of the same tree.

        No template is loaded and no HTML is produced anywhere on this path,
        because stripping rendered markup is exactly what would turn a KPI
        strip and a data table into garbage. Nothing here resolves a theme, a
        density or a font: all three are markup concerns, which is what makes
        one house format possible at all. Deterministic — no clock, no
        randomness, no override.
        """
        self.validate()
        endnotes = self._endnotes()
        return join_sections(
            f"[{self._metadata.stamp}]" if self._metadata.stamp else "",
            *(region.text(facts) for region, facts in self.leading_regions()),
            *(section.text() for section in self._sections),
            endnotes.text() if endnotes else "",
            *(region.text(facts) for region, facts in self.trailing_regions()),
        )

    @_under_own_config
    def rendered_sections(self) -> list[tuple[str, str]]:
        """
        ``(label, markup)`` for each body section, rendered as :meth:`render` renders it.

        The label is the section's title, else its class, after its position.
        No constraint runs, because no document is composed: this is what a
        size report uses to say which section spent the bytes (#259).
        """
        self.validate()
        engine = self._bound_engine()
        return [
            (f"section {n}: {section.heading() or type(section).__name__}", section.render(engine))
            for n, section in enumerate(self._body_sections(), start=1)
        ]

    def save(self, output_path: str | Path) -> Path:
        """Render and write to disk, returning the resolved path."""
        html = self.render()
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8")
        return output_path

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _bound_engine(self) -> Renderer:
        """
        The one resolution point. Every template — skeleton, regions,
        containers, components — reads the same values, because they all
        render through this binder rather than looking any of them up.
        """
        return self._engine.bound(
            theme=resolve_theme(self._metadata.theme),
            size=resolve_size_scheme(self._metadata.size_theme).with_page(self._medium.page_format),
            font=resolve_font_theme(self._metadata.font_theme),
            medium=self._medium,
        )

    def _body_sections(self) -> list[Container]:
        """The sections the body renders, endnotes appended where there is no sheet foot."""
        # A section list for other media renders nothing here, and leaves no line (#365).
        sections = [
            section
            for section in self._sections
            if not isinstance(section, OnlySections) or section.shown_in(self._medium.name)
        ]
        if (endnotes := self._endnotes()) and not self._medium.paged:
            # A mail client has no sheet foot, so the notes a page floats
            # there are gathered after the last section instead.
            sections.append(FullWidth(content=endnotes))
        return sections

    def _body_context(self, engine: Renderer, sections: list[Container]) -> dict[str, Any]:
        """The skeleton's body keys: every section in reading order. A brochure adds its sides."""
        return {"sections_html": "\n".join(section.render(engine) for section in sections)}

    def _components(self) -> list[Component]:
        """Every leaf component, in reading order: sections in turn, a split left to right."""
        return leaves(
            [component for section in self._sections for component in section.components()]
        )

    def _holders(self) -> list[Component | Container]:
        """
        Everything that may call a note or cite, in reading order.

        Each section's leaf components, then the section itself, whose source
        line sits at its foot (#338).
        """
        holders: list[Component | Container] = []
        for section in self._flat_sections():
            holders.extend(leaves(section.components()))
            holders.append(section)
        return holders

    def _marked(self) -> list[tuple[str, Any, list[str]]]:
        """
        ``(owner, holder, copy)`` for everything that may cite, in reading order.

        Every leaf component and section; a medium adds what else carries a
        citation, as a deck adds each slide's source line, and the walk hands
        each its ``citing``.
        """
        return [(_named(h), h, h.marked_copy()) for h in self._holders()]

    def _walk(self) -> None:
        """
        Hand every part of the apparatus what only the whole tree knows.

        Run on each :meth:`add_section` and before each projection, so a
        component shared with another document carries this one's numbers
        while this one renders.
        """
        for letter, section in self._lettered():
            section.letter = letter if section.title else ""
        kept = (section for section in self._flat_sections() if section.keep_together)
        for number, section in enumerate(kept, start=1):
            section.kept_mark = f"kept-section-{number}"
        self._number_exhibits()
        for number, note in enumerate(self._footnotes(), start=1):
            note.number = number
        marked = self._marked()
        bibliography = self._bibliography()
        cited = [key for _, _, copy in marked for text in copy for key in cited_keys(text)]
        citing = bibliography.resolve(cited) if bibliography else UNRESOLVED
        for _, holder, _ in marked:
            holder.citing = citing
        for section in self._flat_sections():
            for component in leaves(section.components()):
                if isinstance(component, Contents):
                    component.entries = self._listing(component.of, component.label, section)

    def kept_sections(self) -> dict[str, str]:
        """Each section kept together on paper, by its row's ``id`` there, to its name (#364)."""
        self._walk()
        return {
            section.kept_mark: section.heading() or type(section).__name__
            for section in self._flat_sections()
            if section.keep_together
        }

    def _raw_html(self) -> list[tuple[str, str]]:
        """Every raw-HTML field in the document, each with who carries it."""
        regions = [region for region, _ in self.leading_regions() + self.trailing_regions()]
        return [
            ("header_disclaimer", self._metadata.header_disclaimer),
            *((type(region).__name__, html) for region in regions for html in region.raw_html()),
            *(
                (type(component).__name__, html)
                for component in self._components()
                for html in component.raw_html()
            ),
        ]

    def _bibliography(self) -> Bibliography | None:
        """The document's bibliography, or ``None`` when it cites nothing."""
        return next((c for c in self._components() if isinstance(c, Bibliography)), None)

    def _check_one_bibliography(self) -> None:
        """Raise on a second bibliography: two would number one citation two ways."""
        if sum(isinstance(c, Bibliography) for c in self._components()) > 1:
            raise ValidationError(
                "a document carries one Bibliography; a second would resolve one citation "
                "two ways. List every Reference in the first."
            )

    def _footnotes(self) -> list[Footnote]:
        """Every note the tree calls, in reading order."""
        return [note for holder in self._holders() for note in holder.footnotes()]

    def _endnotes(self) -> Endnotes | None:
        """The notes gathered for the end of the document, or ``None`` if it has none."""
        notes = self._footnotes()
        return Endnotes(notes) if notes else None

    def _listing(
        self, of: str, label: str | None = None, skip: Container | None = None
    ) -> list[tuple[str, str]]:
        """The entries a contents list of ``of`` holds: sections less ``skip``, or exhibits."""
        if of == "exhibits":
            return self._exhibit_entries(label)
        return self._contents_entries(skip)

    def _exhibit_entries(self, label: str | None = None) -> list[tuple[str, str]]:
        """``(heading, anchor)`` for every numbered exhibit in reading order, or one label's."""
        return [
            (component.listed(), component.resolved_anchor())
            for component in self._components()
            if isinstance(component, Exhibit)
            and component.number
            and label in (None, component.label)
        ]

    def _contents_entries(self, skip: Container | None = None) -> list[tuple[str, str]]:
        """``(title, anchor)`` for every titled section in reading order, less ``skip``."""
        return [
            (section.heading(), section.resolved_anchor())
            for section in self._flat_sections()
            if section.title and section is not skip
        ]

    def _lettered(self) -> list[tuple[str, Container]]:
        """Every section in reading order, with its appendix letter, or ``""`` in the body."""
        lettered: list[tuple[str, Container]] = []
        for section in self._sections:
            if isinstance(section, Appendices):
                lettered.extend(section.lettered())
            else:
                lettered.extend(("", inner) for inner in _flatten(section))
        return lettered

    def _number_exhibits(self) -> None:
        """Number every labelled exhibit in reading order, one count per label and appendix."""
        counts: dict[tuple[str, str], int] = {}
        for letter, section in self._lettered():
            for component in leaves(section.components()):
                if not isinstance(component, Exhibit):
                    continue
                component.appendix = letter
                if component.label:
                    key = (letter, component.label)
                    counts[key] = counts.get(key, 0) + 1
                    component.number = counts[key]
                else:
                    component.number = None

    def _anchors(self) -> list[tuple[str, str]]:
        """Every anchor this document defines, each with who defines it."""
        sections = [
            (anchor, f"the section titled {section.title!r}")
            for section in self._flat_sections()
            if (anchor := section.resolved_anchor())
        ]
        exhibits = [
            (anchor, f"{component.numbered('') or 'an unnumbered'} {type(component).__name__}")
            for component in self._components()
            if isinstance(component, Exhibit) and (anchor := component.resolved_anchor())
        ]
        notes = [
            (anchor(note.number or 0), f"footnote {note.number}")
            for note in self._footnotes()
            for anchor in (note_anchor, note_ref_anchor)
        ]
        others = [pair for component in self._components() for pair in component.anchors()]
        return sections + exhibits + notes + others

    def _inline_image_hint(self) -> str:
        """
        Name inlined images in a constraint failure when there are any.

        A base64 data URI costs +33% on top of the raw bytes and lands
        entirely inside the markup, so it is the usual reason a document that
        was comfortably under a size limit suddenly is not.
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


def _named(holder: Component | Container) -> str:
    """How a refusal names something that may cite: a block by its class, a section by its title."""
    return holder._owner() if isinstance(holder, Container) else type(holder).__name__


def _flatten(section: Container) -> list[Container]:
    """A section, or the sections a page holds in its place."""
    inner = getattr(section, "sections", None)
    return list(inner) if isinstance(inner, list) else [section]


__all__ = ["Document", "RegionFacts", "Renderer"]


def check_density(size_theme: SizeTheme | str | SizeScheme, medium: Medium) -> None:
    """
    Refuse a density the medium has not been rendered at.

    A density tuned for one medium is refused by every other, with no switch
    (``presentation`` belongs to the deck). The shipped email densities are
    the ones checked against the clients; a print density or a custom scheme
    is not, until the caller says it has been, with
    ``Config.allow_custom_email_density``. Other media take the rest.

    Raises:
        ValidationError: Naming the density, and the switch where there is one.
    """
    if not isinstance(size_theme, SizeScheme):
        owner = MEDIUM_DENSITIES.get(SizeTheme(size_theme))
        if owner is not None and owner != medium.name:
            raise ValidationError(
                f"the density {str(size_theme)!r} is tuned for the {owner} medium alone, "
                f"and this document is a {medium.name}. Choose 'spacious' for room, "
                "or build the document the density was made for."
            )
    if not medium.email or get_config().allow_custom_email_density:
        return
    if isinstance(size_theme, SizeScheme):
        what = "a custom SizeScheme"
    elif SizeTheme(size_theme) in PRINT_DENSITIES:
        what = f"the print density {str(size_theme)!r}"
    else:
        return
    raise ValidationError(
        f"{what} has not been rendered in an email client: Gmail's clipping limit, "
        "Outlook's Word engine and the mobile collapse all meet the density at once. "
        "Render it in the clients you send to, then set "
        "Config.allow_custom_email_density (PYHERMES_ALLOW_CUSTOM_EMAIL_DENSITY)."
    )


def _valigned(container: Container) -> tuple[str, str] | None:
    """The first split in one section's subtree aligned off the top, and its value (#356)."""
    for inner in getattr(container, "sections", ()):
        if found := _valigned(inner):
            return found
    candidates: list[object] = [container]
    if not hasattr(container, "sections"):
        candidates.extend(descendants(container.components()))
    for candidate in candidates:
        valign = getattr(candidate, "valign", "top")
        if valign != "top" and not hasattr(candidate, "sections"):
            owner = candidate._owner() if isinstance(candidate, Container) else "Columns"
            return owner, valign
    return None


def _held(container: Container) -> list[Component]:
    """Every block one section's subtree holds, through a page's or a slide's sections."""
    inner = getattr(container, "sections", None)
    if isinstance(inner, list):
        return [block for section in inner for block in _held(section)]
    return descendants(container.components())


def _spacings(container: Container) -> list[tuple[str, Spacing]]:
    """Every spacing override in one section's subtree, with the object that owns it."""
    found: list[tuple[str, Spacing]] = []
    if container.spacing is not None:
        found.append((container._owner(), container.spacing))
    for inner in getattr(container, "sections", ()):
        found.extend(_spacings(inner))
    if not hasattr(container, "sections"):
        found.extend(
            (type(component).__name__, component.spacing)
            for component in descendants(container.components())
            if component.spacing is not None
        )
    return found


def stamp_type(stamp: str, frame: FrameGeometry) -> dict[str, int]:
    """
    The stamp's size, box and slant on ``frame``'s sheet: set along the diagonal (#342).

    As large as a fifth of the short side allows, and smaller where a long
    word would run past three quarters of the diagonal, at the 0.78em a bold
    capital measured. The box is the diagonal wide, so the word never wraps.
    """
    width, height = frame.sheet_width, frame.sheet_height or frame.sheet_width
    diagonal = math.hypot(width, height)
    px = min(0.2 * min(width, height), 0.75 * diagonal / (0.78 * len(stamp)))
    return {
        "px": round(px),
        "width": round(diagonal),
        "angle": round(math.degrees(math.atan2(height, width))),
    }
