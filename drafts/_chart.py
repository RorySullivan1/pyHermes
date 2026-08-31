"""Minimal PNG bar-chart renderer, for a report that has no plotting library.

pyHermes ships no charting dependency and matplotlib is not installed here, so a
chart image has to come from somewhere. This draws one as a raw pixel buffer and
encodes it with the same zlib/CRC chunking ``qa/fixtures/_png.py`` uses, which
keeps the whole draft dependency-free.
"""

from __future__ import annotations

import struct
import zlib

RGB = tuple[int, int, int]


def _chunk(kind: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + kind
        + payload
        + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    )


def _encode(width: int, height: int, pixels: list[list[RGB]]) -> bytes:
    raw = b"".join(b"\x00" + b"".join(struct.pack("BBB", *px) for px in row) for row in pixels)
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(raw, 6))
        + _chunk(b"IEND", b"")
    )


def bar_chart(
    values: list[float],
    *,
    width: int = 560,
    height: int = 260,
    ground: RGB = (255, 255, 255),
    positive: RGB = (74, 124, 89),
    negative: RGB = (184, 84, 80),
    axis: RGB = (200, 195, 185),
) -> bytes:
    """A zero-baselined bar chart: positive bars up, negative down, in theme colours.

    Values are plotted against a shared scale so the bars stay comparable, and the
    zero line is drawn across the full width because a diverging series is unreadable
    without it.
    """
    pixels = [[ground for _ in range(width)] for _ in range(height)]
    pad, gap = 18, 10
    span = max(abs(v) for v in values) or 1.0
    zero_y = height // 2
    slot = (width - 2 * pad) // len(values)
    bar_w = max(slot - gap, 4)

    for x in range(width):
        pixels[zero_y][x] = axis

    for index, value in enumerate(values):
        left = pad + index * slot + (slot - bar_w) // 2
        extent = int((abs(value) / span) * (height // 2 - pad))
        rows = (
            range(zero_y - extent, zero_y) if value >= 0 else range(zero_y + 1, zero_y + 1 + extent)
        )
        colour = positive if value >= 0 else negative
        for y in rows:
            for x in range(left, min(left + bar_w, width)):
                pixels[y][x] = colour
    return _encode(width, height, pixels)


def sparkline_strip(
    series: list[list[float]],
    *,
    width: int = 560,
    row_height: int = 44,
    ground: RGB = (255, 255, 255),
    line: RGB = (58, 90, 120),
    rule: RGB = (222, 218, 210),
) -> bytes:
    """One sparkline per series, stacked — a small-multiples strip.

    Each row is scaled to its **own** range rather than a shared one: these are
    different quantities, and a shared scale would flatten every series but the
    widest into a straight line.
    """
    height = row_height * len(series)
    pixels = [[ground for _ in range(width)] for _ in range(height)]

    for index, values in enumerate(series):
        top = index * row_height
        if index:
            for x in range(width):
                pixels[top][x] = rule
        low, high = min(values), max(values)
        span = (high - low) or 1.0
        pad = 8
        usable = row_height - 2 * pad
        step = (width - 2 * pad) / max(len(values) - 1, 1)
        points = [
            (
                int(pad + i * step),
                top + pad + int((1 - (v - low) / span) * usable),
            )
            for i, v in enumerate(values)
        ]
        for (x0, y0), (x1, y1) in zip(points, points[1:], strict=False):
            steps = max(abs(x1 - x0), abs(y1 - y0), 1)
            for s in range(steps + 1):
                x = x0 + (x1 - x0) * s // steps
                y = y0 + (y1 - y0) * s // steps
                for thickness in (0, 1):
                    if 0 <= y + thickness < height and 0 <= x < width:
                        pixels[y + thickness][x] = line
    return _encode(width, height, pixels)
