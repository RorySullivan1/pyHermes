# 1. Quick start

Install pyHermes, build a one-page market note, and open it in your browser. It takes
about five minutes.

## Install

You need Python 3.11 or newer. pyHermes is not on PyPI, so install it from a copy of the
repository:

```bash
git clone https://github.com/RorySullivan1/pyHermes.git
cd pyHermes
python -m venv .venv
source .venv/bin/activate        # on Windows: .venv\Scripts\activate
pip install -e .
```

That is all an email needs. Some features need an **extra**, which is an optional add-on
you install the same way:

| To… | Install |
|---|---|
| Turn a pandas DataFrame into a table | `pip install -e ".[data]"` |
| Turn a matplotlib chart into an image | `pip install -e ".[charts]"` |
| Print a PDF | `pip install -e ".[pdf]"` (also needs Pango, see [Reports and PDFs](07-reports-and-pdfs.md)) |
| Take screenshots of your email | `pip install -e ".[qa]"`, then `playwright install chromium` |

## Build your first email

1. Create a file called `weekly.py` anywhere you like, and paste this into it:

   ```python
   from pyhermes.builder import CardGroup, EmailBuilder, FullWidth, TextBlock
   from pyhermes.builder.models import KpiItem


   def build():
       return (
           EmailBuilder()
           .metadata({
               "email_subject": "Weekly Market Note",
               "firm_name": "Acme Research",
               "campaign_name": "Weekly Market Note",
               "date_range": "Week ending 25 September 2026",
           })
           .section(FullWidth(
               title="This week",
               content=CardGroup([
                   KpiItem("S&P 500", "5,234", sublabel="+1.4%", tone="positive"),
                   KpiItem("UST 10Y", "4.28%", sublabel="+6 bps", tone="negative"),
                   KpiItem("VIX", "14.3", sublabel="-2.2 pts", tone="positive"),
               ]),
           ))
           .section(FullWidth(
               title="What happened",
               content=TextBlock("<p>Equities rose on softer inflation data.</p>"),
           ))
           .build()
       )


   if __name__ == "__main__":
       build().save("weekly.html")
   ```

2. Run it:

   ```bash
   python weekly.py
   ```

3. Open `weekly.html` in your browser.

**Result:** you see a dark slate masthead reading *Acme Research* and *Weekly Market Note*, a row
of three figures (green for good news, red for bad), a paragraph, and a footer with a
copyright line. To add **Unsubscribe** and **View in browser** links, give their addresses
(see [Set the footer](02-build-an-email.md#how-to-set-the-footer)).

<!-- TODO: screenshot of weekly.html -->

## What you just wrote

- **`.metadata({...})`** gives the facts about the email. `email_subject`, `firm_name` and
  `campaign_name` are required. The masthead shows the firm and campaign names unless
  you choose other wording (see [Change the masthead](02-build-an-email.md#how-to-change-the-masthead)).
- **`.section(FullWidth(...))`** adds a band across the full width of the email, with a
  title and one block inside.
- **`CardGroup`** is a row of two to four figures. **`TextBlock`** is a passage of text,
  written as HTML (`<p>`, `<b>`, `<a href="...">` and so on).
- **`.build()`** gives you the finished `Email`. pyHermes checks your content as you add
  it: a missing subject or a colour written as `green` stops the script straight away,
  with a message that says what to fix.

## Check it before you send it

From any folder, run the check against your file:

```bash
python -m pyhermes.check path/to/weekly.py:build
```

It saves the email into `output/` and checks it against the rules Outlook and Gmail
enforce. `No findings.` means it is safe to send. The part after the colon is the name of
the function in your file that returns the email. Open `output/weekly-build.html` in a
browser to look at it.

> **Tip:** `output/weekly-build.txt` is the plain-text version of your email, which
> pyHermes writes for you. It is what a reader sees if their mail program shows text only.

## Next steps

- Add more kinds of content: [Build an email](02-build-an-email.md).
- Open it in Outlook as a draft ready to send: [Check and send](06-check-and-send.md).
