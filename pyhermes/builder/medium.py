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

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from .exceptions import ValidationError
from .sizing import DEFAULT_PAGE, PageFormat

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

    Frozen and shared process-wide, like a :class:`~pyhermes.builder.theming.Theme`
    or a :class:`~pyhermes.builder.sizing.SizeScheme` — a medium holds no
    per-document state, so two documents may render through one instance
    concurrently.

    :attr:`slots` is **derived** from :attr:`region_types` rather than
    declared beside them. A medium that listed both could disagree with
    itself, and the skeleton would then be right about one of them; deriving
    leaves the region classes as the single owner of what they fill, which is
    what ``Region.SLOTS`` has always been.

    :attr:`page_format` is the medium's half of ``size.frame``; the density
    supplies the rest. :class:`~pyhermes.builder.sizing.PageFormat` carries why.

    :attr:`paged` and :attr:`email` are what a shared template may branch on.
    They are independent rather than one enum: a standalone HTML deliverable
    is neither, and nothing is served by making it claim to be one.
    """

    #: Identifies the medium in errors, goldens and the lint rule table.
    name: str

    #: Template path of the full page, rendered last with every slot filled.
    skeleton: str

    #: The page this medium renders onto. Layered over the density's frame at
    #: render time, so a preset decides how roomy a document feels and the
    #: medium decides how wide it is.
    page_format: PageFormat = field(default=DEFAULT_PAGE)

    #: The region classes whose slots this medium's skeleton names, in
    #: skeleton order. The body's own slot is not here — the ordered section
    #: list is deliberately not a region.
    region_types: tuple[type[Region], ...] = ()

    #: Checks run over the composed document, in order, after rendering.
    constraints: tuple[Constraint, ...] = ()

    #: Template directories searched ahead of the shared tree, so this medium
    #: can fork one template without forking the tree. Usually empty.
    template_search_path: tuple[str, ...] = ()

    paged: bool = False
    email: bool = False

    #: The measure a prose block takes when it names none (#358): ``"standard"``,
    #: ``"narrow"``, or ``None`` for no cap. The medium owns geometry, so it owns this.
    measure: str | None = None

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


#: Every medium the package ships, by name: what ``Only`` and ``OnlySections`` may name (#365).
#: A test holds it to the shipped ``Medium`` objects, which the kit may not import.
SHIPPED_MEDIA: tuple[str, ...] = ("html", "email", "document", "brochure", "deck")

#: The shipped media that print onto sheets, by name; the same test holds it to ``paged``.
PAGED_MEDIA: tuple[str, ...] = ("document", "brochure", "deck")

_WALKING: ContextVar[str | None] = ContextVar("pyhermes_medium", default=None)


@contextmanager
def walking_in(name: str) -> Iterator[None]:
    """A context in which a walk of the tree reads as the medium ``name`` (#365)."""
    token = _WALKING.set(name)
    try:
        yield
    finally:
        _WALKING.reset(token)


def walking_medium() -> str | None:
    """The medium the current walk is for, or ``None`` outside any document's."""
    return _WALKING.get()


def check_media(media: object, owner: str) -> tuple[str, ...]:
    """
    ``media`` as a tuple of shipped medium names.

    Raises:
        ValidationError: On an empty list, or a name nothing ships.
    """
    if isinstance(media, str):
        names: tuple[object, ...] = (media,)
    elif isinstance(media, (list, tuple, set, frozenset)):
        names = tuple(media)
    else:
        raise ValidationError(f"{owner} takes a medium's name or a list of them, got: {media!r}")
    if not names:
        raise ValidationError(f"{owner} needs at least one medium, from {list(SHIPPED_MEDIA)}.")
    for name in names:
        if name not in SHIPPED_MEDIA:
            raise ValidationError(
                f"{owner} names the medium {name!r}, which nothing ships. "
                f"Choose from {list(SHIPPED_MEDIA)}."
            )
    return tuple(str(name) for name in names)
