---
paths:
  - "pyhermes/builder/components.py"
  - "pyhermes/builder/templates/analysis/**/*"
  - "pyhermes/builder/templates/media/**/*"
  - "pyhermes/builder/templates/common/disclosure.html"
---

# An exhibit's fine print — attribution, and the disclosure beneath it

`ChartBlock`, `DataTable` and `ImageBlock` each carry two kinds of fine print, and epic #153
exists because they were one. Both render beneath the exhibit, in `size.type.micro` /
`theme.text.light` italic; everything else about them differs.

| | Field | Answers | Renders |
|---|---|---|---|
| **Attribution** | `source`, `as_of`, `caption` | *where the figure came from* | one short line, left-aligned |
| **Disclosure** | `disclosure` | *what the reader must be told about it* | justified prose, last and finest |

**They coexist; they do not replace each other**, and the order on every exhibit is
**exhibit → attribution → disclosure**.

### Why it is not just a longer `source`

A financial newsletter cannot ship a returns table without the copy that qualifies the
figure. Before #154 there was nowhere to put it that *bound to the exhibit*:

- **Semantically it is not attribution.** `Source: Bloomberg` and *"returns are shown gross
  of the 0.75% fee"* are read by different people for different reasons — a compliance
  reviewer reads them separately — and a four-sentence disclosure jammed into the credit line
  reads as a mistake.
- **It belongs to the exhibit, not the document.** `Footer.disclaimer` and
  `header_disclaimer` already carry document-wide legal copy. Neither can say *"the returns
  in the table above are net of fees"* — that sentence has to sit under **that table**, or it
  qualifies nothing.

**So the steering is: figure-specific copy on the exhibit, document-wide boilerplate on
`Footer.disclaimer`.** That is a byte argument as well as an editorial one — a 400-character
boilerplate repeated under every chart marches an email toward the 102 KB clip, where the
footer costs it once. The `size-budget` lint attributes the bytes to the section that spent
them, so the mistake is visible rather than mysterious.

### `disclosure` is plain text, and that was the decision the epic turned on

`textgen.py` declares a **closed set of five** raw-HTML surfaces and says it "refuses to
grow". A disclosure is the obvious sixth candidate, because the single most common thing a
real disclosure does is link to the full disclosures page.

**It is plain text anyway, escaped by the partial like `source` and `caption`.** The
reasoning is reversibility, not squeamishness: widening a plain-text field to HTML later is
additive and back-compatible, and narrowing one is not. Shipping raw HTML and regretting the
XSS surface is the expensive direction of a decision that is hard to reverse *in spirit* —
callers will have markup in their data by then. Two consequences worth knowing:

- **A disclosure cannot carry an inline link today.** That is the accepted cost, and the
  upgrade path is a follow-up issue, not a workaround at the call site.
- **It renders in a `p`, not a `div`.** #130 forbids a `p` only for the *raw-HTML* five,
  whose documented shape is the caller's own paragraph tags. An escaped field has no markup
  to auto-close the wrapper, so it takes the same element its sibling attribution line does.

### One partial, because the fourth copy is the one that drifts

The attribution line is hand-written in three templates already. Adding a disclosure naively
makes four near-identical `p` blocks, so it is factored into
`templates/common/disclosure.html`, which all three exhibits `{% include %}`.

- **The context key is bare `disclosure`, even on `ChartBlock`**, whose other keys are
  `chart_`-prefixed. One shared partial means one agreed key; a prefix would have meant
  three partials, which is the thing being avoided.
- **The existing `source`/`caption` line was deliberately *not* refactored onto it.** That
  is byte-sensitive against every golden, and mixing "the mechanism arrived" with "the
  markup moved" is a diff nobody can review — #106's two-commit lesson.
- **The empty default costs zero bytes.** The `{% if %}` lives inside the partial, so a
  document setting no disclosure renders exactly what it rendered before. That is what let
  the field land without touching a single shipped email, and `test_an_unset_disclosure_
  renders_nothing_at_all` pins it per exhibit rather than trusting the observation.

### `justify` is fixed by the template, and is not a fourth alignment

`text-align: justify` is what distinguishes a disclosure from the credit above it — a block
meant to be *read*, not a trailing line. It sits oddly beside two standing decisions, and
both survive:

- **Both spellings travel together** (#125), so the partial emits `align="justify"` as well.
  Without the attribute a disclosure justifies in Gmail and reads ragged-right in Outlook's
  Word engine — the half-themed failure in the client hardest to check.
- **The caller-facing vocabulary stays three values.** `TextAlign` omits `justify` because it
  "does nothing to a single short line", and a disclosure is the one place in the package
  rendering multi-sentence prose narrow enough for it to do something. The audit in
  `tests/test_alignment.py` admits it through `_TEMPLATE_FIXED_ALIGNMENTS` — a *template* may
  fix an alignment the axis does not offer, a **caller** may not reach one — and
  `test_the_caller_facing_vocabulary_still_excludes_justify` is what stops that being read as
  permission to widen the enum.

The mobile cost is real and was measured rather than assumed: justified micro-type in a
narrow column opens inter-word rivers. At the 375px viewport the gallery's two-line
disclosure reads cleanly, so justify stays the default and `disclosure_align=` is a later,
additive call if anyone wants it.

### A footnote is not a disclosure, and the two coexist (#182)

A `disclosure` qualifies a whole exhibit, beneath it. A **footnote** qualifies one place in the
copy — a figure, a phrase, a source — and is numbered across the document: at the sheet foot
on paper, as endnotes in an email. Both are plain text for the same reason, so neither carries
a link, and the upgrade path for both is one follow-up. On an exhibit a marker may sit in the
caption or the source; `apparatus.md` has the mechanism.

### What #153 leaves

- **A completeness rule can couple two issues that looked independent.** #154 was specified
  to leave every golden byte-identical and #155 to opt a fixture in — but
  `test_every_data_table_argument_is_exercised` introspects `DataTable.__init__`, so the
  field and its fixture had to land together or the suite was red between them. The phasing
  was written before anyone read the test. **Check what the completeness rules can see
  before splitting an issue by "does the golden move".**
- **The check that fired was right about the axis and wrong about its scope** — the fifth
  instance of this in the repo, and the first where the fix was to *widen* a guard while
  adding a second one to keep the original claim pinned. Admitting a value to an audit
  without pinning what still excludes it is how a guard quietly becomes a comment.
- **A field shared by both media renders in both.** `disclosure` was designed for an email
  and reached the paged document for free, because the exhibits are the shared kit's. The
  paged golden pins it, so a future medium-specific fork of these templates cannot silently
  drop the compliance copy from the PDF.
