"""
Finance number formatting: a figure in, the string both projections read out.

Stdlib only, importing nothing from the builder, and an AST test holds that.
Rounding is ``Decimal`` half up, so ``0.125`` is ``0.13`` where ``round()``
gives ``0.12``. Output is ASCII, minus sign included (#148). ``None`` and NaN
render as ``missing``, and zero, including a value that rounds to zero, is
never signed. Arithmetic runs in a context of its own, never the host's (#448).
`.claude/rules/data-layer.md` carries the reasoning::

    pct(0.0142, sign=True)   # '+1.42%'
    money(-1200)             # '-$1,200'
    compact(1_240_000_000)   # '1.2bn'
"""

from __future__ import annotations

import numbers
from decimal import (
    MAX_EMAX,
    MIN_EMIN,
    ROUND_HALF_UP,
    Context,
    Decimal,
    DivisionByZero,
    InvalidOperation,
    Overflow,
)
from typing import Any

#: What a missing figure renders as. ASCII, for the reason the minus sign is.
MISSING = "--"

_COMPACT_SCALES = (
    (Decimal(1), ""),
    (Decimal(10) ** 3, "k"),
    (Decimal(10) ** 6, "m"),
    (Decimal(10) ** 9, "bn"),
    (Decimal(10) ** 12, "tn"),
)


def number(
    value: Any,
    dp: int = 0,
    *,
    sign: bool = False,
    thousands: str = ",",
    decimal: str = ".",
    missing: str = MISSING,
) -> str:
    """A plain figure: ``number(5234)`` is ``'5,234'``."""
    d = _decimal(value)
    if d is None:
        return missing
    prefix, body = _fixed(d, dp, sign, thousands, decimal)
    return prefix + body


def pct(
    value: Any,
    dp: int = 2,
    *,
    sign: bool = False,
    thousands: str = ",",
    decimal: str = ".",
    missing: str = MISSING,
) -> str:
    """A fraction as a percentage: ``pct(0.0142)`` is ``'1.42%'``."""
    d = _decimal(value)
    if d is None:
        return missing
    prefix, body = _fixed(d, dp, sign, thousands, decimal, shift=2)
    return f"{prefix}{body}%"


def bps(
    value: Any,
    dp: int = 0,
    *,
    sign: bool = True,
    decimal: str = ".",
    missing: str = MISSING,
) -> str:
    """A fraction in basis points, signed by default: ``bps(0.0006)`` is ``'+6 bps'``."""
    d = _decimal(value)
    if d is None:
        return missing
    prefix, body = _fixed(d, dp, sign, ",", decimal, shift=4)
    return f"{prefix}{body} bps"


def delta(
    value: Any,
    dp: int = 2,
    *,
    unit: str = "",
    sign: bool = True,
    thousands: str = ",",
    decimal: str = ".",
    missing: str = MISSING,
) -> str:
    """A signed change with an optional unit: ``delta(-2.18, unit="pts")`` is ``'-2.18 pts'``."""
    d = _decimal(value)
    if d is None:
        return missing
    prefix, body = _fixed(d, dp, sign, thousands, decimal)
    return f"{prefix}{body} {unit}" if unit else prefix + body


def money(
    value: Any,
    dp: int = 0,
    *,
    currency: str = "$",
    sign: bool = False,
    thousands: str = ",",
    decimal: str = ".",
    missing: str = MISSING,
) -> str:
    """An amount, sign before the symbol: ``money(-1200)`` is ``'-$1,200'``, not ``'$-1,200'``."""
    d = _decimal(value)
    if d is None:
        return missing
    prefix, body = _fixed(d, dp, sign, thousands, decimal)
    return f"{prefix}{currency}{body}"


def compact(
    value: Any,
    dp: int = 1,
    *,
    sign: bool = False,
    thousands: str = ",",
    decimal: str = ".",
    missing: str = MISSING,
) -> str:
    """
    A magnitude in k, m, bn or tn: ``compact(1_240_000_000)`` is ``'1.2bn'``.

    Trailing zeros are dropped, so ``340m`` rather than ``340.0m``. A value
    that rounds up to 1,000 of one unit moves to the next, so ``999_950``
    is ``1m`` rather than ``1,000k``.
    """
    d = _decimal(value)
    if d is None:
        return missing
    ctx = _context(d, dp)
    index = max(
        i for i, (scale, _) in enumerate(_COMPACT_SCALES) if i == 0 or d.copy_abs() >= scale
    )
    while True:
        scale, suffix = _COMPACT_SCALES[index]
        rounded = _round(ctx.scaleb(d, -scale.adjusted()), dp, ctx)
        if rounded.copy_abs() < 1000 or index == len(_COMPACT_SCALES) - 1:
            break
        index += 1
    prefix, body = _split(rounded, dp, sign, thousands, decimal)
    if decimal in body:
        body = body.rstrip("0").rstrip(decimal)
    return f"{prefix}{body}{suffix}"


def displays_zero(text: str) -> bool:
    """
    Whether a formatted figure shows as zero, whatever the value's own sign.

    ``pct(-0.00001)`` is ``'0.00%'``. Colouring it negative would put the
    string and its colour in disagreement, so a tone derived from a value
    asks this first.
    """
    return not any(character in "123456789" for character in text)


def _decimal(value: Any) -> Decimal | None:
    """The value as an exact ``Decimal``, or ``None`` when it is missing."""
    if value is None:
        return None
    if isinstance(value, bool):
        raise TypeError("a bool is not a figure; format it as text")
    if isinstance(value, Decimal):
        result = value
    elif isinstance(value, numbers.Integral):
        result = Decimal(int(value))
    elif isinstance(value, numbers.Real):
        # Through repr, so 0.0142 is Decimal('0.0142') and not the binary
        # float's exact expansion, which would round 2.675 down.
        result = Decimal(repr(float(value)))
    else:
        raise TypeError(f"expected a number, got {type(value).__name__}")
    if result.is_nan():
        return None
    if result.is_infinite():
        raise ValueError("an infinite value has no printed form")
    return result


def _context(value: Decimal, dp: int) -> Context:
    """
    A context of its own, wide enough that no step of formatting this figure rounds.

    The ambient one is the host's, and a host that sets its precision or rounding would
    otherwise move every figure printed. Every flag and trap is named so a mutated
    ``DefaultContext`` cannot leak in either.
    """
    if isinstance(dp, bool) or not isinstance(dp, int) or dp < 0:
        raise ValueError(f"dp must be a non-negative int, got {dp!r}")
    digits = max(len(value.as_tuple().digits), value.adjusted() + 1, 1)
    return Context(
        prec=digits + dp + 10,
        rounding=ROUND_HALF_UP,
        Emin=MIN_EMIN,
        Emax=MAX_EMAX,
        capitals=1,
        clamp=0,
        flags=[],
        traps=[InvalidOperation, DivisionByZero, Overflow],
    )


def _round(value: Decimal, dp: int, ctx: Context) -> Decimal:
    return value.quantize(Decimal((0, (1,), -dp)), rounding=ROUND_HALF_UP, context=ctx)


def _fixed(
    value: Decimal, dp: int, sign: bool, thousands: str, decimal: str, *, shift: int = 0
) -> tuple[str, str]:
    """Scale by ``10**shift``, round, then split into the sign and the grouped digits."""
    ctx = _context(value, dp)
    return _split(_round(ctx.scaleb(value, shift), dp, ctx), dp, sign, thousands, decimal)


def _split(rounded: Decimal, dp: int, sign: bool, thousands: str, decimal: str) -> tuple[str, str]:
    """The sign and the grouped digits of a figure already rounded to ``dp``."""
    if rounded == 0:
        prefix = ""
    elif rounded < 0:
        prefix = "-"
    else:
        prefix = "+" if sign else ""
    # Digits are read off the tuple, not formatted, so no context and no int() size limit applies.
    text = "".join(map(str, rounded.as_tuple().digits)).rjust(dp + 1, "0")
    whole, fraction = (text[:-dp], text[-dp:]) if dp else (text, "")
    groups = [whole[max(i - 3, 0) : i] for i in range(len(whole), 0, -3)]
    body = thousands.join(reversed(groups))
    return prefix, f"{body}{decimal}{fraction}" if fraction else body
