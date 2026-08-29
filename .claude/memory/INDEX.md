# MEMORY INDEX  ·  keep ≤ ~80 lines, ≤ ~200 chars per line

## State            (rewrite in place — current truth only, ≤ ~10 lines)
- pyHermes builds and sends: `svc/builder` → `svc/delivery` → `svc/gmail` / `svc/outlook`.
  Architecture and rationale live in CLAUDE.md — do not restate them here.
- `main` @ `e5c587a` — **PR #146 merged**, closing epics #134 and #140 (twelve issues).
  No branch open; the issue backlog is empty.
- Every epic filed before 2026-08-29 is complete and every issue up to #133 is closed.
- **Epics #134 and #140 are COMPLETE.** Every issue up to #146 is closed.
- The prose budget is live: caps in `.claude/prose-budget.json`, 110 baselined locations in
  `qa/prose_baseline.json`, gate in `tests/test_prose_budget.py`.

## Decisions        (append-only; supersede, never delete)
- Entries before 2026-08-27 are in sessions/ARCHIVE-2026.md.
- [2026-08-27] **Parity of fields, not of tokens.** The two boxes fall back to different theme tokens and keep their own `theme_context()`; forcing … — sessions/2026-08-27-2130-footer-box-epic.md
- [2026-08-27] **Keep the `&copy;` ENTITY in the default copyright.** A bare U+00A9 mis-decoded as latin-1 renders as a mojibake pair — the failure … — sessions/2026-08-27-2130-footer-box-epic.md
- [2026-08-27] **`{% endif +%}` disables `trim_blocks` for one tag** — needed to keep a newline after an inline conditional, which is how the link … — sessions/2026-08-27-2130-footer-box-epic.md
- [2026-08-27] **Reconcile a stale epic in a COMMENT, not by rewriting its body.** #98 was filed before PR #86 and described a two-slot footer with a … — sessions/2026-08-27-2130-footer-box-epic.md
- [2026-08-27] **Re-measure an issue's stated motivation before acting on it.** #98 warned a coloured footer would paint a wrapper-level band (it is … — sessions/2026-08-27-2130-footer-box-epic.md
- [2026-08-28] **Decide a `# noqa`'s fate by deleting it and re-running, never by reading it.** `tests/test_theming.py:763` carried `# noqa: <prose>` … — sessions/2026-08-28-2014-fix-invalid-noqa.md
- [2026-08-29] **A line cap on unbounded lines is not a cap.** This index obeyed "≤ ~80
  lines" at 256 lines and ~22,900 tokens against a stated ~600 — the width was the
  evasion, not the count — sessions/2026-08-29-1628-asset-self-restriction.md.
- [2026-08-29] **Reachability, not scope, makes a home canonical.** A brief nothing loads
  is not a fallback, it is an uncorrectable second copy — and it is the stale one —
  sessions/2026-08-29-1628-asset-self-restriction.md.
- [2026-08-29] **Measure per-session context cost, not repo lines.** #140 added +465 lines
  and made every session 215 lines cheaper —
  sessions/2026-08-29-1628-asset-self-restriction.md.

## Threads          (open items; remove when closed)
- **CLAUDE.md is a router**; the detail is in path-scoped `.claude/rules/*.md`, which load
  only when a matching file is read. Add reasoning there, not back into the router.
- **Factory hand-off for #140 is in `.claude/README.md`** — what claudeBrain should take,
  and the four rules worth inheriting.
- **The baseline may only shrink.** #138 and #139 empty it; nothing may be added.
- **Everything in `.claude/` is a factory asset** except `agents/python-developer.md` and
  `agents/finance-quantitative-developer.md`. No project name may enter the others.

## Log              (append-only pointers)
- Entries before 2026-08-28 are in sessions/ARCHIVE-2026.md.
- [2026-08-28 20:14] fix-invalid-noqa — converted the malformed `# noqa:` at `tests/test_theming.py:763` into a plain explanatory comment after … — sessions/2026-08-28-2014-fix-invalid-noqa.md
- [2026-08-28 20:35] datatable-epic — shipped **#119** (row kinds). The design line worth keeping: **a row's kind is chrome, a cell's colour is … — sessions/2026-08-28-1940-datatable-epic.md
- [2026-08-28 21:00] datatable-epic — shipped **#120**. First step in the epic whose goldens *move* (20 lines, 7 files), and the diff is three things … — sessions/2026-08-28-1940-datatable-epic.md
- [2026-08-28 21:30] datatable-epic — shipped **#121**, closing **epic #116**. The field-completeness test is the durable part: it closes a gap the … — sessions/2026-08-28-1940-datatable-epic.md
- [2026-08-28 22:00] datatable-epic — opened **PR #123** for #114 + epic #116, then merged `main` into it after **PR #122** landed underneath …
- [2026-08-29 16:28] asset-self-restriction — **epic #140 complete** (#141–#145) plus #135; the library now bounds the prose it was teaching — sessions/2026-08-29-1628-asset-self-restriction.md
- [2026-08-29 20:30] prose-discipline — **epic #134 complete** (#136–#139) and **PR #146 merged** at `e5c587a`: CLAUDE.md 2,045 -> 160, 2,049 comment bytes off every email, baseline 110 -> 48 — sessions/2026-08-29-1628-asset-self-restriction.md
