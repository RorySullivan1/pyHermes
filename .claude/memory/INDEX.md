# MEMORY INDEX  ·  keep ≤ ~80 lines, ≤ ~200 chars per line

## State            (rewrite in place — current truth only, ≤ ~10 lines)
- pyHermes builds **documents** and renders each onto a **medium**: `svc/builder` is the
  shared kit, `svc/email` and `svc/document` are the two media, and three exporters sit on
  one contract — `svc/delivery`+`gmail`+`outlook`, and `svc/pdf`. Rationale: CLAUDE.md and
  `.claude/rules/media.md`; do not restate it here.
- **Epic #157 (rescope to media) is SHIPPED** — PR #167 merged to `main` at `eff6ece`;
  #157 and #158–#166 all closed. Phases 1–4 shipped golden-identical.
- **Epic #153 (per-exhibit disclosure) is COMPLETE** — #154–#156, open as PR #168
  (https://github.com/RorySullivan1/pyHermes/pull/168), not yet merged.
- Only **#150** (banner VML `src`, needs a real Outlook host) is left open.
- The prose budget is live; the baseline is 45 and may only shrink.

## Decisions        (append-only; supersede, never delete)
- Older entries, and epic #157's, are in sessions/ARCHIVE-2026.md.

- [2026-09-17] **A medium is a product, not a fourth design axis — but it rides the binder
  as the fourth keyword.** Theme/size/font leave the structure untouched; a medium changes
  skeleton, slot set, frame, constraints, lint and exporter, so it is chosen by class, then
  bound so templates can ask `medium.paged` — sessions/2026-09-17-2353-multi-medium-rescope.md

- [2026-09-21] **GitHub closing keywords do not cascade to sub-issues.** `Closes #157` closed
  the epic and left all nine children open; a bare `#158` in a PR table cross-links but never
  closes. An epic PR lists `Closes` once per sub-issue —
  sessions/2026-09-17-2353-multi-medium-rescope.md

- [2026-09-21] **`disclosure` is plain text; the blessed raw-HTML set stays closed at five.**
  No inline link, deliberately: widening plain text to HTML later is additive, narrowing is
  not — sessions/2026-09-21-per-exhibit-disclosure.md
- [2026-09-21] **A template may fix an alignment the caller-facing axis does not offer.**
  `justify` sets the disclosure; `TextAlign` still excludes it, and a test pins that, because
  widening a guard without pinning what it forbids turns it into a comment —
  sessions/2026-09-21-per-exhibit-disclosure.md

## Threads          (open items; remove when closed)
- **PR #168 is open; after it merges the only open issue is #150.** Every issue or PR body
  in this repo is written without angle brackets — GitHub's sanitizer has emptied three.
- **A closing keyword closes only the issue it names.** An epic PR needs one `Closes #N` line
  per sub-issue, not just the epic's — #168 does; #167 did not, and its nine children stayed
  open. Check the parent's `sub_issues_summary` after any epic merge.
- **Two optional extras now.** `[pdf]` (WeasyPrint, needs Pango/Cairo) and `[qa]` (Playwright
  + pypdfium2). `[dev]` alone must stay free of both; their tests skip, which is the proof.
- **CLAUDE.md is a router**; the detail is in path-scoped `.claude/rules/*.md`, which load
  only when a matching file is read. Add reasoning there, not back into the router.
- **Factory hand-off for #140 is in `.claude/README.md`** — what claudeBrain should take,
  and the four rules worth inheriting.
- **The baseline may only shrink.** #138 and #139 empty it; nothing may be added.
- **Everything in `.claude/` is a factory asset** except `agents/python-developer.md` and
  `agents/finance-quantitative-developer.md`. No project name may enter the others.

## Log              (append-only pointers)
- Older entries, and epic #157's, are in sessions/ARCHIVE-2026.md.
- [2026-09-20] **A check can be wrong about its scope, and fixing the code instead is the
  trap.** Four times in one epic: the theme test scanned one module, the golden harness made
  one directory, `page.html` used the wrong colour idiom, and a README-block check would have
  demanded prose parse as Python — sessions/2026-09-17-2353-multi-medium-rescope.md


- [2026-09-21 03:40] multi-medium-rescope — **PR #167 merged** (`eff6ece`). #157 closed by the
  keyword; #158–#166 had to be closed by hand, because closing a parent does not close its
  children — sessions/2026-09-17-2353-multi-medium-rescope.md

- [2026-09-21] per-exhibit-disclosure — **epic #153 complete** (#154–#156): the shared partial,
  the field on three exhibits, both projections, four fixtures, and `disclosure.md`. Fifth
  instance of *a check can be wrong about its scope*, and the first fixed by widening one —
  sessions/2026-09-21-per-exhibit-disclosure.md
