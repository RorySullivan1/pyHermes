"""
The old import name still works for one release, and says so (#248).

Each check runs in a fresh interpreter: an import is cached for the life of a
process, so a warning raised once in this one could not be observed again.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run(source: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-W", "always::DeprecationWarning", "-c", source],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_importing_svc_warns_once_and_names_the_new_name():
    result = _run("import svc, svc.builder, svc.config")
    assert result.returncode == 0, result.stderr
    assert result.stderr.count("DeprecationWarning") == 1
    assert "import pyhermes.builder" in result.stderr


def test_a_name_imported_through_svc_is_the_same_object():
    result = _run(
        "from svc.builder import Email\n"
        "from svc.builder.models import EmailMetadata\n"
        "import pyhermes.builder, pyhermes.builder.models\n"
        "assert Email is pyhermes.builder.Email\n"
        "assert EmailMetadata is pyhermes.builder.models.EmailMetadata\n"
        "import svc.config, pyhermes.config\n"
        "assert svc.config is pyhermes.config\n"
    )
    assert result.returncode == 0, result.stderr


def test_it_renders_an_email():
    result = _run(
        "from svc.builder import EmailBuilder, FullWidth, TextBlock\n"
        "html = (EmailBuilder()\n"
        "    .metadata({'email_subject': 's', 'firm_name': 'f', 'campaign_name': 'c'})\n"
        "    .section(FullWidth(content=TextBlock('<p>Old name.</p>'))).render())\n"
        "assert 'Old name.' in html\n"
    )
    assert result.returncode == 0, result.stderr


def test_an_unknown_submodule_still_fails_as_one():
    result = _run("import svc.no_such_module")
    assert result.returncode != 0
    assert "ModuleNotFoundError" in result.stderr


def test_nothing_in_the_package_imports_the_old_name():
    offenders = [
        str(path.relative_to(ROOT))
        for top in ("pyhermes", "qa", "tests", "examples")
        for path in (ROOT / top).rglob("*.py")
        if path.name != "test_svc_shim.py"
        and any(
            line.lstrip().startswith(("import svc", "from svc"))
            for line in path.read_text(encoding="utf-8").splitlines()
        )
    ]
    assert offenders == []
