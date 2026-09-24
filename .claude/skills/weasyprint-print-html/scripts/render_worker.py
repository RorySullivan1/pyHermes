#!/usr/bin/env python3
"""Render HTML to PDF with the WeasyPrint Python API. Runs INSIDE the WeasyPrint env.

Invoked by `render.py`, never directly by a workflow — `render.py` owns finding the right
interpreter. The Python API is used rather than the CLI for two reasons the CLI cannot give:
a custom `url_fetcher` (for --strict-fetch) and programmatic capture of the `weasyprint`
logger, which is where every silent-degradation warning goes.

Emits one JSON object on stdout: {"ok", "output", "pages", "messages": [{level, name, text}]}.
Everything human-readable goes to stderr so stdout stays parseable.

API facts below are grounded in the WeasyPrint 69.0 source, not assumed:
  - `HTML(filename=..., base_url=..., url_fetcher=...)`; `media_type` already defaults to
    'print', so it is not set here.
  - Valid option names are exactly `weasyprint.DEFAULT_OPTIONS`. `render()` only *warns* on
    an unknown option ("Unknown rendering option: %s."), so a typo would silently do nothing
    — this script validates against DEFAULT_OPTIONS and fails loudly instead.
  - Two loggers exist: `weasyprint` (warnings/errors) and `weasyprint.progress` (info).
    A handler on `weasyprint` at WARNING captures the former without the progress noise.
  - A url_fetcher is invoked as a plain call, `url_fetcher(url)`; `URLFetcher.__call__`
    delegates to `self.fetch(url)`. Subclassing and overriding `fetch` is therefore the
    supported extension point. It must return a `URLFetcherResponse` — returning a dict is
    deprecated. `default_url_fetcher` is itself deprecated in 69.0; do not use it.
"""
import argparse
import json
import logging
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse


def build_strict_fetcher(base_dir, url_fetcher_cls, fail_on_errors):
    """A URLFetcher that allows only data: URIs and file: paths under `base_dir`.

    Use when any part of the template content comes from outside the author's control.

    Containment is immediate — a refused URL is never fetched — but by default WeasyPrint
    turns the refusal into a log line and finishes the render, so the PDF is simply missing
    that asset. Pass `fail_on_errors` to make any failed fetch fatal instead; the base class
    reads that flag and raises FatalURLFetchingError rather than warning.
    """
    root = Path(base_dir).resolve()

    class StrictFetcher(url_fetcher_cls):
        def fetch(self, url, headers=None):
            parsed = urlparse(url)
            if parsed.scheme == "data":
                return super().fetch(url, headers)
            if parsed.scheme != "file":
                raise ValueError(f"strict-fetch: protocol {parsed.scheme!r} refused: {url}")
            target = Path(unquote(parsed.path)).resolve()
            if target != root and root not in target.parents:
                raise ValueError(f"strict-fetch: {target} is outside {root}")
            return super().fetch(url, headers)

    # allowed_protocols is enforced by the base class before fetch() is even reached.
    return StrictFetcher(
        allowed_protocols={"file", "data"}, fail_on_errors=fail_on_errors)


class Collector(logging.Handler):
    """Capture WeasyPrint's warnings/errors instead of letting them print and vanish."""

    def __init__(self):
        super().__init__(level=logging.WARNING)
        self.records = []

    def emit(self, record):
        self.records.append({
            "level": record.levelname.lower(),
            "name": record.name,
            "text": record.getMessage(),
        })


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--pdf-variant", default=None)
    ap.add_argument("--optimize-images", action="store_true")
    ap.add_argument("--jpeg-quality", type=int, default=None)
    ap.add_argument("--dpi", type=int, default=None)
    ap.add_argument("--strict-fetch", action="store_true")
    ap.add_argument("--fail-on-fetch-error", action="store_true",
                    help="make any unreachable asset fatal instead of a warning")
    args = ap.parse_args(argv)

    try:
        from weasyprint import DEFAULT_OPTIONS, HTML
        from weasyprint.pdf import VARIANTS
        from weasyprint.urls import FatalURLFetchingError, URLFetcher
    except ImportError as exc:
        print(json.dumps({"ok": False, "error": f"weasyprint not importable: {exc}"}))
        return 2

    options = {}
    if args.pdf_variant:
        if args.pdf_variant not in VARIANTS:
            print(json.dumps({
                "ok": False,
                "error": f"unknown pdf_variant {args.pdf_variant!r}; "
                         f"valid: {', '.join(sorted(VARIANTS))}",
            }))
            return 2
        options["pdf_variant"] = args.pdf_variant
    if args.optimize_images:
        options["optimize_images"] = True
    if args.jpeg_quality is not None:
        options["jpeg_quality"] = args.jpeg_quality
    if args.dpi is not None:
        options["dpi"] = args.dpi

    # Fail loudly on an option name this WeasyPrint does not know. Left to WeasyPrint it
    # is only a warning, and the option silently does nothing.
    unknown = sorted(set(options) - set(DEFAULT_OPTIONS))
    if unknown:
        print(json.dumps({
            "ok": False,
            "error": f"option(s) not in this WeasyPrint's DEFAULT_OPTIONS: {unknown}",
        }))
        return 2

    base_url = args.base_url or str(Path(args.input).resolve().parent)
    fetcher = None
    if args.strict_fetch:
        fetcher = build_strict_fetcher(base_url, URLFetcher, args.fail_on_fetch_error)
    elif args.fail_on_fetch_error:
        fetcher = URLFetcher(fail_on_errors=True)

    collector = Collector()
    logger = logging.getLogger("weasyprint")
    logger.addHandler(collector)
    previous_level = logger.level
    logger.setLevel(logging.WARNING)
    try:
        document = HTML(
            filename=args.input, base_url=base_url, url_fetcher=fetcher,
        ).render(**options)
        pages = len(document.pages)
        document.write_pdf(args.output, **options)
    # FatalURLFetchingError subclasses BaseException, NOT Exception (weasyprint/urls.py),
    # so `except Exception` silently misses the one error --fail-on-fetch-error exists to
    # raise. Probed 2026-09-15: without naming it here the worker died with a traceback and
    # an empty stdout, and render.py reported "unknown error".
    except (Exception, FatalURLFetchingError) as exc:
        print(json.dumps({
            "ok": False, "error": f"{type(exc).__name__}: {exc}",
            "messages": collector.records,
        }))
        return 2
    finally:
        logger.removeHandler(collector)
        logger.setLevel(previous_level)

    print(json.dumps({
        "ok": True, "output": str(Path(args.output).resolve()),
        "pages": pages, "messages": collector.records,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
