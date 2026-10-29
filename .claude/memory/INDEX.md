# MEMORY INDEX  ·  keep ≤ ~80 lines, ≤ ~200 chars per line

## State            (rewrite in place — current truth only, ≤ ~10 lines)
- pyHermes builds **documents** onto **media** (`email`, `document`, `brochure`, `deck`) from the shared
  `pyhermes/builder` kit; exporters: `delivery`+`gmail`+`outlook`, and `pdf`. Rationale: CLAUDE.md, `media.md`.
- **Shipped through PR #475** (#474); epics #157–#442 all closed, no issues open. #219 DOCX and #300 PPTX
  closed as not planned. #288 is the owner's Outlook-desktop check. The prose baseline is 43, may only shrink.
- **The roadmap is live** in `.meta/roadmap/` (5 stages, 31 epics), surfaced each session by `roadmap_status`;
  v0.2.0 shipped (PR #477); v0.3.0 (reference reports, benchmark) in PR #478; cursor v0.4.0. The owner's six decisions are taken. Mapped from the 2026-10-27 doc — sessions/2026-10-27-0312-roadmap-mapping.md

## Decisions        (append-only; supersede, never delete)
- Older entries, and epic #157's, are in sessions/ARCHIVE-2026.md.
- [2026-10-01] **pyHermes grows by media, not by portability.** A DOCX/PPTX walk is a second render path
  over 46 classes, and a chart is PNG bytes by the time it is in the tree; #219 and #300 closed — `media.md`
- [2026-10-14] **`layout()` returns a `Layout` carrying its profile and document; `render_layout`/`save_layout` take
  no profile (#445); preview lays out once and hands the one layout to lint, PDF and screenshots (#446)** — `media.md`,
  `qa-harness.md`
- [2026-10-14] **A directly built `EmailImage` is validated like a factory's, `mime_type` held to the sniffed bytes
  (#447); the PDF exporter refuses a relative URL by name through a sentinel base URL (#463); every number a layout
  reads is finite, a table cell's NaN still meaning missing (#450); formatters round in a context of their own (#448)**
  — `builder-architecture.md`, `media.md`, `data-layer.md`
- [2026-10-21] **A hosted figure joins the walk through `Component.hosted()`, not `children()` (#454); a deck refuses
  a Slide added twice (#462); a handout is one page a sheet and clipped notes are a lint warning (#459); a running
  header and footer may not share a margin box (#461); `render_math` draws under `rcdefaults()` (#467)** — `apparatus.md`,
  `deck.md`, `media.md`, `math.md`
- [2026-10-27] **pyHermes is a research-report generation framework: research publishing (B) is the identity,
  email (C) the first thing to master, a model as author (E) the access point; an app only on demand. No new
  medium or layout primitive without a reference report that needs it** — `.meta/roadmap/INDEX.md`
- [2026-10-27] **The six roadmap decisions: reference reports a mix (real daily email and product piece,
  `quarterly-review` standing in for long-form); open core (library MIT, service separate); deck kept, frozen;
  DOCX/PPTX closed until 2.5; content model in core; 2.1 spike before v0.7.0** — `.meta/roadmap/INDEX.md`
- [2026-10-28] **Superseded in part: the reference reports are all three stand-ins until Gate 1** (owner),
  in `reference/`; Gate N is stage N's milestone — `.meta/roadmap/INDEX.md`, `reference/README.md`

## Threads          (open items; remove when closed)
- **The first outside user is not yet named** (a colleague or team); needed before Gate 1 — `.meta/roadmap/INDEX.md`.
- **#394's ruling (justify on paper only) was taken under a goal**; the owner may widen it.
- **#400's ruling: `skip_first` is opt-in, not the default under an `EmptyCover`** (goal-taken; `media.md`).
- **A share table holds its share in Word's engine** (owner, via COM, PR #371); a real Outlook client
  is still #288's. The measure is `ch`: in Georgia 75ch sets ~99 characters (`design-axes.md`).
- **Outlook desktop's handling of `dir=rtl` on a reversed split is unverified here**, nor #319's VML
  arrow (or #399's connector), nor #325's square badge and dot, nor #331's empty rule cells (`font-size:0`), nor #337's legend
  swatch; all join #288's check.
- **The suite runs on Windows since #372** (PR #371); no Windows CI job — the owner's run is the check.
- **`epic-autoclose` works** (closed #273, #354, #361, #346, #324, #329, #335). Still confirm each epic closed after its merge.
- **In this container, PDF byte-determinism tests flake** (no HarfBuzz-Subset), and screenshot
  tests skip unless `PYHERMES_CHROMIUM=/opt/pw-browsers/chromium-1194/chrome-linux/chrome`.
- **Every issue or PR body is written without angle brackets** — GitHub's sanitizer has
  emptied three.
- **A closing keyword closes only the issue it names, and this is now proven both ways.**
  #167 named only the epic and left all nine children open; #168, #191 and #192 named every
  issue and closed every one. One `Closes #N` per sub-issue, and check that summary after
  any epic merge.
- **Six optional extras:** `[pdf]`, `[qa]`, `[data]`, `[charts]`, `[math]`, `[qr]` (#344; `zxing-cpp` joined
  `[qa]` as the decoder). `[dev]` alone stays free of
  them; CI's `all-extras` fails on any skip naming one (#239), so a skip reason must name its extra.
- **CLAUDE.md is a router**; the detail is in path-scoped `.claude/rules/*.md`, which load
  only when a matching file is read. Add reasoning there, not back into the router.
- **Factory hand-off for #140 is in `.claude/README.md`** — what claudeBrain should take,
  and the four rules worth inheriting.
- **The baseline may only shrink.** #138 and #139 empty it; nothing may be added.
- **Everything in `.claude/` is a factory asset** except `agents/python-developer.md` and
  `agents/finance-quantitative-developer.md`. No project name may enter the others.

## Log              (append-only pointers)
- Older entries, and epic #157's, are in sessions/ARCHIVE-2026.md.
- [2026-10-13] delivery-contract — epic #418 merged in PR #438, all six children closed — sessions/2026-10-13-delivery-contract.md
- [2026-10-14] render-once — epic #419 merged in PR #440, all three children closed — sessions/2026-10-14-render-once.md
- [2026-10-14] codebase-review-issues — 27 issues: epic #442 (4) and bugs #447–#468, every one re-probed — sessions/2026-10-14-codebase-review-issues.md
- [2026-10-21] email-headroom — the email strips its indentation (owner's pick over moving ratios): `kitchen_sink` 82.5 KB, 8.8 KB under the warning — sessions/2026-10-21-email-headroom.md
- [2026-10-27] roadmap-mapping — the owner's roadmap doc mapped to `.meta/roadmap/` with the factory's
  roadmap kit (skill, two commands, workflow, two hooks); index trimmed to budget — sessions/2026-10-27-0312-roadmap-mapping.md
- [2026-10-28] scope-charter — v0.2.0 through advance-roadmap-step: positioning sentence, standing rule 14 and
  `test_scope_freeze.py`; review closed two bypasses; goal-auditor PASS; PR #477 — sessions/2026-10-28-0900-scope-charter.md
- [2026-10-28] scope-charter — PR #477 merged; v0.2.0 marked shipped in the roadmap and `.meta/version`.
- [2026-10-29] reference-reports — v0.3.0: `reference/` (three stand-ins), `qa.benchmark` and its baseline;
  review had no must-fix; goal-auditor PASS; PR #478 — sessions/2026-10-29-0900-reference-reports.md
