"""
The ``preview`` CLI (#61): build → save → lint → screenshot, in one command.

The workflow the docs prescribed was manual — write a scratch script, build the
email, ``.save()`` it into ``output/``, open a browser, repeat. With the gallery
(#57), the goldens (#58), the screenshot runner (#59) and the lint pass (#60) in
place, that loop gets one entry point, and it serves a real newsletter draft as
readily as a fixture::

    python -m qa.preview --list
    python -m qa.preview kitchen_sink --lint --screenshot
    python -m qa.preview drafts/weekly.py:build --lint --open

**It composes; it does not reimplement.** Fixtures come from
:func:`qa.fixtures.all_fixtures`, findings from :func:`qa.lint.lint_html`,
images from :func:`qa.screenshots.capture_emails`. Anything it needed that they
did not expose was a gap fixed *in them* — that rule is what produced
``capture_emails``, since ``capture_gallery`` could only ever screenshot things
already in the registry, and a user's draft never is.

**No console script**, deliberately. #57 put ``qa/`` outside the wheel because
the gallery is test data; a ``preview`` entry point on the installed package
would contradict that, so the module form is the interface.

Exit codes, so the command composes in a shell:

===  ====================================================================
0    the email built, and nothing asked for was refused
1    ``--lint`` found errors (warnings alone do not fail)
2    the email could not be built, or the target could not be resolved
===  ====================================================================

A missing browser is **not** a failure: ``--screenshot`` says so and carries on,
because the ``[qa]`` extra is optional by design.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
import webbrowser
from pathlib import Path

from svc.builder import Email, EmailBuilder
from svc.builder.exceptions import EmailBuilderError

from .fixtures import all_fixtures
from .lint import Severity, format_findings, lint_html
from .screenshots import ScreenshotError, capture_emails

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


def resolve(target: str) -> tuple[str, Email]:
    """
    Turn a target into ``(name, email)``.

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


def _from_fixture(name: str) -> Email:
    gallery = all_fixtures()
    if name not in gallery:
        raise PreviewError(
            f"No fixture named {name!r}. Available: {', '.join(sorted(gallery))}.\n"
            "For a file, use the path:callable form, e.g. drafts/weekly.py:build"
        )
    return _as_email(gallery[name](), name)


def _from_spec(target: str) -> tuple[str, Email]:
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
    return name, _as_email(builder(), name)


def _as_email(value: object, name: str) -> Email:
    """
    Accept an ``Email`` or an ``EmailBuilder``, since both are public API and a
    caller should not have to remember which one their function returns.
    """
    if isinstance(value, EmailBuilder):
        return value.build()
    if isinstance(value, Email):
        return value
    raise PreviewError(f"{name} returned {type(value).__name__}, not an Email or EmailBuilder.")


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
            "  drafts/weekly.py:build   a zero-arg callable returning an Email\n"
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
        for name in sorted(all_fixtures()):
            print(name)
        return EXIT_OK

    if not args.target:
        parser.error("a target is required (or --list)")

    try:
        name, email = resolve(args.target)
        html = email.render()
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

    exit_code = EXIT_OK

    if args.lint:
        findings = lint_html(html)
        print(format_findings(findings))
        if any(finding.severity is Severity.ERROR for finding in findings):
            exit_code = EXIT_LINT_ERRORS

    if args.screenshot:
        try:
            shots, environment = capture_emails({name: email}, args.out / "screenshots")
        except ScreenshotError as exc:
            # Not a failure: the browser extra is optional by design, so a
            # missing one must not turn a good email into a bad exit code.
            print(f"screenshots skipped: {exc}", file=sys.stderr)
        else:
            print(f"Chromium {environment['browser']}")
            for shot in shots:
                print(f"  {shot.path}  {shot.width}x{shot.height}")

    if args.open:
        webbrowser.open(destination.resolve().as_uri())

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
