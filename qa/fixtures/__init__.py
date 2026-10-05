"""
The fixture gallery: representative emails as builder code.

Every downstream tool in epic #54 enumerates the gallery through
:func:`all_fixtures` rather than importing the modules one by one, so adding a
fixture is a one-line registry change and every consumer picks it up.

**Determinism is the rule the gallery rests on.** A fixture must render
byte-identically on every call: fixed strings, no clock, no ``random``, and
image bytes generated from constants (see :mod:`qa.fixtures._png`). Content-IDs
are ``sha256(bytes)[:16]``, so an image that varies changes the ``cid:``
references in the HTML — a golden snapshot would fail for a reason that has
nothing to do with the change under review.
"""

from __future__ import annotations

from collections.abc import Callable

from pyhermes.builder import Email
from pyhermes.builder.document import Document

from . import (
    a4_editorial,
    a4_equations,
    a4_glance_layout,
    a4_labelled_layout,
    a4_long_table,
    a4_placed_layout,
    a4_portrait,
    a4_research_note,
    aligned_layout,
    compact_size,
    composed_layout,
    custom_banner,
    custom_footer,
    glance_layout,
    image_matrix,
    kitchen_sink,
    labelled_layout,
    letter_dense,
    letter_landscape_report,
    letter_quant_table,
    minimal,
    minimal_banner,
    minimal_footer,
    modern_fonts,
    no_header,
    pitch_16_9,
    pitch_layouts_16_9,
    placed_layout,
    research_note,
    rich_table,
    slate_theme,
    slide_16_9,
    spacious_size,
    surfaced_layout,
    tri_fold_letter,
)

#: Components that are exempt from the ``kitchen_sink`` completeness rule.
#:
#: ``KpiStrip`` is a deprecated alias for ``CardGroup(orientation="horizontal")``
#: and warns on construction. Including it would render markup identical to a
#: section the gallery already has, while emitting a ``DeprecationWarning`` on
#: every build of every downstream tool. The completeness test subtracts this
#: set — the *inclusion* side stays introspected, so a genuinely new component
#: still cannot slip through.
DEPRECATED_COMPONENTS = frozenset({"KpiStrip"})

#: A fixture builder. Callable with no arguments — that is the contract every
#: consumer relies on, and what :func:`all_fixtures` promises.
#:
#: Each builder also accepts an optional ``template_dir``, threaded to
#: ``EmailBuilder``, so the whole gallery can be rendered against a candidate
#: template set rather than the packaged one. That is how a template migration
#: asks "does this edit move any email?", and how the golden harness's
#: detection test perturbs a real template rather than only the compared text.
#: It stays out of the alias deliberately: consumers must not be obliged to
#: pass it.
FixtureBuilder = Callable[[], Email]

#: A paged fixture builder, on the same no-argument contract.
PagedFixtureBuilder = Callable[[], Document]


def all_fixtures() -> dict[str, FixtureBuilder]:
    """
    The gallery, name → builder.

    Returns a fresh mapping each call, so a consumer that mutates it cannot
    corrupt the gallery for the next one.
    """
    return {
        "minimal": minimal.build,
        "kitchen_sink": kitchen_sink.build,
        "custom_banner": custom_banner.build,
        "custom_footer": custom_footer.build,
        "image_matrix": image_matrix.build,
        "minimal_banner": minimal_banner.build,
        "minimal_footer": minimal_footer.build,
        "no_header": no_header.build,
        "slate_theme": slate_theme.build,
        "compact_size": compact_size.build,
        "spacious_size": spacious_size.build,
        "modern_fonts": modern_fonts.build,
        "rich_table": rich_table.build,
        "aligned_layout": aligned_layout.build,
        "composed_layout": composed_layout.build,
        "surfaced_layout": surfaced_layout.build,
        "research_note": research_note.build,
        "placed_layout": placed_layout.build,
        "glance_layout": glance_layout.build,
        "labelled_layout": labelled_layout.build,
    }


def all_paged_fixtures() -> dict[str, PagedFixtureBuilder]:
    """
    The paged gallery, name → builder.

    **A second registry rather than a wider one, deliberately.**
    :func:`all_fixtures` is consumed by a dozen test modules whose assertions
    are about *emails* — Outlook lint rules, a phone viewport, the
    ``kitchen_sink`` completeness rules keyed to ``EmailMetadata``. Widening
    it here would drag every one of them onto a paged render several phases
    before the harness knows what a medium is. #165 is where the two become
    one registry keyed by medium; until then the split is what keeps each
    gallery's tests about the thing they test.
    """
    return {
        "a4_portrait": a4_portrait.build,
        "a4_long_table": a4_long_table.build,
        "a4_editorial": a4_editorial.build,
        "slide_16_9": slide_16_9.build,
        "letter_landscape_report": letter_landscape_report.build,
        "letter_dense": letter_dense.build,
        "letter_quant_table": letter_quant_table.build,
        "a4_equations": a4_equations.build,
        "a4_research_note": a4_research_note.build,
        "a4_placed_layout": a4_placed_layout.build,
        "a4_glance_layout": a4_glance_layout.build,
        "a4_labelled_layout": a4_labelled_layout.build,
    }


def all_brochure_fixtures() -> dict[str, PagedFixtureBuilder]:
    """
    The brochure gallery, name → builder (#172).

    A third registry for :func:`all_paged_fixtures`' reason: the paged tests
    read the cover, the running boxes and the back matter off every fixture
    they are given, and a brochure has none of them. Every face of a
    brochure is a panel.
    """
    return {"tri_fold_letter": tri_fold_letter.build}


def all_deck_fixtures() -> dict[str, PagedFixtureBuilder]:
    """
    The deck gallery, name → builder (#296).

    A fourth registry for :func:`all_brochure_fixtures`' reason: the paged
    tests read a cover, running boxes and back matter off every fixture, and
    a deck has a title slide and a closing slide instead.
    """
    return {"pitch_16_9": pitch_16_9.build, "pitch_layouts_16_9": pitch_layouts_16_9.build}


__all__ = [
    "DEPRECATED_COMPONENTS",
    "FixtureBuilder",
    "PagedFixtureBuilder",
    "all_brochure_fixtures",
    "all_deck_fixtures",
    "all_fixtures",
    "all_paged_fixtures",
]
