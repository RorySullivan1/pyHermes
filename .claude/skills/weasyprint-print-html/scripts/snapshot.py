#!/usr/bin/env python3
"""Rasterize a PDF to page PNGs and report embedded fonts. Stdlib only; wraps poppler.

Claude cannot judge page layout from HTML or from a PDF's bytes. This script produces the
only artifact that answers "does page 2 look right" — one PNG per page — plus the font
report that catches the most common silent failure, a family that fell back because it was
never embedded.

Requires poppler's `pdftoppm` and `pdffonts` (conda: `conda install poppler`). Run
`--check-tools` first if unsure; a missing tool is reported as a precondition, never as a
clean result.

Resolution defaults to 110 dpi deliberately: high enough to read 8pt type, low enough that
viewing several pages does not dominate the context budget. Raise it only to inspect a
specific detail.

Exit codes: 0 all checks passed, 1 findings to look at, 2 could not run (missing tool,
missing input).
"""
import argparse
import hashlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

TOOLS = ("pdftoppm", "pdffonts")
# Families that show up when a requested font was never embedded. Seeing one of these is
# the signature of a silent @font-face failure, not a styling choice.
FALLBACK_SIGNATURES = ("dejavu", "liberation", "nimbus", "freeserif", "freesans", "c059",
                       "urw", "standard symbols")


def missing_tools():
    return [t for t in TOOLS if shutil.which(t) is None]


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def rasterize(pdf, out_dir, dpi):
    out_dir.mkdir(parents=True, exist_ok=True)
    for stale in out_dir.glob("page-*.png"):
        stale.unlink()
    done = run(["pdftoppm", "-png", "-r", str(dpi), str(pdf), str(out_dir / "page")])
    if done.returncode != 0:
        return None, done.stderr.strip()
    # pdftoppm zero-pads to the page count's width (page-1 / page-01 / page-001).
    pages = sorted(out_dir.glob("page-*.png"),
                   key=lambda p: int(re.sub(r"\D", "", p.stem) or 0))
    return pages, ""


def parse_pdffonts(text):
    """Parse `pdffonts` tabular output into [{name, type, embedded}].

    Column positions are taken from the header's `emb` offset rather than assumed, because
    the name and type columns are variable width. Untestable in an environment without
    poppler — if this ever mis-parses, compare against raw `pdffonts <pdf>` output first.
    """
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) < 2:
        return []
    header = lines[0]
    emb_at = header.find("emb")
    fonts = []
    for line in lines[2:]:  # line 1 is the ---- rule
        name = line[:header.find("type")].strip() if header.find("type") > 0 else line.split()[0]
        embedded = None
        if emb_at >= 0 and len(line) > emb_at:
            embedded = line[emb_at:emb_at + 3].strip().lower().startswith("y")
        fonts.append({"name": name, "embedded": embedded})
    return fonts


def hash_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pdf", nargs="?", help="PDF to inspect")
    ap.add_argument("--out-dir", default=None,
                    help="where page PNGs go (default: <pdf parent>/pages)")
    ap.add_argument("--dpi", type=int, default=110)
    ap.add_argument("--expected-fonts", default="",
                    help="comma-separated family substrings that SHOULD be embedded")
    ap.add_argument("--max-pages", type=int, default=None)
    ap.add_argument("--baseline", default=None,
                    help="directory of previously approved page PNGs to diff against")
    ap.add_argument("--check-tools", action="store_true",
                    help="report poppler availability and exit")
    args = ap.parse_args(argv)

    absent = missing_tools()
    if args.check_tools:
        for tool in TOOLS:
            location = shutil.which(tool)
            print(f"  {tool}: {location or 'NOT FOUND'}")
        if absent:
            print(f"snapshot: {', '.join(absent)} missing — install with "
                  f"`conda install poppler`. See references/environment.md.")
            return 2
        print("snapshot: poppler available.")
        return 0

    if not args.pdf:
        ap.error("pdf is required unless --check-tools is given")
    pdf = Path(args.pdf)
    if not pdf.is_file():
        print(f"snapshot: PDF not found: {pdf}", file=sys.stderr)
        return 2
    if absent:
        print(f"snapshot: cannot run — {', '.join(absent)} not on PATH. This is a missing "
              f"precondition, NOT a clean snapshot.", file=sys.stderr)
        print("  Install with `conda install poppler`; see references/environment.md.",
              file=sys.stderr)
        return 2

    out_dir = Path(args.out_dir) if args.out_dir else pdf.parent / "pages"
    pages, error = rasterize(pdf, out_dir, args.dpi)
    if pages is None:
        print(f"snapshot: pdftoppm failed — {error}", file=sys.stderr)
        return 2

    findings = []
    print(f"snapshot: {len(pages)} page(s) at {args.dpi} dpi in {out_dir}/")
    for page in pages:
        print(f"    {page}")
    if args.max_pages is not None and len(pages) > args.max_pages:
        findings.append(f"page count {len(pages)} exceeds --max-pages {args.max_pages}")

    fonts_out = run(["pdffonts", str(pdf)])
    fonts = parse_pdffonts(fonts_out.stdout)
    print(f"\nsnapshot: {len(fonts)} font(s) reported by pdffonts")
    for font in fonts:
        state = {True: "embedded", False: "NOT EMBEDDED", None: "unknown"}[font["embedded"]]
        print(f"    {font['name']}  [{state}]")
        if font["embedded"] is False:
            findings.append(f"font not embedded: {font['name']}")
        if any(sig in font["name"].lower() for sig in FALLBACK_SIGNATURES):
            findings.append(
                f"fallback family present ({font['name']}): a requested @font-face "
                f"probably failed to load and WeasyPrint substituted silently")

    expected = [e.strip().lower() for e in args.expected_fonts.split(",") if e.strip()]
    if expected:
        present = " ".join(f["name"].lower() for f in fonts)
        for want in expected:
            if want not in present:
                findings.append(f"expected font `{want}` is absent from the PDF")

    if args.baseline:
        baseline = Path(args.baseline)
        if not baseline.is_dir():
            findings.append(f"baseline directory {baseline} does not exist")
        else:
            # Rasters, not PDF bytes: a PDF carries creation timestamps, so identical
            # input produces different bytes on every run.
            for page in pages:
                old = baseline / page.name
                if not old.is_file():
                    findings.append(f"{page.name} is new (no baseline)")
                elif hash_file(old) != hash_file(page):
                    findings.append(f"{page.name} CHANGED vs baseline — review visually")
            for old in sorted(baseline.glob("page-*.png")):
                if not (out_dir / old.name).is_file():
                    findings.append(f"{old.name} present in baseline but not in this render")

    if findings:
        print("\nsnapshot: findings")
        for finding in findings:
            print(f"    - {finding}")
        print("\nNow VIEW the page PNGs above; the font and hash checks cannot see layout.")
        return 1
    print("\nsnapshot: fonts and page count OK. Now VIEW the page PNGs — no automated "
          "check here can judge layout.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
