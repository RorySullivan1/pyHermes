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

from . import image_matrix, kitchen_sink, minimal

#: Components that are exempt from the ``kitchen_sink`` completeness rule.
#:
#: ``KpiStrip`` is a deprecated alias for ``CardGroup(orientation="horizontal")``
#: and warns on construction. Including it would render markup identical to a
#: section the gallery already has, while emitting a ``DeprecationWarning`` on
#: every build of every downstream tool. The completeness test subtracts this
#: set — the *inclusion* side stays introspected, so a genuinely new component
#: still cannot slip through.
DEPRECATED_COMPONENTS = frozenset({"KpiStrip"})

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
        "image_matrix": image_matrix.build,
    }


__all__ = ["DEPRECATED_COMPONENTS", "FixtureBuilder", "all_fixtures"]
