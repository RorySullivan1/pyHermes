"""
Every text read and write names its encoding (#372).

``Path.read_text()`` and ``write_text()`` with no ``encoding=`` use the locale's,
which is cp1252 on Windows, so a template holding an em dash failed to read
there and passed on Linux. The rule is checked on the syntax tree, not by grep,
so a call split over lines is seen and a string naming the method is not.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: The trees whose text I/O must be explicit: the package, the harness and the suite.
SCANNED = ("pyhermes", "qa", "tests", "conftest.py")

METHODS = {"read_text", "write_text"}


def bare_calls(source: str, path: str) -> list[str]:
    """``path:line method()`` for each text read or write in ``source`` that names no encoding."""
    found = []
    for node in ast.walk(ast.parse(source, path)):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in METHODS
            and not any(keyword.arg == "encoding" for keyword in node.keywords)
        ):
            found.append(f"{path}:{node.lineno} {node.func.attr}()")
    return found


def _sources() -> list[Path]:
    files: list[Path] = []
    for name in SCANNED:
        target = ROOT / name
        files.extend([target] if target.is_file() else sorted(target.rglob("*.py")))
    return files


def test_every_text_read_and_write_names_its_encoding():
    offenders = [
        call
        for path in _sources()
        for call in bare_calls(path.read_text(encoding="utf-8"), str(path.relative_to(ROOT)))
    ]
    assert not offenders, (
        "text I/O without encoding='utf-8' reads the locale's, cp1252 on Windows:\n"
        + "\n".join(offenders)
    )


def test_the_check_sees_a_call_split_over_lines_and_ignores_one_that_names_it():
    source = 'p.read_text(\n)\np.write_text("x", encoding="utf-8")\np.read_text()\n'
    assert bare_calls(source, "x.py") == ["x.py:1 read_text()", "x.py:4 read_text()"]
