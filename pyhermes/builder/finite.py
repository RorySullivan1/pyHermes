"""
One test for a number that no template or computation can read: NaN and both infinities (#450).

A check that says "positive" or "below one" passes NaN, because every comparison
with it is false, and passes infinity, which is positive. Each such field asks
here instead, so the refusal is worded and placed once.
"""

from __future__ import annotations

import math
from decimal import Decimal
from typing import Any

from .exceptions import ValidationError


def is_finite(value: Any) -> bool:
    """Whether ``value`` is an int, float or Decimal that is neither NaN nor infinite."""
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    return isinstance(value, Decimal) and value.is_finite()


def require_finite(value: Any, name: str) -> None:
    """
    Raise unless ``value`` is a finite number.

    Raises:
        ValidationError: Naming ``name`` and the value.
    """
    if not is_finite(value):
        raise ValidationError(f"'{name}' must be a finite number, got: {value!r}")
