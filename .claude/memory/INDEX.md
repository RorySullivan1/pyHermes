# MEMORY INDEX  ·  keep ≤ ~80 lines, ≤ ~200 chars per line

## State            (rewrite in place — current truth only, ≤ ~10 lines)
- pyHermes builds and sends: `svc/builder` → `svc/delivery` → `svc/gmail` / `svc/outlook`.
  Architecture and rationale live in CLAUDE.md — do not restate them here.
- `main` @ `e56d214` (PR #131, epic #124 + #129/#130/#132/#133). Working branch
  `claude/review-open-issues-rr8quq`, no PR open yet.
- Every epic filed before 2026-08-29 is complete and every issue up to #133 is closed.
- Open: epic #134 (prose discipline, #135–#139) and epic #140 (`.claude/` self-restriction,
  #141–#145). #141, #142 and #135 are done on the working branch.
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
  evasion, not the count — sessions/ARCHIVE-2026.md.

## Threads          (open items; remove when closed)
- **Epic #134** — prose discipline. #135 done (caps, baseline, gate). Next: #136 split
  CLAUDE.md, #137 stop shipping comments in the email, #138 rewrite `svc/`, #139 `qa/`.
- **Epic #140** — `.claude/` self-restriction, portable so claudeBrain can repackage.
  #141 (standard) and #142 (hook) done. Open: #143, #144 router, #145 `context/` precedence.
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
