---
paths:
  - "svc/builder/apparatus.py"
  - "svc/builder/document.py"
  - "svc/builder/templates/common/notes.html"
  - "svc/builder/templates/common/endnotes.html"
  - "svc/builder/templates/common/contents-list.html"
  - "svc/builder/templates/text/contents.html"
  - "svc/builder/templates/document/regions/contents.html"
  - "svc/builder/templates/document/regions/running-box.html"
---

# The document apparatus — numbers, notes, contents, references

Epic #171 gave a document the apparatus a reader navigates by. #157 and #153 each deferred it by
name. Five sub-issues: exhibit numbering (#181), footnotes (#182), a contents list (#183),
cross-references (#184) and a running header that follows the section (#185).

| Apparatus | Paged | Email | Plain text |
|---|---|---|---|
| Exhibit number | "Exhibit 3 · …" on the heading line, `id="exhibit-3"` | the same | the same |
| Footnote | `float: footnote`, at the foot of the marker's sheet | endnotes after the last section | `[7]`, then a Notes block |
| Contents | `ContentsPage`, after the cover, with page numbers | the `Contents` component, a linked list | the titles, one per line |
| Cross-reference | "Exhibit 3 (p. 4)" | "Exhibit 3", linked | "Exhibit 3" |
| Running section | `string-set` from the current section title | none (no sheets) | none, by decision |

## The one rule: Python numbers everything but the page

**Numbering is computed in Python, once, so both projections agree.** A CSS counter would
number the HTML and leave the plain-text part unnumbered. An exhibit called "Exhibit 3" in
the PDF and nothing in the text is the divergence #116 exists to prevent. So `Document._walk()`
hands every part of the apparatus what only the whole tree knows, and the templates print what
they are handed:

- each labelled exhibit's `number`, counted per label in reading order;
- each `Footnote.number`, across the whole tree in reading order;
- each `Contents` component's entries, every titled section but its own.

**The walk runs on every `add_section` and again before each projection.** Running it at
render is what lets a component shared between two documents carry each document's number
while that document renders. **An exhibit never numbers itself**, because it cannot see the
tree. That is also why the number is data on the exhibit after the walk, and assigned by the
document.

**The one exception is the page number, which only the print engine knows.**
`target-counter(attr(href), page)` supplies it on paper, for contents entries and
cross-references. That is a stated per-medium degradation rather than a divergence. The
*reference* is the same in all three projections, and only the page is absent where there
are no pages.

## Print-engine features, named for the next exporter

`target-counter`, `leader`, `float: footnote`, `::footnote-call`, `::footnote-marker`,
`@footnote`, `string-set` and `string()` come from CSS Generated Content for Paged Media and CSS
Paged Media. They are **WeasyPrint features, not universal CSS**. The paged medium's exporter
is WeasyPrint by decision (#164), and every rule using them sits in `document/base.html`'s
`style` block or in `running-box.html`, with a comment saying so. A future exporter inherits
exactly that list. The email never loads either template, so no rule costs an email a byte.

## Anchors are stable and derived

- A **section**'s `id` is a slug of its title (`factor-returns`). `anchor=` overrides it, and
  an untitled section has none. A `Page`'s own title is never rendered, so it claims no
  anchor; the sections inside it stand in for it.
- An **exhibit**'s is its label and number (`exhibit-3`, `figure-1`). `anchor=` overrides it,
  and it is the only anchor an unlabelled exhibit can have.
- A **note**'s pair is `note-7` for the note and `note-ref-7` for its marker, generated.
- **Two claimants raise `ValidationError` in `add_section`**, naming both. The section is
  popped and the walk re-run, so a rejected section leaves the document as it was.

The section-anchor commit shipped alone. A script compared all 16 goldens against the
previous commit: 89 lines changed, each by one inserted `id` attribute. That commit is the
one to point at when someone asks what the email pays for a destination: nothing but the
attribute.

## Exhibits (#181)

- `label=` opts in. Unset renders byte-identically, and every golden stayed put until the
  fixtures opted in. That made the mechanism reviewable separately from the diff it causes.
- The number prefixes the **heading line**: the caption on `DataTable` and `ImageBlock`, and a
  new `ChartBlock.caption`. `MathBlock` (#229) is the fourth exhibit kind, and
  `label="Equation"` gives "Equation 2" and `id="equation-2"` by the same walk (`math.md`). The chart's caption is the figure table's first row rather than a
  paragraph above it, so the `.figure` break rule keeps it with its chart and the table's
  `id` lands on the heading a reader was sent to.
- The separator is **house style**, so it lives in `Config.exhibit_separator` (" · ") and is
  read at render. `Config.from_env` learned a string field for it, taken verbatim.

## Footnotes (#182) — two halves, and neither widens the raw-HTML set

A footnote has a **marker** in the running copy and the **note text** collected elsewhere. The
marker sits inside prose, and the prose fields are the raw-HTML five. That pairing was the
risk the epic named. The design keeps the set closed at five:

- **The marker is a plain-text convention, `[^1]`, never markup.** The builder replaces it.
  It is legal in the raw fields (`TextBlock.content`, `NumberedItem.body`) and in the plain
  ones (an exhibit's caption and source) alike.
- **The note is a `Footnote`: plain text, escaped**, for `disclosure.md`'s reason. Widening a
  plain field later is additive, and narrowing one is not. A note therefore carries no link.
  That is the follow-up the disclosure epic deferred, not a sixth surface.
- **Markers are local, numbers are the document's.** A component writes `[^1]` to `[^n]`
  against its own `notes=` list. Validation at construction requires each exactly once, so a
  marker without a note and a note without a marker both raise. The document renumbers
  across the tree, so the `[^1]` in the third component is printed as 7.
- **One macro renders every site.** `common/notes.html`'s `marked(parts, raw)` walks what
  `apparatus.split_markers` cut. Every part carries all three keys, because
  `StrictUndefined` raises on a missing one. A field with no marker is one run of copy, and
  the macro prints it exactly as before. All goldens were byte-identical with the macro in
  place before any fixture opted in.
- **Where each medium can honestly put the note.** On paper a `span.footnote` follows the
  marker and the skeleton floats it to the foot of that sheet. The note inherits from where
  its marker sat (a bold caption, italic fine print), so its face, weight and slant are
  stated rather than inherited. In an email there is no sheet foot, so the document appends
  an `Endnotes` block after the last section, each note carrying the `id` its marker links to
  and a link back. The text part prints `[7]` at the marker and a Notes block in every
  medium.
- **The marker takes the UA's `smaller`, not a size token.** Pinned to `size.type.micro`, a
  marker in 9.5px fine print was as large as the line it sat in. A relative size is right in
  every line, and `line-height: 0` stops it opening the line box.

## Contents (#183)

- **One partial, two owners.** `Contents` is a component the caller places, typically as an
  email's "In this issue". `ContentsPage` is the paged medium's region, the sheet after the
  cover. Both render `common/contents-list.html`, so they cannot drift.
- **The markup is the same in every medium.** The page column is one CSS rule in the paged
  skeleton, `leader(".") target-counter(...)` on each link's `::after`. The issue proposed a
  `{% if medium.paged %}` branch, and a rule the email never loads made the branch
  unnecessary.
- **It is structurally aligned.** An entry is a title, a leader and a page, left to right, so
  the list declares its own `left` in both spellings on a wrapping `div`. `TestTheBoundaryHolds`
  covers it. `ContentsPage` has no `align` for the same reason.
- **The region reads titles as facts.** `PagedDocument` hands `contents_entries` down, layered
  over the region's fields, so the list cannot restate a title the body spells differently.
- **Its heading is not a section title.** It has no `section-title` hook, so a running header
  never follows it.
- **It is opt-in, unlike the other paged regions.** `EmptyContentsPage` is the default,
  because a two-sheet factsheet is not improved by a third sheet that indexes it.

## Cross-references (#184) — and the one check that runs at render

The mechanism is a class hook, one CSS rule, one degrader rule and one validator. A caller
writes `a href="#exhibit-3" class="xref"` in a raw field, which the contract always allowed.
Paper appends " (p. N)". `format_link` spells a same-document link as its label alone, since a
fragment points nowhere in a plain-text part.

**The dangling-reference check is the one apparatus check that does not run in
`add_section`.** "Validation at construction" is a hard constraint, and this check is the
exception. The reason is that a reference may name a section not yet added: forward
references are ordinary prose, and only the finished tree can answer them. So
`Document.validate()` runs at the start of `render()` and `text()`, **before any template
loads**. That keeps the constraint's purpose: no render discovers a bad shape halfway through
a template. It is public, so a caller can check sooner. It reads every raw field, which
components and regions declare through `raw_html()`, the `images()` shape, plus
`header_disclaimer`. It catches the renumbering mistake: relabel "Exhibit" as "Table" and every
`#exhibit-n` in the prose is named.

## Running section header (#185)

- **The title reaches the margin through CSS, not the facts.** Which section a sheet holds is
  the page's own knowledge, not a fact about the document. `media.md` records the same.
- **Each box follows a string of its own** (`running-header`, `running-footer`), so the header
  can follow the section while the footer keeps the firm and the folio. The skeleton's single
  `.section-title h2` rule sets both. Two regions each writing that selector would overwrite
  each other.
- **The fallback took four probes to get right.** `label` shows on sheets before the first
  section, such as a contents sheet. Three simpler designs failed a case:
  - A `string-set` on the `body` or the document table wins on **every** sheet it spans.
  - A leaf element ahead of the cover opens a **blank sheet**, because the cover is a named
    page.
  - A single string seeded on a leaf after the cover hides the first section's title on the
    sheet they share, which the long table showed at once.
  
  The design that holds is a second string, `running-header-fallback`. It is seeded on a
  zero-height leaf after the cover and cleared to `""` by every section title. The box prints
  `string(fallback, last) string(section, first)`. It was probed with a cover and contents,
  with a cover only, bare, and with no titled section.
- **Each region still owns exactly one slot.** The two leaves are skeleton markup, like the
  slot names themselves. A second slot per box would have broken the rule
  `builder-architecture.md` tests.
- `a4_portrait`'s header follows, and `a4_long_table` pins the other half: a fixed header over
  a following footer. The paged region-completeness test reads the paged gallery, as standing
  rule 9 words it. A field on the shared base cannot be non-default on both boxes in one
  document without the two saying the same thing.

## Non-goals, as decisions

- **No index, bibliography or list of figures.** Each is a smaller later addition on this
  numbering, and a factsheet needs none of them.
- **No multi-level numbering** (`3.2.1`). Sections are flat, and the contents list is one level.
- **No footnote in an email as a footnote.** Endnotes are the honest degradation. A caller who
  wants per-exhibit qualification already has `disclosure`.
- **No link inside a note or a disclosure**, the same follow-up for both.

## What the epic leaves

- **A byte-verified diff is not a verified render, a third time.** The footnote marker's size,
  the parenthesised cross-reference ("(Exhibit 1 (p. 3))") and the chart that emptied a third
  of a sheet were all correct markup to every golden. The raster found each of them.
- **A fixture change can quietly retire a test's claim.** Adding a chart made A4 and the slide
  paginate to the same count. That silently dropped the claim "the same content on a shorter
  page needs more sheets". A tall chart was the cause, and moving it into a split kept both
  the numbering and the claim. When a count changes, ask what the old count was *saying*.
- **A test can be right about the claim and wrong about the scope.** The table-width test
  assumed every table on the body sheet is frame-wide. A table inside a column correctly fills
  its column, so the test now measures each table against its container. Perturbing the
  skeleton still names eight shrink-wrapped tables.
- **Probe the print engine before designing on it.** Every mechanism here was tried in a
  scratch document under WeasyPrint 70 before any code was written. `string-set` failed two
  intuitive designs that the specification would have endorsed.
