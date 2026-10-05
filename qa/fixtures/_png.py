"""
Deterministic PNG bytes, built in code.

The gallery must render byte-identically on every run, and Content-IDs are
``sha256(bytes)[:16]`` — so a fixture image that varies at all changes the
``cid:`` references in the HTML and breaks every golden downstream. Checking
PNG files into the repo would solve determinism but reintroduces binary
fixtures nobody can diff; generating them from constants solves both.

Only what the builder actually needs: a solid-colour image, small enough that
the inline-strategy fixture stays well under ``inline_image_limit_kb``, and a
two-colour grid of modules for a QR code (#344).
"""

from __future__ import annotations

import struct
import zlib

_SIGNATURE = b"\x89PNG\r\n\x1a\n"

#: zlib level pinned explicitly. The default is already 6 on CPython, but the
#: determinism rule should not rest on a default staying put across versions.
_COMPRESSION_LEVEL = 6


def _chunk(kind: bytes, payload: bytes) -> bytes:
    """One PNG chunk: length, type, payload, CRC32 of type+payload."""
    return (
        struct.pack(">I", len(payload))
        + kind
        + payload
        + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    )


def solid_png(width: int, height: int, rgb: tuple[int, int, int]) -> bytes:
    """
    An 8-bit RGB PNG of one colour.

    Args:
        width:  Pixel width. Must be positive.
        height: Pixel height. Must be positive.
        rgb:    Channel values, each 0–255.

    Returns:
        Complete PNG bytes — the same bytes for the same arguments, always.
    """
    if width <= 0 or height <= 0:
        raise ValueError(f"solid_png needs a positive size, got {width}x{height}.")
    if not all(0 <= channel <= 255 for channel in rgb):
        raise ValueError(f"solid_png channels must be 0-255, got {rgb}.")

    # Colour type 2 = truecolour RGB, bit depth 8, no interlace.
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    # Each scanline is prefixed with its filter byte; 0 = None.
    scanline = b"\x00" + bytes(rgb) * width
    pixels = zlib.compress(scanline * height, _COMPRESSION_LEVEL)

    return _SIGNATURE + _chunk(b"IHDR", header) + _chunk(b"IDAT", pixels) + _chunk(b"IEND", b"")


def matrix_png(
    rows: tuple[str, ...] | list[str],
    *,
    scale: int,
    border: int,
    dark: tuple[int, int, int],
    light: tuple[int, int, int] = (255, 255, 255),
) -> bytes:
    """
    A grid of square modules, ``1`` dark and ``0`` light, ``scale`` px each, inside a light border.

    Returns:
        Complete PNG bytes — the same bytes for the same arguments, always.
    """
    width = len(rows[0]) + 2 * border
    blank = "0" * width
    grid = [blank] * border + [f"{'0' * border}{row}{'0' * border}" for row in rows]
    grid += [blank] * border
    colours = {"0": bytes(light), "1": bytes(dark)}
    lines = [b"\x00" + b"".join(colours[cell] * scale for cell in row) for row in grid]
    pixels = zlib.compress(
        b"".join(line for line in lines for _ in range(scale)), _COMPRESSION_LEVEL
    )
    side = width * scale
    header = struct.pack(">IIBBBBB", side, side, 8, 2, 0, 0, 0)
    return _SIGNATURE + _chunk(b"IHDR", header) + _chunk(b"IDAT", pixels) + _chunk(b"IEND", b"")
