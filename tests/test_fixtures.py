"""
The fixture gallery's own guarantees (#57).

The gallery is the shared input for every later tool in epic #54 — goldens,
screenshots, the lint pass, the preview CLI — so its promises are tested here
rather than assumed by each consumer:

* every fixture builds, renders, and passes the size gate;
* every ``cid:`` in the rendered HTML has a manifest entry, and vice versa;
* rendering twice yields identical bytes;
* ``kitchen_sink`` contains every public component, enforced by introspection
  rather than a hand-kept list.
"""

from __future__ import annotations

import inspect

import pytest

import svc.builder as builder_api
from qa.fixtures import DEPRECATED_COMPONENTS, all_fixtures
from qa.fixtures import kitchen_sink as kitchen_sink_module
from qa.fixtures._png import solid_png
from svc.builder.components import Component
from svc.delivery import collect_cid_references

FIXTURE_NAMES = sorted(all_fixtures())


@pytest.fixture(params=FIXTURE_NAMES)
def fixture_name(request: pytest.FixtureRequest) -> str:
    return str(request.param)


class TestEveryFixture:
    def test_builds_and_renders(self, fixture_name):
        """Rendering runs _validate_size, so passing here is the size gate too."""
        html = all_fixtures()[fixture_name]().render()
        assert html.startswith("<!DOCTYPE html")
        assert "</html>" in html

    def test_manifest_matches_the_cid_references(self, fixture_name):
        email = all_fixtures()[fixture_name]()
        referenced = set(collect_cid_references(email.render()))
        attached = {asset.content_id for asset in email.assets()}
        assert referenced == attached, (
            f"{fixture_name}: referenced-but-unattached={referenced - attached}, "
            f"attached-but-unreferenced={attached - referenced}"
        )

    def test_render_is_deterministic(self, fixture_name):
        """
        Two builds must be byte-equal.

        Rebuilt from scratch each time, not rendered twice from one instance:
        the risk being guarded against is a fixture reading the clock or
        hashing something unstable at *construction*.
        """
        build = all_fixtures()[fixture_name]
        assert build().render().encode("utf-8") == build().render().encode("utf-8")

    def test_content_ids_are_stable_across_builds(self, fixture_name):
        build = all_fixtures()[fixture_name]
        first = [asset.content_id for asset in build().assets()]
        assert first == [asset.content_id for asset in build().assets()]


class TestGalleryRegistry:
    def test_is_not_empty(self):
        assert FIXTURE_NAMES

    def test_returns_a_fresh_mapping(self):
        """A consumer that mutates the mapping must not corrupt the gallery."""
        all_fixtures().clear()
        assert sorted(all_fixtures()) == FIXTURE_NAMES


class TestKitchenSinkCompleteness:
    @staticmethod
    def _public_components() -> set[str]:
        """Every public Component subclass exported from svc.builder."""
        return {
            name
            for name, obj in vars(builder_api).items()
            if not name.startswith("_")
            and inspect.isclass(obj)
            and issubclass(obj, Component)
            and obj is not Component  # the abstract base renders nothing
        } - DEPRECATED_COMPONENTS

    def test_every_public_component_appears(self):
        """
        Introspected, not hand-listed: a component added to svc.builder and
        forgotten here fails the suite instead of going unrendered forever.
        """
        source = inspect.getsource(kitchen_sink_module)
        missing = {name for name in self._public_components() if f"{name}(" not in source}
        assert not missing, (
            f"kitchen_sink() is missing {sorted(missing)}. Add a section using each, "
            "or add it to DEPRECATED_COMPONENTS with a reason."
        )

    def test_the_exemptions_are_real_components(self):
        """A stale exemption would silently excuse a component that still exists."""
        exported = {
            name
            for name, obj in vars(builder_api).items()
            if inspect.isclass(obj) and issubclass(obj, Component)
        }
        assert DEPRECATED_COMPONENTS <= exported

    def test_it_exercises_every_container_ratio(self):
        source = inspect.getsource(kitchen_sink_module)
        for ratio in (
            "EQUAL",
            "NARROW_WIDE",
            "WIDE_NARROW",
            "WIDE_LEFT",
            "WIDE_CENTER",
            "WIDE_RIGHT",
        ):
            assert ratio in source, f"kitchen_sink() never uses the {ratio} ratio."
        assert "highlight=True" in source


class TestDeterministicPng:
    def test_same_arguments_yield_the_same_bytes(self):
        assert solid_png(8, 4, (1, 2, 3)) == solid_png(8, 4, (1, 2, 3))

    def test_it_is_a_png_the_builder_accepts(self):
        assert solid_png(8, 4, (1, 2, 3)).startswith(b"\x89PNG\r\n\x1a\n")

    @pytest.mark.parametrize("width,height", [(0, 4), (4, 0), (-1, 4)])
    def test_a_non_positive_size_is_rejected(self, width, height):
        with pytest.raises(ValueError, match="positive size"):
            solid_png(width, height, (0, 0, 0))

    def test_an_out_of_range_channel_is_rejected(self):
        with pytest.raises(ValueError, match="0-255"):
            solid_png(4, 4, (0, 256, 0))
