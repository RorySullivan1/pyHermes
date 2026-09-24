# 2026-09-24 · sync-claudebrain-assets

**Goal:** Bring pyHermes' `.claude/` up to date with claudeBrain (`example-project/.claude/`), keeping pyHermes as the main repo.

## What happened
- Classified every differing file by hashing ours against the factory's git history: a match = stale
  copy (took upstream); no match = pyHermes adaptation (3-way `git merge-file` against the nearest
  factory blob). The two agents, `git_guards.py` and `settings.json` had no upstream change since
  their base, so they are unchanged. Three README conflicts resolved by hand, keeping our prose.
- Added, by fit to a Python email/document/brochure builder: skills `weasyprint-print-html`,
  `outlook-html-specifications`, `brochure-builder`, `pamphlet-builder`, `one-pager-builder`,
  `deck-builder`, `factsheet-template`, `technical-documentation-drafter`, `user-guide-drafter`;
  agents `outlook-html-designer`, `presentation-architect`, `prose-auditor`, `data-analyst`;
  commands `/epic`, `/issue`, `/prose-review`; workflow `establish-verification` + a pyHermes
  `context/verification-surface.md` (all rows `—`: claimed, not yet proved).
- Installed the `installs.json` byte-copies: `.github/ISSUE_TEMPLATE/{epic,task,bug,feature}.md`,
  `.github/pull_request_template.md`, `.github/workflows/epic-autoclose.yml`.
- Left out, as before: VBA/VSTO/PowerApps/SharePoint/Power BI/Graph, the roadmap layer
  (`development-mapping`, `roadmap_*` hooks, commands, `advance-roadmap-step`), `hooks/probes/`.

## Gotchas
- The new `prose_budget.py` keys a comment run by a content hash, not an ordinal. 17 baseline keys
  were re-keyed one-for-one (same reasons, same line counts, count still 45) — a migration, not growth.
- `outlook-html-specifications`, `outlook-html-designer` and `prose-auditor` name `vba-development`
  as a boundary; it is not installed here, so treat those as "out of scope" pointers.
