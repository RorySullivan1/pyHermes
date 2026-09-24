"""
The equation renderer: LaTeX becomes the image a ``MathBlock`` takes.

A sibling of ``svc.data`` on the same terms. It imports the builder, the
builder never imports it, and matplotlib is the ``[math]`` extra, imported
lazily, so the core install stays Jinja2-only.
"""

from .adapter import DEFAULT_MATH_FONTSET, DEFAULT_MATH_SCALE, image_from_math, math_block
from .exceptions import BackendMissingError, MathError, MathSyntaxError
from .render import FONTSETS, RenderedMath, available, render_math

__all__ = [
    "DEFAULT_MATH_FONTSET",
    "DEFAULT_MATH_SCALE",
    "FONTSETS",
    "BackendMissingError",
    "MathError",
    "MathSyntaxError",
    "RenderedMath",
    "available",
    "image_from_math",
    "math_block",
    "render_math",
]
