"""
Deterministic PNG bytes, built in code.

The gallery must render byte-identically on every run, and Content-IDs are
``sha256(bytes)[:16]`` — so a fixture image that varies at all changes the
``cid:`` references in the HTML and breaks every golden downstream. Checking
PNG files into the repo would solve determinism but reintroduces binary
fixtures nobody can diff; generating them from constants solves both.

Only what the builder actually needs: a solid-colour image, small enough that
the inline-strategy fixture stays well under ``inline_image_limit_kb``.
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
