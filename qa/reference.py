"""
The reference reports every roadmap gate is tested against (roadmap v0.3.0).

Each lives in ``reference/<name>/`` as a ``SPEC.md`` and a ``build.py`` whose
``build()`` returns the report as a built document. ``.meta/roadmap/INDEX.md``
names them, and rule 14 admits a new medium or layout only for one of them.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

from octavo.builder.document import Document

ROOT = Path(__file__).resolve().parent.parent
REFERENCE_DIR = ROOT / "reference"

#: The three reports, in the order the roadmap names them.
REPORTS = ("daily-note", "research-report", "product-brochure")


def load_script(path: Path) -> ModuleType:
    """Import a script by path, without requiring it to be a package."""
    spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def example(name: str) -> ModuleType:
    """The worked example ``examples/<name>/<name>.py``, imported."""
    return load_script(ROOT / "examples" / name / f"{name}.py")


def build_script(name: str) -> Path:
    """The ``build.py`` of the reference report ``name``."""
    return REFERENCE_DIR / name / "build.py"


def build(name: str) -> Document:
    """Build the reference report ``name``."""
    document: Document = load_script(build_script(name)).build()
    return document
