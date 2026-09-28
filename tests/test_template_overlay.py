"""
A caller's template overlay: one fork, or a template of their own, without the tree (#247).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from qa.fixtures import kitchen_sink
from svc.builder import Component, Email, EmailBuilder, FullWidth, TemplateEngine
from svc.builder.engine import _packaged_template_dir
from svc.builder.exceptions import TemplateError
from svc.builder.medium import Medium
from svc.document import PagedDocument

MARKER = "<!-- house footer -->\n"


@pytest.fixture
def footer_overlay(tmp_path: Path) -> Path:
    """An overlay holding one fork: the packaged footer behind a marker."""
    packaged = (_packaged_template_dir() / "regions" / "footer.html").read_text(encoding="utf-8")
    (tmp_path / "regions").mkdir()
    (tmp_path / "regions" / "footer.html").write_text(MARKER + packaged, encoding="utf-8")
    return tmp_path


class Widget(Component):
    """A caller-defined component whose template exists only in the overlay."""

    template_path = "house/widget.html"

    def __init__(self, label: str):
        self.label = label

    def context(self) -> dict[str, Any]:
        return {"label": self.label}

    def text(self) -> str:
        return f"Widget: {self.label}"


class TestAForkedTemplate:
    def test_it_replaces_the_footer_and_nothing_else(self, footer_overlay):
        forked = kitchen_sink.build(template_overlay=footer_overlay).render()
        assert forked.count(MARKER) == 1
        # Remove the marker and every other byte is the packaged render's.
        assert forked.replace(MARKER, "") == kitchen_sink.build().render()

    def test_the_builder_takes_several_directories_in_order(self, footer_overlay, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        email = kitchen_sink.build(template_overlay=[empty, footer_overlay])
        assert MARKER in email.render()

    def test_a_paged_document_takes_one_too(self, footer_overlay):
        document = PagedDocument(
            {"firm_name": "F", "campaign_name": "C"}, template_overlay=footer_overlay
        )
        assert document._engine.overlays == (footer_overlay.resolve(),)


class TestACallersComponent:
    @pytest.fixture
    def email(self, tmp_path, valid_metadata) -> Email:
        (tmp_path / "house").mkdir()
        (tmp_path / "house" / "widget.html").write_text(
            '<div class="widget">{{ label | escape_html }}</div>', encoding="utf-8"
        )
        email = EmailBuilder(template_overlay=tmp_path).metadata(valid_metadata).build()
        email.add_section(FullWidth(content=Widget("Q3 & beyond"), title="House"))
        return email

    def test_it_renders_from_the_overlay(self, email):
        assert '<div class="widget">Q3 &amp; beyond</div>' in email.render()

    def test_it_projects_to_text(self, email):
        assert "Widget: Q3 & beyond" in email.text()

    def test_without_the_overlay_it_is_not_found(self, valid_metadata):
        email = Email(valid_metadata)
        email.add_section(FullWidth(content=Widget("x")))
        with pytest.raises(TemplateError, match="house/widget.html"):
            email.render()


class TestAMissingOverlay:
    def test_it_raises_at_construction_naming_the_path(self, tmp_path, valid_metadata):
        missing = tmp_path / "no-such-dir"
        with pytest.raises(TemplateError, match="no-such-dir"):
            Email(valid_metadata, template_overlay=missing)


class TestPrecedence:
    """The same relative path in all three places: overlay, then the medium's fork, then root."""

    @pytest.fixture
    def tree(self, tmp_path: Path) -> tuple[Path, Path]:
        root, overlay = tmp_path / "root", tmp_path / "overlay"
        for directory, who in ((root, "root"), (root / "fork", "medium"), (overlay, "overlay")):
            directory.mkdir(parents=True)
            (directory / "x.html").write_text(who, encoding="utf-8")
        return root, overlay

    def _winner(self, root: Path, **kwargs: Any) -> str:
        return TemplateEngine(root, **kwargs).render("x.html", {})

    def test_the_overlay_shadows_the_medium_and_the_root(self, tree):
        root, overlay = tree
        assert self._winner(root, search_path=("fork",), overlays=(overlay,)) == "overlay"

    def test_the_medium_shadows_the_root(self, tree):
        root, _ = tree
        assert self._winner(root, search_path=("fork",)) == "medium"

    def test_the_root_is_the_floor(self, tree):
        root, _ = tree
        assert self._winner(root) == "root"

    def test_a_document_orders_them_the_same_way(self, tree, valid_metadata):
        root, overlay = tree
        medium = Medium(name="forked", skeleton="x.html", template_search_path=("fork",))
        document = Email(valid_metadata, template_dir=root, medium=medium, template_overlay=overlay)
        assert document._engine.render("x.html", {}) == "overlay"
