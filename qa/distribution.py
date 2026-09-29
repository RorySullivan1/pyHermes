"""
Check the built artefacts a consumer installs, not the tree they came from (#237).

    python -m qa.distribution dist/     # every wheel and sdist in dist/, listed and checked

Exits 1 naming each problem. CI's ``wheel`` job runs it after ``python -m build``;
`.claude/rules/working-in-the-code.md` records what each check guards.
"""

from __future__ import annotations

import sys
import tarfile
import zipfile
from pathlib import Path

#: The import root the wheel ships.
PACKAGE = "svc"

#: Files a wheel must carry beyond the code. ``py.typed`` is what tells a
#: consumer's type checker to read the annotations instead of typing everything
#: as ``Any`` (PEP 561).
WHEEL_REQUIRED = (f"{PACKAGE}/py.typed",)

#: The top-level entries an sdist may hold: the library, what builds it, what
#: describes it, and the two files hatchling always writes (``PKG-INFO``, and a
#: ``.gitignore`` it adds whatever the config says).
SDIST_ALLOWED = frozenset(
    {PACKAGE, "pyproject.toml", "README.md", "LICENSE", "PKG-INFO", ".gitignore"}
)

#: What an sdist must hold for its metadata to build: ``readme`` and
#: ``license-files`` name the last two, so dropping either breaks the install.
SDIST_REQUIRED = ("pyproject.toml", "README.md", "LICENSE", f"{PACKAGE}/__init__.py")


def wheel_problems(path: Path) -> list[str]:
    """Each way the wheel at ``path`` falls short, or an empty list."""
    with zipfile.ZipFile(path) as wheel:
        names = set(wheel.namelist())
    missing = [required for required in WHEEL_REQUIRED if required not in names]
    return [f"{path.name} is missing {required}" for required in missing]


def sdist_problems(path: Path) -> list[str]:
    """Each path the sdist should not carry, and each it lacks, or an empty list."""
    with tarfile.open(path) as sdist:
        names = [name.partition("/")[2] for name in sdist.getnames()]
    present = {name for name in names if name}
    stray = sorted({name.split("/")[0] for name in present} - SDIST_ALLOWED)
    missing = [required for required in SDIST_REQUIRED if required not in present]
    return [f"{path.name} carries {root}, outside the library" for root in stray] + [
        f"{path.name} is missing {required}" for required in missing
    ]


def main(argv: list[str]) -> int:
    """List and check every artefact in the directory given; 0 when all pass."""
    dist = Path(argv[0] if argv else "dist")
    checks = [(wheel, wheel_problems) for wheel in sorted(dist.glob("*.whl"))]
    checks += [(sdist, sdist_problems) for sdist in sorted(dist.glob("*.tar.gz"))]
    if not checks:
        print(f"no wheel or sdist in {dist}", file=sys.stderr)
        return 1
    problems: list[str] = []
    for artefact, check in checks:
        found = check(artefact)
        print(f"{artefact.name}: {'FAILED' if found else 'ok'}")
        problems += found
    for problem in problems:
        print(f"error: {problem}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
