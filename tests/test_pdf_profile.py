"""
The ``PdfProfile`` (#196): how a PDF is written, validated at construction.

Runs without ``[pdf]``: a profile is setup, and a caller must be able to build
and validate one with the extra absent. The two tests that compare against the
installed backend skip without it.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

from pyhermes.pdf import (
    PDF_VARIANTS,
    PRINT,
    SCREEN,
    PdfError,
    PdfProfile,
    ProfileError,
    available,
)

requires_backend = pytest.mark.skipif(
    not available(), reason='no WeasyPrint; the PDF exporter is the optional "[pdf]" extra'
)


class TestAProfileIsValidatedAtConstruction:
    @pytest.mark.parametrize(
        ("field", "value", "names"),
        [
            ("name", "  ", "name"),
            ("dpi", 0, "dpi"),
            ("dpi", -150, "dpi"),
            ("jpeg_quality", 96, "jpeg_quality"),
            ("jpeg_quality", -1, "jpeg_quality"),
            ("variant", "pdf/ua-3", "pdf/ua-3"),
            ("identifier", b"", "identifier"),
        ],
    )
    def test_a_bad_field_names_itself(self, field, value, names):
        fields = {"name": "custom", field: value}
        with pytest.raises(ProfileError, match=names.replace("/", r"\/")):
            PdfProfile(**fields)

    def test_the_error_is_the_exporters_and_a_value_error(self):
        # PdfError so a caller of the exporter's documented contract catches
        # it; ValueError because a profile is setup, as a Config field is.
        assert issubclass(ProfileError, PdfError)
        assert issubclass(ProfileError, ValueError)

    def test_the_edges_of_each_range_are_legal(self):
        PdfProfile(name="edge", dpi=1, jpeg_quality=0)
        PdfProfile(name="edge", jpeg_quality=95, variant="pdf/ua-1", identifier=b"x")

    def test_it_is_frozen(self):
        with pytest.raises(AttributeError):
            SCREEN.dpi = 300  # type: ignore[misc]


class TestThePresets:
    def test_print_changes_nothing(self):
        assert (PRINT.dpi, PRINT.jpeg_quality, PRINT.optimize_images) == (None, None, False)
        assert (PRINT.variant, PRINT.identifier) == (None, None)

    def test_screen_is_150_dpi_and_quality_85(self):
        # The preset's own numbers, not Config's: they describe a preset, as
        # A4_PORTRAIT's margin does, and a caller wanting others builds one.
        assert (SCREEN.dpi, SCREEN.jpeg_quality, SCREEN.optimize_images) == (150, 85, True)

    def test_both_write_the_same_identifier(self):
        # None: WeasyPrint writes no /ID unless a variant requires one, and a
        # required one is derived from the file's own bytes. Either way the
        # bytes are the document's, never a clock's or a random source's.
        assert PRINT.identifier == SCREEN.identifier is None

    def test_the_options_name_every_field_weasyprint_reads(self):
        assert set(SCREEN.options()) == {
            "dpi",
            "jpeg_quality",
            "optimize_images",
            "pdf_variant",
            "pdf_identifier",
        }


class TestTheProfileIsAnExporterFact:
    def test_the_builder_never_imports_it(self):
        # PdfProfile lives in pyhermes/pdf: nothing a document is built from may
        # depend on how one exporter writes it.
        for path in sorted(pathlib.Path("pyhermes/builder").rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    assert not node.module.startswith("pyhermes.pdf"), path


@requires_backend
class TestTheProfileAgreesWithTheBackend:
    def test_the_variant_list_is_weasyprints(self):
        from weasyprint.pdf import VARIANTS

        assert set(VARIANTS) - {"debug"} == PDF_VARIANTS

    def test_print_is_weasyprints_own_defaults(self):
        # Which is why a PRINT render is byte-identical to one written with no
        # options at all, and no existing caller's bytes moved.
        from weasyprint import DEFAULT_OPTIONS

        for key, value in PRINT.options().items():
            assert DEFAULT_OPTIONS[key] == value, key
