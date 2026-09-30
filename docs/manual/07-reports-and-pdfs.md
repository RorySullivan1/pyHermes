# 7. Reports and PDFs

The sections you build for an email can also be printed as a paged report, with a cover,
page numbers, and tables that carry their headings onto every page. The blocks are the
same. Only the object you put them in changes.

**Before you start:** printing needs the `[pdf]` extra, and that needs system libraries
for laying out text (Pango, Cairo and HarfBuzz):

```bash
pip install -e ".[pdf]"
# Debian or Ubuntu:  sudo apt install libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0
# macOS:             brew install pango harfbuzz
```

On Windows, follow WeasyPrint's own installation guide for the libraries. If they are
missing, printing stops with a message saying so. Building the email still works.

```python
from pyhermes.builder import DataTable, FullWidth, TextBlock
from pyhermes.builder.models import TableRow
from pyhermes.document import BackMatter, Cover, PagedDocument, RunningFooter

facts = {
    "firm_name": "Acme Research",
    "campaign_name": "Quarterly Review",
    "date_range": "Quarter ending 30 September 2026",
}
summary = FullWidth(TextBlock("<p>The curve steepened.</p>"), title="Summary")
returns = FullWidth(
    DataTable(["Factor", "Q3"], [TableRow(["Value", "+2.4%"]), TableRow(["Momentum", "-1.1%"])]),
    title="Returns",
)
```

## How to print a report

```python
report = PagedDocument(
    facts,
    cover=Cover(title="Quarterly Review", subtitle="What the curve priced"),
    running_footer=RunningFooter(label="Confidential", show_page_number=True),
    back_matter=BackMatter(heading="Important Disclosures"),
)
report.add_section(summary)
report.add_section(returns)
report.save("review.html")
```

<!-- manual: needs pdf -->
```python
from pyhermes.pdf import save_pdf

save_pdf(report, "review.pdf")
```

**Result:** an A4 PDF with a cover page, your sections, *Confidential* and a page number
at the foot of every page, and a closing disclosures page.

**Notes:**
- Unlike an email, a report does not need `email_subject`.
- For US Letter or a landscape page, pass
  `medium=paged_medium(LETTER_PORTRAIT)` (from `pyhermes.document` and
  `pyhermes.builder.sizing`). `LETTER_LANDSCAPE` and `SLIDE_16_9` are there too.
- `report.add_page([...])` starts the sections you give it on a new page.
- A report has no 102 KB limit, but it cannot fetch images from the web. Use
  `EmailImage.attached(...)` for every picture in it.

## How to attach a PDF report to an email

**When to use this:** a short cover email, with the full report attached.

<!-- manual: needs pdf -->
```python
from pyhermes.builder import EmailBuilder
from pyhermes.delivery import build_message, save_eml
from pyhermes.pdf import pdf_attachment

cover_email = (
    EmailBuilder()
    .metadata({**facts, "email_subject": "Quarterly Review: the third quarter"})
    .section(FullWidth(TextBlock("<p>This quarter's review is attached.</p>")))
    .build()
)
message = build_message(
    cover_email,
    sender="research@example.com",
    to="clients@example.com",
    attachments=[pdf_attachment(report, "quarterly-review.pdf")],
)
save_eml(message, "review.eml")
```

**Result:** the cover email with `quarterly-review.pdf` attached. `pdf_attachment` makes a
PDF sized for reading on screen, with images reduced to keep the file small. Open or send
the `.eml` as described in [Check and send](06-check-and-send.md).

## Other printed forms

The project [README](../../README.md) covers two more:

- **A folded brochure**: a single sheet folded into panels, imposed for a printer with
  bleed and crop marks ([The same content, folded](../../README.md#the-same-content-folded)).
- **Contents pages, footnotes and cross-references** in a long report
  ([Numbers, notes, contents and references](../../README.md#numbers-notes-contents-and-references)).

The worked examples in [`examples/`](../../examples/README.md) include a quarterly review
and a two-page fund factsheet, each with its source script.
