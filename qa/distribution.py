"""
Check the built artefacts a consumer installs, not the tree they came from (#237).

    python -m qa.distribution dist/     # every wheel in dist/, listed and checked

Exits 1 naming each problem. CI's ``wheel`` job runs it after ``python -m build``;
`.claude/rules/working-in-the-code.md` records what each check guards.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

#: The import root the wheel ships.
PACKAGE = "svc"

#: Files a wheel must carry beyond the code. ``py.typed`` is what tells a
#: consumer's type checker to read the annotations instead of typing everything
#: as ``Any`` (PEP 561).
WHEEL_REQUIRED = (f"{PACKAGE}/py.typed",)


def wheel_problems(path: Path) -> list[str]:
    """Each way the wheel at ``path`` falls short, or an empty list."""
    with zipfile.ZipFile(path) as wheel:
        names = set(wheel.namelist())
    missing = [required for required in WHEEL_REQUIRED if required not in names]
    return [f"{path.name} is missing {required}" for required in missing]


def main(argv: list[str]) -> int:
    """List and check every artefact in the directory given; 0 when all pass."""
    dist = Path(argv[0] if argv else "dist")
    wheels = sorted(dist.glob("*.whl"))
    if not wheels:
        print(f"no wheel in {dist}", file=sys.stderr)
        return 1
    problems = [problem for wheel in wheels for problem in wheel_problems(wheel)]
    for wheel in wheels:
        print(f"{wheel.name}: ok" if not wheel_problems(wheel) else f"{wheel.name}: FAILED")
    for problem in problems:
        print(f"error: {problem}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
