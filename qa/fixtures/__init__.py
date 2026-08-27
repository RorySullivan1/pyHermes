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

from svc.builder import Email

from . import (
    compact_size,
    custom_banner,
    image_matrix,
    kitchen_sink,
    minimal,
    minimal_banner,
    minimal_footer,
    no_header,
    slate_theme,
    spacious_size,
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
        "image_matrix": image_matrix.build,
        "minimal_banner": minimal_banner.build,
        "minimal_footer": minimal_footer.build,
        "no_header": no_header.build,
        "slate_theme": slate_theme.build,
        "compact_size": compact_size.build,
        "spacious_size": spacious_size.build,
    }


__all__ = ["DEPRECATED_COMPONENTS", "FixtureBuilder", "all_fixtures"]
