---
name: brochure-builder
description: >
  Expert at building a folded brochure — the execution tier that turns a design spec into a finished,
  print-ready folded marketing piece. Use this skill whenever the user wants to *build*, *generate*, or
  *export* a brochure: a tri-fold, bi-fold, gate-fold, or z-fold single-sheet marketing/promotional
  piece (product brochure, service overview, event handout, mailer). Trigger on phrases like "build
  this brochure", "make a tri-fold / bi-fold / gate-fold", "lay out this brochure for print", "generate
  the brochure PDF", "set up the panels for a folded leaflet", "impose this brochure for folding", or
  any request to produce a *folded panel* piece as a print-ready file. This is the single-sheet, folded
  multi-panel format — for a flat single page use `one-pager-builder`, for a multi-page stitched
  booklet/leaflet use `pamphlet-builder`, and for slide decks use `deck-builder`. Defer the
  narrative/panel content to `presentation-architect` and the visual + copy design to
  `presentation-design` — those are inputs this skill renders. This skill picks the tool, gets the panel
  geometry and fold imposition right, and verifies the piece is print-ready.
---

# Brochure Builder

Expert at the **execution tier** for a folded, single-sheet brochure: taking a design spec and
producing a finished, print-ready file with the panels correctly placed for folding. The defining
challenge here is **fold geometry and imposition** — what the reader sees panel-by-panel as they open
it is *not* the order the panels sit on the printed sheet.

## Where this sits

```
presentation-architect  →  presentation-design  →  brochure-builder
(panel content + order)     (look + final copy)      (THIS: build the folded sheet)
```

- **Inputs (not this skill's calls):** the panel content and reveal order (from
  `presentation-architect`) and the per-panel visual + copy design (from `presentation-design`).
  Missing either → get it or ask.
- **This skill owns:** tool choice, the fold/panel geometry and print imposition, building to spec, and
  verifying the piece folds and prints correctly.

## Fold geometry & imposition (the part that's easy to get wrong)

A brochure is one sheet, printed both sides, then folded. The **reading order** (cover → inside panels)
maps to specific **positions on the flat sheet**, which differ by fold type:

- **Bi-fold** (4 panels): one fold; front/back outer, two inner.
- **Tri-fold / letter-fold** (6 panels): two folds. The panel that **folds inward must be ~2–3mm
  narrower** than the others so it tucks without buckling. Outside sheet = back | front cover | inner-flap;
  inside sheet = the three-panel spread.
- **Z-fold** (6 panels): two folds accordion-style; all panels equal width, different imposition than a
  tri-fold.
- **Gate-fold** (the two outer panels fold in to meet at center): two narrower outer panels.

Always lay panels out by **fold position on the sheet, not reading order**, set fold lines (and fold
marks for the printer), and account for **panel-width differences** on inward-folding panels. When in
doubt, build a folding dummy / proof and fold it to confirm sequence before final export.

## Choosing the tool

| Tool | Reach for it when | Build method |
|---|---|---|
| **InDesign / Affinity Publisher / Scribus** | Real print brochure; precise panels, bleed, CMYK | Page-layout app; panel guides + fold marks on a sheet |
| **Canva / Figma** | Brand-kit, quick, non-technical hand-off | Brochure template with preset panels |
| **HTML/CSS → PDF** (WeasyPrint, Paged.js) | Data-driven or version-controlled | CSS `@page` sized to the full sheet; panel columns |
| **LaTeX (the `leaflet` class)** | Typeset, reproducible | Source → PDF; `leaflet` does the two-fold single-sheet imposition for you |

Default to a page-layout app for any serious print run; use HTML/CSS→PDF when it must be data-driven.

## Build principles

1. **Impose by fold, not by reading order.** Place each panel where it lands on the sheet; verify by
   folding a proof.
2. **Set the sheet geometry first.** Sheet size (e.g. US Letter / A4 landscape), panel count, fold type,
   per-panel widths (narrow the tuck-in panel), **bleed** (3mm/0.125in), and a safe margin from folds
   and trim. Keep critical text clear of fold lines.
3. **Render the spec; don't redesign.** Per-panel layout, type, color, imagery, and copy come from
   `presentation-design`.
4. **Print-ready output.** CMYK, embedded fonts, PDF/X with bleed and crop/fold marks. Confirm the
   printer's fold and bleed specs up front.
5. **Reproducible when data-driven.** Keep content separate from layout so it rebuilds deterministically.

## Workflow

1. **Gather inputs** — panel content + reveal order (architect), per-panel design (design), assets,
   brand/template, fold type, and the **printer's specs** (bleed, fold tolerance). Missing upstream → ask.
2. **Choose tool & method**; state why.
3. **Set sheet & fold geometry** — sheet size, panel widths (tuck-in panel narrower), fold lines, bleed,
   safe margins, fold/crop marks.
4. **Impose & build** — place each panel at its **sheet position** (not reading order), build each to the
   design spec, content pulled from source.
5. **Verify** — render both sides; **fold a proof** (or simulate) to confirm reading sequence; nothing
   critical crosses a fold; bleed present; fonts embedded; CMYK; colors/images correct.
6. **Deliver** the print-ready PDF (+ a reader-order preview so the client can sanity-check), the build
   script if reproducible, and notes on fold type and printer specs. Flag anything unrendered or missing.

## Output

- **The print-ready brochure file** (imposed for folding) plus a **reading-order preview**, and the
  build script if reproducible.
- **Build notes** — tool/method, fold type, sheet size, panel widths, bleed, printer specs assumed.
- **Verification** — folds to the right sequence, nothing critical on a fold line, bleed/CMYK/fonts
  correct; anything unrendered, and missing assets.

## What this skill does *not* do

- **Set panel content / message order** — that's `presentation-architect`.
- **Decide the visual design or write the copy** — that's `presentation-design`.
- **Flat single page** → `one-pager-builder`; **multi-page stitched booklet/leaflet** → `pamphlet-builder`.
- **Invent facts or data** — render what's given; flag gaps.

## Anti-patterns

- **Laying panels out in reading order** — they print in fold-position order; the result folds into nonsense.
- **Equal-width tuck-in panel** — the inward-folding panel buckles if it isn't slightly narrower.
- **Text across a fold** — headlines/critical copy split or creased by the fold line.
- **No bleed / RGB to print** — white edges at trim, color shifts on press.
- **No folded proof** — shipping without folding a dummy to confirm the sequence.
- **Redesigning during the build** — making design calls that belong to `presentation-design`.
</content>
