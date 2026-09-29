"""
The ``preview`` CLI (#61): build, save, lint and screenshot in one command.

    python -m qa.preview kitchen_sink --lint --screenshot --open
    python -m qa.preview drafts/weekly.py:build --lint

Writes **both** projections — ``<name>.html`` and ``<name>.txt`` — because an
email has two readable parts and no screenshot or lint rule can show the
second one.

Takes a gallery fixture by name or any ``path.py:callable`` returning an
``Document``, so a draft outside the gallery uses the same loop.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
import webbrowser
from collections.abc import Callable
from pathlib import Path

from pyhermes.builder import EmailBuilder
from pyhermes.builder.document import Document
from pyhermes.builder.exceptions import EmailBuilderError
from pyhermes.pdf import PdfError

from .fixtures import all_brochure_fixtures, all_fixtures, all_paged_fixtures
from .lint import Severity, format_findings, lint_document
from .screenshots import ScreenshotError, capture_emails, capture_pages

#: Where rendered HTML lands. Gitignored, per the repo's existing convention.
DEFAULT_OUT_DIR = Path("output")

EXIT_OK = 0
EXIT_LINT_ERRORS = 1
EXIT_BUILD_FAILED = 2


class PreviewError(RuntimeError):
    """A target that could not be resolved into an email."""


# ──────────────────────────────────────────────────────────────────────
# Resolving a target
# ──────────────────────────────────────────────────────────────────────


def resolve(target: str) -> tuple[str, Document]:
    """
    Turn a target into ``(name, document)``.

    Two forms, told apart by the ``:``:

    * ``kitchen_sink`` — a fixture in the #57 gallery.
    * ``drafts/weekly.py:build`` — a zero-argument callable in a Python file,
      returning an ``Email`` or an ``EmailBuilder``. This is the form that
      makes the tool useful for drafting a real newsletter rather than only
      for inspecting fixtures.

    Raises:
        PreviewError: The target names no fixture, no file, or no callable.
        EmailBuilderError: The email itself was rejected — propagated as-is,
            since the builder's own message is the useful one.
    """
    if ":" in target:
        return _from_spec(target)
    return target, _from_fixture(target)


def _gallery() -> dict[str, Callable[[], Document]]:
    """
    Every gallery, for a tool that only ever *looks* at what it is given.

    The two registries stay apart for the test suite, whose assertions are
    per-medium (#165 merges them). Here the distinction buys nothing: this
    command renders a document and shows it to you, and refusing to preview
    a paged fixture would be the tool having an opinion it has no use for.
    """
    return {**all_fixtures(), **all_paged_fixtures(), **all_brochure_fixtures()}


def _from_fixture(name: str) -> Document:
    gallery = _gallery()
    if name not in gallery:
        raise PreviewError(
            f"No fixture named {name!r}. Available: {', '.join(sorted(gallery))}.\n"
            "For a file, use the path:callable form, e.g. drafts/weekly.py:build"
        )
    return _as_document(gallery[name](), name)


def _from_spec(target: str) -> tuple[str, Document]:
    """
    Load ``path/to/module.py:callable``.

    Split on the *last* colon so a Windows drive letter cannot be mistaken for
    the separator.

    The file is executed, which is what importing anything means — this is a
    developer tool pointed at the developer's own draft, the same trust as
    running the script directly.
    """
    path_text, _, attribute = target.rpartition(":")
    path = Path(path_text)
    if not attribute:
        raise PreviewError(f"{target!r} names no callable. Expected path/to/module.py:callable.")
    if not path.is_file():
        raise PreviewError(f"No such file: {path}")

    module_name = f"_qa_preview_{path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise PreviewError(f"{path} is not importable as Python.")
    module = importlib.util.module_from_spec(spec)
    # Registered before execution so the module can find itself — dataclasses
    # and anything else that looks up __module__ need it present.
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except EmailBuilderError:
        raise
    except Exception as exc:
        raise PreviewError(f"{path} failed to import: {exc}") from exc

    builder = getattr(module, attribute, None)
    if builder is None:
        raise PreviewError(f"{path} has no attribute {attribute!r}.")
    if not callable(builder):
        raise PreviewError(f"{attribute!r} in {path} is not callable.")

    name = f"{path.stem}-{attribute}"
    return name, _as_document(builder(), name)


def _as_document(value: object, name: str) -> Document:
    """
    Accept a ``Document``, an ``Email`` or an ``EmailBuilder``.

    All three are public API and a caller should not have to remember which
    one their own function returns. An ``Email`` *is* a ``Document`` since
    #162, so the check is one line shorter than it looks.
    """
    if isinstance(value, EmailBuilder):
        return value.build()
    if isinstance(value, Document):
        return value
    raise PreviewError(
        f"{name} returned {type(value).__name__}, not a Document, Email or EmailBuilder."
    )


# ──────────────────────────────────────────────────────────────────────
# The command
# ──────────────────────────────────────────────────────────────────────


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m qa.preview",
        description="Build an email, save it, and optionally lint and screenshot it.",
        epilog=(
            "targets:\n"
            "  kitchen_sink             a fixture from the gallery (see --list)\n"
            "  drafts/weekly.py:build   a zero-arg callable returning a Document\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("target", nargs="?", help="Fixture name, or path/to/module.py:callable.")
    parser.add_argument("--list", action="store_true", help="List the gallery fixtures and exit.")
    parser.add_argument("--lint", action="store_true", help="Report portability findings (#60).")
    parser.add_argument("--screenshot", action="store_true", help="Capture PNGs (#59).")
    parser.add_argument("--open", action="store_true", help="Open the HTML in a browser.")
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUT_DIR}).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)

    if args.list:
        for name in sorted(_gallery()):
            print(name)
        return EXIT_OK

    if not args.target:
        parser.error("a target is required (or --list)")

    try:
        name, email = resolve(args.target)
        html = email.render()
        text = email.text()
    except PreviewError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_BUILD_FAILED
    except EmailBuilderError as exc:
        # The builder's own message names the field or the limit. Printing it
        # bare beats a traceback wall for what is nearly always a data mistake.
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return EXIT_BUILD_FAILED

    args.out.mkdir(parents=True, exist_ok=True)
    destination = args.out / f"{name}.html"
    destination.write_text(html, encoding="utf-8")
    print(f"{destination}  ({len(html.encode('utf-8')) / 1024:.1f} KB)")

    # Both projections, always. Since #109 an email has two readable parts and
    # this is the loop for eyeballing one email, so writing only the HTML would
    # leave the half that no screenshot and no lint rule can show you.
    text_destination = args.out / f"{name}.txt"
    text_destination.write_text(text, encoding="utf-8")
    print(f"{text_destination}  ({len(text.encode('utf-8')) / 1024:.1f} KB)")

    exit_code = EXIT_OK

    if args.lint:
        # Judged by its own medium's rules since #165: an email answers to
        # the ten about mail clients, a paged document to the six about a page.
        findings = lint_document(email)
        print(format_findings(findings))
        if any(finding.severity is Severity.ERROR for finding in findings):
            exit_code = EXIT_LINT_ERRORS

    pdf_destination = None
    if email.medium.paged:
        # A paged document's deliverable is the PDF, so preview writes one
        # where it writes the HTML -- and says why it could not, rather than
        # failing, because the backend is an optional extra like the browser.
        try:
            from pyhermes.pdf import page_count, save_pdf

            pdf_destination = save_pdf(email, args.out / f"{name}.pdf")
            size_kb = pdf_destination.stat().st_size / 1024
            print(f"{pdf_destination}  ({size_kb:.1f} KB, {page_count(email)} page(s))")
        except PdfError as exc:
            print(f"pdf skipped: {exc}", file=sys.stderr)

    if args.screenshot:
        try:
            if email.medium.paged:
                shots, environment = capture_pages({name: email}, args.out / "screenshots")
                print(f"pdfium {environment['renderer']}")
            else:
                shots, environment = capture_emails({name: email}, args.out / "screenshots")
                print(f"Chromium {environment['browser']}")
        except (ScreenshotError, PdfError) as exc:
            # Not a failure: both extras are optional by design, so a missing
            # one must not turn a good document into a bad exit code.
            print(f"screenshots skipped: {exc}", file=sys.stderr)
        else:
            for shot in shots:
                print(f"  {shot.path}  {shot.width}x{shot.height}")

    if args.open:
        # A paged document opens as the thing it is. Showing its HTML in a
        # browser would show a page without pages -- the one property the
        # medium exists for.
        webbrowser.open((pdf_destination or destination).resolve().as_uri())

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
