# MEMORY INDEX  ·  keep ≤ ~80 lines, ≤ ~200 chars per line

## State            (rewrite in place — current truth only, ≤ ~10 lines)
- pyHermes builds **documents** and renders each onto a **medium**: `pyhermes/builder` is the
  shared kit, `pyhermes/email`, `pyhermes/document`, `pyhermes/brochure` and `pyhermes/deck` are the media, and exporters sit on
  one contract — `pyhermes/delivery`+`gmail`+`outlook`, and `pyhermes/pdf`. Rationale: CLAUDE.md and
  `.claude/rules/media.md`; do not restate it here.
- **Shipped**: #157, #153, #169, #170, #171, #172, #193 (PRs #167–#203); #201, #150, #202 (PRs #204–#206);
  #209 (PR #222); #217 (PR #234); #221 (PR #235); #238 (PR #253); #237, #255, #239 (PRs #254–#257); manual
  + #258 (PR #260); #261 + #258's fix (PR #283); #265 (PR #284); #277 (PR #285); #282 (PR #286); #273 (PR #287); #270
  (PR #289); #259 (PR #292); #281 (PR #293); #272 (PR #294); #280 (PR #295); #220 (PR #313); #218 (PR #314). #288 is the human Outlook-desktop check.
  #220 research apparatus (#308–#312) shipped in PR #313; epic-autoclose closed it.
  #218 deck medium shipped in PR #314; epic-autoclose closed it. #300 PPTX was closed with #219.
  Epics defined, not started: #219 DOCX (#302–#307); content #318 #324 #329 #335 #340 #346;
  position #354 #361. Subs #319–#367. Deck bugs #315–#317 come before #346.
- The prose budget is live; the baseline is 44 and may only shrink.

## Decisions        (append-only; supersede, never delete)
- Older entries, and epic #157's, are in sessions/ARCHIVE-2026.md.

- [2026-09-24] **Re-syncing from claudeBrain is a 3-way merge, never a copy.** Base = the factory
  blob nearest our file; pyHermes-adapted agents/hooks stay ours — sessions/2026-09-24-sync-claudebrain-assets.md
- [2026-09-24] **Spacing has two levels: a preset (or a derived scheme), then `spacing=` per object as a
  derive of the bound scheme.** The email gates both; no px enters the API — `design-axes.md`,
  sessions/2026-09-24-spacing-two-levels.md
- [2026-09-24] **A `colspan` is admitted in a `thead` only, and Outlook's handling of it is unverified
  here.** A cell note is the `[^n]` marker, never a field — #217, sessions/2026-09-24-1208-define-epic-217.md

- [2026-09-24] **A cell's text on its own heat tint takes the more legible theme token, and a
  marker hangs past the point on paper.** Both were found only by the #228 rasters —
  sessions/2026-09-24-table-semantics.md

- [2026-09-24] **An equation's component takes bytes and the [math] extra renders them**, because the
  builder never imports a backend; **the picture is painted for the theme the caller passes** — `math.md`

- [2026-09-28] **A config travels with the work: explicit, then context, then default.** A `ContextVar`
  over `set_config`; a new thread starts from the default. Soft limits are warnings — `config.md`

- [2026-09-29] **The import root is `pyhermes` alone**; the `svc` shim was removed (#255) before any
  release shipped it. Checks read the built wheel and sdist, never the tree — `working-in-the-code.md`

## Threads          (open items; remove when closed)
- **Open deck bugs #315–#317** (overflow check crash, wrapped title, Slide in Panel); #347 waits on #316.
- **`epic-autoclose` works again**: it closed #273 on 2026-10-01. Still confirm each epic closed.
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

## Log              (append-only pointers)
- Older entries, and epic #157's, are in sessions/ARCHIVE-2026.md.
- [2026-10-01] deck-medium — **#218 implemented**: Deck, Slide, overflow, notes, `presentation`,
  `pitch_16_9` — sessions/2026-10-01-deck-medium.md
- [2026-10-01] examples-drift — **#281 implemented**: README facts, three examples regenerated, the
  committed-output test — sessions/2026-10-01-examples-drift.md
- [2026-10-01] customise-the-layout — **#272 implemented**: manual page 9, every example run —
  sessions/2026-10-01-customise-the-layout.md
- [2026-10-01] prose-styles — **#280 implemented**: the `prose` filter, three tokens, the h1/h2
  refusal, manual page 9's tag table — sessions/2026-10-01-prose-styles.md
- [2026-10-01] research-apparatus — **#220 implemented** (#308–#312): exhibits list, appendices,
  citations, glossary, the research-note fixtures — sessions/2026-10-01-research-apparatus.md
