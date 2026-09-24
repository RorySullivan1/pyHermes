---
name: pamphlet-builder
description: >
  Expert at building a multi-page pamphlet or booklet — the execution tier that turns a design spec into
  a finished, print-ready informational leaflet/booklet. Use this skill whenever the user wants to
  *build*, *generate*, or *export* a pamphlet: a saddle-stitched booklet, a folded informational leaflet,
  a small handbook, or an educational/instructional multi-page piece. Trigger on phrases like "build this
  pamphlet", "make a booklet", "lay out this leaflet", "saddle-stitch this", "impose these pages for a
  booklet", "turn this into a multi-page informational handout", "generate the booklet PDF". This is the
  *multi-page, info-dense* format (often stitched/bound, pages in multiples of 4) — for a flat single page
  use `one-pager-builder`, for a single-sheet folded marketing piece use `brochure-builder`, and for slide
  decks use `deck-builder`. Defer the content/sequence to `presentation-architect` and the visual + copy
  design to `presentation-design` — those are inputs this skill renders. This skill picks the tool, gets
  the booklet page imposition right, handles longer text flow, and verifies the piece is print-ready.
---

# Pamphlet Builder

Expert at the **execution tier** for a multi-page pamphlet/booklet: taking a design spec and producing a
finished, print-ready piece. Unlike a brochure (one folded sheet, promotional), a pamphlet is **multi-page
and information-dense** — instructional, educational, or reference — so the build is about **booklet page
imposition**, consistent multi-page flow, and longer running text.

## Where this sits

```
presentation-architect  →  presentation-design  →  pamphlet-builder
(content + page sequence)    (look + final copy)      (THIS: build the booklet)
```

- **Inputs (not this skill's calls):** the content and page sequence (from `presentation-architect`) and
  the per-page visual + copy design (from `presentation-design`). Missing either → get it or ask.
- **This skill owns:** tool choice, booklet imposition, multi-page layout flow, and verifying the piece
  prints and binds correctly.

## Booklet imposition (the distinctive part)

A saddle-stitched booklet is printed on sheets folded and nested, so **reader page order ≠ sheet order**:

- **Total pages must be a multiple of 4** (each folded sheet = 4 pages). Pad with intentional blanks if
  needed; don't let content force an odd count.
- **Imposition pairs pages** across the spine: for an n-page booklet, sheet fronts/backs pair (1,n),
  (2,n−1), … Most tools (and `pdfbook`/`booklet` utilities) impose automatically — **let the tool impose**
  from a sequential reader-order PDF rather than hand-arranging, then verify.
- **Mind creep/shingling** on thicker booklets (inner pages push outward when folded) — pull margins in or
  let the tool compensate.
- **Spreads** (content crossing the centerfold) only work on the true center spread; keep critical content
  off the spine elsewhere.
- A simple folded leaflet (non-stitched) is the light case: same fold logic as a brochure but treated as
  ordered pages.

## Choosing the tool

| Tool | Reach for it when | Build method |
|---|---|---|
| **InDesign / Affinity Publisher / Scribus** | Real booklet; master pages, page numbers, print booklet export | Master pages + built-in booklet/imposition export |
| **LaTeX / Typst** | Text-heavy, reproducible, auto page numbering/TOC | Source → PDF, then `pdfbook`/booklet impose |
| **HTML/CSS → PDF** (WeasyPrint, Paged.js) | Data-driven, version-controlled | Paged media + running headers; impose after |
| **Pandoc → PDF** | Markdown source → typeset booklet | Markdown → LaTeX/PDF |

Default to a page-layout app or LaTeX/Typst for real booklets (they handle masters, numbering, and
imposition); use HTML/CSS or Pandoc when the source must be text/version-controlled.

## Build principles

1. **Author in reader order; let the tool impose.** Build a sequential reader-order document, then export
   with booklet imposition — never hand-place pages onto sheets.
2. **Keep page count a multiple of 4**; plan intentional blanks.
3. **Set up multi-page structure once** — master pages, consistent margins (with a larger **inner/gutter**
   margin for binding), running headers/footers, and page numbers.
4. **Render the spec; don't redesign.** Per-page layout, type, color, imagery, and copy come from
   `presentation-design`. Manage longer text flow faithfully (widows/orphans, consistent leading).
5. **Print-ready output.** CMYK, embedded fonts, PDF/X, bleed, gutter for binding; confirm the printer's
   binding (saddle-stitch vs perfect-bind) and creep handling.
6. **Reproducible when data-driven** — content separate from layout so it rebuilds deterministically.

## Workflow

1. **Gather inputs** — content + page sequence (architect), per-page design (design), assets,
   brand/template, target page count, and **binding/printer specs**. Missing upstream → ask.
2. **Choose tool & method**; state why.
3. **Set up the document** — page size, master pages, gutter/inner margin, running heads, page numbers,
   bleed; confirm/pad to a multiple of 4 pages.
4. **Build in reader order** — flow content page by page to the design spec, content pulled from source.
5. **Impose & verify** — export with booklet imposition; check page count ÷ 4, reader sequence after
   imposition, gutter clearance, nothing critical on the spine, creep handled, bleed/CMYK/fonts correct.
6. **Deliver** the print-ready imposed PDF **and** a reader-order PDF (for review), the build script if
   reproducible, and notes on binding/imposition. Flag anything unrendered or missing.

## Output

- **Two PDFs** — a reader-order proof and the imposed print-ready booklet — plus the build script if
  reproducible.
- **Build notes** — tool/method, page count, binding type, imposition, gutter/bleed, printer specs assumed.
- **Verification** — page count is a multiple of 4, imposed sequence is correct, gutter/spine clear, creep
  handled, CMYK/fonts/bleed correct; anything unrendered, and missing assets.

## What this skill does *not* do

- **Set content / page sequence** — that's `presentation-architect`.
- **Decide the visual design or write the copy** — that's `presentation-design`.
- **Flat single page** → `one-pager-builder`; **single-sheet folded marketing piece** → `brochure-builder`.
- **Invent facts or data** — render what's given; flag gaps.

## Anti-patterns

- **Hand-imposing pages** — manually arranging sheet order instead of authoring in reader order and letting
  the tool impose; almost always produces a mis-ordered booklet.
- **Page count not a multiple of 4** — leaves blank or dropped pages at the printer.
- **No gutter margin** — inner text swallowed by the binding.
- **Ignoring creep** — outer-edge content trimmed off inner pages on thick booklets.
- **Content on the spine** — text/images split across the binding (except the true centerfold).
- **Redesigning during the build** — making design calls that belong to `presentation-design`.
</content>
