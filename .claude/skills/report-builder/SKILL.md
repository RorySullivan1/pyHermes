---
name: report-builder
description: >
  Expert at building a long-form report or document — the execution tier that turns a structure +
  design spec into a finished, multi-page document file. Use this skill whenever the user wants to
  *build*, *generate*, *assemble*, or *export* a long document: a research report, whitepaper, annual
  report, technical/business report, proposal, dossier, manual, or any multi-section, multi-page
  read-alone document. Trigger on phrases like "build this report", "generate the whitepaper / annual
  report", "assemble this document", "turn this outline into a report", "produce the PDF/docx report",
  "add a table of contents and sections", "lay out this long document for print/PDF", "compile this
  into a report", or any request to produce a *long-form document* file. This is the multi-page,
  text-heavy, read-alone format with document structure (ToC, sections, cross-references, figures/
  tables, footnotes, pagination) — for slide decks use `deck-builder`, a flat single page use
  `one-pager-builder`, a folded marketing piece use `brochure-builder`, and a stitched booklet use
  `pamphlet-builder`. Defer the narrative/section structure to `presentation-architect`, the visual +
  copy design to `presentation-design`, and the reusable identity to `branding` — those are inputs
  this skill renders, not calls it makes. This skill picks the tool, gets document structure and long
  text flow right, and verifies the output. For a large job, delegate the verbose build to the
  `token-manager` agent so the bulk stays out of the main context.
---

# Report Builder

Expert at the **execution tier** for long-form documents: taking a structure and a design spec and
producing a real, complete, multi-page report. Where `presentation-architect` decides *what to say in
what order* and `presentation-design` decides *how it looks and reads*, this skill decides *how to
actually build it* — the tool, the method (template-driven, scripted, or document-assembled), the
long-document machinery (ToC, sections, cross-references, figures/tables, footnotes, pagination), and
the reproducible steps that yield a correct file.

## Where this sits

```
branding  →  presentation-architect  →  presentation-design  →  long-form-report-building
(identity)   (structure/section flow)   (document design +       (THIS: build the report file —
                                         copy)                     ToC, sections, refs, pagination)
```

- **Inputs (not this skill's calls):** the section structure/flow (`presentation-architect`), the
  document design + final copy (`presentation-design`), and the brand (`branding`). If any is missing,
  get it upstream or ask — don't improvise the structure or invent the design while building.
- **This skill owns:** choosing the build tool, the build method, applying the template/styles,
  rendering each section faithfully, the long-document structure, and verifying the result.

## Choosing the tool

Pick by output need, length, math/citation requirements, and whether the build must be
**reproducible/automated** or hand-finished. Default to the format the user/organization standardizes on.

| Tool / format | Reach for it when | Build method |
|---|---|---|
| **Word (.docx)** | Editable hand-off; corporate template; tracked review/comments | `python-docx` scripted, or assemble on a `.dotx` template with styles |
| **LaTeX (PDF)** | Academic/technical; heavy math, citations, precise typesetting | `.tex` source → `pdflatex`/`latexmk`, BibTeX/biblatex for refs |
| **Typst (PDF)** | Modern alternative to LaTeX; faster, scriptable, clean syntax | Typst source → `typst compile` |
| **Quarto / Pandoc (MD → PDF/docx/HTML)** | Version-controlled, text-first, multi-format from one source | Markdown + a reference template → CLI render |
| **HTML/CSS → PDF** | Web-styled, programmatic, data-driven | HTML template + CSS Paged Media → WeasyPrint/Prince |
| **Google Docs** | Cloud collaboration | Docs API, or import a generated `.docx` |

Guidance:
- **Editable corporate report** → `.docx` on the official template so heading/body/caption **styles**,
  fonts, and colors come from the template (which itself should reflect `branding`).
- **Reproducible, data-driven, or version-controlled** → script it (`python-docx`) or a text source
  (Quarto/Pandoc, Typst, LaTeX) so the report regenerates from source. In this project's Python
  tooling, `python-docx` pairs with the `python-development` skill.
- **Equation/citation-heavy, fixed PDF** → LaTeX or Typst.

## Build principles

1. **Render the spec faithfully — don't redesign or rewrite.** Structure comes from the architect,
   design and copy from `presentation-design`, identity from `branding`. Your job is fidelity. If the
   spec is under-specified, ask; don't invent styling or prose to fill the gap.
2. **Use named styles, not manual formatting.** Drive every heading, body, caption, and quote from
   the template's **style definitions** so the document is consistent, re-themeable, and its ToC and
   navigation are generated correctly. Manual per-paragraph formatting is the cardinal sin of long docs.
3. **Generate document structure, don't hand-build it.** Table of contents, lists of figures/tables,
   section/figure numbering, cross-references, and the index must be *generated* from the styles and
   labels so they stay correct as content changes — never typed by hand.
4. **Make it reproducible when content will change.** For data-driven or regenerated reports, script
   the build so it rebuilds deterministically from source (data + spec); separate content/data from
   rendering.
5. **One source of truth for content & numbers.** Pull text, tables, and figures from the provided
   content/data, not retyped copies, so the report can't drift from its source.
6. **Get long-document mechanics right.** Page size/margins, running headers/footers, page numbers,
   section breaks, widow/orphan control, figure/table placement near their reference, consistent
   caption style, footnotes/endnotes, and a correct citation/bibliography style.

## Scale & context economy

Long reports are the one builder where the *build itself* can be high-volume — large source documents,
long generated prose, multi-pass assembly. When a job is large, **delegate the verbose build to the
`token-manager` agent** (per the `token-optimizer` skill) so raw content and tool output stay out of
the main context and only a tight summary returns. Keep this skill's own footprint lean: work
section-by-section, and don't echo full document bodies back into the conversation.

## Workflow

1. **Gather inputs.** Confirm the section structure (`presentation-architect`), the design + copy
   spec (`presentation-design`), the brand (`branding`), plus assets (figures, tables, data, logo) and
   any org template. Missing an upstream input → request it; don't build blind.
2. **Choose the tool & method.** Pick from the table by output need, length, math/citation needs, and
   whether the build must be reproducible. State the choice and why.
3. **Set up the scaffold.** Apply the template/styles (heading/body/caption/quote), page setup,
   headers/footers, and numbering schemes. Wire fonts/colors from the brand/template.
4. **Build section by section.** Flow each section's copy into the right styles; place figures/tables
   with captions and labels; add cross-references by label (not by typed number); add footnotes/
   citations. Keep content sourced from the data, not retyped.
5. **Generate the apparatus.** Build/refresh the table of contents, lists of figures/tables, and any
   index; resolve all cross-references and the bibliography.
6. **Verify.** Open/render the output and check: it compiles/opens without error; ToC and cross-refs
   resolve — grep the exact strings, they are easy to get subtly wrong: LaTeX emits a bold
   `??`, Word emits **`Error! Reference source not found.`** (the word *source* is part of it)
   and **`Error! Bookmark not defined.`** for the sibling bookmark failure; section/figure numbering is correct and
   sequential; headers/footers and page numbers are right; figures/tables render near their references
   with captions; styles are applied consistently; citations/bibliography are complete; page count and
   file size are sane. For scripted builds, re-run to confirm determinism.
7. **Deliver.** Hand back the file (and, for scripted builds, the script + how to regenerate). Note any
   spec items that couldn't be rendered and why, and any missing assets/sources.

## Output

- **The report file** in the chosen format (and the build script, if scripted/reproducible).
- **Build notes** — tool and method chosen and why; how to regenerate (for scripted builds); template/
  styles and page setup applied.
- **Verification** — confirmation it compiles/opens, ToC/cross-refs/numbering/citations resolve, and
  sections match the spec; anything that couldn't be rendered to spec, and missing assets/sources.

## What this skill does *not* do

- **Decide the section structure or narrative** — that's `presentation-architect`.
- **Decide the visual design or write the prose** — that's `presentation-design` (and the brand voice
  from `branding`).
- **Invent facts, data, figures, or citations** — render what's provided; flag gaps, never fabricate
  (and never invent a citation).

## Anti-patterns

- **Manual formatting instead of styles** — hand-set headings/sizes that break the ToC, re-theming,
  and consistency.
- **Typed-by-hand ToC, numbering, or cross-references** — they rot the moment content shifts; generate
  them.
- **Rewriting or redesigning during the build** — making copy/design calls that belong upstream.
- **Retyping numbers/tables** — copy from the source so the report can't silently drift.
- **Flooding the main context** — assembling a huge report inline instead of delegating the verbose
  build to `token-manager`.
- **Shipping unverified** — handing over a report with broken references, a stale ToC, or missing
  figures because it was never compiled/opened and checked.
- **Fabricated citations** — inventing a reference to fill a gap instead of flagging it.
</content>
