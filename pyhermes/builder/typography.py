"""
Every typeface in the email, as one validated object per house voice.

A ``FontTheme`` is four roles named by job rather than by face — ``heading``,
``body``, ``label``, ``numeric`` — each a ``FontStack`` whose families are
stored unquoted and rendered by a byte-exact ``css`` property. Every stack
must end in a generic family; a bare generic alone is rejected.

``EmailMetadata.font_theme`` names a preset or supplies a ``FontTheme``;
:meth:`Email.render` resolves it once and binds it as the ``font`` namespace,
so no template holds a ``font-family`` literal.

`.claude/rules/design-axes.md` carries the presets, the validation rules and
their reasons, and the ``[if mso]`` block that is the watch-site for a
literal creeping back.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, fields, replace
from pathlib import Path

from .exceptions import ValidationError
from .images import ImageAsset

#: The CSS generic families a stack may end in. Not a taste list — these are
#: the five CSS2 generics every client resolves to *something*, which is what
#: makes them a floor rather than a preference. ``cursive``/``fantasy`` are
#: legal CSS and deliberately absent: neither belongs at the end of a chain in
#: a financial newsletter, and admitting them would make the rule decorative.
GENERIC_FAMILIES: frozenset[str] = frozenset({"serif", "sans-serif", "monospace"})

#: Characters that cannot appear in a family name. A ``font-family`` value is
#: emitted inside a double-quoted ``style`` attribute, so these would break out
#: of the declaration or the attribute — the same safety family as
#: ``_validate_url``'s scheme check, and shape rather than taste.
_FORBIDDEN_IN_FAMILY = ('"', "'", ";", "{", "}", "<", ">")


#: A font file's leading bytes, and the CSS ``format()`` and MIME type each is served as.
_FONT_SIGNATURES: dict[bytes, tuple[str, str, str]] = {
    b"\x00\x01\x00\x00": ("truetype", "font/ttf", "ttf"),
    b"true": ("truetype", "font/ttf", "ttf"),
    b"OTTO": ("opentype", "font/otf", "otf"),
    b"wOFF": ("woff", "font/woff", "woff"),
    b"wOF2": ("woff2", "font/woff2", "woff2"),
}

_WEIGHTS = ("100", "200", "300", "400", "500", "600", "700", "800", "900")


@dataclass(frozen=True)
class FontFile:
    """
    One face of a house typeface: a weight, a style, and the file's bytes (#391).

    Read and sniffed at construction, so a path that is missing or is not a
    font fails where it was named, never inside the PDF engine. The bytes are
    served to the print engine under :attr:`content_id`, as an image is.
    """

    weight: int
    style: str
    path: Path
    data: bytes = field(repr=False)

    @classmethod
    def read(cls, key: str, path: str | Path, owner: str) -> FontFile:
        """The face ``key`` (``"700"``, ``"400 italic"``) read from ``path``."""
        weight, _, style = str(key).partition(" ")
        if weight not in _WEIGHTS or style not in ("", "italic"):
            raise ValidationError(
                f"{owner}'s files are keyed by weight, as '400' or '700 italic', got: {key!r}"
            )
        if not isinstance(path, (str, Path)):
            raise ValidationError(f"{owner}'s {key} face is a file path, got: {path!r}")
        resolved = Path(path)
        try:
            data = resolved.read_bytes()
        except OSError as exc:
            raise ValidationError(f"{owner}'s {key} face cannot be read: {exc}") from None
        if data[:4] not in _FONT_SIGNATURES:
            raise ValidationError(
                f"{owner}'s {key} face {str(resolved)!r} is not a TrueType, OpenType "
                "or WOFF font file."
            )
        return cls(int(weight), style or "normal", resolved, data)

    @property
    def format(self) -> str:
        """The ``format()`` hint an ``@font-face`` rule gives for this file."""
        return _FONT_SIGNATURES[self.data[:4]][0]

    @property
    def content_id(self) -> str:
        """The manifest name the print engine fetches this file under: a hash of its bytes."""
        digest = hashlib.sha256(self.data).hexdigest()[:16]
        return f"font-{digest}.{_FONT_SIGNATURES[self.data[:4]][2]}"

    def asset(self) -> ImageAsset:
        """This file as a manifest entry, served to the PDF exporter beside the images."""
        return ImageAsset(
            content_id=self.content_id,
            data=self.data,
            mime_type=_FONT_SIGNATURES[self.data[:4]][1],
            filename=self.path.name,
        )


@dataclass(frozen=True)
class FontFace:
    """One ``@font-face`` rule: the family it names and the file it serves."""

    family: str
    file: FontFile

    @property
    def css(self) -> str:
        """The ``@font-face`` rule, byte-exact, its source a ``cid:`` in the manifest."""
        file = self.file
        return (
            f"@font-face {{ font-family: '{self.family}'; "
            f"src: url('cid:{file.content_id}') format('{file.format}'); "
            f"font-weight: {file.weight}; font-style: {file.style}; }}"
        )


@dataclass(frozen=True)
class FontStack:
    """
    A font fallback chain, stored as families and composed at render.

    Storing ``"Georgia, 'Times New Roman', serif"`` as a string would make it
    unvalidatable and un-inspectable — you could not ask whether it ends in a
    generic without parsing CSS back out of it. Storing the families keeps a
    stack a *chain*.

    **The formatting contract is byte-exact and load-bearing**, the lesson
    :class:`~pyhermes.builder.theming.Rgba` learned: one composer means two emission
    sites cannot drift. Families are separated by ``", "``, and a name
    containing a space is quoted on emission with single quotes — never stored
    pre-quoted, so ``families`` is always the plain names.

    **A house typeface (#391).** ``files`` declares the font files of the
    first family, keyed by weight: ``{"400": path, "700": path}``, with
    ``"400 italic"`` for an italic. A paged document embeds them; an email
    ignores them and walks the chain, since ``css`` does not change.

    Args:
        families: The chain, in order, ending in a CSS generic family.
        files: The first family's font files by weight, or none.

    Raises:
        ValidationError: For a chain that does not end in a generic, one with
            fewer than two entries, or a family name that is empty or carries a
            character that would break out of the ``style`` attribute; and for
            a file that is missing, is not a font, or is keyed by no weight.
    """

    families: tuple[str, ...]
    files: tuple[FontFile, ...]

    def __init__(self, *families: str, files: Mapping[str, str | Path] | None = None) -> None:
        # Varargs rather than a tuple argument: ``FontStack("Georgia",
        # "Times New Roman", "serif")`` reads as the chain it is, and a caller
        # cannot accidentally pass a bare string and get it iterated per
        # character — the failure mode a tuple field invites.
        object.__setattr__(self, "families", tuple(families))
        self.validate()
        if files is not None and not isinstance(files, Mapping):
            raise ValidationError(
                f"'font stack' files map a weight to a path, as {{'400': path}}, got: {files!r}"
            )
        owner = f"font stack {self.families[0]!r}"
        faces = tuple(FontFile.read(key, path, owner) for key, path in (files or {}).items())
        object.__setattr__(self, "files", faces)

    @property
    def faces(self) -> tuple[FontFace, ...]:
        """The ``@font-face`` rules this stack declares: its first family, once per file."""
        return tuple(FontFace(self.families[0], file) for file in self.files)

    def validate(self) -> None:
        """Raise :class:`ValidationError` if this chain is not renderable."""
        if len(self.families) < 2:
            raise ValidationError(
                f"'font stack' needs at least a face and a generic fallback, got: "
                f"{list(self.families)}. A bare generic is legal CSS but an empty "
                f"design decision — name the face you mean."
            )
        for name in self.families:
            if not isinstance(name, str) or not name.strip():
                raise ValidationError(
                    f"'font stack' family names must be non-empty strings, got: {name!r}"
                )
            bad = [ch for ch in _FORBIDDEN_IN_FAMILY if ch in name]
            if bad:
                raise ValidationError(
                    f"'font stack' family {name!r} contains {bad} — a family name is "
                    f"emitted inside a quoted style attribute and may not carry these."
                )
        terminal = self.families[-1]
        if terminal not in GENERIC_FAMILIES:
            raise ValidationError(
                f"'font stack' must end in a CSS generic family "
                f"{sorted(GENERIC_FAMILIES)}, got: {terminal!r}. In email the "
                f"fallback chain is the rendering — Outlook walks it and the generic "
                f"is the floor."
            )

    @property
    def css(self) -> str:
        """The ``font-family`` value, in exactly the shipped formatting."""
        return ", ".join(f"'{name}'" if " " in name else name for name in self.families)

    def __str__(self) -> str:
        """So a template can write ``{{ font.body }}`` and get CSS."""
        return self.css


def _validate_stack_fields(instance: object, prefix: str) -> None:
    """
    Check every role of a frozen layer holds a real :class:`FontStack`.

    A non-stack is rejected here rather than reaching a template as whatever it
    is: every field on this layer is a chain, so anything else is wrong in the
    same way. The stacks themselves validated at their own construction.
    """
    for spec in fields(instance):  # type: ignore[arg-type]
        value = getattr(instance, spec.name)
        if not isinstance(value, FontStack):
            raise ValidationError(
                f"'{prefix}.{spec.name}' must be a FontStack, got: {type(value).__name__}"
            )


@dataclass(frozen=True)
class FontTheme:
    """
    Every typeface the email renders with, as one validated object.

    Frozen, with no optional role and every value validated at construction —
    so a ``FontTheme`` that exists is a ``FontTheme`` that renders, and
    ``StrictUndefined`` cannot be tripped by a half-built one. The same
    guarantee :class:`~pyhermes.builder.theming.Theme` and
    :class:`~pyhermes.builder.sizing.SizeScheme` make, for the third axis.

    **The unit of customisation is the theme, never a face at a call site** —
    a ``heading_font=`` parameter anywhere would dissolve the system one call
    site at a time, exactly as a ``title_color=`` would dissolve the palette.
    There is deliberately no per-component or per-region font override.

    Attributes:
        heading: Display and structural type — the masthead title, section
                 titles, item titles, list ordinals.
        body:    The reading voice: prose, the page default, and the KPI
                 values, which are display numerals rather than data.
        label:   Chrome and supporting copy — meta lines, captions, table
                 text, the strip and the footer.
        numeric: Figures that must align in columns; monospace by default,
                 and the only role a table's non-first columns read.
    """

    heading: FontStack = field(
        default_factory=lambda: FontStack("Georgia", "Times New Roman", "serif")
    )
    body: FontStack = field(
        default_factory=lambda: FontStack("Georgia", "Times New Roman", "serif")
    )
    label: FontStack = field(default_factory=lambda: FontStack("Arial", "Helvetica", "sans-serif"))
    numeric: FontStack = field(
        default_factory=lambda: FontStack("Courier New", "Courier", "monospace")
    )

    def __post_init__(self) -> None:
        _validate_stack_fields(self, "font")

    @property
    def faces(self) -> tuple[FontFace, ...]:
        """Every ``@font-face`` the roles declare, each family and face once (#391)."""
        seen: dict[tuple[str, int, str], FontFace] = {}
        for spec in fields(self):
            for face in getattr(self, spec.name).faces:
                seen.setdefault((face.family, face.file.weight, face.file.style), face)
        return tuple(seen.values())

    def assets(self) -> list[ImageAsset]:
        """The font files a printed document serves its print engine, one entry per file."""
        unique: dict[str, ImageAsset] = {}
        for face in self.faces:
            unique.setdefault(face.file.content_id, face.file.asset())
        return list(unique.values())

    def derive(self, **roles: FontStack | Iterable[str]) -> FontTheme:
        """
        A copy of this theme with some roles replaced.

        The common case is not "build a theme from nothing" — it is "the
        shipped voice, with our masthead face"::

            DEFAULT_FONTS.derive(heading=FontStack("Verdana", "Geneva", "sans-serif"))

        A role may be given a :class:`FontStack` or any iterable of family
        names, which is built into one. Everything else is inherited, and the
        result is **re-validated**, so a derived theme cannot be less valid
        than one built from scratch.

        Raises:
            ValidationError: For an unknown role, or a chain that fails its
                own rule.
        """
        known = {spec.name for spec in fields(self)}
        unknown = set(roles) - known
        if unknown:
            raise ValidationError(
                f"unknown font role(s) {sorted(unknown)}; known roles: {sorted(known)}"
            )
        replacements: dict[str, FontStack] = {}
        for name, value in roles.items():
            replacements[name] = value if isinstance(value, FontStack) else FontStack(*value)
        return replace(self, **replacements)


#: The typefaces this repo has always rendered. Every value traces to the audit
#: in the module docstring.
DEFAULT_FONTS = FontTheme()

#: A sans-display counterpart to ``classic``'s all-serif voice.
#:
#: Curated, not computed — the ``SLATE_THEME`` bar: a face nobody has
#: rendered in a real client is a compatibility claim nobody has tested, so
#: every entry here is websafe and every chain is walked down to a floor.
#:
#: **The design is the inversion, not the substitution.** ``classic`` sets
#: structure and reading copy in one serif; this sets structure and chrome in
#: a sans and *keeps the serif for prose*, which is the standard editorial
#: pairing and the reason the role vocabulary was cut where it was: ``heading``
#: and ``body`` share a stack in the default and are separate roles anyway, and
#: this preset is where that separation becomes visible. ``numeric`` does not
#: move — figures align in a monospace or they do not align.
#:
#: Tahoma leads because a research masthead wants neutral authority rather
#: than character: Verdana is wider than a 28px title wants, and Trebuchet is
#: friendlier than the subject matter. Verdana is Tahoma's near-metric
#: relative and effectively universal, so the second entry degrades by width
#: rather than by voice; Geneva covers older Macs before the generic floor.
#:
#: The name is about the design, not the type-historical "modern" (Didone) —
#: a caller reading ``font_theme="modern"`` should expect a contemporary
#: sans-over-serif newsletter, and that is what they get.
MODERN_FONTS = FontTheme(
    heading=FontStack("Tahoma", "Verdana", "Geneva", "sans-serif"),
    body=DEFAULT_FONTS.body,
    label=FontStack("Tahoma", "Verdana", "Geneva", "sans-serif"),
    numeric=DEFAULT_FONTS.numeric,
)

#: Curated presets, repo-owned. A caller's own theme is passed as an object,
#: never registered here — the registry is a set of design decisions, not a
#: namespace, and nothing mutates it at runtime.
FONT_THEMES: dict[str, FontTheme] = {"classic": DEFAULT_FONTS, "modern": MODERN_FONTS}


def resolve_font_theme(value: FontTheme | str) -> FontTheme:
    """
    Turn whatever a caller supplied into a concrete :class:`FontTheme`.

    Accepts a ``FontTheme`` — returned as-is, since it validated itself at its
    own construction — or the name of a curated preset. An unknown name raises
    :class:`~pyhermes.builder.exceptions.ValidationError` naming what is available,
    because a preset name that names nothing is a typo and a typo belongs to
    construction rather than to render.

    Unlike ``size_theme``, an *object* is accepted: a custom
    :class:`FontTheme` is safe by construction, since the terminal-generic rule
    means Outlook always walks a chain the caller curated down to a floor.
    """
    if isinstance(value, FontTheme):
        return value
    try:
        return FONT_THEMES[value]
    except KeyError:
        raise ValidationError(
            f"unknown font theme {value!r}; available: {sorted(FONT_THEMES)}"
        ) from None


__all__ = [
    "DEFAULT_FONTS",
    "MODERN_FONTS",
    "FONT_THEMES",
    "GENERIC_FAMILIES",
    "FontFace",
    "FontFile",
    "FontStack",
    "FontTheme",
    "resolve_font_theme",
]
