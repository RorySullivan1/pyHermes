# MEMORY INDEX  ·  keep ≤ ~80 lines, ≤ ~200 chars per line

## State            (rewrite in place — current truth only, ≤ ~10 lines)
- pyHermes builds **documents** and renders each onto a **medium**: `pyhermes/builder` is the
  shared kit, `pyhermes/email`, `document`, `brochure` and `deck` are the media, and exporters sit on
  one contract — `delivery`+`gmail`+`outlook`, and `pdf`. Rationale: CLAUDE.md and `media.md`.
- **Shipped through PR #371; nothing is in flight.** Epics #157–#220 and #218 (PRs #167–#314); deck bugs
  #315–#317 (PR #369); #361 (PR #370); #354 and #372 (PR #371). #219 DOCX closed not planned, with #300 PPTX.
- **Open: six content epics, filed 2026-10-01 against `59be201`.** Order: **#318** glance objects first
  (#319 arrow probe → #320 → #321; #322 HeroStat; #323) — #346 deck layouts needs #322, and #324 badges
  reuses #319's shape call; then #346, #324, #329 and #335 (independent); #340 last (three WeasyPrint
  probes, the `[qr]` extra). #288 is the owner's Outlook-desktop check, run on Windows.
- The prose budget is live; the baseline is 44 and may only shrink.

## Decisions        (append-only; supersede, never delete)
- Older entries, and epic #157's, are in sessions/ARCHIVE-2026.md.
- [2026-09-28] **A config travels with the work: explicit, then context, then default.** A `ContextVar`
  over `set_config`; a new thread starts from the default. Soft limits are warnings — `config.md`
- [2026-09-29] **The import root is `pyhermes` alone**; the `svc` shim was removed (#255) before any
  release shipped it. Checks read the built wheel and sdist, never the tree — `working-in-the-code.md`
- [2026-09-30] **A composite is a component; the document walks leaves, containers the top level.** So a
  composite delegates images and reports no notes of its own — `builder-architecture.md` (#261)
- [2026-10-01] **A section's ground rebinds the theme for its subtree; a block that paints its own surface
  resets it and, on a ground, sits on the theme's surface** — `design-axes.md` (#265)
- [2026-10-01] **The lint rules are product behaviour and ship as `pyhermes.check`; the gallery stays test
  data. Desktop Outlook is drafts only, never send** — `qa-harness.md`, `delivery.md` (#277)
- [2026-10-01] **An oversize-picture threshold must clear the package's own deliberate density: equations at
  4x, print at 3.125x. So 4.5, not 3** — `data-layer.md`, `config.md` (#276)
- [2026-10-01] **The size report attributes bytes from the section tree, never new comments; `SizeError`
  carries the refused HTML so the check measures over the limit** — `qa-harness.md` (#259)
- [2026-10-01] **Prose markup is styled by a closed tag set from a template, the author's `style` wins, and
  `h1`/`h2` are refused rather than demoted** — `design-axes.md` (#280)
- [2026-10-01] **A committed example is a golden: a test compares it to a fresh render, masking only
  Content-IDs, whose chart bytes are the machine's** — `qa-harness.md` (#281)
- [2026-10-01] **A deck is a medium, superseding "a slide is a page"; one slide is one sheet, overflow a
  finding; `presentation` is the first density one medium alone may take** — `deck.md` (#218)
- [2026-10-01] **Owner's calls for the filed epics**: trend arrows are drawn shapes, never glyphs; the notes
  handout fits #299; `[qr]` is the sixth extra; kicker and badge both sit on `Container` — #318–#346
- [2026-10-01] **Position routes**: split `valign` is paper-only and an email refuses it (C); the prose
  measure is a medium default written only where it bites (D); visibility is `Only`/`OnlySections` (B) — #354, #361
- [2026-10-01] **Appendices reopen numbering by one letter level only; a citation is `[@key]` in the
  `[^n]` fields, resolved by the walk; a term link is a plain `#term-` anchor** — `apparatus.md` (#220)
- [2026-10-02] **Placement is decided in Python per medium**: reverse stacking is the `dir=rtl`
  hybrid technique, unstacked is a fluid percentage row gated at the 375px floor, visibility rides
  a medium context var beside the config one — `design-axes.md`, `media.md`, `deck.md` (#361)
- [2026-10-03] **Placement within a block's space is paper-first**: `valign` anchors a fixed box by a
  CSS-aligned cell, a split's `valign` is refused in an email (route C), a share is the section's
  align, and the measure is in `ch` and the medium's (route D) — `design-axes.md`, `deck.md` (#354)

## Threads          (open items; remove when closed)
- **A share table holds its share in Word's engine** (owner, via COM, PR #371); a real Outlook client
  is still #288's. The measure is `ch`: in Georgia 75ch sets ~99 characters (`design-axes.md`).
- **Outlook desktop's handling of `dir=rtl` on a reversed split is unverified here**; add it to #288's
  human check.
- **The suite runs on Windows since #372** (PR #371); no Windows CI job — the owner's run is the check.
- **`epic-autoclose` works** (closed #273, #354, #361). Still confirm each epic closed after its merge.
- **In this container, PDF byte-determinism tests flake** (no HarfBuzz-Subset), and screenshot
  tests skip unless `PYHERMES_CHROMIUM=/opt/pw-browsers/chromium-1194/chrome-linux/chrome`.
- **Every issue or PR body is written without angle brackets** — GitHub's sanitizer has
  emptied three.
- **A closing keyword closes only the issue it names, and this is now proven both ways.**
  #167 named only the epic and left all nine children open; #168, #191 and #192 named every
  issue and closed every one. One `Closes #N` per sub-issue, and check that summary after
  any epic merge.
- **Five optional extras:** `[pdf]`, `[qa]`, `[data]`, `[charts]`, `[math]`. `[dev]` alone stays free of
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
- [2026-10-01] research-apparatus — **#220 implemented** (#308–#312): exhibits list, appendices,
  citations, glossary, the research-note fixtures — sessions/2026-10-01-research-apparatus.md
- [2026-10-02] placement — **#361 implemented** (#362–#367): stack, keep/break, Only/OnlySections,
  slide layouts, placed_layout fixtures — sessions/2026-10-02-placement.md
- [2026-10-03] position — **#354 implemented** (#355–#360): valign, `width=` shares, the `ch` measure,
  floated figures; with #372, merged in PR #371 — sessions/2026-10-03-position.md
- [2026-10-04] memory — State, Threads and the epic order re-synced with GitHub after PR #371.
