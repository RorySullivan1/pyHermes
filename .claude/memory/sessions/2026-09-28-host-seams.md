# 2026-09-28 · host-seams

**Goal:** Develop and implement epic #238 (seams for a host application).

## What happened
- Branch `claude/integrate-claude-assets-pyhermes-d4spzb` restarted from `main` @ `3fd3d65` after
  PR #235 merged. One commit per child, in the epic's order.
- #246: the four `print` sites became `SizeWarning` / `PrintQualityWarning` (both `UserWarning`s,
  exported from `svc.builder`), the "OK" line is gone, and an AST test holds `svc/` print-free.
  `warn_caller` walks out of `svc` to name the caller's line.
- #249: `get_config()` reads a `ContextVar` over the `set_config` default; `config_override` takes
  a whole `Config` too; `config=` on every `Document` class, `EmailBuilder` and `build_message`.
- #247: `template_overlay=` on the same classes; `TemplateEngine(overlays=)` searches them first.

## Gotchas & dead ends
- **A fixed `stacklevel` cannot name the caller**: one check is reached through `render()`,
  `Email.render()`, `EmailBuilder.render()` and a brochure constructor. The first draft was off by
  one (the start frame is level 2, not 1); the test asserting the warning's filename caught it.
- **Proved the thread test bites** by swapping `_context` for a shared object: both thread tests
  fail with the old semantics.
- `mypy` on PATH here is another environment's and cannot see jinja2; use `python -m mypy`.
- Adding `config` and `template_overlay` lines pushed three class docstrings over the 28-line cap;
  the two args share one line, and the fork how-to now lives only in `media.md`.
- The PDF byte-determinism tests still flake here (no HarfBuzz-Subset); nothing else fails.

## State at end
- Three commits pushed; every golden byte-identical. No PR opened (not asked for).
