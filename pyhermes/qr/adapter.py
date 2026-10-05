"""
A URL, as a :class:`~pyhermes.builder.QrCode` that prints and scans (#344).

segno is pure Python and needs no system library, which is why it is the
backend. The PNG is painted once, in the theme's ink on its surface, at
enough pixels for ``Config.print_dpi`` at the printed size.
"""

from __future__ import annotations

import io
import math
from typing import Any

from pyhermes.builder import QrCode
from pyhermes.builder.surfaces import QR_SIZE, check_qr_url
from pyhermes.builder.theming import Theme, resolve_theme
from pyhermes.config import get_config

from .exceptions import BackendMissingError

#: The quiet zone round the symbol, in modules: the four the QR standard asks for.
BORDER = 4

#: CSS px to the inch, against which a print resolution is reckoned.
_CSS_DPI = 96


def available() -> bool:
    """Whether segno is installed."""
    try:
        import segno  # noqa: F401
    except ImportError:
        return False
    return True


def render_qr(url: str, *, size: int = QR_SIZE, dark: str, light: str) -> bytes:
    """
    The QR symbol for ``url`` as PNG bytes, ``size`` CSS px across at print resolution.

    Each module is a whole number of pixels, the fewest that reach
    ``Config.print_dpi`` at ``size``, so the edges stay sharp and two renders
    of one URL are the same bytes. segno writes no text chunk or timestamp.

    Raises:
        BackendMissingError: When the ``[qr]`` extra is not installed.
    """
    segno = _backend()
    symbol = segno.make(url, error="m", micro=False)
    modules = symbol.symbol_size(border=BORDER)[0]
    scale = math.ceil(size * get_config().print_dpi / _CSS_DPI / modules)
    out = io.BytesIO()
    symbol.save(out, kind="png", scale=scale, border=BORDER, dark=dark, light=light)
    return out.getvalue()


def qr_code(
    url: str,
    caption: str | None = None,
    *,
    theme: Theme | str = "classic",
    size: int = QR_SIZE,
    align: str | None = None,
) -> QrCode:
    """
    A :class:`QrCode` for ``url``, in ``theme``'s primary text on its surface.

    The URL is checked by the component before anything renders, so a scheme
    the builder refuses never reaches segno.
    """
    check_qr_url(url)
    palette = resolve_theme(theme)
    png = render_qr(url, size=size, dark=palette.text.primary, light=palette.palette.surface)
    return QrCode(png, url, caption, size=size, align=align)


def _backend() -> Any:
    try:
        import segno
    except ImportError as exc:
        raise BackendMissingError('A QR code needs segno: pip install "pyhermes[qr]"') from exc
    return segno
