"""
A QR code for the gallery, built without the ``[qr]`` extra (#344).

The goldens run where segno is absent, so a fixture's code is its module
matrix as a constant, drawn by :func:`qa.fixtures._png.matrix_png`. A test
under the extra holds the constant to segno's encoding of :data:`URL`, so the
printed code still decodes to it.
"""

from __future__ import annotations

from ._png import matrix_png

#: What the gallery's code encodes: the brochure's web version.
URL = "https://example.com/rates-folded"

#: segno's symbol for :data:`URL` at error level M, one string a row, ``1`` dark.
MODULES: tuple[str, ...] = (
    "11111110001011011010001111111",
    "10000010011111001011101000001",
    "10111010101111100111101011101",
    "10111010011111011010001011101",
    "10111010110100010110001011101",
    "10000010101101001101101000001",
    "11111110101010101010101111111",
    "00000000010111000110000000000",
    "01001010111010001100110110100",
    "00101000101001101110011110011",
    "10100010101101010110110001101",
    "01000100100010001110110101011",
    "00110011000110101100000101001",
    "00101101110100110100001010101",
    "01110110110010101110101010001",
    "11011100110110011100111101000",
    "11011011110100000101110000000",
    "10111001101000100010101110001",
    "00110111111111011100100111001",
    "00101000010100110101000100011",
    "11010011001000100101111111000",
    "00000000110001010011100010101",
    "11111110010011110111101010001",
    "10000010011011010101100011010",
    "10111010110111100101111110011",
    "10111010011010011110000100001",
    "10111010000010010111110001111",
    "10000010101100010101101101011",
    "11111110001010100100110010010",
)

#: The quiet zone, in modules, as the adapter draws it.
BORDER = 4

#: Nine pixels a module: 333 across, over 300 dpi at the one-inch default.
SCALE = 9


def qr_png() -> bytes:
    """The code as PNG bytes, ink on white. Deterministic, as every gallery image is."""
    return matrix_png(MODULES, scale=SCALE, border=BORDER, dark=(59, 59, 59))
