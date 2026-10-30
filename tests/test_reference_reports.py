"""
The reference reports build, render and check clean in CI (roadmap v0.3.0).

Every gate is measured against them, so one that stopped building would leave
the roadmap measuring nothing. The daily note draws its charts through the
``[charts]`` extra and skips without it; ``all-extras`` runs it.
"""

from __future__ import annotations

import re

import pytest

from octavo.check.lint import Severity, lint_document
from octavo.data.exceptions import BackendMissingError
from qa.benchmark import author_lines, main, measure, table
from qa.reference import REFERENCE_DIR, REPORTS, ROOT, build, build_script, load_script

SPEC_FIELDS = ("**Owner**", "**Status**", "**Medium**", "**Audience**", "**Cadence**")
SPEC_SECTIONS = ("## Sections", "## Data inputs")


def _built(name: str):
    try:
        return build(name)
    except BackendMissingError as exc:
        pytest.skip(str(exc))  # the package's message names its extra


@pytest.mark.parametrize("name", REPORTS)
class TestEachReport:
    def test_it_builds_renders_and_checks_clean(self, name):
        document = _built(name)
        assert document.render()
        errors = [f for f in lint_document(document) if f.severity is Severity.ERROR]
        assert errors == []

    def test_its_spec_names_owner_audience_cadence_sections_and_data(self, name):
        spec = (REFERENCE_DIR / name / "SPEC.md").read_text(encoding="utf-8")
        for required in SPEC_FIELDS + SPEC_SECTIONS:
            assert required in spec, f"{name}/SPEC.md lacks {required}"

    def test_a_stand_in_says_so_and_when_it_goes(self, name):
        spec = (REFERENCE_DIR / name / "SPEC.md").read_text(encoding="utf-8")
        source = load_script(build_script(name)).SOURCE
        assert (ROOT / source).is_file()
        if not source.as_posix().startswith("reference/"):
            assert "Stand-in" in spec and "before Gate 1" in spec

    def test_the_roadmap_names_it(self, name):
        roadmap = (ROOT / ".meta" / "roadmap" / "INDEX.md").read_text(encoding="utf-8")
        assert f"`{name}`" in roadmap


def test_the_directory_holds_exactly_the_registered_reports():
    found = {p.name for p in REFERENCE_DIR.iterdir() if p.is_dir() and p.name[0] not in "._"}
    assert found == set(REPORTS)


class TestTheBenchmark:
    def test_author_lines_skip_blanks_comments_and_docstrings(self, tmp_path):
        source = tmp_path / "s.py"
        source.write_text(
            '"""Module.\n\nMore."""\n\n# a comment\nx = 1\n\n\ndef f():\n    """Doc."""\n'
            "    return [\n        x,\n    ]\n",
            encoding="utf-8",
        )
        assert author_lines(source) == 5

    def test_it_measures_a_report_and_tables_it(self):
        measured = measure("research-report", runs=1)
        assert measured.author_lines > 0 and measured.errors == 0
        assert re.search(r"\| research-report \| \d+ \|", table([measured]))

    def test_the_cli_refuses_an_unknown_report(self):
        with pytest.raises(SystemExit) as exit_:
            main(["weekly-wrap"])
        assert exit_.value.code == 2
