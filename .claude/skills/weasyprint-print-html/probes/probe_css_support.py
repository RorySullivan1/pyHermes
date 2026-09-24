#!/usr/bin/env python3
"""Measure which CSS declarations WeasyPrint actually honours. Runs IN the WeasyPrint env.

`references/css-support.md` is the linter's rule set, so a stale table produces confidently
wrong advice. Re-run this after every WeasyPrint upgrade and update the table from the
output — do not edit the table from memory.

Method: render one declaration at a time and capture the `weasyprint` logger. A declaration
the parser rejects is logged as ``Ignored `prop:value` … unknown property``; one it accepts
is silent. Silence therefore means "parsed", NOT "has an effect" — see the INERT note below.

Controls (the run is void without them):
  POSITIVE  a property known supported (`border-radius`) must come back `accepted`.
  NEGATIVE  a property known dropped (`box-shadow`) must come back `dropped`.
If either control fails, the capture harness is broken and no row below is evidence.

Run: python3 probe_css_support.py
"""
import io
import logging
import sys

# Measured 2026-09-15 against WeasyPrint 69.0. Expected verdicts are asserted so the probe
# reports DRIFT on an upgrade rather than quietly producing a new table nobody compares.
EXPECTED = {
    "box-shadow": ("0 2px 6px rgba(0,0,0,.2)", "dropped"),
    "text-shadow": ("1px 1px 2px #999", "dropped"),
    "filter": ("blur(2px)", "dropped"),
    "backdrop-filter": ("blur(4px)", "dropped"),
    "mix-blend-mode": ("multiply", "dropped"),
    "background-blend-mode": ("screen", "dropped"),
    "clip-path": ("circle(40%)", "dropped"),
    "mask": ("url(#m)", "dropped"),
    "perspective": ("500px", "dropped"),
    "transform-style": ("preserve-3d", "dropped"),
    "aspect-ratio": ("16/9", "dropped"),
    "writing-mode": ("vertical-rl", "dropped"),
    # Rejected as an invalid VALUE, not an unknown property.
    "position": ("sticky", "dropped"),
    # INERT: parses, logs nothing, does nothing on a static page. The probe cannot tell
    # these apart from genuinely supported properties — that is the whole point of the
    # W007 lint rule, and why css-support.md lists them by hand.
    "animation": ("spin 2s linear infinite", "accepted"),
    "transition": ("all .2s ease", "accepted"),
    "will-change": ("transform", "accepted"),
    "scroll-behavior": ("smooth", "accepted"),
    # Supported.
    "transform": ("rotate(3deg)", "accepted"),
    "border-radius": ("2mm", "accepted"),
    "background-image": ("linear-gradient(#fff,#eee)", "accepted"),
    "opacity": ("0.6", "accepted"),
    "gap": ("4mm", "accepted"),
    "display": ("grid", "accepted"),
    "grid-template-columns": ("1fr 1fr", "accepted"),
    "float": ("left", "accepted"),
    "object-fit": ("cover", "accepted"),
    "hyphens": ("auto", "accepted"),
    "orphans": ("3", "accepted"),
    "break-inside": ("avoid", "accepted"),
    "string-set": ("x content()", "accepted"),
    "bookmark-level": ("1", "accepted"),
    "columns": ("2", "accepted"),
}


def measure(html_cls, prop, value):
    captured = []
    handler = logging.Handler()
    handler.emit = lambda record: captured.append(record.getMessage())
    handler.setLevel(logging.WARNING)
    logger = logging.getLogger("weasyprint")
    logger.addHandler(handler)
    previous = logger.level
    logger.setLevel(logging.WARNING)
    source = (
        "<!doctype html><html><head><meta charset='utf-8'><style>"
        f"@page{{size:A4;margin:10mm}} .t{{{prop}:{value}}}"
        "</style></head><body><div class='t'>x</div></body></html>")
    try:
        html_cls(string=source, base_url=".").write_pdf(io.BytesIO())
    except Exception as exc:
        captured.append(f"RENDER ERROR {exc}")
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous)
    rejected = [m for m in captured
                if "gnored" in m or "nsupported" in m or "not supported" in m
                or "RENDER ERROR" in m]
    return ("dropped" if rejected else "accepted"), (rejected[0] if rejected else "")


def main():
    try:
        from weasyprint import HTML, __version__
    except ImportError as exc:
        print(f"probe: weasyprint not importable ({exc}). Run this inside the WeasyPrint "
              f"environment — see references/environment.md.")
        return 2

    controls = {
        "POSITIVE border-radius -> accepted":
            measure(HTML, "border-radius", "2mm")[0] == "accepted",
        "NEGATIVE box-shadow    -> dropped ":
            measure(HTML, "box-shadow", "0 2px 6px #000")[0] == "dropped",
    }
    for label, passed in controls.items():
        print(f"CONTROL {label}: {'PASS' if passed else 'FAIL'}")
    if not all(controls.values()):
        print("\nSTOP THE LINE — the capture harness is broken. No row below is evidence.")
        return 1

    print(f"\nWeasyPrint {__version__}\n")
    print(f"{'property':24} {'measured':9} {'expected':9} detail")
    drift = []
    for prop, (value, expected) in EXPECTED.items():
        verdict, detail = measure(HTML, prop, value)
        flag = "" if verdict == expected else "  <-- DRIFT"
        if flag:
            drift.append((prop, expected, verdict))
        print(f"{prop:24} {verdict:9} {expected:9} {detail[:52]}{flag}")

    if drift:
        print(f"\n{len(drift)} property/ies changed verdict since 2026-09-15 "
              f"(WeasyPrint 69.0):")
        for prop, was, now in drift:
            print(f"  {prop}: was {was}, now {now}")
        print("Update references/css-support.md AND the lists in "
              "scripts/lint_print_html.py before trusting the linter again.")
        return 1
    print("\nNo drift: css-support.md and the linter's lists still match this WeasyPrint.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
