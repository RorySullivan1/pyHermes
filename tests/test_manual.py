"""
The user manual's examples run, and its links land.

Each ``python`` block in ``docs/manual/`` runs after the runnable blocks above
it on the same page, in a scratch directory holding the images the manual names.
A comment on the line before a fence changes that: ``<!-- manual: skip -->``
leaves a block unrun (it needs credentials or a network), and
``<!-- manual: needs pdf charts -->`` skips it without those extras.
"""

from __future__ import annotations

import importlib.util
import re
from dataclasses import dataclass
from pathlib import Path

import pytest

from qa.fixtures._png import solid_png

MANUAL = Path(__file__).resolve().parent.parent / "docs" / "manual"
PAGES = sorted(MANUAL.glob("*.md"))

FENCE = re.compile(r"^(?P<prefix>[ \t]*(?:>[ \t]?)*)```(?P<lang>\w*)[ \t]*$")
DIRECTIVE = re.compile(r"<!--\s*manual:\s*(?P<word>skip|needs)(?P<extras>[\w ]*)-->")

#: The files the manual's examples read, as the reader would have them.
IMAGES = {
    "logo.png": (240, 80),
    "chart.png": (1232, 640),
    "masthead.png": (1360, 400),
    "photo.png": (1280, 720),
    "portrait.png": (640, 720),
}

#: The font files a page names, each a copy of the gallery's specimen face (#391).
FONTS_DIR = Path(__file__).resolve().parent.parent / "qa" / "fixtures" / "fonts"
FONTS = {
    "house-sans-regular.ttf": "SpecimenCondensed-Regular.ttf",
    "house-sans-bold.ttf": "SpecimenCondensed-Bold.ttf",
}


@dataclass(frozen=True)
class Block:
    page: Path
    line: int
    code: str
    skip: bool
    extras: tuple[str, ...]


def blocks(page: Path) -> list[Block]:
    """Every ``python`` fence on the page, with the directive on the line before it."""
    lines = page.read_text(encoding="utf-8").splitlines()
    found, i = [], 0
    while i < len(lines):
        fence = FENCE.match(lines[i])
        if not fence or not fence["lang"]:
            i += 1
            continue
        prefix, start = fence["prefix"], i
        body: list[str] = []
        i += 1
        while i < len(lines) and lines[i].strip().lstrip("> ").strip() != "```":
            body.append(lines[i][len(prefix) :] if lines[i].startswith(prefix) else "")
            i += 1
        i += 1
        if fence["lang"] != "python":
            continue
        before = next((ln for ln in reversed(lines[:start]) if ln.strip(" >")), "")
        directive = DIRECTIVE.search(before)
        extras = tuple(directive["extras"].split()) if directive else ()
        skip = bool(directive and directive["word"] == "skip")
        found.append(Block(page, start + 1, "\n".join(body) + "\n", skip, extras))
    return found


def _missing(extra: str) -> bool:
    if extra == "pdf":
        from pyhermes.pdf import available

        return not available()
    module = {"data": "pandas", "charts": "matplotlib", "math": "matplotlib", "qr": "segno"}[extra]
    return importlib.util.find_spec(module) is None


RUNNABLE = [b for page in PAGES for b in blocks(page) if not b.skip]


@pytest.mark.parametrize("block", RUNNABLE, ids=lambda b: f"{b.page.stem}:{b.line}")
def test_the_example_runs(block: Block, tmp_path, monkeypatch):
    for extra in block.extras:
        if _missing(extra):
            pytest.skip(f'needs the "[{extra}]" extra')
    for name, (width, height) in IMAGES.items():
        (tmp_path / name).write_bytes(solid_png(width, height, (44, 62, 80)))
    for name, specimen in FONTS.items():
        (tmp_path / name).write_bytes((FONTS_DIR / specimen).read_bytes())
    monkeypatch.chdir(tmp_path)
    setup = [b for b in RUNNABLE if b.page == block.page and b.line < block.line]
    namespace: dict[str, object] = {"__name__": "__main__", "__file__": str(tmp_path / "x.py")}
    for earlier in [*[b for b in setup if not b.extras], block]:
        exec(compile(earlier.code, f"{earlier.page.name}:{earlier.line}", "exec"), namespace)


def test_every_page_has_examples_or_says_why_not():
    assert PAGES, "docs/manual/ is empty"
    assert all(blocks(page) for page in PAGES if page.name != "README.md")


LINK = re.compile(r"\]\((?!https?:|mailto:)(?P<path>[^)#\s]*)(?:#(?P<anchor>[^)\s]+))?\)")


def _anchors(page: Path) -> set[str]:
    headings = re.findall(r"^#+ (.+)$", page.read_text(encoding="utf-8"), re.MULTILINE)
    return {re.sub(r"[^\w\- ]", "", h.lower()).replace(" ", "-") for h in headings}


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.stem)
def test_every_link_lands(page: Path):
    broken = []
    for match in LINK.finditer(page.read_text(encoding="utf-8")):
        target = (page.parent / match["path"]).resolve() if match["path"] else page
        if not target.exists():
            broken.append(match.group(0))
        elif match["anchor"] and target.suffix == ".md" and match["anchor"] not in _anchors(target):
            broken.append(match.group(0))
    assert broken == []
