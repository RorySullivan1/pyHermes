"""
The scope charter has teeth (standing rule 14, roadmap v0.2.0).

No new medium and no new layout primitive joins octavo without a reference report
that needs it. Both sets are found by walking the package, so one cannot be added
without this file changing, and the change names its report.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
import re
from pathlib import Path

import pytest

import octavo
from octavo.builder.components import Component
from octavo.builder.containers import Container
from octavo.builder.document import Document
from octavo.builder.medium import SHIPPED_MEDIA, Medium

ROOT = Path(__file__).resolve().parent.parent

POSITIONING = (
    "octavo is a framework for research reports: quantitative research goes in as data, "
    "exhibits, findings and disclosures, and comes out as an email, a printed report or a "
    "folded brochure, each checked for the medium it is read on."
)

FROZEN_MEDIA = {"html", "email", "document", "brochure", "deck"}

#: A medium is chosen by the class constructed, so a factory-built one arrives with a class.
FROZEN_DOCUMENTS = {"Document", "Email", "PagedDocument", "Brochure", "Deck"}

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

#: Media and layout primitives added after the freeze, each mapped to the reference report
#: that needs it, by a name `.meta/roadmap/INDEX.md` uses. Empty until one earns its place.
ADMITTED_MEDIA: dict[str, str] = {}
ADMITTED_LAYOUTS: dict[str, str] = {}

#: The optional backends a module may lack in a `[dev]`-only install.
OPTIONAL_BACKENDS = {
    "weasyprint",
    "pandas",
    "numpy",
    "matplotlib",
    "segno",
    "pypdfium2",
    "playwright",
    "zxingcpp",
}


def _modules():
    for info in pkgutil.walk_packages(octavo.__path__, "octavo."):
        if info.name.endswith("__main__"):
            continue
        try:
            yield importlib.import_module(info.name)
        except ModuleNotFoundError as exc:
            # A missing extra is skipped; a broken octavo import is a failure, not a pass.
            if (exc.name or "").split(".")[0] not in OPTIONAL_BACKENDS:
                raise


def _media() -> set[str]:
    found = {v.name for m in _modules() for v in vars(m).values() if isinstance(v, Medium)}
    return found | set(SHIPPED_MEDIA)


def _documents() -> set[str]:
    return {
        v.__name__
        for m in _modules()
        for v in vars(m).values()
        if inspect.isclass(v) and issubclass(v, Document) and v.__module__ == m.__name__
        if not v.__name__.startswith("_")
    }


def _layouts() -> set[str]:
    found = set()
    for module in _modules():
        for value in vars(module).values():
            if not inspect.isclass(value) or value.__module__ != module.__name__:
                continue
            if value.__name__.startswith("_") or value is Container:
                continue
            composed = module.__name__ == "octavo.builder.composition"
            if issubclass(value, Container) or (composed and issubclass(value, Component)):
                found.add(value.__name__)
    return found


def _unadmitted(found: set[str], frozen: set[str], admitted: dict[str, str]) -> list[str]:
    return sorted(found - frozen - admitted.keys())


class TestTheFreeze:
    def test_no_medium_joins_without_a_reference_report(self):
        assert _unadmitted(_media(), FROZEN_MEDIA, ADMITTED_MEDIA) == [], (
            "a new medium needs a reference report: add it to ADMITTED_MEDIA with the report"
        )

    def test_no_document_class_joins_without_a_reference_report(self):
        assert _unadmitted(_documents(), FROZEN_DOCUMENTS, ADMITTED_MEDIA) == [], (
            "a new document class is a new medium: add it to ADMITTED_MEDIA with the report"
        )

    def test_no_layout_primitive_joins_without_a_reference_report(self):
        assert _unadmitted(_layouts(), FROZEN_LAYOUTS, ADMITTED_LAYOUTS) == [], (
            "a new layout primitive needs a reference report: add it to ADMITTED_LAYOUTS "
            "with the report"
        )

    def test_the_frozen_sets_are_still_all_present(self):
        # A removal is allowed, but the list must say so, or it outlives what it froze.
        assert FROZEN_MEDIA <= _media()
        assert FROZEN_DOCUMENTS <= _documents()
        assert FROZEN_LAYOUTS <= _layouts()

    @pytest.mark.parametrize("admitted", [ADMITTED_MEDIA, ADMITTED_LAYOUTS])
    def test_every_admission_names_a_report_the_roadmap_names(self, admitted):
        roadmap = (ROOT / ".meta" / "roadmap" / "INDEX.md").read_text(encoding="utf-8").lower()
        for name, report in admitted.items():
            assert report.strip() and report.lower() in roadmap, f"{name}: {report!r}"

    def test_a_new_container_is_caught(self, monkeypatch):
        import octavo.builder.containers as containers

        class Carousel(Container):
            pass

        Carousel.__module__ = containers.__name__
        monkeypatch.setattr(containers, "Carousel", Carousel, raising=False)
        assert _unadmitted(_layouts(), FROZEN_LAYOUTS, ADMITTED_LAYOUTS) == ["Carousel"]

    def test_a_medium_only_the_registry_names_is_caught(self, monkeypatch):
        import octavo.builder.medium as medium

        monkeypatch.setattr(medium, "SHIPPED_MEDIA", (*SHIPPED_MEDIA, "screen"))
        monkeypatch.setitem(globals(), "SHIPPED_MEDIA", medium.SHIPPED_MEDIA)
        assert _unadmitted(_media(), FROZEN_MEDIA, ADMITTED_MEDIA) == ["screen"]


def _prose_paragraphs(text: str) -> list[str]:
    paragraphs = re.split(r"\n\s*\n", text)
    skip = ("#", "[!", "![", "<", "===", "---")
    kept = [p for p in paragraphs if p.strip() and not p.lstrip().startswith(skip)]
    return [" ".join(p.split()) for p in kept]


class TestThePositioning:
    def test_the_readme_opens_on_the_sentence(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        assert _prose_paragraphs(readme)[0] == POSITIONING

    def test_the_router_opens_its_purpose_on_the_sentence(self):
        router = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        heading = "## What this project is"
        assert heading in router, f"CLAUDE.md lost its {heading!r} section"
        section = router.split(heading, 1)[1]
        assert _prose_paragraphs(section)[0].startswith(POSITIONING)
