---
description: Show where the project is on its development map — the cursor version, what's shipped, and what's next.
argument-hint: (none)
---

You are reporting the project's position on its **development map**. Read-only — change nothing.

## 1. Read the map and the cursor
- `.meta/roadmap/INDEX.md` — the objective, stages, and the version status table.
- `.meta/version` — the version currently in flight (the live cursor) and its `status`/`pr`.

If `.meta/roadmap/` doesn't exist, say so and point to `/roadmap-set` to create one.

## 2. Reconcile
Cross-check the two: the `in-progress` row in INDEX should match `.meta/version`. Flag any
drift (e.g. INDEX says v0.2.0 in-progress but `.meta/version` is v0.3.0, or a PR is merged
but the row still says `in-progress`).

## 3. Report
A tight status, not a transcript:
- **Objective** — one line.
- **Done** — shipped versions (with PR links if present).
- **Now** — the cursor version, its goals, and its `status`/PR.
- **Next** — the next 1–2 planned versions and their one-line goals.
- **Drift** — anything to reconcile, with the fix (`/roadmap-set` to re-slice, or update a
  status), if applicable.
