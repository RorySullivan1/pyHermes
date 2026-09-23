"""
``Document`` — the medium-neutral product: metadata, regions, a section tree.

What every destination has in common. Three projections of one tree —
:meth:`render` to markup, :meth:`text` to the plain-text part and
:meth:`assets` to the images a delivery layer must carry — plus the one
resolution point where the theme, density, typefaces and medium are bound.

A subclass supplies its regions through :meth:`leading_regions` and
:meth:`trailing_regions`; :class:`~svc.builder.email.Email` is the worked
example. `.claude/rules/builder-architecture.md` carries the layer model.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Self

from .apparatus import check_unique, note_anchor, note_ref_anchor, references
from .components import Component, Contents, Endnotes, Exhibit
from .containers import Container, FullWidth
from .engine import Renderer, TemplateEngine
from .enums import EmbedStrategy
from .exceptions import ValidationError
from .images import EmailImage, ImageAsset, dedupe_assets
from .medium import DEFAULT_MEDIUM, Medium
from .models import DocumentMetadata, Footnote
from .sizing import resolve_size_scheme
from .textgen import join_sections
from .theming import resolve_theme
from .typography import resolve_font_theme

if TYPE_CHECKING:  # pragma: no cover - regions imports models, which imports this
    from .regions import Region

#: One region and the facts handed down to it. Ordered pairs rather than a
#: mapping, because the skeleton's order is part of the contract.
RegionFacts = tuple["Region", dict[str, Any]]


class Document:
    """
    A renderable document: its facts, its sections, and where it is read.

    Construct with a mapping of facts or a :class:`~svc.builder.models.
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
    ):
        # The medium is settled first: it names the templates this engine
        # searches before the shared tree.
        self._medium: Medium = medium if medium is not None else DEFAULT_MEDIUM
        self._engine = TemplateEngine(template_dir, search_path=self._medium.template_search_path)

        if isinstance(metadata, dict):
            self._metadata: DocumentMetadata = self.METADATA(**metadata)
        else:
            self._metadata = metadata

        # Validation happens at construction time, not render time, so a
        # missing required field names itself instead of surfacing later as a
        # confusing render-time symptom.
        self._metadata.validate()
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
            ValidationError: If the section claims an anchor the document already
                has; the document is left as it was.
        """
        self._sections.append(container)
        try:
            self._walk()
            check_unique(self._anchors())
        except ValidationError:
            self._sections.pop()
            self._walk()
            raise
        return self

    def _flat_sections(self) -> list[Container]:
        """
        Every section in reading order, a page's own flattened in.

        A :class:`~svc.document.page.Page` is a sheet boundary, not a section a
        reader navigates to, so the sections inside it stand in for it.
        """
        return [inner for section in self._sections for inner in _flatten(section)]

    def validate(self) -> None:
        """
        Check what only the finished tree can answer, before any template loads.

        Every ``#fragment`` in caller markup must land on an anchor this
        document defines. It runs at the start of each projection rather than
        in :meth:`add_section`, because a reference may name a section not yet
        added; call it directly to check sooner.

        Raises:
            ValidationError: Naming the first dangling reference and who made it.
        """
        self._walk()
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
            for component in section.components():
                images.extend(component.images())
        images.extend(image for region, _ in self.trailing_regions() for image in region.images())
        return images

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
        # The one resolution point. Every template below — skeleton, regions,
        # containers, components — reads the same values, because they all
        # render through this binder rather than looking any of them up.
        engine = self._engine.bound(
            theme=resolve_theme(self._metadata.theme),
            size=resolve_size_scheme(self._metadata.size_theme).with_page(self._medium.page_format),
            font=resolve_font_theme(self._metadata.font_theme),
            medium=self._medium,
        )

        ctx = self._metadata.to_dict()
        sections = list(self._sections)
        if (endnotes := self._endnotes()) and not self._medium.paged:
            # A mail client has no sheet foot, so the notes a page floats
            # there are gathered after the last section instead.
            sections.append(FullWidth(content=endnotes))
        ctx["sections_html"] = self._render_body(engine, sections)
        for region, facts in self.leading_regions() + self.trailing_regions():
            ctx.update(region.render_slots(engine, facts))

        html = engine.render(self._medium.skeleton, ctx)
        self._medium.validate(html, self._inline_image_hint())
        return html

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
            *(region.text(facts) for region, facts in self.leading_regions()),
            *(section.text() for section in self._sections),
            endnotes.text() if endnotes else "",
            *(region.text(facts) for region, facts in self.trailing_regions()),
        )

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

    def _render_body(self, engine: Renderer, sections: list[Container]) -> str:
        """The body slot: every section in reading order. A brochure lays out sides instead."""
        return "\n".join(section.render(engine) for section in sections)

    def _components(self) -> list[Component]:
        """Every component, in reading order: sections in turn, a split left to right."""
        return [component for section in self._sections for component in section.components()]

    def _walk(self) -> None:
        """
        Hand every part of the apparatus what only the whole tree knows.

        Run on each :meth:`add_section` and before each projection, so a
        component shared with another document carries this one's numbers
        while this one renders.
        """
        self._number_exhibits()
        for number, note in enumerate(self._footnotes(), start=1):
            note.number = number
        for section in self._flat_sections():
            for component in section.components():
                if isinstance(component, Contents):
                    component.entries = self._contents_entries(skip=section)

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

    def _footnotes(self) -> list[Footnote]:
        """Every note the tree calls, in reading order."""
        return [note for component in self._components() for note in component.footnotes()]

    def _endnotes(self) -> Endnotes | None:
        """The notes gathered for the end of the document, or ``None`` if it has none."""
        notes = self._footnotes()
        return Endnotes(notes) if notes else None

    def _contents_entries(self, skip: Container | None = None) -> list[tuple[str, str]]:
        """``(title, anchor)`` for every titled section in reading order, less ``skip``."""
        return [
            (section.title, section.resolved_anchor())
            for section in self._flat_sections()
            if section.title and section is not skip
        ]

    def _number_exhibits(self) -> None:
        """Number every labelled exhibit in reading order, one count per label."""
        counts: dict[str, int] = {}
        for component in self._components():
            if isinstance(component, Exhibit):
                if component.label:
                    counts[component.label] = counts.get(component.label, 0) + 1
                    component.number = counts[component.label]
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
        return sections + exhibits + notes

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


def _flatten(section: Container) -> list[Container]:
    """A section, or the sections a page holds in its place."""
    inner = getattr(section, "sections", None)
    return list(inner) if isinstance(inner, list) else [section]


__all__ = ["Document", "RegionFacts", "Renderer"]
