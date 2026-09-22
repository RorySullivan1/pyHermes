"""
A matplotlib Figure, as the :class:`~svc.builder.images.EmailImage` a chart takes.

pyHermes does not draw charts. This accepts one the caller drew and renders it
at the pixel size its display width needs, so a caller never writes a PNG to
disk first. matplotlib is the ``[charts]`` extra, imported only on use.
"""

from __future__ import annotations

import io
from typing import Any

from svc.builder import ChartBlock
from svc.builder.enums import EmbedStrategy
from svc.builder.exceptions import ValidationError
from svc.builder.images import EmailImage

from .exceptions import BackendMissingError


def available() -> bool:
    """Whether matplotlib is installed, for a caller that wants to skip."""
    try:
        import matplotlib  # noqa: F401
    except ImportError:
        return False
    return True


def image_from_figure(
    figure: Any,
    *,
    alt: str,
    width: int,
    scale: int = 2,
    strategy: EmbedStrategy | str = EmbedStrategy.CID,
    transparent: bool = False,
    tight: bool = False,
) -> EmailImage:
    """
    Render a Figure to PNG bytes ``width × scale`` pixels wide.

    ``width`` is the *display* width, emitted as the ``width`` attribute
    Outlook honours, and ``scale=2`` makes the bytes a retina asset. The
    Figure is not modified. ``CID`` is the default because ``DATA_URI`` is
    stripped by Gmail and capped, and a 2x chart is routinely over the cap.
    ``tight=True`` crops to the drawn area, which makes the pixel width
    whatever the crop leaves, so it is off unless asked for.
    """
    mpl = _backend()
    if not isinstance(figure, mpl.figure.Figure):
        raise ValidationError(f"image_from_figure takes a Figure, got {type(figure).__name__}")
    for name, value in (("width", width), ("scale", scale)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValidationError(f"{name!r} must be a positive int, got {value!r}")
    if strategy == EmbedStrategy.REMOTE:
        raise ValidationError("a rendered Figure has no host; embed it as 'cid' or 'data_uri'")

    buffer = io.BytesIO()
    figure.savefig(
        buffer,
        format="png",
        dpi=width * scale / figure.get_figwidth(),
        transparent=transparent,
        bbox_inches="tight" if tight else None,
        # The version string would change the bytes, and with them the
        # content-addressed cid, on every matplotlib upgrade.
        metadata={"Software": None},
    )
    data = buffer.getvalue()
    if strategy == EmbedStrategy.DATA_URI:
        return EmailImage.inline(data, alt=alt, width=width)
    return EmailImage.attached(data, alt=alt, width=width)


def chart_from_figure(
    figure: Any,
    *,
    alt: str,
    width: int,
    scale: int = 2,
    strategy: EmbedStrategy | str = EmbedStrategy.CID,
    source: str = "",
    subtitle: str | None = None,
    disclosure: str = "",
    align: str | None = None,
) -> ChartBlock:
    """A :class:`ChartBlock` around :func:`image_from_figure`, attribution included."""
    image = image_from_figure(figure, alt=alt, width=width, scale=scale, strategy=strategy)
    return ChartBlock(image, source=source, subtitle=subtitle, disclosure=disclosure, align=align)


def _backend() -> Any:
    """
    Import matplotlib, or say what to install.

    ``matplotlib.figure`` is imported explicitly: the top-level package does
    not load it, and a caller's Figure may come from a module that never did.
    """
    try:
        import matplotlib
        import matplotlib.figure  # noqa: F401
    except ImportError as exc:
        raise BackendMissingError(
            "Rendering a chart from a Figure needs matplotlib, which is an optional extra. "
            'Install it with: pip install "pyhermes[charts]"'
        ) from exc
    return matplotlib
