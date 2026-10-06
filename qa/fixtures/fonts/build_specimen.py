"""
Build the specimen house face the gallery embeds (#391), from DejaVu Sans.

Run once by hand; the two ``.ttf`` files it writes are committed, so no test
needs fontTools. The face is subset to Latin-1 and a few marks, narrowed to
82% so a sheet shows at a glance that it is not an installed sans, and renamed
"Specimen Condensed", as the Bitstream Vera licence (``LICENSE.txt``) requires
of a modified copy.

    python qa/fixtures/fonts/build_specimen.py /usr/share/fonts/truetype/dejavu
"""

from __future__ import annotations

import sys
from pathlib import Path

from fontTools import subset
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

FAMILY = "Specimen Condensed"
NARROW = 0.82
TEXT = "".join(chr(c) for c in range(0x20, 0x7F)) + "".join(chr(c) for c in range(0xA0, 0x100))
TEXT += "–—‘’“”•…−€′×  "
HERE = Path(__file__).parent


def build(source: Path, style: str) -> None:
    font = TTFont(source)
    options = subset.Options()
    options.name_IDs = [0, 1, 2, 3, 4, 5, 6]
    options.hinting = False
    options.layout_features = ["kern", "liga"]
    subsetter = subset.Subsetter(options)
    subsetter.populate(text=TEXT)
    subsetter.subset(font)
    glyf, hmtx, order = font["glyf"], font["hmtx"], font.getGlyphOrder()
    for name in order:
        pen = TTGlyphPen(glyf)
        glyf[name].draw(TransformPen(pen, (NARROW, 0, 0, 1, 0, 0)), glyf)
        glyf[name] = pen.glyph()
        advance, lsb = hmtx[name]
        hmtx[name] = (round(advance * NARROW), round(lsb * NARROW))
    font["hhea"].advanceWidthMax = max(width for width, _ in hmtx.metrics.values())
    for table in ("GPOS", "kern"):
        if table in font:
            del font[table]
    names = font["name"]
    full = f"{FAMILY} {style}" if style != "Regular" else FAMILY
    ps = f"SpecimenCondensed-{style}"
    for record in list(names.names):
        if record.nameID in (16, 17, 21, 22):
            names.removeNames(nameID=record.nameID)
    for name_id, value in ((1, FAMILY), (2, style), (3, ps), (4, full), (6, ps)):
        names.setName(value, name_id, 3, 1, 0x409)
        names.setName(value, name_id, 1, 0, 0)
    font["head"].modified = font["head"].created
    font.save(HERE / f"{ps}.ttf", reorderTables=True)


if __name__ == "__main__":
    root = Path(sys.argv[1])
    build(root / "DejaVuSans.ttf", "Regular")
    build(root / "DejaVuSans-Bold.ttf", "Bold")
