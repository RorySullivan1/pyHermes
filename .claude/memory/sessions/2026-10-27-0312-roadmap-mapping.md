# 2026-10-27 03:12 · roadmap-mapping

**Goal:** Map the owner's 2026-10-27 roadmap doc into .meta/roadmap and install the factory's roadmap kit

## What happened
- A scoping review with the owner chose an identity: research publishing (B), email first (C), a model
  as author (E), an app only on demand. A generic "reporting framework" was rejected: Quarto owns it, and
  pyHermes is the render stage without the run, data and distribution layers around it.
- The plan was written as a Claude Docs roadmap (five phases, 31 epics, four gates), then mapped here with
  `/roadmap-set`: phases are stages 00-04, each epic one version. Stages 00 and 01 have cards
  (v0.2.0-v0.11.0); 02-04 are sketches in their STAGE.md, as the development-mapping skill says.
- The factory's roadmap kit was copied from claudeBrain's example-project: the `development-mapping`
  skill, `/roadmap-set`, `/roadmap-status`, `advance-roadmap-step`, `roadmap_status.py` with its
  SessionStart fragment, and `roadmap_guard.py`, registered in `git_guards.py` rather than as a fragment.
- Supporting: CLAUDE.md points at the roadmap; `.claude/README.md` and the hooks README no longer say
  the roadmap system was left out; the catalog was regenerated; the memory index was archived to budget.

## Gotchas & dead ends
- The branch was behind main by #475's merge; it was restarted from origin/main before any change.
- `pip install -e .[dev]` fails on Debian's httplib2 (no RECORD) and pip and python differ here: use
  `python -m pip install --ignore-installed httplib2 -e ".[dev]"`.
- `roadmap_guard` ignores an INDEX row whose version cell is not a single label, so the sketch rows
  (`v0.12.0–v0.20.0`) are invisible to it by design.

## State at end
- Roadmap live, cursor v0.2.0 (the scope charter). Six owner decisions open, listed in the INDEX.
- pytest, ruff, ruff format and mypy clean. Shipped as one PR onto main.

## Open threads
- The six roadmap decisions; then `advance-roadmap-step` on v0.2.0.
- The Claude Docs copy is the owner's; the repo copy is the one agents trust.
