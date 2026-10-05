---
paths:
  - "pyhermes/builder/apparatus.py"
  - "pyhermes/builder/document.py"
  - "pyhermes/builder/exhibits.py"
  - "pyhermes/builder/templates/analysis/figure-grid.html"
  - "pyhermes/builder/templates/common/source-line.html"
  - "pyhermes/builder/research.py"
  - "pyhermes/builder/templates/text/bibliography.html"
  - "pyhermes/builder/templates/text/glossary.html"
  - "pyhermes/builder/templates/common/notes.html"
  - "pyhermes/builder/templates/common/endnotes.html"
  - "pyhermes/builder/templates/common/contents-list.html"
  - "pyhermes/builder/templates/text/contents.html"
  - "pyhermes/builder/templates/document/regions/contents.html"
  - "pyhermes/builder/templates/document/regions/running-box.html"
---

# The document apparatus — numbers, notes, contents, references, sources

Epic #171 gave a document the apparatus a reader navigates by. #157 and #153 each deferred it by
name. Five sub-issues: exhibit numbering (#181), footnotes (#182), a contents list (#183),
cross-references (#184) and a running header that follows the section (#185). Epic #220 added
the long-form half on the same walk: a list of exhibits (#308), lettered appendices (#309),
citations and a bibliography (#310), a glossary (#311), and a research-note fixture (#312).
Epic #335 let exhibits group: lettered panels in one exhibit (#336), a chart's key in markup
(#337) and one source line for a section (#338), carried by the research note (#339).

| Apparatus | Paged | Email | Plain text |
|---|---|---|---|
| Exhibit number | "Exhibit 3 · …" on the heading line, `id="exhibit-3"` | the same | the same |
| Footnote | `float: footnote`, at the foot of the marker's sheet | endnotes after the last section | `[7]`, then a Notes block |
| Contents | `ContentsPage`, after the cover, with page numbers | the `Contents` component, a linked list | the titles, one per line |
| Cross-reference | "Exhibit 3 (p. 4)" | "Exhibit 3", linked | "Exhibit 3" |
| Running section | `string-set` from the current section title | none (no sheets) | none, by decision |
| List of exhibits | `ExhibitsPage`, or `ContentsPage(of="exhibits")`, with page numbers | `Contents(of="exhibits")` | the headings, one per line |
| Appendix | "Appendix A: Data sources", exhibits "A.1", `id="exhibit-a-1"` | the same | the same |
| Citation | "(Fama and French 1993)" or "[3]", linked to `ref-<key>` | the same | the same, unlinked |
| Bibliography | entries hung under their first line | the same | hung by four spaces, or under the label |
| Glossary term | `term-<slug>`, a two-column table | the same, stacked on a phone | "Term: definition" |
| Grid panel | "(b) Europe" over the panel, `id="exhibit-3-b"`, a reference reads its page | the same, stacked on a phone | "(b) Europe [alt]" under the heading |
| Section source | one fine-print line at the section's foot, kept with it | the same | the line after the section's blocks |

## The one rule: Python numbers everything but the page

**Numbering is computed in Python, once, so both projections agree.** A CSS counter would
number the HTML and leave the plain-text part unnumbered. An exhibit called "Exhibit 3" in
the PDF and nothing in the text is the divergence #116 exists to prevent. So `Document._walk()`
hands every part of the apparatus what only the whole tree knows, and the templates print what
they are handed:

- each labelled exhibit's `number`, counted per label in reading order;
- each `Footnote.number`, across the whole tree in reading order;
- each `Contents` component's entries, every titled section but its own, or every numbered
  exhibit;
- each appendix section's letter, and each exhibit's appendix (#309);
- the bibliography's citation order, and every component's `citing` (#310).

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

- **Superseded (#220): "No index, bibliography or list of figures."** It said each was a
  smaller later addition on this numbering. The list of exhibits and the bibliography are now
  that addition; **no index** still stands, for the reason it was given: a factsheet needs
  none, and an index is a page-number product only the print engine could finish.
- **Superseded (#309), by one bounded step: "No multi-level numbering (`3.2.1`)."** Body
  sections are still flat and unnumbered, and the contents list is still one level. What was
  reopened is a single letter level, for appendices only, below.
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

## The list of exhibits (#308)

- **The same walk read another way.** `Contents(of="exhibits", label=None)` lists every
  numbered exhibit in reading order, under the heading it prints (`Exhibit.listed()`: the
  numbered caption, markers removed). `label` narrows it to one sequence. `of="sections"` is
  the default and is byte-identical.
- **On paper it is a region in a slot of its own.** A research note wants both lists, and a
  region owns exactly one slot, so `ExhibitsPage` is a `ContentsPage` with
  `SLOTS = ("exhibits",)`, refusing `of="sections"`. The skeleton prints
  `{{ contents_html }}{{ exhibits_html }}` on one line, so an empty slot adds no byte and no
  golden moved. `ContentsPage(of="exhibits")` also works, for a document with one list.
- **The page numbers are the contents CSS, unchanged**: both share `common/contents-list.html`.

## Appendices, lettered (#309) — the reopened decision

**The reason to reopen:** a methodology paper's appendices are lettered, and their exhibits
are numbered within them. Typing "Appendix A" into a title gave the heading and left every
exhibit inside counting on from the body, "Exhibit 7" where a reader expects "A.1".

- **`Appendices(sections)` is a section list, as `Page` is.** It flattens in rendering, opens
  a fresh sheet on paper unless `break_before=False`, and emits no wrapper in an email. Each
  titled section opens the next appendix; an untitled one continues it, so the first must be
  titled. One per document, at most 26, and it cannot nest with a `Page` either way round.
- **The walk letters, the container prints.** `Container.letter` is set by the walk and
  `Container.heading()` formats it through `Config.appendix_heading`
  (`"Appendix {letter}: {title}"`). Every consumer reads `heading()`: the `h2`, the text
  part, both contents lists, and so the running header, which follows the `h2`. The section's
  anchor stays the slug of the caller's title, so a link to it survives a reordering.
- **An exhibit counts per label and appendix.** `Exhibit.appendix` is set by the walk;
  `numbered()` prints "A.1" and `resolved_anchor()` gives `exhibit-a-1`, which no body
  anchor can collide with.
- **#171's probes, re-run under WeasyPrint 70 with lettered anchors** (`test_appendices.py`,
  `TestOnPaper`): the running header on an appendix sheet reads "Appendix A: Data sources",
  `target-counter(attr(href), page)` resolves `#exhibit-a-1` to its sheet in a cross-reference
  and in the list of exhibits. No CSS changed; the fallback string still shows on the
  contents sheets.

## Citations and the bibliography (#310)

- **A citation is a record cited by key, unlike a note.** `Reference(key, authors, year,
  title, venue, url, doi)` is a frozen dataclass validated at construction. Authors are
  written "Surname, Given"; a citation prints the part before the comma. No BibTeX or CSL
  parser, by decision: a `[bibtex]` adapter can follow as `[data]` did.
- **`[@key]` follows the footnote marker's rules**: plain text in exactly the fields a `[^n]`
  works in, so the raw-HTML set stays at five. `[@a; @b]` cites several. A component lists
  those fields in `marked_copy()`, which is what the walk reads.
- **The walk resolves it.** It reads every key in reading order, hands the order to the one
  `Bibliography`, and hands every leaf the `Citing` it returns: each key's label and the
  style's punctuation. `split_markers` and `text_markers` take it, so the markup and the text
  part spell a citation the same way. A component rendered alone holds `UNRESOLVED`, which
  prints the key.
- **Two styles, each a curated house form.** Author-year cites "(Fama and French 1993)",
  shortening past `Config.citation_authors` (2) to "et al.", sorts by first author then year,
  and letters a collision "1993a". Numeric cites "[3]", numbering by first citation, reusing a
  number on re-citation, and listing the uncited after. An entry reads
  "Authors. Year. Title. *Venue.* link", the first author inverted and the rest in reading
  order, a DOI linked through doi.org ahead of a URL.
- **The entry is a hung `p`, not an `li`**: Outlook indents a list item by its own rules. The
  text part hangs a continuation by four spaces, or under the widest numeric label. Long links
  are never broken in the text part.
- **Refusals**: an unknown key is named by `validate()`, before any template loads; a second
  `Bibliography` is refused in `add_section`; a key listed twice, at construction.
- **A known limit, kept**: in the text part a numeric citation "[1]" and a footnote marker
  "[1]" look alike, the two lists headed "References" and "Notes". Respelling the marker would
  move every golden carrying a note; a document with notes reads better in author-year.

## The glossary (#311)

- **A term link is an ordinary link.** `Term(term, definition)` is anchored `term-<slug>`; a
  `Glossary`'s anchors join the document's through `Component.anchors()`, so
  `a href="#term-duration"` validates and a dangling one is named, by the existing check.
  No marker, and no automatic linking: the author links what they mean.
- **A layout table, not a data table**: a paged data table needs a `thead` a glossary has no
  use for. Both cells take the skeleton's `stack-column` class, so it stacks on a phone with
  no change to the `@media` block. Two terms with one anchor are refused at construction.

## The research note (#312)

`a4_research_note` and `research_note` build the same sections (`qa/fixtures/_research.py`):
citations, glossary links, a key-takeaways `Callout`, two body exhibits, a bibliography, a
glossary and two appendices. `test_research_note.py` reads each medium's exhibits, appendix
headings and citations against the other's, and reads both lists' page numbers back from the
PDF. Every other golden was byte-identical except the kitchen-sink family, which gained the
section rule 1 required. Since #339 it also carries a grid in the body (Exhibit 3, with a key
and a reference to its panel (b)), a section source line citing and calling a note, and a
grid in Appendix B (B.2); `test_grouped_exhibits.py` reads the panel reference's page back.


## Grouped exhibits (#335)

**A grid is one exhibit, and the walk stops at it.** `FigureGrid(panels)` holds two to four
`ChartBlock`s or `ImageBlock`s, and its `children()` are the panels, so the spacing checks and
the gallery tests see them. The walk reads `leaves()`, which since #336 treats **any `Exhibit`
as one stop even when it holds blocks**: the grid is numbered, listed and cited once, and a
panel is never numbered. `ChartBlock(legend=)` rides the same rule, its key a child the walk
never reaches. A panel's `label`, `anchor`, `caption`, `source`, `disclosure`, `notes` and
`wrap` are refused, because the grid carries one of each for all of them; its `subtitle` is
kept as its title. A decorative panel is refused, since a panel carries information.

**The panel anchor scheme: the grid's anchor, a hyphen, the letter.** `exhibit-3-a`, in an
appendix `exhibit-a-1-a`, and with `anchor="premia"` `premia-a`. A panel's letter is its place
in the grid (`(a)` to `(d)`), fixed at construction, so only the prefix is the walk's. Panel
anchors join the document's through `Component.anchors()`, as a glossary's terms do (#311), so
`href="#exhibit-3-b"` validates, a missing panel is named by `validate()`, and a section that
slugs to a panel's anchor is refused in `add_section`. An unlabelled grid with no anchor has
no panel anchors. Each panel's `id` sits on its own cell, so on paper `target-counter` reads
the panel's page, which `test_grouped_exhibits.py` and the research note read back from a PDF.

**One `figure` table holds the whole grid**, its caption row first, as a chart's does, so the
paged `.figure` rule keeps the grid on one sheet; a sweep test fails with that rule stripped.
The panels sit in one layout table a row, `stack-column` cells with a gutter cell between, so
a short last row keeps the others' width and a phone stacks them. The row tables separate
their borders: the model is inherited from the collapsing `figure` table, and a stacked cell
in a collapsing table drops its padding (#332). Each panel's image is capped at its cell,
`(cell - gutters) / columns`, in both spellings (#201). The gap under a panel is `block_gap`:
on paper and a slide under every row but the last, in an email under every panel but the last,
so stacked panels never touch; on a desktop that space falls below a row, as `Columns`' does.

**A section's source line is the exhibit's, a level up (#338).** `source`, `as_of` and
`source_notes` on every container render one `fine-print` line, "X as of Y" as an exhibit's
source reads, at the foot of the section: inside the content cell of a full-width section,
and as a table of its own under a split's columns, at the band's inset. The paged
`.fine-print` rule keeps it with the section above; a sweep test fails with that rule
stripped, in both shapes. A `[^n]` and an `[@key]` work in it as in an exhibit's source, so
`Container.footnotes()` and `marked_copy()` report it and **the walk reads sections as holders
too**, each after its own blocks (`Document._holders()`). The keyword is `source_notes`, not
`notes`, because a `Slide` is a `Container` whose `notes` are what the presenter says.

**On a slide the two lines are kept apart.** The slide's own `source` (#347) is its band over
the footer; a section's line sits at the section's foot inside the body, and the deck's walk
reads each section's line before the slide's. A deck still refuses a footnote, here as
anywhere.

**The caption heads the grid, and the rest of the shared copy sits beneath it.** #336 put
"one caption, one source line and one disclosure beneath all the panels". The caption went
above instead, in the figure table's first row as on a chart (#181), because it carries the
number, and the number heads an exhibit in every medium and in the list of exhibits; the source
and the disclosure sit beneath every panel, through the exhibits' shared lines.

**The plain text** prints a grid's heading once, then `(a) UK [alt]` a panel, a panel's key
after it, then the shared source and disclosure; a section's line follows its blocks.

**Non-goals, as decisions**: no nested grid, no table in a grid (a table is its own exhibit),
more than four panels, and a per-row source in a table, which is a footnote marker's job.
