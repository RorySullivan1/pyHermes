#!/usr/bin/env python3
"""Render print HTML to PDF. Stdlib only — finds the WeasyPrint env and drives the worker.

Nothing in the pipeline outside `render_worker.py` imports WeasyPrint, which is what keeps
the renderer swappable: replacing WeasyPrint with another engine means replacing one worker.

Interpreter search order (first hit wins):
  1. --python PATH
  2. $WEASYPRINT_PYTHON
  3. the current interpreter, if `import weasyprint` succeeds in it

Exit codes: 0 rendered clean, 1 rendered WITH warnings, 2 render failed.
Exit 1 matters: WeasyPrint degrades silently — a missing font or an unfetchable image
produces a plausible-looking PDF and a log line. Treat 1 as "look at the warnings", not
as success.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

WORKER = Path(__file__).resolve().parent / "render_worker.py"
REFERENCE = "references/environment.md"

# Grounded in the WeasyPrint 69.0 source: these are the literal message shapes its logger
# emits. Categorising on invented substrings would silently drop warnings into "other".
CATEGORIES = (
    ("fonts", ("font-face", "cannot be loaded")),
    ("failed_fetches", ("failed to load", "failed to render svg", "malformed url",
                        "malformed base url")),
    ("ignored_css", ("ignored `", "not supported", "unsupported")),
    ("bad_options", ("unknown rendering option",)),
)


def categorize(text):
    low = text.lower()
    for name, needles in CATEGORIES:
        if any(n in low for n in needles):
            return name
    return "other"


def interpreter_has_weasyprint(python):
    try:
        done = subprocess.run(
            [python, "-c", "import weasyprint"], capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return False
    return done.returncode == 0


def find_interpreter(explicit):
    tried = []
    for candidate, label in (
        (explicit, "--python"),
        (os.environ.get("WEASYPRINT_PYTHON"), "$WEASYPRINT_PYTHON"),
        (sys.executable, "the current interpreter"),
    ):
        if not candidate:
            continue
        resolved = shutil.which(candidate) or candidate
        tried.append(f"{label}: {candidate}")
        if Path(resolved).exists() and interpreter_has_weasyprint(resolved):
            return resolved, tried
    return None, tried


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("input", help="HTML file to render")
    ap.add_argument("output", help="PDF path to write")
    ap.add_argument("--base-url", default=None,
                    help="defaults to the input file's directory")
    ap.add_argument("--python", default=None, help="interpreter that has weasyprint")
    ap.add_argument("--pdf-variant", default=None,
                    help="e.g. pdf/a-3b for archival output; the worker validates the name")
    ap.add_argument("--optimize-images", action="store_true")
    ap.add_argument("--jpeg-quality", type=int, default=None)
    ap.add_argument("--dpi", type=int, default=None)
    ap.add_argument("--strict-fetch", action="store_true",
                    help="allow only data: URIs and files under the base directory")
    ap.add_argument("--fail-on-fetch-error", action="store_true",
                    help="exit 2 on any unreachable asset instead of warning and "
                         "shipping a PDF with a hole in it")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    source = Path(args.input)
    if not source.is_file():
        print(f"render: input not found: {source}", file=sys.stderr)
        return 2

    python, tried = find_interpreter(args.python)
    if python is None:
        print("render: no interpreter with WeasyPrint installed.", file=sys.stderr)
        for line in tried:
            print(f"  tried {line}", file=sys.stderr)
        print(f"  Set $WEASYPRINT_PYTHON or pass --python. See {REFERENCE} for the conda\n"
              f"  install and for the sys.executable mismatch between terminal and notebook.",
              file=sys.stderr)
        return 2

    cmd = [python, str(WORKER), str(source), args.output]
    if args.base_url:
        cmd += ["--base-url", args.base_url]
    if args.pdf_variant:
        cmd += ["--pdf-variant", args.pdf_variant]
    if args.optimize_images:
        cmd.append("--optimize-images")
    if args.jpeg_quality is not None:
        cmd += ["--jpeg-quality", str(args.jpeg_quality)]
    if args.dpi is not None:
        cmd += ["--dpi", str(args.dpi)]
    if args.strict_fetch:
        cmd.append("--strict-fetch")
    if args.fail_on_fetch_error:
        cmd.append("--fail-on-fetch-error")

    done = subprocess.run(cmd, capture_output=True, text=True)
    try:
        result = json.loads(done.stdout or "{}")
    except ValueError:
        print("render: worker produced unparseable output — treating as failure.",
              file=sys.stderr)
        print(done.stdout[-2000:], file=sys.stderr)
        print(done.stderr[-2000:], file=sys.stderr)
        return 2

    if not result.get("ok"):
        print(f"render: FAILED — {result.get('error', 'unknown error')}", file=sys.stderr)
        for message in result.get("messages", []):
            print(f"  {message['level']}: {message['text']}", file=sys.stderr)
        return 2

    messages = result.get("messages", [])
    grouped = {}
    for message in messages:
        grouped.setdefault(categorize(message["text"]), []).append(message)

    if args.json:
        print(json.dumps({
            "ok": True, "output": result["output"], "pages": result.get("pages"),
            "interpreter": python, "warnings": grouped,
        }, indent=2))
    else:
        print(f"render: wrote {result['output']} ({result.get('pages', '?')} page(s)) "
              f"using {python}")
        if not messages:
            print("render: no warnings.")
        else:
            for name in ("bad_options", "fonts", "failed_fetches", "ignored_css", "other"):
                bucket = grouped.get(name)
                if not bucket:
                    continue
                print(f"\n  {name} ({len(bucket)}):")
                for message in bucket[:12]:
                    print(f"    {message['level']}: {message['text']}")
                if len(bucket) > 12:
                    print(f"    … {len(bucket) - 12} more")
            print("\nrender: warnings present — WeasyPrint degrades silently, so read these "
                  "before trusting the layout.")
    return 1 if messages else 0


if __name__ == "__main__":
    raise SystemExit(main())
