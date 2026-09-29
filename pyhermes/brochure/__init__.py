"""
The brochure medium: one sheet folded into panels, printed on both sides.

``Brochure`` is the product; ``Panel`` is the layout unit, and flattens in any
other medium as ``Page`` does; ``FoldFormat`` is the sheet and its fold, and
its presets are the shipped folds. Imposition, from the reader's order to the
printer's, is the medium's and never the caller's.
"""

from .document import Brochure
from .fit import overflowing_panels
from .fold import (
    BI_FOLD_LETTER,
    FOLD_FORMATS,
    GATE_FOLD_A4,
    TRI_FOLD_LETTER,
    Z_FOLD_LETTER,
    FoldFormat,
    FoldKind,
)
from .imposition import FACE_NAMES, IMPOSITION, face_name, impose
from .medium import BROCHURE_MEDIUM, brochure_medium
from .panel import Panel, PanelBox

__all__ = [
    "BI_FOLD_LETTER",
    "BROCHURE_MEDIUM",
    "FACE_NAMES",
    "FOLD_FORMATS",
    "GATE_FOLD_A4",
    "IMPOSITION",
    "TRI_FOLD_LETTER",
    "Z_FOLD_LETTER",
    "Brochure",
    "FoldFormat",
    "FoldKind",
    "Panel",
    "PanelBox",
    "brochure_medium",
    "face_name",
    "impose",
    "overflowing_panels",
]
