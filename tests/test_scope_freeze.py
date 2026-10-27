"""
The scope charter has teeth (standing rule 14, roadmap v0.2.0).

No new medium and no new layout primitive joins pyHermes without a reference report
that needs it. Both sets are found by walking the package, so one cannot be added
without this file changing, and the change names its report.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
import re
from pathlib import Path

import pyhermes
from pyhermes.builder.components import Component
from pyhermes.builder.containers import Container
from pyhermes.builder.medium import Medium

ROOT = Path(__file__).resolve().parent.parent

FROZEN_MEDIA = {"html", "email", "document", "brochure", "deck"}

FROZEN_LAYOUTS = {
    "FullWidth",
    "FlowedColumns",
    "TwoColumn",
    "ThreeColumn",
    "FourColumn",
    "Appendices",
    "OnlySections",
    "Stack",
    "Columns",
    "Only",
    "Page",
    "Panel",
    "Slide",
    "DividerSlide",
    "StatementSlide",
}

#: A medium or layout primitive added after the freeze, mapped to the reference report
#: (`.meta/roadmap/`) that needs it. Empty until one earns its place.
ADMITTED: dict[str, str] = {}


def _modules():
    for info in pkgutil.walk_packages(pyhermes.__path__, "pyhermes."):
        if info.name.endswith("__main__"):
            continue
        try:
            yield importlib.import_module(info.name)
        except ModuleNotFoundError:
            continue  # an optional extra; CI's all-extras job imports it


def _media() -> set[str]:
    return {v.name for m in _modules() for v in vars(m).values() if isinstance(v, Medium)}


def _layouts() -> set[str]:
    found = set()
    for module in _modules():
        for value in vars(module).values():
            if not inspect.isclass(value) or value.__module__ != module.__name__:
                continue
            if value.__name__.startswith("_") or value is Container:
                continue
            composed = module.__name__ == "pyhermes.builder.composition"
            if issubclass(value, Container) or (composed and issubclass(value, Component)):
                found.add(value.__name__)
    return found


def _unadmitted(found: set[str], frozen: set[str]) -> list[str]:
    return sorted(found - frozen - ADMITTED.keys())


class TestTheFreeze:
    def test_no_medium_joins_without_a_reference_report(self):
        assert _unadmitted(_media(), FROZEN_MEDIA) == [], (
            "a new medium needs a reference report: add it to ADMITTED with the report's name"
        )

    def test_no_layout_primitive_joins_without_a_reference_report(self):
        assert _unadmitted(_layouts(), FROZEN_LAYOUTS) == [], (
            "a new layout primitive needs a reference report: add it to ADMITTED with the "
            "report's name"
        )

    def test_the_frozen_sets_are_still_all_present(self):
        # A removal is allowed, but the list must say so, or it outlives what it froze.
        assert FROZEN_MEDIA <= _media()
        assert FROZEN_LAYOUTS <= _layouts()

    def test_every_admission_names_a_report(self):
        assert all(report.strip() for report in ADMITTED.values())

    def test_a_new_container_is_caught(self, monkeypatch):
        import pyhermes.builder.containers as containers

        class Carousel(Container):
            pass

        Carousel.__module__ = containers.__name__
        monkeypatch.setattr(containers, "Carousel", Carousel, raising=False)
        assert _unadmitted(_layouts(), FROZEN_LAYOUTS) == ["Carousel"]


def _first_paragraph(text: str) -> str:
    body = text.split("\n## ", 1)[0]
    paragraphs = [p for p in re.split(r"\n\s*\n", body) if p.strip() and not p.startswith("#")]
    return " ".join(paragraphs[0].split())


class TestThePositioning:
    def test_the_readme_and_the_router_open_on_the_same_sentence(self):
        readme = _first_paragraph((ROOT / "README.md").read_text(encoding="utf-8"))
        router = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        section = router.split("## What this project is", 1)[1]
        assert _first_paragraph(section).startswith(readme)
