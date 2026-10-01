# 10. Write a research note

A research note or a methodology paper needs more than sections: it cites its sources,
defines its terms, lists its tables and figures, and puts the detail in lettered
appendices. pyHermes numbers all of it for you, once, so the email, the PDF and the
plain-text part always agree.

Every example on this page adds to the one before it.

```python
from pyhermes.builder import (
    Appendices,
    Bibliography,
    Contents,
    DataTable,
    EmailBuilder,
    FullWidth,
    Glossary,
    Reference,
    Term,
    TextBlock,
)
from pyhermes.builder.models import TableRow

facts = {
    "email_subject": "Momentum After Costs",
    "firm_name": "Acme Research",
    "campaign_name": "Momentum After Costs",
}
```

## How to cite a source

**When to use this:** your copy refers to a paper, a report or a dataset, and the reader
should be able to find it.

Describe each source once as a `Reference`, with a short key of your choice. Then write
`[@key]` in your copy wherever you cite it, and put a `Bibliography` at the back.

```python
references = [
    Reference(
        "jt1993",
        ["Jegadeesh, Narasimhan", "Titman, Sheridan"],
        1993,
        "Returns to buying winners and selling losers",
        "The Journal of Finance",
        doi="10.1111/j.1540-6261.1993.tb04702.x",
    ),
    Reference(
        "carhart1997", ["Carhart, Mark M."], 1997, "On persistence in mutual fund performance"
    ),
]

summary = FullWidth(
    TextBlock(
        "<p>Momentum has earned a premium since the first evidence [@jt1993], "
        "and it survives the four-factor model [@carhart1997].</p>"
    ),
    title="Summary",
)
sources = FullWidth(Bibliography(references), title="References")
```

**Result:** the citations read "(Jegadeesh and Titman 1993)" and "(Carhart 1997)", each
linked to its entry, and the references are listed alphabetically by first author.

**Notes:**
- Write each author as "Surname, Given names". A citation prints the surname. An
  institution is written as its name alone.
- Cite several sources at once with `[@jt1993; @carhart1997]`.
- For numbered citations, "[1]", write `Bibliography(references, style="numeric")`. Sources
  are numbered in the order you first cite them.
- `[@key]` works wherever a footnote marker `[^1]` does: in a text block, a list item, and a
  table's or a chart's caption and source.
- If you cite a key the bibliography does not list, the build stops and names the key.

## How to define your terms

**When to use this:** your note uses words a reader may not know.

```python
terms = Glossary(
    [
        Term("Momentum", "The tendency of recent winners to keep outperforming recent losers."),
        Term("Turnover", "The share of a portfolio traded each month to keep it on its signal."),
    ]
)
method = FullWidth(
    TextBlock('<p>Costs depend on <a href="#term-turnover">turnover</a>.</p>'),
    title="Method",
)
glossary = FullWidth(terms, title="Glossary")
```

**Result:** each term sits beside its definition, sorted alphabetically, and the link in
the method section jumps to *Turnover*.

**Notes:**
- A term's link is `#term-` followed by the term in lower case, with spaces and punctuation
  turned into hyphens: "Winner-minus-loser" is `#term-winner-minus-loser`.
- A link to a term the glossary does not define stops the build and names the link.
- Pass `sort=False` to keep your own order.

## How to add lettered appendices

**When to use this:** detail a reader may skip, such as data sources or robustness checks.

Wrap the sections in `Appendices`. Each titled section starts the next appendix.

```python
coverage = DataTable(
    ["Region", "Stocks"],
    [TableRow(["United States", "3,412"]), TableRow(["Europe", "2,180"])],
    caption="Data coverage",
    label="Exhibit",
)
appendices = Appendices(
    [
        FullWidth(coverage, title="Data sources"),
        FullWidth(TextBlock("<p>The results hold in each decade.</p>"), title="Robustness"),
    ]
)
```

**Result:** the headings read "Appendix A: Data sources" and "Appendix B: Robustness", and
the table reads "Exhibit A.1". A table in the body still counts 1, 2, 3.

**Notes:**
- Link to an appendix table with `#exhibit-a-1`.
- A document has one `Appendices`, and its first section must have a title.
- On paper the appendices start on a new page. Pass `break_before=False` to run on.

## How to list your tables and figures

**When to use this:** a long note, where a reader wants to find an exhibit quickly.

`Contents()` lists your sections. `Contents(of="exhibits")` lists your numbered tables,
charts and images instead.

```python
note = (
    EmailBuilder()
    .metadata(facts)
    .section(FullWidth(Contents(of="exhibits"), title="Tables and Figures"))
    .section(summary)
    .section(method)
    .section(sources)
    .section(glossary)
    .section(appendices)
    .build()
)
note.save("note.html")
```

**Result:** "Exhibit A.1 · Data coverage", linked to the table.

**Notes:**
- `Contents(of="exhibits", label="Table")` lists only the exhibits labelled "Table".
- An exhibit is listed only if it has a `label`.

## How to print it with both lists

On paper, the contents and the list of exhibits each get a page after the cover, with page
numbers. Reuse the same sections in a `PagedDocument`.

```python
from pyhermes.document import ContentsPage, Cover, ExhibitsPage, PagedDocument

report = PagedDocument(
    {"firm_name": "Acme Research", "campaign_name": "Momentum After Costs"},
    cover=Cover(title="Momentum After Costs"),
    contents=ContentsPage(),
    exhibits=ExhibitsPage(heading="Tables and Figures"),
)
for section in (summary, method, sources, glossary, appendices):
    report.add_section(section)
report.save("note-print.html")
```

<!-- manual: needs pdf -->
```python
from pyhermes.pdf import save_pdf

save_pdf(report, "note.pdf")
```

**Result:** a cover, a contents page, a page listing every exhibit with its page number,
then the note. Each appendix page's header reads "Appendix A: Data sources" when the
running header follows the section.

**Notes:**
- Use `RunningHeader(follow="section")` to put the current section, or appendix, in the
  page header.
- A link with `class="xref"`, such as `<a class="xref" href="#exhibit-a-1">Exhibit A.1</a>`,
  gains the page number on paper: "Exhibit A.1 (p. 6)".
- In the plain-text part of an email, numbered citations "[1]" look like footnote markers.
  If your note has footnotes, the author-year style reads more clearly.
