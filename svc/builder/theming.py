"""
Theming — every colour and shadow in the email, as one validated object.

Colour used to be 18 distinct hex values in 245 occurrences across all 20
template files, plus three ``rgba()`` literals and three Python-side
fallbacks. A palette *comment* in ``base.html`` named 13 roles, but it was
dead text: it could not be read by anything, and it had already drifted (see
the audit below). This module is what replaces it — a named home for every
value, frozen and validated, so a caller can re-skin the newsletter from one
field instead of forking 20 templates.

**The theme is the unit of customisation, never a single colour at a call
site.** Coherence survives because the whole theme is the atom: the layers
are frozen, no token field is optional, and every value is validated at
construction. There is no way to build a ``Theme`` that later fails a render
under ``StrictUndefined`` — completeness is structural, not remembered.

Four layers, because they answer different questions:

============== ==================================================
:class:`Palette`        surfaces and structure — what the email is made of
:class:`TextColors`     the type, on light grounds and on the navy masthead
:class:`SemanticColors` what a *number* means; defaults and fallbacks only
:class:`ShadowStyle`    the three composed ``rgba()`` values
============== ==================================================

``SemanticColors`` deserves its own note. ``KpiItem.color`` and
``TableRow.colors`` are the caller's statement about the **data** ("this
number is down"), not a styling choice — they stay caller-supplied. The
theme provides only what is used when the caller says nothing.

The audit
---------

Every default below is exactly what the templates hardcode today. Occurrence
counts are over ``svc/builder/templates/``; the palette comment's own 13
lines are excluded from "renders in".

Palette
    ``wrapper_bg``     ``#F2F1EE``  13×  base, footer-legal — the warm stone padding,
                                         and the preheader text hidden against it
    ``surface``        ``#FFFFFF``  63×  everywhere — the white email body
    ``header_bg``      ``#2C3E50``   9×  the masthead band — soft navy
    ``accent``         ``#5B8A9A``   9×  links, the CTA button, rules — muted teal
    ``rule``           ``#D6D2CB``  33×  the standard hairline, all 8 containers
    ``rule_subtle``    ``#EAE8E4``   2×  data-table row separators, author-block top
    ``rule_dark``      ``#2C3E50``   1×  the section-title underline
    ``highlight_tint`` ``#F8F7F5``  27×  ``highlight=True`` in all 8 containers
    ``row_alt``        ``#F8F7F5``   9×  data-table alternating rows

TextColors
    ``primary``        ``#3B3B3B``  26×  body copy
    ``secondary``      ``#7A7A72``  12×  captions, sources, sublabels
    ``light``          ``#A09E97``   6×  as-of lines, the copyright line
    ``heading``        ``#2C3E50``  11×  section titles, table headers, author name
    ``fine_print``     ``#8A8880``   1×  the footer disclaimer
    ``on_dark``        ``#FFFFFF``   2×  the firm name over navy
    ``on_dark_secondary`` ``#CFD8DC``  2×  the campaign name over navy
    ``on_dark_muted``  ``#90A4AE``   6×  header disclaimer, date range, issue label
    ``on_accent``      ``#FFFFFF``   2×  the contact CTA's label, on the accent fill

SemanticColors
    ``positive``       ``#4A7C59``   0×  **no render site today** — see below
    ``negative``       ``#B85450``   0×  **no render site today** — see below
    ``neutral``        ``#5A5A5A``   2×  the data-table header row and its cell
                                         fallback; also what an unset
                                         ``Card.color`` resolves to

ShadowStyle
    ``scrim``          ``#141E2C`` @ 0.65  the header hero's legibility overlay
    ``title``          ``#000000`` @ 0.4   ``text-shadow`` on the firm name
    ``subtitle``       ``#000000`` @ 0.3   ``text-shadow`` on the campaign name

Four things the audit found, recorded rather than quietly fixed
---------------------------------------------------------------

* **The palette comment was wrong, not merely incomplete.** It named "Row alt
  ``#F5F4F1``", but ``data-table.html`` alternates rows with ``#F8F7F5`` — the
  same value as the highlight tint. ``#F5F4F1`` appears nowhere else in the
  repo. The *role* was real; the value the comment claimed was not, which is
  precisely the failure mode a comment nothing can read is prone to.

* **``row_alt`` and ``highlight_tint`` are separate tokens that happen to
  share a value.** Collapsing them would make the coincidence permanent and
  deny a theme author the distinction the comment itself drew.

* **``rule_dark`` is ``header_bg``'s value by design, and stays a distinct
  token** for the same reason — a section heading's underline matching the
  masthead is a decision a theme may want to keep or break.

* **``default_color`` and ``validate_hex_color`` were registered filters that
  no template called.** ``default_color``'s ``#5A5A5A`` was therefore a
  literal in a code path nothing exercised. The migration puts the filter to
  work — ``{{ card.color | default_color(theme.semantic.neutral) }}`` — which
  removes the literal, resolves an unset ``Card.color`` against the live
  theme, and validates an explicit one on the way through.

* **``positive`` and ``negative`` render nowhere by default.** They live in
  the docstring examples and in callers' own ``KpiItem`` data. They are
  tokens here because they are the vocabulary the palette comment published
  and callers already use — but tokenising them changes no byte, and nothing
  in the templates reads them.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, fields, replace
from typing import Any, ClassVar

from .exceptions import ValidationError
from .models import _validate_color


def _validate_hex_fields(instance: object, prefix: str) -> None:
    """
    Run every token of a frozen layer through the hex rule.

    A non-string is rejected here rather than allowed to reach a template as
    whatever it is: every field on these layers is a colour, so anything that
    is not a ``#RRGGBB`` string is wrong in the same way.
    """
    for spec in fields(instance):  # type: ignore[arg-type]
        value = getattr(instance, spec.name)
        name = f"{prefix}.{spec.name}"
        if not isinstance(value, str):
            raise ValidationError(
                f"'{name}' must be a hex color string, got: {type(value).__name__}"
            )
        _validate_color(value, name)


@dataclass(frozen=True)
class Palette:
    """Surfaces and structure: what the email is made of."""

    wrapper_bg: str = "#F2F1EE"
    surface: str = "#FFFFFF"
    header_bg: str = "#2C3E50"
    accent: str = "#5B8A9A"
    rule: str = "#D6D2CB"
    rule_subtle: str = "#EAE8E4"
    rule_dark: str = "#2C3E50"
    highlight_tint: str = "#F8F7F5"
    row_alt: str = "#F8F7F5"

    def __post_init__(self) -> None:
        _validate_hex_fields(self, "palette")


@dataclass(frozen=True)
class TextColors:
    """
    The type, on both grounds the email uses.

    ``primary`` → ``secondary`` → ``light`` is the ladder on light surfaces;
    ``on_dark`` → ``on_dark_secondary`` → ``on_dark_muted`` is the same ladder
    over the navy masthead. ``fine_print`` is the footer disclaimer, which
    sits between ``secondary`` and ``light`` and is neither.

    ``heading`` and ``on_accent`` share a value with ``palette.header_bg``
    and ``palette.surface`` today, and are separate tokens for the reason the
    whole module exists: a theme with a navy masthead and charcoal headings,
    or a pale accent needing dark button text, is a design somebody may want.
    Type is not a surface, even when it borrows a surface's colour.
    """

    primary: str = "#3B3B3B"
    secondary: str = "#7A7A72"
    light: str = "#A09E97"
    heading: str = "#2C3E50"
    fine_print: str = "#8A8880"
    on_dark: str = "#FFFFFF"
    on_dark_secondary: str = "#CFD8DC"
    on_dark_muted: str = "#90A4AE"
    on_accent: str = "#FFFFFF"

    def __post_init__(self) -> None:
        _validate_hex_fields(self, "text")


@dataclass(frozen=True)
class SemanticColors:
    """
    What a number *means* — defaults and fallbacks only.

    ``KpiItem.color`` and ``TableRow.colors`` stay caller data: they are a
    statement about the figure, not about the design. These are what renders
    when the caller says nothing.
    """

    positive: str = "#4A7C59"
    negative: str = "#B85450"
    neutral: str = "#5A5A5A"

    def __post_init__(self) -> None:
        _validate_hex_fields(self, "semantic")


@dataclass(frozen=True)
class Rgba:
    """
    A colour with an alpha, stored as its parts and composed at render.

    Storing ``rgba(20,30,44,0.65)`` as a string would make it unthemeable —
    a theme author would have to hand-write CSS rather than pick a colour.
    Storing hex plus alpha keeps the *colour* a colour.

    **The formatting contract is byte-exact and load-bearing**: no spaces
    after the commas, and the alpha with no trailing zeros — ``0.65``, not
    ``0.650``, and ``1`` rather than ``1.0``. That is what the three shipped
    literals look like today, and the goldens fail on a single character.
    """

    color: str
    alpha: float

    def __post_init__(self) -> None:
        _validate_color(self.color, "shadow.color")
        if not isinstance(self.alpha, int | float) or isinstance(self.alpha, bool):
            raise ValidationError(
                f"'shadow.alpha' must be a number, got: {type(self.alpha).__name__}"
            )
        if not 0 <= self.alpha <= 1:
            raise ValidationError(f"'shadow.alpha' must be within [0, 1], got: {self.alpha}")

    @property
    def css(self) -> str:
        """The ``rgba(...)`` string, in exactly the shipped formatting."""
        red, green, blue = (int(self.color[i : i + 2], 16) for i in (1, 3, 5))
        return f"rgba({red},{green},{blue},{float(self.alpha):.10g})"

    @property
    def opacity_percent(self) -> str:
        """
        The same alpha in VML's spelling: ``65%``.

        Outlook's ``<v:fill>`` takes the colour and the opacity as two
        separate attributes, so the scrim exists twice in the masthead — once
        as CSS ``rgba()`` for everyone else, once as VML for Outlook. Both
        read this one object, which is the only reason they cannot drift.
        """
        return f"{float(self.alpha) * 100:.10g}%"

    def __str__(self) -> str:
        """So a template can write ``{{ theme.shadow.scrim }}`` and get CSS."""
        return self.css


@dataclass(frozen=True)
class ShadowStyle:
    """The three composed ``rgba()`` values, all of them in the masthead."""

    scrim: Rgba = field(default_factory=lambda: Rgba("#141E2C", 0.65))
    title: Rgba = field(default_factory=lambda: Rgba("#000000", 0.4))
    subtitle: Rgba = field(default_factory=lambda: Rgba("#000000", 0.3))

    def __post_init__(self) -> None:
        for spec in fields(self):
            if not isinstance(getattr(self, spec.name), Rgba):
                raise ValidationError(
                    f"'shadow.{spec.name}' must be an Rgba, got: "
                    f"{type(getattr(self, spec.name)).__name__}"
                )


@dataclass(frozen=True)
class Theme:
    """
    Every colour and shadow the email uses, as one validated object.

    Frozen, and with no optional token fields anywhere in the tree: a
    ``Theme`` that exists is a ``Theme`` that renders. Construct one from
    scratch, or start from a preset — the layers each carry today's values
    as their defaults, so overriding one token is a one-argument change.
    """

    palette: Palette = field(default_factory=Palette)
    text: TextColors = field(default_factory=TextColors)
    semantic: SemanticColors = field(default_factory=SemanticColors)
    shadow: ShadowStyle = field(default_factory=ShadowStyle)

    LAYERS: ClassVar[dict[str, type]] = {
        "palette": Palette,
        "text": TextColors,
        "semantic": SemanticColors,
        "shadow": ShadowStyle,
    }

    def __post_init__(self) -> None:
        for name, layer_cls in self.LAYERS.items():
            if not isinstance(getattr(self, name), layer_cls):
                raise ValidationError(
                    f"'theme.{name}' must be a {layer_cls.__name__}, got: "
                    f"{type(getattr(self, name)).__name__}"
                )

    def derive(self, **layers: Any) -> Theme:
        """
        A copy of this theme with some tokens replaced.

        The common case is not "build a palette from nothing" — it is "the
        shipped palette, with our brand's masthead and accent"::

            DEFAULT_THEME.derive(palette={"header_bg": "#1B3A5C",
                                          "accent": "#7FA8B8"})

        Each keyword names a layer and takes either a mapping of the tokens
        to change or a whole replacement layer. Everything else is inherited,
        and the result is a normal ``Theme`` — frozen, complete, and
        **re-validated**, so a derived theme cannot be less valid than one
        built from scratch.

        Raises:
            ValidationError: For an unknown layer, an unknown token within a
                layer, or a value that fails its own rule.
        """
        unknown = set(layers) - set(self.LAYERS)
        if unknown:
            raise ValidationError(
                f"unknown theme layer(s) {sorted(unknown)}; known layers: {sorted(self.LAYERS)}"
            )
        replacements: dict[str, Any] = {}
        for name, override in layers.items():
            layer_cls = self.LAYERS[name]
            if isinstance(override, layer_cls):
                replacements[name] = override
                continue
            if not isinstance(override, Mapping):
                raise ValidationError(
                    f"'{name}' must be a {layer_cls.__name__} or a mapping of its "
                    f"tokens, got: {type(override).__name__}"
                )
            current = getattr(self, name)
            known = {f.name for f in fields(current)}
            stray = set(override) - known
            if stray:
                raise ValidationError(
                    f"unknown {name} token(s) {sorted(stray)}; known tokens: {sorted(known)}"
                )
            replacements[name] = replace(current, **override)
        return replace(self, **replacements)


#: The palette this repo has always rendered. Every value traces to the audit
#: in the module docstring.
DEFAULT_THEME = Theme()

#: A cool blue-grey counterpart to ``classic``'s warm stone.
#:
#: Curated, not computed. A hue rotation of the default would have been one
#: line and would have proved nothing: every value here is chosen the way the
#: default's were, which is what makes this a second design rather than a
#: filter over the first. It exists so the seam carries weight — a preset
#: nobody can compare against is a refactor — and as the reference for what
#: a complete theme looks like when you write one yourself.
SLATE_THEME = Theme(
    palette=Palette(
        wrapper_bg="#EDF0F3",
        surface="#FFFFFF",
        header_bg="#26333F",
        accent="#4A6E8A",
        rule="#CBD3DA",
        rule_subtle="#E2E7EC",
        rule_dark="#26333F",
        highlight_tint="#F4F6F8",
        row_alt="#F4F6F8",
    ),
    text=TextColors(
        primary="#33393F",
        secondary="#6B747C",
        light="#98A1A9",
        heading="#26333F",
        fine_print="#82898F",
        on_dark="#FFFFFF",
        on_dark_secondary="#C6D2DC",
        on_dark_muted="#8FA0AE",
        on_accent="#FFFFFF",
    ),
    semantic=SemanticColors(positive="#3F7A63", negative="#A8514E", neutral="#5A6068"),
    shadow=ShadowStyle(
        scrim=Rgba("#0F1A24", 0.65),
        title=Rgba("#000000", 0.4),
        subtitle=Rgba("#000000", 0.3),
    ),
)

#: Curated presets, repo-owned. A caller's own theme is passed as an object,
#: never registered here — the registry is a set of design decisions, not a
#: namespace, and nothing mutates it at runtime.
THEMES: dict[str, Theme] = {"classic": DEFAULT_THEME, "slate": SLATE_THEME}


def resolve_theme(value: Theme | str) -> Theme:
    """
    Turn whatever a caller supplied into a concrete :class:`Theme`.

    Accepts a ``Theme`` — returned as-is, since it validated itself at its
    own construction — or the name of a curated preset. An unknown name
    raises :class:`~svc.builder.exceptions.ValidationError` naming what is
    available, because "neon" is a typo, not a design decision.

    Called from :meth:`svc.builder.email.Email.render` and from
    :meth:`svc.builder.models.EmailMetadata.__post_init__`; the latter is
    what makes a bad preset name fail at construction rather than at render.
    """
    if isinstance(value, Theme):
        return value
    if isinstance(value, str):
        try:
            return THEMES[value]
        except KeyError:
            raise ValidationError(
                f"unknown theme preset {value!r}; known presets: "
                f"{sorted(THEMES)}. Pass a Theme instance for a custom palette."
            ) from None
    raise ValidationError(f"'theme' must be a Theme or a preset name, got: {type(value).__name__}")
