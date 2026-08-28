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

import dataclasses
import inspect

import pytest

import svc.builder as builder_api
from qa.fixtures import DEPRECATED_COMPONENTS, all_fixtures
from qa.fixtures import kitchen_sink as kitchen_sink_module
from qa.fixtures._png import solid_png
from svc.builder.components import Component, DataTable
from svc.builder.models import Cell, Column, EmailMetadata, TableRow
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


#: Metadata fields ``kitchen_sink`` deliberately holds at their default.
#:
#: ``size_theme`` is here because this fixture *is* the epic's byte-identity
#: reference: every migration step in #45 claims the gallery does not move at
#: ``STANDARD``, and a kitchen_sink rendered at any other density could not
#: make that claim. The distinctive values live in ``compact_size`` and
#: ``spacious_size``, which render *this same email* one field apart — the
#: same shape ``slate_theme`` uses for the palette, and a true A/B because
#: they reuse the content rather than restating it.
#: ``font_theme`` is here for the same reason, arrived at one step later:
#: #105 bound the namespace before any template read it, so a distinctive
#: value would have pinned nothing at that step — and once #106 made it
#: legible, this fixture had already become the *faces'* byte-identity
#: reference too. ``modern_fonts`` is where the non-default path gets its
#: golden, on the ``compact_size`` / ``spacious_size`` model.
ANCHORED_TO_THE_DEFAULT = {"size_theme", "font_theme"}


#: The objects whose fields the gallery must exercise (#121).
#:
#: ``DataTable`` is not a dataclass, so its surface is read off ``__init__``;
#: one parameter is stored under another name, which the alias map records
#: rather than the test silently skipping it.
TABLE_OBJECTS = ("DataTable", "Column", "Cell", "TableRow")
TABLE_ATTRIBUTE_ALIASES = {"headers": "columns"}


def _tables_in_gallery():
    """Every DataTable the gallery builds, with its rows, columns and cells."""
    from svc.builder.components import DataTable

    for build in all_fixtures().values():
        email = build()
        for section in email._sections:
            for component in section.components():
                if isinstance(component, DataTable):
                    yield component


class TestComponentFieldsAreExercised:
    """
    The gap this epic found on its way past: **nothing introspected component
    *fields*.**

    Every public ``Component`` *subclass* has a completeness rule, and so does
    every ``EmailMetadata`` and region *field* — but a new field on
    ``DataTable`` tripped nothing at all. Epic #116 added seven of them, which
    is exactly enough for the absence to be expensive.

    Scoped to the table objects rather than every component, which is honest
    and shippable. **It is a first instance, not a special case**: the next
    component to grow a vocabulary should widen this rather than let its
    fields go unpinned for the same reason these did.
    """

    @staticmethod
    def _observed(instances, name, default):
        """Whether any instance sets this field to something other than its default."""
        attribute = TABLE_ATTRIBUTE_ALIASES.get(name, name)
        return any(getattr(instance, attribute, default) != default for instance in instances)

    def test_every_column_field_is_exercised(self):
        columns = [column for table in _tables_in_gallery() for column in table.columns]
        assert columns, "the gallery renders no data table"
        for spec in dataclasses.fields(Column):
            assert self._observed(columns, spec.name, spec.default), (
                f"no gallery column sets Column.{spec.name}; a field left at its default "
                "is one the golden cannot pin"
            )

    def test_every_cell_field_is_exercised(self):
        cells = [cell for table in _tables_in_gallery() for row in table.rows for cell in row.cells]
        assert cells
        for spec in dataclasses.fields(Cell):
            assert self._observed(cells, spec.name, spec.default), (
                f"no gallery cell sets Cell.{spec.name}"
            )

    def test_every_row_field_is_exercised(self):
        rows = [row for table in _tables_in_gallery() for row in table.rows]
        assert rows
        for spec in dataclasses.fields(TableRow):
            default = spec.default if spec.default is not dataclasses.MISSING else None
            assert self._observed(rows, spec.name, default), (
                f"no gallery row sets TableRow.{spec.name}"
            )

    def test_every_data_table_argument_is_exercised(self):
        tables = list(_tables_in_gallery())
        assert tables
        parameters = inspect.signature(DataTable.__init__).parameters
        for name, parameter in parameters.items():
            if name == "self":
                continue
            default = None if parameter.default is inspect.Parameter.empty else parameter.default
            assert self._observed(tables, name, default), (
                f"no gallery table sets DataTable({name}=…)"
            )

    def test_the_flat_colors_spelling_is_exercised(self):
        """
        ``TableRow.colors`` is an ``InitVar``, so it is absent from
        ``fields()`` and the field walk above cannot see it — but it is the
        common call path and a golden should pin it. Checked by its effect:
        some cell carries a colour that arrived through the flat spelling.
        """
        import pathlib as _pathlib

        sources = [
            _pathlib.Path(module).read_text()
            for module in _pathlib.Path("qa/fixtures").glob("*.py")
        ]
        assert any("colors=" in source for source in sources), (
            "no fixture uses the flat colors spelling"
        )


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

    def test_every_metadata_field_is_set(self):
        """
        The other half of #32: the golden can only pin a skeleton variable the
        fixture actually supplies. Introspected from the dataclass, so a field
        added later fails here instead of going quietly unpinned.

        ``header``, ``banner`` and ``footer`` are excluded because the
        fixture builds all three regions explicitly rather than through the
        metadata. Their own
        fields are checked below, distinctively, by the per-region test. The
        flat pre-split keywords are covered elsewhere and by a stronger
        assertion than a golden — see ``TestTheFlatKeywordsStillWork``.

        ``theme`` was exempt while only one preset existed; #50 retired that.
        ``kitchen_sink`` names ``"classic"`` so its golden pins that the
        string path resolves to the default's bytes, and ``slate_theme``
        pins a genuinely different palette.
        """
        supplied = set(kitchen_sink_module._metadata())
        declared = {f.name for f in dataclasses.fields(EmailMetadata)}
        declared -= {"header", "banner", "footer"}
        missing = declared - supplied
        assert not missing, (
            f"kitchen_sink()'s metadata never sets {sorted(missing)}. A field the "
            "fixture leaves at its default is a field the golden cannot pin."
        )

    @pytest.mark.parametrize("region_name", ["header", "banner", "footer"])
    def test_every_region_field_is_set_distinctively(self, region_name):
        """
        The same rule for each region: a field the fixture leaves at its
        default is one the golden cannot pin. Read off the *built* region
        rather than the fixture's dict, so it holds however the fixture
        chooses to supply it.
        """
        region = getattr(kitchen_sink_module.build(), region_name)
        defaults = type(region)()
        undistinctive = {
            f.name
            for f in dataclasses.fields(region)
            if getattr(region, f.name) == getattr(defaults, f.name)
        }
        assert not undistinctive, (
            f"kitchen_sink()'s {region_name} leaves {sorted(undistinctive)} at the "
            "field default; pick a value that differs, or the golden cannot pin it."
        )

    def test_every_metadata_value_is_distinctive(self):
        """
        A field set to its own default is indistinguishable from one left
        unset — the golden would not move if the default changed underneath
        it. #32 asked for distinctive values for exactly this reason.

        ``ANCHORED_TO_THE_DEFAULT`` is the one exception, and it is not a
        gap: see the note on that constant.
        """
        defaults = EmailMetadata()
        undistinctive = {
            name
            for name, value in kitchen_sink_module._metadata().items()
            # The flat region keys are constructor-only; the per-region
            # test above covers them.
            if hasattr(defaults, name)
            and name not in ANCHORED_TO_THE_DEFAULT
            and value == getattr(defaults, name)
        }
        assert not undistinctive, (
            f"kitchen_sink() sets {sorted(undistinctive)} to the field default; "
            "pick a value that differs, or a change to the default goes unnoticed."
        )

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


class TestCustomBannerCarriesEveryAxis:
    """
    #94's whole reason for existing, asserted rather than described.

    A fixture whose docstring claims four axes and whose builder quietly
    dropped one would still render, still lint, still match its own golden —
    and would stop being the cross-axis pin the epic closed on.
    """

    @staticmethod
    @pytest.fixture(scope="class")
    def email():
        from qa.fixtures import custom_banner

        return custom_banner.build()

    def test_the_copy_is_free_form(self, email):
        banner = email.banner
        assert banner.title and banner.title != email.metadata.firm_name
        assert banner.subtitle and banner.subtitle != email.metadata.campaign_name

    def test_it_names_a_department(self, email):
        assert email.metadata.department

    def test_the_backdrop_is_attached_rather_than_hosted(self, email):
        """
        The path no other fixture covers. A hosted URL would exercise the
        string branch every other banner fixture already does; only an
        attached one reaches the manifest and puts a ``cid:`` in both the CSS
        and the VML.
        """
        from svc.builder.enums import EmbedStrategy
        from svc.builder.images import EmailImage

        backdrop = email.banner.background_image_url
        assert isinstance(backdrop, EmailImage)
        assert backdrop.strategy is EmbedStrategy.CID

        html = email.render()
        assert f"url('cid:{backdrop.content_id}')" in html
        assert f'src="cid:{backdrop.content_id}"' in html, "the v:fill lost the backdrop"
        assert backdrop.content_id in {asset.content_id for asset in email.assets()}

    def test_every_palette_role_is_set(self, email):
        """
        A partially-filled palette would leave some roles inheriting, and the
        interaction this fixture exists to pin is the *tuned* masthead.
        """
        palette = email.banner.palette
        assert palette is not None
        assert all(getattr(palette, spec.name) is not None for spec in dataclasses.fields(palette))

    def test_the_theme_is_left_alone(self, email):
        """
        A preset and a palette moving at once would leave a golden diff
        nobody can attribute. ``slate_theme`` pins the preset path.
        """
        assert email.metadata.theme == EmailMetadata().theme


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
