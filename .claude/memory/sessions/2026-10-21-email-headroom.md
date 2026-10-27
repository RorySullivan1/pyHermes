# 2026-10-21 — kitchen_sink headroom: the email medium strips its indentation

**Trigger:** the thread "`kitchen_sink` is at its 90 KB ceiling" (`modern_fonts` 357 bytes under the warning).

## Decision (owner, at the start)
Three options were put to the owner, with numbers:
1. strip each line's indentation in every email (recommended);
2. move the three wide ThreeColumn ratios out of `kitchen_sink`;
3. both.

**Owner chose option 1.** Option 2 freed about the same (~8 KB) for the fixture alone, and lost those
ratios' density and font A/Bs. Option 1 gives every user's email 6–23% back.

## What changed
- `Medium.finishers`: transforms run over the composed document *before* the constraints.
  `Document.render` and `rendered_sections()` both run them.
- The email medium's one finisher is `strip_indentation` (`pyhermes/email/medium.py`):
  - it strips each line's leading and trailing spaces and tabs, and drops blank lines;
  - every newline stays;
  - `pre` and `textarea` pass through whole.
  Every other medium has none.
- Sizes: `kitchen_sink` 90,907 → 82,484 bytes; `modern_fonts` 91,803 → 83,380, i.e. 8,780 bytes under 90 KB.

## How it was proved
- **Screenshots:** 48 of 48 pixel-identical (24 email fixtures × 1000/375px, golden against new render).
- **Lint:** no finding moved in any fixture.
- **Goldens:** the 24 email HTML goldens moved, and nothing else (no text, asset, paged, brochure or
  deck golden). Their diff is empty under `git diff -w --ignore-blank-lines`.
- **Equivalence:** an email with the finisher removed equals the old golden byte for byte.
- **Test teeth:** running the size check before the finisher turns
  `test_the_size_check_measures_the_finished_markup` red.

## Tests touched
Four tests compared a standalone render with an email's: hosted figure, aside, pull quote, button.
Each now finishes the expected side the same way, which keeps its claim.

## Container notes
- The digital-PDF determinism tests fail here on `main` too: no HarfBuzz-Subset, so fontTools stamps
  the clock. They pass with the clock pinned.
- The `mypy` on PATH lacks jinja2; `python3 -m mypy` is clean.
