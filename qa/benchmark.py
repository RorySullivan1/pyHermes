"""
The speed benchmark over the reference reports (roadmap v0.3.0).

For each report it measures what an author writes (the code lines of the source that
builds it) and how long a machine takes from that source to a checked, sendable
artifact: build, render, lint, and the PDF where the medium prints and ``[pdf]`` is
installed. ``reference/README.md`` records each gate's run.

    python -m qa.benchmark                  # every report, five runs each
    python -m qa.benchmark daily-note -n 9
"""

from __future__ import annotations

import argparse
import ast
import io
import platform
import statistics
import sys
import time
import tokenize
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from pyhermes.builder.document import Document
from pyhermes.check.lint import Severity, lint_document
from qa.reference import REPORTS, ROOT, build, build_script, load_script

_SKIPPED = (
    tokenize.COMMENT,
    tokenize.NL,
    tokenize.NEWLINE,
    tokenize.INDENT,
    tokenize.DEDENT,
    tokenize.ENDMARKER,
)


@dataclass(frozen=True)
class Measurement:
    """One report's numbers: milliseconds are medians over the runs."""

    report: str
    source: str
    author_lines: int
    build_ms: float
    render_ms: float
    check_ms: float
    pdf_ms: float | None
    errors: int


def _docstring_lines(tree: ast.Module) -> set[int]:
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                if isinstance(body[0].value.value, str):
                    end = body[0].end_lineno or body[0].lineno
                    lines.update(range(body[0].lineno, end + 1))
    return lines


def author_lines(path: Path) -> int:
    """Lines of ``path`` that carry code: no blanks, comments or docstrings."""
    text = path.read_text(encoding="utf-8")
    docstrings = _docstring_lines(ast.parse(text))
    code: set[int] = set()
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if token.type not in _SKIPPED:
            code.update(range(token.start[0], token.end[0] + 1))
    return len(code - docstrings)


def _median_ms(action: Callable[[], object], runs: int) -> float:
    timings = []
    for _ in range(runs):
        start = time.perf_counter()
        action()
        timings.append((time.perf_counter() - start) * 1000)
    return statistics.median(timings)


def _pdf_ms(document: Document, runs: int) -> float | None:
    from pyhermes.pdf import available, render_pdf

    if not document.medium.paged or not available():
        return None
    return _median_ms(lambda: render_pdf(document), runs)


def measure(name: str, runs: int = 5) -> Measurement:
    """Measure the reference report ``name`` over ``runs`` runs."""
    source = Path(load_script(build_script(name)).SOURCE)
    document = build(name)
    findings = lint_document(document)
    return Measurement(
        report=name,
        source=source.as_posix(),
        author_lines=author_lines(ROOT / source),
        build_ms=_median_ms(lambda: build(name), runs),
        render_ms=_median_ms(document.render, runs),
        check_ms=_median_ms(lambda: lint_document(document), runs),
        pdf_ms=_pdf_ms(document, runs),
        errors=sum(f.severity is Severity.ERROR for f in findings),
    )


def table(measurements: Sequence[Measurement]) -> str:
    """The measurements as the markdown table ``reference/README.md`` records."""
    rows = [
        "| Report | Author lines | Build ms | Render ms | Check ms | PDF ms | Lint errors |",
        "|---|---|---|---|---|---|---|",
    ]
    for m in measurements:
        pdf = "n/a" if m.pdf_ms is None else f"{m.pdf_ms:.0f}"
        rows.append(
            f"| {m.report} | {m.author_lines} | {m.build_ms:.0f} | {m.render_ms:.0f} "
            f"| {m.check_ms:.0f} | {pdf} | {m.errors} |"
        )
    return "\n".join(rows)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m qa.benchmark")
    parser.add_argument("reports", nargs="*", metavar="report", help=", ".join(REPORTS))
    parser.add_argument("-n", "--runs", type=int, default=5)
    args = parser.parse_args(argv)
    unknown = sorted(set(args.reports) - set(REPORTS))
    if unknown:
        parser.error(f"no reference report named {', '.join(unknown)}; choose from {REPORTS}")
    args.reports = args.reports or list(REPORTS)
    measurements = [measure(name, args.runs) for name in args.reports]
    print(table(measurements))
    print(f"\n{args.runs} runs each; Python {platform.python_version()}, {platform.platform()}")
    return 1 if any(m.errors for m in measurements) else 0


if __name__ == "__main__":
    sys.exit(main())
