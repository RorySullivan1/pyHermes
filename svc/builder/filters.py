"""
Custom Jinja2 filters and tests for the email builder.
"""

import re
from typing import Any

import jinja2


def validate_hex_color(value: str) -> str:
    """
    Validate that a string is a valid hex color code.
    Returns the value if valid, raises ValueError otherwise.

    Usage in templates:
        {{ color | validate_hex_color }}
    """
    if not isinstance(value, str):
        raise ValueError(f"Expected string for hex color, got {type(value).__name__}")
    if not re.match(r"^#[0-9A-Fa-f]{6}$", value):
        raise ValueError(f"Invalid hex color: {value}")
    return value


def size_kb(value: str) -> float:
    """
    Return the size of a string in kilobytes (UTF-8 encoded).

    Usage in templates:
        {{ content | size_kb }}
    """
    return len(str(value).encode("utf-8")) / 1024


def default_color(value: Any, fallback: str = "#5A5A5A") -> str:
    """
    Return the value if truthy, otherwise return the fallback color.
    Validates the result is a hex color.

    Usage in templates:
        {{ row_color | default_color('#4A7C59') }}
    """
    result = value if value else fallback
    return validate_hex_color(result)


def register_all(env: jinja2.Environment) -> None:
    """
    Register all custom filters and tests on a Jinja2 Environment.

    Args:
        env: jinja2.Environment instance
    """
    env.filters["validate_hex_color"] = validate_hex_color
    env.filters["size_kb"] = size_kb
    env.filters["default_color"] = default_color
