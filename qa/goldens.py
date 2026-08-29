"""
Golden snapshots over the fixture gallery (#58).

Three artifacts per fixture, because a render, its attachments and its
plain-text projection drift independently:

``goldens/<name>.html``       the rendered HTML, byte for byte, unnormalised
``goldens/<name>.assets.txt`` the asset manifest, one record per ``ImageAsset``
``goldens/<name>.txt``        the plain-text projection (#110)

``pytest --update-goldens`` is the only regeneration path, and a **missing**
golden fails rather than creating itself — a golden that writes itself on
first run pins whatever the code did that day.

`.claude/rules/qa-harness.md` carries the mismatch report's shape and why.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from svc.builder import Email

#: Where the checked-in goldens live — inside the fixture package, next to the
#: code that generates them.
GOLDEN_DIR = Path(__file__).parent / "fixtures" / "goldens"

#: The opt-in regeneration flag, named once so the failure message and the
#: conftest that registers it cannot drift apart.
UPDATE_FLAG = "--update-goldens"

#: Lines of leading context in a mismatch report, and the point at which a
#: single line is elided. A 90 KB document has lines far too long to print
#: whole, and an unreadable report is barely better than "bytes differ".
_CONTEXT_LINES = 3
_EXCERPT_CHARS = 120


def html_path(name: str) -> Path:
    """Path to a fixture's rendered-HTML golden."""
    return GOLDEN_DIR / f"{name}.html"


def manifest_path(name: str) -> Path:
    """Path to a fixture's asset-manifest golden."""
    return GOLDEN_DIR / f"{name}.assets.txt"


def text_path(name: str) -> Path:
    """Path to a fixture's plain-text golden."""
    return GOLDEN_DIR / f"{name}.txt"


def render_manifest(email: Email) -> str:
    """
    Serialise an email's asset manifest to the checked-in text form.

    Empty for a fixture with no CID images — an empty file is the honest
    record of "this email attaches nothing", and it still fails loudly the
    day an attachment appears.

    Raises:
        ValueError: If a field contains a tab or newline, which would make
            the record ambiguous. Neither can occur today (a Content-ID is
            constrained to ``[A-Za-z0-9._+-]`` and filenames derive from it),
            so this guards the format against a future that loosens either.
    """
    lines = []
    for asset in email.assets():
        fields = (asset.content_id, asset.mime_type, str(len(asset.data)), asset.filename)
        for field in fields:
            if "\t" in field or "\n" in field:
                raise ValueError(
                    f"Asset field {field!r} contains a tab or newline, which the "
                    "manifest golden's line format cannot represent."
                )
        lines.append("\t".join(fields))
    return "".join(f"{line}\n" for line in lines)


@dataclass(frozen=True)
class GoldenMismatch:
    """One artifact of one fixture, diverging from what is checked in."""

    fixture: str
    artifact: str
    path: Path
    report: str

    def __str__(self) -> str:
        return self.report


def artifacts(name: str, email: Email) -> list[tuple[str, Path, str]]:
    """
    Every artifact pinned for one fixture: ``(label, path, content)``.

    The single list :func:`check_fixture` and :func:`write_fixture` both walk,
    so checking and regenerating cannot come to disagree about what is pinned
    — which is how a fourth artifact would otherwise be checked but never
    written, or written but never checked.
    """
    return [
        ("rendered HTML", html_path(name), email.render()),
        ("asset manifest", manifest_path(name), render_manifest(email)),
        ("plain text", text_path(name), email.text()),
    ]


def check_fixture(name: str, email: Email) -> list[GoldenMismatch]:
    """
    Compare a built email against every one of its goldens.

    Returns:
        A list of mismatches, empty when the fixture matches. Every artifact
        is always checked, so one run reports HTML *and* manifest *and* text
        drift rather than hiding the later ones behind the first.
    """
    return [
        mismatch
        for artifact, path, actual in artifacts(name, email)
        if (mismatch := _compare(name, artifact, path, actual)) is not None
    ]


def write_fixture(name: str, email: Email) -> list[Path]:
    """
    Rewrite every golden for one fixture. The ``--update-goldens`` path.

    Returns the paths written, so a caller can report what it touched.
    """
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    for _, path, content in artifacts(name, email):
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written


# ──────────────────────────────────────────────────────────────────────
# Diagnosis
# ──────────────────────────────────────────────────────────────────────


def _compare(name: str, artifact: str, path: Path, actual: str) -> GoldenMismatch | None:
    """Compare one artifact, building a diagnosable report if it differs."""
    if not path.exists():
        return GoldenMismatch(
            fixture=name,
            artifact=artifact,
            path=path,
            report=(
                f"{name}: no {artifact} golden is checked in at {_display(path)}.\n"
                f"  A golden is never created implicitly — run `pytest {UPDATE_FLAG}` "
                "and commit the result, so the first pinned bytes are reviewed like "
                "any other change."
            ),
        )

    expected = path.read_text(encoding="utf-8")
    if expected == actual:
        return None

    return GoldenMismatch(
        fixture=name,
        artifact=artifact,
        path=path,
        report=_report(name, artifact, path, expected, actual),
    )


def _report(name: str, artifact: str, path: Path, expected: str, actual: str) -> str:
    """
    Locate the first divergence and describe it.

    "Bytes differ" on a 90 KB document costs the next reader an hour, so the
    report names the fixture, the line, the byte offset, and shows the two
    versions of the line that moved.
    """
    line_no, offset = _first_difference(expected, actual)
    expected_lines = expected.splitlines()
    actual_lines = actual.splitlines()

    context = expected_lines[max(0, line_no - 1 - _CONTEXT_LINES) : line_no - 1]
    body = [
        f"{name}: {artifact} differs from its golden.",
        f"  golden: {_display(path)}",
        f"  first divergence at line {line_no}, byte offset {offset}",
        f"  ({len(expected.encode('utf-8'))} bytes expected, {len(actual.encode('utf-8'))} actual)",
    ]
    body += [
        f"    {line_no - len(context) + i:>6} | {_elide(line)}" for i, line in enumerate(context)
    ]
    body += [
        f"  - expected {line_no:>6} | {_elide(_line_at(expected_lines, line_no))}",
        f"  + actual   {line_no:>6} | {_elide(_line_at(actual_lines, line_no))}",
        f"  If this change is intended, regenerate with `pytest {UPDATE_FLAG}` and "
        "commit the diff — that diff is the claim that it was intended.",
    ]
    return "\n".join(body)


def _first_difference(expected: str, actual: str) -> tuple[int, int]:
    """
    The (1-based line, 0-based byte offset) where two strings first diverge.

    When one is a prefix of the other — a truncated or extended render — the
    divergence is reported at the end of the shorter, which is where a reader
    should start looking.
    """
    limit = min(len(expected), len(actual))
    index = limit
    for i in range(limit):
        if expected[i] != actual[i]:
            index = i
            break
    prefix = expected[:index]
    return prefix.count("\n") + 1, len(prefix.encode("utf-8"))


def _line_at(lines: list[str], line_no: int) -> str:
    """The 1-based line, or a marker when the text ended before it."""
    if line_no - 1 < len(lines):
        return lines[line_no - 1]
    return "<end of file>"


def _elide(line: str) -> str:
    """Trim a line that is too long to read in a failure report."""
    if len(line) <= _EXCERPT_CHARS:
        return line
    return f"{line[:_EXCERPT_CHARS]}… (+{len(line) - _EXCERPT_CHARS} chars)"


def _display(path: Path) -> str:
    """Repo-relative when possible, so a report is readable from any cwd."""
    try:
        return str(path.relative_to(Path(__file__).parent.parent))
    except ValueError:
        return str(path)


__all__ = [
    "GOLDEN_DIR",
    "UPDATE_FLAG",
    "GoldenMismatch",
    "artifacts",
    "check_fixture",
    "html_path",
    "manifest_path",
    "render_manifest",
    "text_path",
    "write_fixture",
]
