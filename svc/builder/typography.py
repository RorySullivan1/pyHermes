"""
The email's typeface vocabulary — one validated object per house voice.

Faces were the last hardcoded axis of the design system. Colour became a
resolved :class:`~svc.builder.theming.Theme` in #46 and density a resolved
:class:`~svc.builder.sizing.SizeScheme` in #45, but ``font-family`` stacks
stayed baked into the templates: repeated per declaration, unnamed,
unvariable. A newsletter wanting a different house face forked templates.
This module is that owner.

::

    EmailMetadata.font_theme        (a preset name, or a FontTheme)
            |  resolved ONCE in Email.render()
            v
    FontTheme                       (frozen, validated at construction)
    +-- heading    FontStack        masthead title, section titles, item titles
    +-- body       FontStack        prose, the page default, KPI values
    +-- label      FontStack        meta, captions, table text, footer, chrome
    +-- numeric    FontStack        the data table's figure columns

**The audit this module is pinned to** — every ``font-family`` declaration in
``svc/builder/templates/``, 2026-08-28. Three stacks, 49 declarations:

===========================================  =====  ==============================
stack                                        count  drawn at
===========================================  =====  ==============================
``Georgia, 'Times New Roman', serif``           21  the page default (``<body>``
                                                    inline **and** the ``[if mso]``
                                                    ``body, td, th`` fallback),
                                                    masthead title, section titles,
                                                    italic subtitles, item titles,
                                                    list ordinals, prose body, and
                                                    the **KPI values**
``Arial, Helvetica, sans-serif``                27  the strip, masthead subtitle /
                                                    meta / department, card labels
                                                    and sublabels, table headers and
                                                    cells, captions, contact copy,
                                                    the footer
``'Courier New', Courier, monospace``            1  the data table's non-first
                                                    columns, via ``{% if
                                                    loop.first %}`` — the figures
===========================================  =====  ==============================

**Four roles, not three, and the difference is the whole point.** Naming them
after the values — ``serif`` and ``sans`` — is the mistake the colour and size
audits each existed to avoid, and here it would also be *wrong*: the serif is
not "headings", it is the editorial voice, and it sets the KPI numerals as
readily as the masthead. A preset that wants a sans masthead over a serif body
— the motivating variant — needs ``heading`` and ``body`` separately
addressable, so the vocabulary is cut by the job a face does rather than by
which face happens to do it today. That ``heading`` and ``body`` are the same
stack in the default is a fact about the default, not about the roles.

**A stack is the atom, never a face.** Every :class:`FontStack` must end in a
CSS generic family, because in email the fallback chain *is* the rendering:
Outlook's Word engine walks the chain and lands wherever it lands, so the
generic is the floor that makes a custom face safe rather than a gamble. That
rule is checkable without maintaining a list of "websafe" names that would rot,
and it is what lets ``font_theme`` accept a caller's own object where
``size_theme`` accepts only a preset name.

**Weights, italics and letter-spacing stay literal, and that is a decision.**
The audit found ``font-weight`` at ``bold`` (16), ``400`` (2) and ``300`` (1),
plus ``font-style:italic`` (10). These are structural emphasis riding the role
sites — the same call ``border-width`` and ``letter-spacing`` got in #45: shape
rather than voice. Numeric weights beyond 400/700 are also unreliable in the
Word engine, which synthesises what a face does not supply. A theme that wants
a lighter voice picks a lighter *face*, in the stack, where the fallback chain
can be reasoned about.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field, fields, replace

from .exceptions import ValidationError

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


@dataclass(frozen=True)
class FontStack:
    """
    A font fallback chain, stored as families and composed at render.

    Storing ``"Georgia, 'Times New Roman', serif"`` as a string would make it
    unvalidatable and un-inspectable — you could not ask whether it ends in a
    generic without parsing CSS back out of it. Storing the families keeps a
    stack a *chain*.

    **The formatting contract is byte-exact and load-bearing**, the lesson
    :class:`~svc.builder.theming.Rgba` learned: one composer means two emission
    sites cannot drift. Families are separated by ``", "``, and a name
    containing a space is quoted on emission with single quotes — never stored
    pre-quoted, so ``families`` is always the plain names.

    Args:
        families: The chain, in order, ending in a CSS generic family.

    Raises:
        ValidationError: For a chain that does not end in a generic, one with
            fewer than two entries, or a family name that is empty or carries a
            character that would break out of the ``style`` attribute.
    """

    families: tuple[str, ...]

    def __init__(self, *families: str) -> None:
        # Varargs rather than a tuple argument: ``FontStack("Georgia",
        # "Times New Roman", "serif")`` reads as the chain it is, and a caller
        # cannot accidentally pass a bare string and get it iterated per
        # character — the failure mode a tuple field invites.
        object.__setattr__(self, "families", tuple(families))
        self.validate()

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
    guarantee :class:`~svc.builder.theming.Theme` and
    :class:`~svc.builder.sizing.SizeScheme` make, for the third axis.

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
    :class:`~svc.builder.exceptions.ValidationError` naming what is available,
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
    "FontStack",
    "FontTheme",
    "resolve_font_theme",
]
