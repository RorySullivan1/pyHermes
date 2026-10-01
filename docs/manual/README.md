# pyHermes — User Manual

Build a research email in Python that looks right in Outlook and Gmail, then send it.

## What this is for

pyHermes turns a short Python script into a finished HTML email: a masthead, sections of
figures, tables, charts and commentary, and a footer. It handles the parts that usually go
wrong. Outlook on Windows lays emails out with Microsoft Word, which ignores most modern web
styling, and Gmail cuts off any email over about 102 KB. pyHermes builds around both.

It is for anyone who sends a regular note to readers, such as a weekly market wrap, a
research brief or a client update, and wants to write it in code instead of rebuilding it
by hand every time. You describe *what* the email says. pyHermes decides how it is laid out.

The same content can also be printed as a PDF report. See
[Reports and PDFs](07-reports-and-pdfs.md).

## Where to start

New to pyHermes? Read [Quick start](01-quick-start.md) first. It takes about five minutes
and ends with an email open in your browser.

| Page | Read it when you want to… |
|---|---|
| [1. Quick start](01-quick-start.md) | Install pyHermes and build your first email |
| [2. Build an email](02-build-an-email.md) | Add sections, text, figures, the masthead and the footer |
| [3. Tables and numbers](03-tables-and-numbers.md) | Show a table, format figures, colour gains and losses |
| [4. Images and charts](04-images-and-charts.md) | Add a logo, a picture or a matplotlib chart |
| [5. Look and feel](05-look-and-feel.md) | Change colours, spacing, typefaces and alignment |
| [6. Check and send](06-check-and-send.md) | Preview it, open it as an Outlook draft, or send it |
| [7. Reports and PDFs](07-reports-and-pdfs.md) | Print the same content as a PDF, or attach one |
| [8. Troubleshooting](08-troubleshooting.md) | Fix an error message or an email that looks wrong |
| [9. Customise the layout](09-customise-the-layout.md) | Move one section's spacing, add a block of your own, or see what is fixed and why |
| [10. Write a research note](10-write-a-research-note.md) | Cite sources, define terms, letter appendices and list your tables and figures |

## Three words used throughout

- **Section**: one horizontal band of the email. It has an optional title and holds one,
  two or three pieces of content side by side.
- **Block**: one piece of content inside a section, such as a paragraph, a row of figures,
  a table or a chart.
- **Metadata**: the facts about the email: its subject, who it is from, the date. You give
  them once, and every part of the email that needs them reads them from there.

> **Note:** Every Python example in this manual is run by the test suite
> (`tests/test_manual.py`), so the examples match the code you have installed.

## Getting help

If this manual does not answer your question, check [Troubleshooting](08-troubleshooting.md)
first. If you are still stuck, open an issue at
[github.com/RorySullivan1/pyHermes/issues](https://github.com/RorySullivan1/pyHermes/issues)
with the error message and the smallest script that shows it.

For the reasoning behind each design choice, see the project [README](../../README.md).
