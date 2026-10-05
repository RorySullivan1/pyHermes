# MEMORY INDEX  ·  keep ≤ ~80 lines, ≤ ~200 chars per line

## State            (rewrite in place — current truth only, ≤ ~10 lines)
- pyHermes builds **documents** and renders each onto a **medium**: `pyhermes/builder` is the
  shared kit, `pyhermes/email`, `document`, `brochure` and `deck` are the media, and exporters sit on
  one contract — `delivery`+`gmail`+`outlook`, and `pdf`. Rationale: CLAUDE.md and `media.md`.
- **Shipped through PR #382.** Epics #157–#220 and #218 (PRs #167–#314); deck bugs #315–#317
  (PR #369); #361 (PR #370); #354 and #372 (PR #371); #318 (PR #373); #346 (PR #374); #324 (PR #376);
  #329 (PR #378); #335 (PR #380); #340 (PR #382). #219 DOCX closed not planned, with #300 PPTX.
- **#340 shipped** in PR #382 (#341–#345); the epic was closed by hand when its autoclose runs sat queued.
  Its merge turned `main`'s `pdf` job red (a stamped deck's handout lacked `stamp_type`), fixed after.
  #288 is the owner's Outlook-desktop check, run on Windows.
- The prose budget is live; the baseline is 44 and may only shrink.

## Decisions        (append-only; supersede, never delete)
- Older entries, and epic #157's, are in sessions/ARCHIVE-2026.md.
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
- [2026-10-04] **A glance object is drawn from cells and tokens, never an image; an arrow is a
  CSS shape with a VML twin, its direction the number's (`Card.arrow` is `init=False`)** — `glance.md` (#318)
- [2026-10-04] **A deck's layouts are per slide and off by default: the box narrows per slide, a
  photograph's tone is named, and the handout scales the deck's own sheets rather than rastering
  them, so `[pdf]` alone prints it** — `deck.md` (#346)

- [2026-10-05] **A badge takes a tone, never a colour, and is square in Outlook by decision: no VML,
  nbsp padding in an mso conditional; a status dot is the same span unlabelled** — `design-axes.md` (#324)
- [2026-10-05] **A timeline spans no cell: a capsule marker the title's height, the rule a half-cell's
  border; a kicker is the `h2`'s sibling, never inside it; four kitchen_sink sections became two Stacks
  to pay for #329's bytes** — `design-axes.md`, `builder-architecture.md` (#329)

- [2026-10-05] **A grid is one exhibit: `leaves()` stops at any `Exhibit`, panels anchor `<grid>-<letter>`;
  a legend names theme colours (a hex is checked in `add_section`), never reads the plot; a section's
  source is `source_notes`, read by the walk after its blocks** — `apparatus.md`, `data-layer.md` (#335)

- [2026-10-05] **A turned page is a body table of its own (a named page is inert on a `tr`); a stamp is a
  fact set OVER the copy, translucent (under, grounds hid it), and no constructor `stamp=`; an aside is a
  value object rendered through `Callout`; a gallery QR is a module-matrix constant** — `media.md`, `brochure.md` (#340)

## Threads          (open items; remove when closed)
- **A share table holds its share in Word's engine** (owner, via COM, PR #371); a real Outlook client
  is still #288's. The measure is `ch`: in Georgia 75ch sets ~99 characters (`design-axes.md`).
- **Outlook desktop's handling of `dir=rtl` on a reversed split is unverified here**, nor #319's VML
  arrow, nor #325's square badge and dot, nor #331's empty rule cells (`font-size:0`), nor #337's legend
  swatch; all join #288's check.
- **`kitchen_sink` is at its 90 KB ceiling**: `modern_fonts` has 962 bytes left after #340, which untitled
  the three wide `ThreeColumn` ratios to pay for the stamp and the QR button; the next epic must merge or move.
- **The suite runs on Windows since #372** (PR #371); no Windows CI job — the owner's run is the check.
- **`epic-autoclose` works** (closed #273, #354, #361, #346, #324, #329, #335). Still confirm each epic closed after its merge.
- **A dark split leaves a light seam under its left column on paper**, on `main` since before #324;
  queued as a suggested task, not yet an issue (repro in sessions/2026-10-05-labels.md).
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
- [2026-10-05] labels — **#324 implemented** (#325–#328): badges, status dots, tag rows, the
  labelled fixtures — sessions/2026-10-05-labels.md
- [2026-10-05] organising — **#329 implemented** (#330–#334): fact lists, timelines, teaser lists,
  kickers, the organised fixtures — sessions/2026-10-05-organising.md
- [2026-10-05] grouped — **#335 implemented** (#336–#339): figure grids, legends, section source
  lines, the research note's grids — sessions/2026-10-05-grouped-exhibits.md
- [2026-10-05] memory — State and Threads re-synced with GitHub after PR #380.
- [2026-10-05] page-level — **#340 implemented** (#341–#345): landscape pages, stamps, asides, QR codes,
  `a4_wide_appendix` — sessions/2026-10-05-page-level.md
- [2026-10-05] windows — the 7 reported Windows failures were already fixed by #372; its own drive-path
  test still failed (a `WindowsPath` prints backslashes), fixed — sessions/2026-10-05-1657-windows-suite-recheck.md
