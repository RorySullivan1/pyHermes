"""
The all-extras rule fails a skip that names an extra, and nothing else (#239).

Each case runs a throwaway pytest in a subprocess with the plugin loaded, so the
rule is judged on real reports rather than on a hand-built one.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from qa.require_extras import ENV, EXTRA_SKIP

ROOT = Path(__file__).resolve().parent.parent

CASES = """
import pytest

def test_skipped_for_an_extra():
    pytest.skip('no WeasyPrint; the PDF exporter is the optional "[pdf]" extra')

@pytest.mark.skipif(True, reason='the DataFrame adapter needs "pyhermes[data]"')
def test_marked_for_an_extra():
    pass

def test_skipped_for_another_reason():
    pytest.skip("rateLimitExceeded is resolved in Python, never emitted")

@pytest.mark.xfail(reason='known on the "[qa]" extra', strict=False)
def test_expected_to_fail():
    assert False

def test_passes():
    pass
"""


#: A whole module skipped at import, the way ``tests/test_frames.py`` is without pandas.
MODULE = """
import pytest

pytest.importorskip("no_such_backend", reason='the DataFrame adapter needs "pyhermes[data]"')

def test_never_collected():
    pass
"""


def _run(tmp_path: Path, required: bool) -> subprocess.CompletedProcess[str]:
    (tmp_path / "test_cases.py").write_text(CASES, encoding="utf-8")
    (tmp_path / "test_module_skip.py").write_text(MODULE, encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k != ENV}
    if required:
        env[ENV] = "1"
    env["PYTHONPATH"] = str(ROOT)
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-p",
            "qa.require_extras",
            "-p",
            "no:cacheprovider",
            "-rA",
            "--continue-on-collection-errors",
            "--rootdir",
            str(tmp_path),
            str(tmp_path),
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_with_the_variable_an_extra_skip_fails_and_names_itself(tmp_path):
    result = _run(tmp_path, required=True)
    assert result.returncode == 1, result.stdout
    assert "FAILED test_cases.py::test_skipped_for_an_extra" in result.stdout
    # A skipif mark skips at setup, so its failure is reported as an error.
    assert "ERROR test_cases.py::test_marked_for_an_extra" in result.stdout
    assert '"[pdf]" extra' in result.stdout
    assert "ERROR test_module_skip.py" in result.stdout
    assert "1 failed, 1 passed, 1 skipped, 1 xfailed, 2 errors" in result.stdout


def test_without_it_every_skip_stays_a_skip(tmp_path):
    result = _run(tmp_path, required=False)
    assert result.returncode == 0, result.stdout
    assert "1 passed, 4 skipped, 1 xfailed" in result.stdout


@pytest.mark.parametrize(
    "reason",
    [
        'the "[pdf]" extra',
        'no browser; the "[qa]" extra',
        'pip install "pyhermes[charts]"',
        'rendering an equation is the "[math]" extra',
        'the DataFrame adapter needs "pyhermes[data]"',
    ],
)
def test_the_pattern_matches_every_extras_spelling(reason):
    assert EXTRA_SKIP.search(reason)


def test_the_pattern_matches_every_declared_extra_but_dev():
    import tomllib

    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    extras = set(config["project"]["optional-dependencies"]) - {"dev"}
    assert {e for e in extras if EXTRA_SKIP.search(f"[{e}]")} == extras
