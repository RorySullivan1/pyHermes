"""
Centralized enum vocabulary for the email builder.

A single home for the small closed sets of string options the builder
accepts — column ratios, card orientation — so the allowed values live in
one place instead of being scattered as bare string literals across the
container and component classes.

Every enum here is a :class:`~enum.StrEnum`: each member *is* its wire
string (``TwoColumnRatio.EQUAL == "50-50"`` and hashes the same), so a
caller may pass either the enum member or the plain string interchangeably.
That keeps the enums a purely additive, backward-compatible convenience —
existing ``ratio="50-50"`` / ``orientation="horizontal"`` calls are
unaffected. Note the containers/components may now *store* the value as an
enum member (e.g. from the default), but a member is-a ``str``
(``isinstance(TwoColumnRatio.EQUAL, str)`` is ``True``), so attribute reads
and ``==`` comparisons behave exactly as with the plain string.

Note these enums hold only the *vocabulary*. The mapping from a ratio to
its template file stays with the container that owns it (``_ratio_map`` in
``containers.py``), because a template path is a rendering detail, not part
of the type.
"""

from __future__ import annotations

from enum import StrEnum


class TwoColumnRatio(StrEnum):
    """Column-width splits supported by :class:`~svc.builder.containers.TwoColumn`."""

    EQUAL = "50-50"
    NARROW_WIDE = "30-70"
    WIDE_NARROW = "70-30"


class ThreeColumnRatio(StrEnum):
    """Column-width splits supported by :class:`~svc.builder.containers.ThreeColumn`."""

    EQUAL = "33-33-33"
    WIDE_LEFT = "50-25-25"
    WIDE_CENTER = "25-50-25"
    WIDE_RIGHT = "25-25-50"


class CardOrientation(StrEnum):
    """Layout direction for a :class:`~svc.builder.components.CardGroup`."""

    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
