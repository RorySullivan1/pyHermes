#!/usr/bin/env python3
"""Compute WCAG contrast ratios and report pass/fail against the AA bar.

The `branding` skill sets WCAG 2.2 Level AA as the accessibility floor. This makes
that bar checkable instead of quotable: hand it colour pairs, get ratios and verdicts.

    python3 contrast.py "#1A1A1A on #F5F5F5" "#0B5FFF on #FFFFFF"
    python3 contrast.py --self-test

Formula and thresholds are the normative ones from WCAG 2.2 (W3C Recommendation,
12 December 2024) — see the skill's *Contrast* section for the citations. Colour
input is sRGB hex only; other spaces must be converted first.
"""

from __future__ import annotations

import sys

#: Level AA thresholds, keyed by what is being measured. Large text is >= 18pt, or
#: >= 14pt bold (WCAG's normative wording is points, not pixels).
AA = {"normal_text": 4.5, "large_text": 3.0, "ui_and_graphics": 3.0}

#: Level AAA, the stricter tier. Non-text contrast has no AAA criterion.
AAA = {"normal_text": 7.0, "large_text": 4.5}


def _channel(value: int) -> float:
    srgb = value / 255
    return srgb / 12.92 if srgb <= 0.04045 else ((srgb + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_colour: str) -> float:
    """Relative luminance of an sRGB hex colour, 0 (black) to 1 (white)."""
    raw = hex_colour.strip().lstrip("#")
    if len(raw) == 3:
        raw = "".join(c * 2 for c in raw)
    if len(raw) != 6:
        raise ValueError(f"not a hex colour: {hex_colour!r}")
    r, g, b = (int(raw[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast_ratio(foreground: str, background: str) -> float:
    """Contrast ratio between two sRGB hex colours, from 1.0 to 21.0."""
    lighter, darker = sorted(
        (relative_luminance(foreground), relative_luminance(background)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def verdicts(ratio: float) -> dict[str, bool]:
    """Pass/fail for each threshold. Rounding is deliberate: WCAG states a minimum,
    so 4.49 fails 4.5 — never round a near-miss up into a pass."""
    return {f"AA {k}": ratio >= v for k, v in AA.items()} | {
        f"AAA {k}": ratio >= v for k, v in AAA.items()}


def report(foreground: str, background: str) -> str:
    ratio = contrast_ratio(foreground, background)
    passed = [k for k, ok in verdicts(ratio).items() if ok]
    return (f"{foreground} on {background}: {ratio:.2f}:1 — "
            + (", ".join(passed) if passed else "fails every threshold"))


def self_test() -> int:
    """Controls first: the harness must be shown able to FAIL before a pass counts.

    The boundary pair is the real control — #767676 passes 4.5:1 on white and
    #777777 misses it. An implementation wrong in the luminance curve still gets
    black/white right, so the extremes alone would prove nothing.
    """
    cases = [
        ("#000000", "#FFFFFF", 21.00, "max possible ratio"),
        ("#FFFFFF", "#FFFFFF", 1.00, "min possible ratio"),
        ("#767676", "#FFFFFF", 4.54, "boundary: passes AA normal text"),
        ("#777777", "#FFFFFF", 4.48, "boundary: FAILS AA normal text"),
        ("#FFF", "#000", 21.00, "3-digit hex expands"),
    ]
    failures = 0
    for fg, bg, expected, why in cases:
        actual = contrast_ratio(fg, bg)
        ok = abs(actual - expected) < 0.01
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {fg}/{bg} = {actual:.2f} "
              f"(expected {expected:.2f}) — {why}")
    if contrast_ratio("#767676", "#FFFFFF") < 4.5 or contrast_ratio("#777777", "#FFFFFF") >= 4.5:
        print("  [FAIL] the boundary control did not discriminate at 4.5:1")
        failures += 1
    print("self-test:", "PASS" if not failures else f"{failures} FAILURE(S)")
    return 1 if failures else 0


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 0
    if argv[0] == "--self-test":
        return self_test()
    for pair in argv:
        try:
            fg, bg = (part.strip() for part in pair.lower().split(" on "))
            print(report(fg, bg))
        except ValueError as exc:
            print(f"{pair!r}: {exc} (expected '#FG on #BG')")
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
