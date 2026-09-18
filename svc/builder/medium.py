"""
The medium: where a rendered document is going to be read.

An email client, a printed page, a browser. A medium is chosen by
constructing the document that has one, never by setting a field, because it
decides the skeleton, the slots that skeleton names and the checks the
composed document must pass. Once chosen it rides the render binder as one
more shared value, so no container, component or region changes signature to
see it.

`.claude/rules/builder-architecture.md` carries the four-layer model this
sits above.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:  # pragma: no cover - regions imports nothing from here
    from .regions import Region


@runtime_checkable
class Constraint(Protocol):
    """
    A check a medium runs over the composed document, raising on failure.

    ``hint`` is caller-supplied context appended to the failure message —
    the email medium uses it to name inlined images in a size failure. It is
    optional so a constraint that has no use for one still satisfies this
    protocol.
    """

    def __call__(self, html: str, hint: str = "") -> None: ...


@dataclass(frozen=True)
class Medium:
    """
    One destination: its skeleton, its region set and its constraints.

    Frozen and shared process-wide, like a :class:`~svc.builder.theming.Theme`
    or a :class:`~svc.builder.sizing.SizeScheme` — a medium holds no
    per-document state, so two documents may render through one instance
    concurrently.

    :attr:`slots` is **derived** from :attr:`region_types` rather than
    declared beside them. A medium that listed both could disagree with
    itself, and the skeleton would then be right about one of them; deriving
    leaves the region classes as the single owner of what they fill, which is
    what ``Region.SLOTS`` has always been.

    :attr:`paged` and :attr:`email` are what a shared template may branch on.
    They are independent rather than one enum: a standalone HTML deliverable
    is neither, and nothing is served by making it claim to be one.
    """

    #: Identifies the medium in errors, goldens and the lint rule table.
    name: str

    #: Template path of the full page, rendered last with every slot filled.
    skeleton: str

    #: The region classes whose slots this medium's skeleton names, in
    #: skeleton order. The body's own slot is not here — the ordered section
    #: list is deliberately not a region.
    region_types: tuple[type[Region], ...] = ()

    #: Checks run over the composed document, in order, after rendering.
    constraints: tuple[Constraint, ...] = ()

    paged: bool = False
    email: bool = False

    @property
    def slots(self) -> tuple[str, ...]:
        """Every slot this medium's regions fill, in skeleton order."""
        return tuple(slot for region in self.region_types for slot in region.SLOTS)

    def validate(self, html: str, hint: str = "") -> None:
        """Run every constraint over the composed document."""
        for constraint in self.constraints:
            constraint(html, hint)


#: The floor the engine guarantees when nothing binds a medium: plain HTML,
#: no constraints, no client to accommodate. Rendering one component on its
#: own goes through this, and so would a standalone-HTML deliverable.
DEFAULT_MEDIUM = Medium(name="html", skeleton="base.html")
