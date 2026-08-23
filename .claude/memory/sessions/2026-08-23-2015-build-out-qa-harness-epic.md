# 2026-08-23 20:15 · build-out-qa-harness-epic

**Goal:** Build out epic #54 (preview & QA harness) into filed, linked sub-issues.

## What happened
- Filed and GitHub-linked six sub-issues under #54, and rewrote the epic body's "planned breakdown" into the filed dependency list:
  - **#57 fixture gallery** — deterministic builder-code fixtures (`kitchen_sink()` / `image_matrix()` / `minimal()` + registry). Foundation for everything else. Carries the *component completeness test*: every public `Component` subclass must appear in `kitchen_sink()` (introspected, not hand-listed) — the enforcement teeth for the future "new component joins the gallery" rule.
  - **#58 golden snapshots** — pins HTML + asset manifest per fixture; regeneration only via explicit `--update-goldens`; diagnosable failure output. **Hard rule written into the issue: #58 and #32 resolve to ONE snapshot harness** — whichever lands second reuses, never duplicates; the resolution must be recorded on #32.
  - **#59 screenshot runner** — Playwright/Chromium at pinned desktop + ~375px mobile viewports (exercises the `.kpi-cell` collapse), CI artifacts on every PR. Playwright lives in a separate `[qa]` extra so `[dev]` stays browser-free; screenshots named `chromium-*` to state fidelity honestly (approximates Gmail, never Outlook).
  - **#60 lint pass v1** — parse-don't-grep; rules: `img-width-attr`, `img-alt`, `outlook-css` (small, *sourced* denylist), `no-external-css`, `size-budget` (per-section byte breakdown extending — not reshaping — `_validate_size`, which is a `@staticmethod` with message-asserting tests). Must *land green*: fix/file findings before merging the linter.
  - **#61 preview CLI** — `preview <fixture>` / `module.py:callable`, `--lint/--screenshot/--open/--list`; composes #57/#59/#60, reimplements nothing; builder errors exit cleanly.
  - **#62 docs** — replaces the "no end-to-end smoke test, eyeball by hand" CLAUDE.md paragraph; states the three standing rules (component joins gallery; golden diff = intended visual change; screenshots ≈ Gmail, lint owns Outlook).
- Dependency shape: #57 → (#58 ∥ #59 ∥ #60) → #61 → #62.
- No code changed; issues + memory only.

## Gotchas & dead ends
- The #32/#58 overlap is the one coordination hazard in this epic: #32 (epic #38's golden test) and #58 describe the same mechanism at different widths. Both issues now point at each other; do NOT let two snapshot harnesses appear.

## State at end
- Four active epics with sub-issues (#38, #45, #46, #54), four deferred parents (#52, #53, #55, #56).
- Natural next implementation PR: #57 (+ resolving #32 via #58's harness).

## Open threads
- When #57 starts, decide fixture-package placement (`qa/` top-level vs `tests/fixtures/`) based on whether the preview CLI ships in the wheel — #61 inherits the decision.
