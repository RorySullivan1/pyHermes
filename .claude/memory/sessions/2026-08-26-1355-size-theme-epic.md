# 2026-08-26 13:55 · size-theme-epic

**Goal:** Execute epic #45 (size themes) end to end: #39-#44

## What happened

Six sub-issues, six commits, one branch (`claude/review-open-issues-rr8quq`), each step
leaving the suite / ruff / mypy green and **all six pre-existing goldens unregenerated**.

- **#39 — `svc/builder/sizing.py`.** Audited every size literal in the 20 templates first;
  the audit table (token → value → sites) is the module docstring and is re-asserted by a
  test that also fails if a *new* token never joins it. Four frozen layers — `TypeScale`,
  `SpacingScale`, `ComponentScale`, `FrameGeometry` — composed into `SizeScheme`, plus
  `SizeTheme` in `enums.py`. Nothing imported it; zero rendered change.
- **#40 — `EmailMetadata.size_theme`,** resolved once in `Email.render()` and bound onto the
  **existing** `BoundEngine` alongside the theme. No container/component/region signature
  changed. `TemplateEngine.render` now layers `STANDARD_SIZES` under the caller's context,
  the same floor the theme already had.
- **#41 — the migration.** ~200 literals across 20 templates, applied as *counted* exact
  substitutions (a script that asserts each old string's occurrence count and writes only if
  every edit matched). Goldens green after every batch.
- **#42 — the geometry.** `column_layout()` in `sizing.py`; the eight per-ratio templates
  collapsed to one `columns.html`.
- **#43 — `COMPACT_SIZES` / `SPACIOUS_SIZES`,** written as `SizeScheme().derive(...)` so the
  diff *is* the design, plus two gallery fixtures. Desktop screenshot heights: 2516 /
  3030 / 3731 px for the same email.
- **#44 — docs:** a `### Sizing` section in CLAUDE.md at the same altitude as `### Theming`,
  standing rule 5 (no hardcoded px, four named exceptions), a reframed "not parameters,
  deliberately", a README `## Size` section, and a wheel-job smoke assertion that a size
  theme actually moves column geometry from a clean install.

## Gotchas & dead ends

- **The eight container templates were byte-identical apart from a Jinja comment and the
  numbers.** `sed -E 's/[0-9]+/N/g'` + `diff` proved it in one command, and that finding is
  what turned #42 from "tokenise eight files" into "delete seven of them". Check this before
  assuming per-file duplication carries per-file decisions.
- **195/194/195 is not floor+leftmost and not largest-remainder-by-index.** The odd pixels go
  to the *outer* columns. `_remainder_order(n)` = `[0, n-1, 1, n-2, …]` reproduces it, and
  Python's stable `sorted` is what keeps that order for the equal-fraction case.
- **The column padding threshold (300px) had to be *recovered*, not invented.** 300 and 420
  carried 20px; 292 and smaller carried 16. Nothing wrote it down.
- **`9.5px` is a real size**, so "px values must be ints" (the issue's wording) was wrong. The
  rule that actually prevents `font-size:14.0px` is: positive `int`, or a **non-integral**
  `float`. Ints render as ints; 9.5 renders as 9.5.
- **A sentinel scheme is the only way to prove a token is *wired*.** A migration that
  replaces a literal with a token nothing reads is byte-identical and completely inert.
  Rendering `kitchen_sink` under a scheme where every token is a distinct number, parametrized
  per token, names the one that never arrived. Two traps in building it: `FrameGeometry`
  validates `pad_x*2 < width` and `breakpoint > width` (so sentinel frames need shaping), and
  `narrow_column` must sit between the computed column widths or one of the two column
  paddings goes untested.
- **`kitchen_sink` cannot set `size_theme` to a non-default.** It *is* the epic's
  byte-identity reference. The completeness test needed a named `ANCHORED_TO_THE_DEFAULT`
  exemption, with the distinctive value living in `compact_size` / `spacious_size` — the same
  shape #50 used with `slate_theme` for the palette.
- **The golden harness's own drift test broke** because it perturbs `width="680"` in
  `base.html`, and after #42 there is no width literal left to perturb. Re-anchored on
  `align="center"`.
- **Screenshots need `PYHERMES_CHROMIUM`** here: Playwright looks for
  `chromium_headless_shell-1234` and the machine has `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`.
- Shell `cwd` silently persisted from an earlier `cd` into `svc/builder/templates` and made a
  migration script find zero files (empty dict → `KeyError`). Scripts that write files should
  assert they found their inputs.

## State at end

- **PR #83 merged to `main` (`1105532`) at 2026-08-26 20:47**, closing #39–#44 and epic #45
  at 6/6. Branch reset to `main`; 1179 passed / 7 skipped on merged main, ruff + mypy clean,
  eight golden fixture pairs present.
- Gallery is **eight** fixtures; `svc/builder/templates/common/containers/` is **two** files.
- Zero scale-participating px literals in any template; four named exceptions remain.

## Open threads

- #76 is now *themed*: the mobile `.kpi-cell` overflow scales with density (383 / 387 / 395 px
  at a 375px viewport). The fix is still one `box-sizing` rule in `base.html`, not per-theme.
- #78 unchanged by this epic.
- #53 (plain-text) and #56 (typography) are the remaining parents, both previously blocked on
  #45 and now unblocked.
