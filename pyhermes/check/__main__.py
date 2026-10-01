"""
``python -m pyhermes.check path/to/module.py:callable``: build, save and check a draft.

Writes ``<name>.html`` and ``<name>.txt``, prints the findings, and exits 0
when clean, 1 on an error finding and 2 when the draft does not build. This
module is the package's one writer to stdout: it runs only as a program.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pyhermes.builder.exceptions import EmailBuilderError

from .lint import Severity, format_findings, lint_html, render_for_check
from .target import TargetError, load_target

EXIT_OK = 0
EXIT_LINT_ERRORS = 1
EXIT_BUILD_FAILED = 2

#: Where the two parts land unless ``--out`` says otherwise.
DEFAULT_OUT_DIR = Path("output")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m pyhermes.check",
        description="Build a draft, save its HTML and text, and check it for client problems.",
    )
    parser.add_argument("target", help="path/to/module.py:callable returning an Email.")
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help=f"Output folder (default: {DEFAULT_OUT_DIR}).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        name, document = load_target(args.target)
        html = render_for_check(document)
        text = document.text()
    except TargetError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_BUILD_FAILED
    except EmailBuilderError as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return EXIT_BUILD_FAILED

    args.out.mkdir(parents=True, exist_ok=True)
    for suffix, part in (("html", html), ("txt", text)):
        destination = args.out / f"{name}.{suffix}"
        destination.write_text(part, encoding="utf-8")
        print(f"{destination}  ({len(part.encode('utf-8')) / 1024:.1f} KB)")

    findings = lint_html(html, document.medium.name, document.rendered_sections())
    print(format_findings(findings))
    failed = any(finding.severity is Severity.ERROR for finding in findings)
    return EXIT_LINT_ERRORS if failed else EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
