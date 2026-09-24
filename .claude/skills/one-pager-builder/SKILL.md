---
name: one-pager-builder
description: >
  Expert at building a single-page document — the execution tier that turns a design spec into a
  finished one-pager file. Use this skill whenever the user wants to *build*, *generate*, or *export*
  a one-page piece: a sell sheet, leave-behind, fact sheet, executive summary, resume/CV, flyer, or
  single-page poster, as a print-ready PDF, an image (PNG), or a web page. Trigger on phrases like
  "build this one-pager", "make a one-page PDF", "generate the sell sheet / fact sheet / flyer",
  "export this to a single page", "turn this into a one-page leave-behind", "build my resume",
  "single-page poster". This is the flat, *unfolded* single-page format — for folded multi-panel
  pieces use `brochure-builder`, for multi-page booklets/leaflets use `pamphlet-builder`, and for
  slide decks use `deck-builder`. Defer the narrative/priority of content to `presentation-architect`
  and the visual + copy design to `presentation-design` — those are inputs this skill renders, not
  calls it makes. This skill picks the tool, builds reliably, and verifies the page is print/share-ready.
---

# One-Pager Builder

Expert at the **execution tier** for a single, unfolded page: taking a design spec and producing a
finished, share-ready one-pager file. The whole message lives on **one side of one page**, grasped in
~30 seconds — so the build is about faithful layout, a clean single eye-path, and an export that looks
right both on screen and in print.

## Where this sits

```
presentation-architect  →  presentation-design  →  one-pager-builder
(what to say, priority)     (look + final copy)      (THIS: build the page file)
```

- **Inputs (not this skill's calls):** the content priority/flow (from `presentation-architect`) and
  the visual + copy design spec (from `presentation-design`). Missing either → get it or ask; don't
  invent the message or redesign while building.
- **This skill owns:** tool choice, building the page to spec, and verifying it exports correctly.

## Choosing the tool

| Tool | Reach for it when | Build method |
|---|---|---|
| **HTML/CSS → PDF** (WeasyPrint, Paged.js, wkhtmltopdf) | Data-driven, version-controlled, or web + PDF from one source | Template + CSS `@page`; script the fill |
| **InDesign / Affinity Publisher / Scribus** | High-design print piece, precise typography | Page-layout app on a template |
| **Canva / Figma** | Quick, brand-kit-driven, non-technical hand-off | Template, manual or API export |
| **LaTeX / Typst** | Typeset, equation- or text-heavy (e.g. CV, fact sheet) | Source → PDF |

Default to whatever the org standardizes on; pick **HTML/CSS→PDF** or a template-driven app when the
one-pager is data-driven or regenerated often.

## Build principles

1. **One page, one eye-path, one dominant element.** Enforce the single-page limit hard — if it
   overflows, that's a content/design problem to send back, not something to solve by shrinking type
   to 6pt. The largest thing on the page is the main takeaway.
2. **Render the spec; don't redesign.** Layout, hierarchy, type, color, and copy come from
   `presentation-design`. Build to fidelity.
3. **Set the page geometry first.** Page size (US Letter / A4 / custom), orientation, and margins. If
   it will be **printed**, add bleed (typically 3mm/0.125in) and a safe margin, and export CMYK,
   print-ready PDF (PDF/X). If it's **screen/web only**, RGB and an optimized PNG/PDF are fine.
4. **Make it reproducible when content changes.** Data-driven sell/fact sheets should rebuild from
   source (data + template) deterministically; keep content separate from layout code.
5. **Export for the destination.** Print → high-res, embedded fonts, bleed/crop marks if required.
   Email/web → compressed PDF or PNG, RGB, reasonable file size. Often produce both.

## Workflow

1. **Gather inputs** — content priority (architect), design spec (design), assets (logo, images,
   data), brand/template, and the **destination** (print vs screen). Missing upstream input → request it.
2. **Choose tool & method** and state why.
3. **Set page geometry** — size, orientation, margins, bleed/safe-area for print.
4. **Build the page** to the design spec: place the dominant element, then the hierarchy; pull text and
   numbers from the source, not retyped.
5. **Verify** — opens/renders cleanly; everything fits on **one** page; nothing inside the bleed/safe
   margin is clipped; fonts embedded; images sharp at output size; colors correct for print vs screen.
   Re-run scripted builds to confirm determinism.
6. **Deliver** the file(s) (print and/or screen export) and, for scripted builds, the script + how to
   regenerate. Note anything that couldn't fit or render, and missing assets.

## Output

- **The one-pager file(s)** in the needed format(s) (print PDF and/or web PNG/PDF), plus the build
  script if reproducible.
- **Build notes** — tool/method and why; page size + bleed; print vs screen targets; how to regenerate.
- **Verification** — fits one page, nothing clipped, fonts/images/colors correct; anything that
  couldn't render to spec, and missing assets.

## What this skill does *not* do

- **Set content priority / message** — that's `presentation-architect`.
- **Decide the visual design or write the copy** — that's `presentation-design`.
- **Handle folds or multiple pages** — use `brochure-builder` (folded) or `pamphlet-builder` (booklet).
- **Invent facts or data** — render what's given; flag gaps.

## Anti-patterns

- **Overflow rescue by shrinking** — cramming a two-page worth of content onto one with tiny type;
  send it back to design instead.
- **No bleed on a printed piece** — white slivers at the trim edge.
- **Redesigning during the build** — making hierarchy/color/copy calls that belong to design.
- **Screen export sent to print** — RGB, low-res, no bleed at the print shop.
- **Retyping numbers** — drift from the data source.
- **Shipping unverified** — handing over a PDF you never opened at output size.
</content>
