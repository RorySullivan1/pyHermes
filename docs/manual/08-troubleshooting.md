# 8. Troubleshooting

pyHermes checks your email while it builds, so most problems stop the build with a message
naming what to fix. Find the message, or what you are seeing, below.

**Contents:** [Errors while building](#errors-while-building) ·
[Size](#size) · [Images](#images) · [How it looks](#how-it-looks) ·
[Sending and PDFs](#sending-and-pdfs) · [Still stuck?](#still-stuck)

## Errors while building

### I get "Call .metadata() before adding sections"

**Likely cause:** `.section(...)`, `.banner(...)` or `.footer(...)` came before
`.metadata(...)`.

**Fix:** put `.metadata({...})` straight after `EmailBuilder()`.

### I get "'email_subject' is required and cannot be empty"

**Likely cause:** one of the three required facts, `email_subject`, `firm_name` or
`campaign_name`, is missing or blank. The message names which.

**Fix:** add it to your metadata. See the table in
[Build an email](02-build-an-email.md#how-to-write-the-facts-about-your-email).

### I get "unexpected keyword argument"

**Likely cause:** a misspelt metadata key, such as `"subject"` for `"email_subject"`.

**Fix:** check the key named in the message against the table in
[Build an email](02-build-an-email.md#how-to-write-the-facts-about-your-email).

### I get "must be a hex color"

**Likely cause:** a colour written as a name (`"green"`) or a short code (`"#0A0"`).

**Fix:** write all six digits: `"#00AA00"`. Or use `tone="positive"` and let the theme
choose the colour.

### I get "uses unsupported URL scheme"

**Likely cause:** a link that does not start with `http://`, `https://` or `mailto:`, such as
`www.example.com` or `file:///C:/report.pdf`.

**Fix:** write the full address, `https://www.example.com`. A file on your computer cannot
be linked from an email. Attach it instead
([Check and send](06-check-and-send.md#how-to-attach-a-file)).

### I get "'image.alt' is required and cannot be empty"

**Likely cause:** a picture with no description.

**Fix:** add `alt="..."` describing what the picture shows, or `decorative=True` if it is
only decoration.

### I get "cannot read image file"

**Likely cause:** the path is relative to the folder you ran Python from, not the folder
your script is in.

**Fix:** build the path from your script's location:

```python
from pathlib import Path

from pyhermes.builder.images import EmailImage

HERE = Path(__file__).parent        # the folder your script is in
logo = EmailImage.attached(HERE / "logo.png", alt="Acme Research", width=120)
```

### I get "WebP images are not supported" or "SVG"

**Fix:** save the picture as PNG (for charts and logos) or JPEG (for photographs).

### I get "A horizontal CardGroup requires 2–4 items"

**Fix:** split the figures into two `CardGroup`s in two sections, or stack them with
`orientation="vertical"`.

### I get "FullWidth.content must be a Component, got list"

**Likely cause:** a section was given a list of blocks, plain text or another section, where
it takes one block. The message names the slot: `TwoColumn.left`, `ThreeColumn.center` and
so on.

**Fix:** for several blocks in one cell, wrap them in `Stack([...])`. To split a cell, use
`Columns([...])` rather than putting a `TwoColumn` inside a section. Put text in a
`TextBlock`.

### I get "add_section takes a section, got TextBlock"

**Likely cause:** a block was added to the email directly.

**Fix:** wrap it in a section: `email.add_section(FullWidth(TextBlock("...")))`.

### I get "DataTable row 0 has 1 cells but there are 2 headers"

**Likely cause:** a row with fewer or more entries than the table has columns. Rows count
from 0, so *row 0* is the first.

**Fix:** give every row one entry per heading. Use `""` for an empty cell. A label band
across the table is `TableRow(["Equities"], kind="subhead")`.

### I get "has a marker [^1] but carries 0 note(s)", or "has no marker"

**Likely cause:** a `[^1]` marker with no note in `notes=[...]`, or a note that nothing
refers to.

**Fix:** give each marker a note, in order, and each note a marker.

### I get "anchor '…' is claimed twice in one document"

**Likely cause:** two sections in the same email have the same title.

**Fix:** give one of them its own `anchor="…"`, for example
`FullWidth(..., title="Outlook", anchor="outlook-credit")`.

### I get "links to #…, which nothing in this document defines"

**Likely cause:** a link to `#something` in the email, where no section or exhibit has that
name. Often an exhibit was renumbered.

**Fix:** check the name after `#`. A section titled *Factor Returns* is `#factor-returns`,
and the first table labelled *Exhibit* is `#exhibit-1`.

### I get "holds an <h2>; the section title owns that level"

**Likely cause:** an `<h1>` or `<h2>` in a `TextBlock`, a card's body or a numbered item's
body. The section's title is the heading at that level.

**Fix:** use `<h3>` for a subheading, and `<h4>` beneath it. For a heading of its own, start
a new section with a `title=`.

### I get "has not been rendered in an email client"

**Likely cause:** `"size_theme": "dense"`, or a custom spacing scheme, in an email.

**Fix:** use `"compact"` for a tighter email. `dense` is for printed reports. If you have
tested your own spacing in the mail programs your readers use, you can allow it with
`Email(facts, config=Config(allow_custom_email_density=True))`, where `Config` comes from
`pyhermes.config`.

## Size

### I get "SizeError" about the 102 KB Gmail clipping limit

**Likely cause:** Gmail cuts off any email over 102 KB and shows *"View entire message"*.
pyHermes stops rather than let that happen. The usual causes are `EmailImage.inline(...)`
pictures, very long text, or many large tables.

**Fix:**
1. Change any `EmailImage.inline(...)` to `EmailImage.attached(...)`. Attached pictures do
   not count towards the limit, and inline ones are the usual cause.
2. Move long detail into an attached PDF ([Reports and PDFs](07-reports-and-pdfs.md)), or
   link to it on your website.
3. To find which section is heaviest, run the check on your draft. It still reports on an
   email over the limit, lists the sections heaviest first, and exits with code 1:

   ```bash
   python -m pyhermes.check drafts/weekly.py:build
   ```

   ```text
   error: size-budget at whole document — over 102 KB. 149.5 KB total; heaviest regions:
        59.6 KB  section 3: Positioning
        40.1 KB  section 4: Appendix
        30.3 KB  section 2: Market wrap
        10.8 KB  section 1: Outlook
         2.9 KB  (document head)
   ```

   `python -m qa.preview drafts/weekly.py:build --lint` prints the same report. From Python,
   the same report comes from the email itself:

   ```python
   from pyhermes.builder import Email, FullWidth, TextBlock
   from pyhermes.check import render_for_check, size_report

   facts = {"email_subject": "Rates Weekly", "firm_name": "Acme", "campaign_name": "Rates"}
   email = Email(facts)
   email.add_section(FullWidth(TextBlock("<p>" + "word " * 30_000 + "</p>"), title="Long"))
   report = size_report(render_for_check(email), email.rendered_sections())
   print(report.summary())
   ```

4. `"size_theme": "compact"` does **not** help much here. It saves height, not bytes.

**If you only send through Outlook:** the limit is Gmail's. You can raise it with
`Email(facts, config=Config(size_limit_kb=200, size_warn_kb=180))`. Do this only if you
are sure no reader uses Gmail.

### I see "SizeWarning: Email size 95.3 KB (target < 90 KB)"

The email is close to the limit but will still send. Treat it as the time to trim, using
the steps above.

## Images

### My pictures are broken when I open the .html file

**Likely cause:** that is expected for attached pictures. They travel inside the message,
and a bare `.html` file has no message around it.

**Fix:** open the `.eml` file ([Check and send](06-check-and-send.md)), or run
`python -m qa.preview … --screenshot`, which puts them in place.

### My pictures do not show in Outlook

**Likely cause:** they are `EmailImage.hosted(...)`. Outlook hides pictures from the web
until the reader clicks **Download pictures**. Or they are `EmailImage.inline(...)`, which
Outlook never shows.

**Fix:** use `EmailImage.attached(...)`.

### My picture is the wrong size

**Fix:** set `width=` on the `EmailImage` to the display width in pixels: 616 for a
full-width section. Outlook ignores sizes set any other way.

## How it looks

### It looks different in Outlook from in my browser

**Likely cause:** Outlook for Windows lays out email with Microsoft Word, which ignores a
lot of web styling. pyHermes's own layout is built for it. Styling you add yourself inside
a `TextBlock`, such as `style="display:flex"`, may not survive.

**Fix:**
1. Run `python -m pyhermes.check …`. It lists anything Outlook will ignore or break.
2. Keep your `TextBlock` HTML to plain tags: `<p>`, `<b>`, `<i>`, `<a>`, `<h3>`, `<ul>`,
   `<li>`, `<br>`. Change colours and spacing through the theme ([Look and feel](05-look-and-feel.md)).
3. Send yourself a test and open it in Outlook.

### I see `&amp;` or `<b>` as text in a title or a table

**Likely cause:** HTML, or text you escaped yourself, in a field that pyHermes escapes for
you: a title, a label, a table cell or a caption.

**Fix:** pass plain text to those fields, with `&` and `<` written as they are. Only
`TextBlock`, a numbered item's body, and the header and footer disclaimers take HTML.

### The footer has no Unsubscribe or View in browser link

**Likely cause:** each default link only appears once its address is set.

**Fix:** set `unsubscribe_url` and `view_in_browser_url` in the metadata, or pass your own
links ([Build an email](02-build-an-email.md#how-to-set-the-footer)).

### A table runs off the side of the screen on a phone

**Fix:** keep tables to about five columns, or split one across a `TwoColumn`. See
[Tables and numbers](03-tables-and-numbers.md#how-to-keep-a-wide-table-readable-on-a-phone).

## Sending and PDFs

### The .eml opens as a received email, not a draft I can send

**Likely cause:** the message was not marked unsent, or your mail program is not classic
Outlook for Windows.

**Fix:** add `message["X-Unsent"] = "1"` before `save_eml`
([Check and send](06-check-and-send.md#how-to-open-your-email-as-an-outlook-draft)). With
classic Outlook on Windows, skip the file and
[create the draft directly](06-check-and-send.md#how-to-put-the-email-straight-into-your-outlook-drafts).
In other mail programs, send through Microsoft 365 or Gmail instead.

### I get "No module named qa"

**Likely cause:** the `preview` command was run from outside the `pyHermes` folder.

**Fix:** to check an email, use `python -m pyhermes.check C:\work\weekly.py:build`, which
works from any folder. Only the screenshots need the `pyHermes` folder and
`python -m qa.preview`.

### "create_draft" says it needs Windows and classic Outlook

**Likely cause:** you are on a Mac or Linux, you use the new Outlook, or the
`[outlook-desktop]` extra is not installed.

**Fix:** install the extra with `pip install -e ".[outlook-desktop]"` on Windows with
classic Outlook. Otherwise save the message with `save_eml` or send it through Microsoft 365.

### I get "Rendering a PDF needs WeasyPrint" or "could not load a system library"

**Fix:** install the extra from the `pyHermes` folder with `pip install -e ".[pdf]"`, then
the system libraries listed in [Reports and PDFs](07-reports-and-pdfs.md).

### I get "is not in this document's asset manifest" when printing

**Likely cause:** a picture in the report is `EmailImage.hosted(...)`. A PDF never fetches
from the web.

**Fix:** use `EmailImage.attached(...)` for every picture in a report.

## Still stuck?

1. Build the smallest script that shows the problem.
2. Copy the full error message, including the last line of the traceback.
3. Open an issue at
   [github.com/RorySullivan1/pyHermes/issues](https://github.com/RorySullivan1/pyHermes/issues)
   with both.
