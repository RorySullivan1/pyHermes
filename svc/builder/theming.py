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
    ``wrapper_bg``     ``#F2F1EE``  12×  base, footer-legal — the warm stone padding
    ``surface``        ``#FFFFFF``  67×  everywhere — the white email body
    ``header_bg``      ``#2C3E50``  22×  header regions, headings, rules — soft navy
    ``accent``         ``#5B8A9A``   9×  links, the CTA button, rules — muted teal
    ``rule``           ``#D6D2CB``  33×  the standard hairline, all 8 containers
    ``rule_subtle``    ``#EAE8E4``   2×  data-table row separators, author-block top
    ``rule_dark``      ``#2C3E50``   —   the same value as ``header_bg``; see below
    ``highlight_tint`` ``#F8F7F5``  27×  ``highlight=True`` in all 8 containers
    ``row_alt``        ``#F8F7F5``   9×  data-table alternating rows

TextColors
    ``primary``        ``#3B3B3B``  26×  body copy
    ``secondary``      ``#7A7A72``  12×  captions, sources, sublabels
    ``light``          ``#A09E97``   6×  as-of lines, the copyright line
    ``fine_print``     ``#8A8880``   1×  the footer disclaimer
    ``on_dark``        ``#FFFFFF``   —   the firm name over navy; ``surface``'s value
    ``on_dark_secondary`` ``#CFD8DC``  2×  the campaign name over navy
    ``on_dark_muted``  ``#90A4AE``   6×  header disclaimer, date range, issue label

SemanticColors
    ``positive``       ``#4A7C59``   0×  **no render site today** — see below
    ``negative``       ``#B85450``   0×  **no render site today** — see below
    ``neutral``        ``#5A5A5A``   2×  data-table header + cell fallback,
                                         ``filters.default_color``, ``Card.color``

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

* **``positive`` and ``negative`` render nowhere by default.** They live in
  the docstring examples and in callers' own ``KpiItem`` data. They are
  tokens here because they are the vocabulary the palette comment published
  and callers already use — but tokenising them changes no byte, and nothing
  in the templates reads them.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields

from .exceptions import ValidationError
from .models import _validate_color


def _validate_hex_fields(instance: object, prefix: str) -> None:
    """Run every ``str`` field of a frozen token layer through the hex rule."""
    for spec in fields(instance):  # type: ignore[arg-type]
        value = getattr(instance, spec.name)
        if isinstance(value, str):
            _validate_color(value, f"{prefix}.{spec.name}")


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
    """

    primary: str = "#3B3B3B"
    secondary: str = "#7A7A72"
    light: str = "#A09E97"
    fine_print: str = "#8A8880"
    on_dark: str = "#FFFFFF"
    on_dark_secondary: str = "#CFD8DC"
    on_dark_muted: str = "#90A4AE"

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

    def __post_init__(self) -> None:
        expected = {
            "palette": Palette,
            "text": TextColors,
            "semantic": SemanticColors,
            "shadow": ShadowStyle,
        }
        for name, layer_cls in expected.items():
            if not isinstance(getattr(self, name), layer_cls):
                raise ValidationError(
                    f"'theme.{name}' must be a {layer_cls.__name__}, got: "
                    f"{type(getattr(self, name)).__name__}"
                )


#: The palette this repo has always rendered. Every value traces to the audit
#: in the module docstring.
DEFAULT_THEME = Theme()

#: Curated presets, repo-owned. A caller's own theme is passed as an object,
#: never registered here — the registry is a set of design decisions, not a
#: namespace.
THEMES: dict[str, Theme] = {"classic": DEFAULT_THEME}
