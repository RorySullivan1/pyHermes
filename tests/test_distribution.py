"""
The artefact checks catch what they exist to catch (#237).

The real wheel and sdist are built and checked in CI's ``wheel`` job; these
build small stand-ins so each check is proven to fail without a build backend.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from qa.distribution import PACKAGE, main, wheel_problems

ROOT = Path(__file__).resolve().parent.parent


def _wheel(path: Path, names: list[str]) -> Path:
    with zipfile.ZipFile(path, "w") as wheel:
        for name in names:
            wheel.writestr(name, "")
    return path


class TestTheWheel:
    def test_the_marker_is_in_the_source_package(self):
        marker = ROOT / PACKAGE / "py.typed"
        assert marker.is_file() and marker.read_bytes() == b""

    def test_a_wheel_with_the_marker_passes(self, tmp_path):
        wheel = _wheel(tmp_path / "p.whl", [f"{PACKAGE}/__init__.py", f"{PACKAGE}/py.typed"])
        assert wheel_problems(wheel) == []

    def test_a_wheel_without_it_is_named(self, tmp_path):
        wheel = _wheel(tmp_path / "p.whl", [f"{PACKAGE}/__init__.py"])
        assert wheel_problems(wheel) == [f"p.whl is missing {PACKAGE}/py.typed"]

    def test_the_command_fails_on_it(self, tmp_path, capsys):
        _wheel(tmp_path / "p.whl", [f"{PACKAGE}/__init__.py"])
        assert main([str(tmp_path)]) == 1
        assert "missing" in capsys.readouterr().err

    def test_the_command_fails_on_an_empty_directory(self, tmp_path):
        assert main([str(tmp_path)]) == 1
