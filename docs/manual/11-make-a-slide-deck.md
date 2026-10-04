# 11. Make a slide deck

A deck puts one idea on each slide. Every slide has a title at the top and a footer at the
bottom with your firm's name and the slide's number. The deck opens on a title slide, can
mark each part with a divider slide, and closes on your disclosures. You build the slides
from the same sections and blocks as an email.

**Before you start:** a deck is meant to be sent as a PDF, so printing it needs the `[pdf]`
extra. Building and checking the slides works without it. See
[Reports and PDFs](07-reports-and-pdfs.md) for installing it.

```python
from pyhermes.builder import CardGroup, DataTable, FullWidth, TextBlock, TwoColumn
from pyhermes.builder.models import KpiItem, TableRow

facts = {
    "firm_name": "Acme Research",
    "campaign_name": "Q3 Strategy Review",
    "department": "Multi-Asset",
    "date_range": "October 2026",
    "header_disclaimer": "<p>For professional investors only. Not investment advice.</p>",
}
```

## How to build a deck

```python
from pyhermes.deck import Deck

deck = Deck(facts)
deck.add_divider("Where markets stand", "Levels, curve and premium")
deck.add_slide(
    [FullWidth(content=CardGroup([KpiItem("10Y gilt", "4.21%"), KpiItem("2s10s", "38 bps")]))],
    "The quarter in two numbers",
)
deck.add_slide(
    [
        TwoColumn(
            "50-50",
            left=TextBlock("<p><strong>Steepener.</strong> Own 30Y against 5Y.</p>"),
            right=TextBlock("<p><strong>Hedge.</strong> Hold breakevens.</p>"),
        )
    ],
    "What we would do",
)
deck.save("deck.html")
```

<!-- manual: needs pdf -->
```python
from pyhermes.pdf import save_pdf

save_pdf(deck, "deck.pdf")
```

**Result:** a 16:9 PDF of five slides: the title slide, the divider, your two slides and
the disclosures. Each slide after the divider says *Acme Research · Where markets stand* in
its footer, beside its number.

**Notes:**

- `add_slide` takes a list of sections, the same `FullWidth`, `TwoColumn` and other
  sections you use in an email, and the slide's title.
- The title slide reads the deck's subject, firm, department and dates from `facts`. To
  change its wording, pass `title_slide=TitleSlide(title="...", subtitle="...")`.
- The closing slide shows `header_disclaimer`. To rename its heading, pass
  `closing_slide=ClosingSlide(heading="Important information")`.
- To leave either out, pass `EmptyTitleSlide()` or `EmptyClosingSlide()`.
- For an older projector, pass `page=SLIDE_4_3` (from `pyhermes.deck`).

## How to add speaker notes

Notes travel with each slide. They are never printed and never appear in the plain-text
version.

```python
deck.add_slide(
    [FullWidth(content=TextBlock("<p>The long end did the work.</p>"))],
    "Why the curve steepened",
    notes="Pause here. Ask who holds duration.",
)
print(deck.notes())
```

**Result:** the notes for every slide that has any, each under its number and title:

```text
Slide 5: Why the curve steepened
--------------------------------

Pause here. Ask who holds duration.
```

## How to add an agenda

Put a `Contents` block on a slide. It lists every titled slide and divider after it, and in
the PDF each entry shows the slide's number.

```python
from pyhermes.builder import Contents

agenda = Deck(facts)
agenda.add_slide([FullWidth(content=Contents())], "Agenda")
agenda.add_divider("Markets")
agenda.add_slide([FullWidth(content=TextBlock("<p>Rates rose.</p>"))], "Rates")
```

## How to put a sidebar on a slide

**When to use this:** a slide has a main point and a short column of facts beside it, or two
halves that each hold more than one section.

**Steps:** pass `layout="sidebar"` or `layout="split"`, and the side's sections as `side=`.

```python
deck.add_slide(
    [FullWidth(TextBlock("<p>Rates have further to rise at the long end.</p>"), title="Our view")],
    "The view in brief",
    layout="sidebar",
    side=[
        FullWidth(
            CardGroup([KpiItem("10Y gilt", "4.21%"), KpiItem("2s10s", "38 bps")],
                      orientation="vertical"),
            title="In figures",
            highlight=True,
        )
    ],
)
```

**Result:** the main area takes two thirds of the slide and the sidebar the rest; `"split"`
gives two equal halves. Either region running past the footer names the slide, as a full
slide does. In an email or a report the slide's sections run main first, then the side.

## How to give a slide its source

**When to use this:** a slide of text, figures or several blocks needs a source, and no single
table or chart on it has a `source` line of its own.

```python
deck.add_slide(
    [FullWidth(content=TextBlock("<p>Ten-year yields rose 18 bps in the quarter.</p>"))],
    "The quarter in one line",
    source="Acme Research; Bloomberg",
    as_of="30 September 2026",
)
```

**Result:** one line of fine print just above the footer, reading *Acme Research; Bloomberg
as of 30 September 2026*. The slide's body gives up that line, so a slide that only just fit
before may now be too full; [check it](#how-to-find-a-slide-that-is-too-full).

**Notes:**

- A citation such as `[@boe2026]` works in a source, as in a table's, and resolves against a
  `Bibliography` anywhere in the deck. A footnote marker `[^1]` is refused.
- In the plain-text version the source follows the slide's content.

## How to put a picture on a slide

**When to use this:** to open a part on a photograph, or to set a picture beside your point.

**Steps:** pass `background_image=` and say whether the picture is `"dark"` or `"light"`, so
the type is set to read on it. Or pass `image=` and `image_side=` for a picture filling half
the slide.

```python
from pyhermes.builder.images import EmailImage

deck.add_slide(
    [FullWidth(content=TextBlock("<p>The long end did the work.</p>"))],
    "Where the curve stands",
    background_image=EmailImage.attached("photo.png", alt="The trading floor"),
    ground="dark",
)
deck.add_slide(
    [FullWidth(content=TextBlock("<p>The premium rose for a third quarter.</p>"))],
    "Beside the argument",
    image=EmailImage.attached("portrait.png", alt="The Bank of England"),
    image_side="left",
)
```

**Result:** the first slide is the photograph edge to edge, with its title and text in light
type over it. The second has the picture filling its left half, top to bottom, and the title,
text and footer in the right half.

**Notes:**

- The picture must travel with the deck: `EmailImage.attached(...)`, never `hosted(...)`,
  because the PDF is made without fetching anything.
- A picture needs one pixel for each pixel of slide it fills: 1280 wide for a full 16:9
  slide, 640 for half. Below that you get a warning, and below half of it an error.
- In an email or a report the slide shows its sections only, and the picture is left out.

## How to make a statement slide

**When to use this:** one number deserves a slide of its own.

```python
from pyhermes.builder import HeroStat

deck.add_statement(
    HeroStat("38 bps", "2s10s", "The steepest curve since 2022"),
    "The lead figure",
    notes="Let the number sit before saying anything.",
)
```

**Result:** the figure, very large, in the middle of a dark slide, with the footer but no
title. The title is what an agenda lists and what the plain-text version heads it with. In an
email the slide is just the figure.

## How to show the agenda on every divider, and count the slides

**When to use this:** a long deck, where the audience should see which part they are in, and
a footer that reads "4 / 12" under a confidentiality notice.

```python
from pyhermes.deck import DeckFooter

banked = Deck(
    facts,
    divider_agenda=True,
    footer=DeckFooter(counter="total", label="Strictly private and confidential"),
)
banked.add_divider("Markets")
banked.add_slide([FullWidth(content=TextBlock("<p>Rates rose.</p>"))], "Rates")
banked.add_divider("Positions")
banked.add_slide([FullWidth(content=TextBlock("<p>Own the long end.</p>"))], "Trades")
```

**Result:** each divider lists every part, with its first slide's number, and the part you are
in is set brighter than the rest. Every slide's footer ends *2 / 6*, *3 / 6* and so on, with
the label beside the firm's name. The title slide shows neither, as it has no footer.

## How to print a handout with your notes

**When to use this:** to rehearse from paper, or to brief a colleague with what you will say.

<!-- manual: needs pdf -->
```python
from pyhermes.pdf import save_handout

save_handout(deck, "handout.pdf")
```

**Result:** an A4 portrait PDF with one page for each slide: the slide, shrunk to the page's
width, and its notes under it. A slide without notes still gets a page. Pass
`page=LETTER_PORTRAIT` (from `pyhermes.builder.sizing`) for US Letter.

## How to find a slide that is too full

A slide never runs onto a second page. If its content does not fit, the bottom is cut off
in the PDF. Check for it before you send:

<!-- manual: needs pdf -->
```python
from pyhermes.deck import overflowing_slides

rows = [TableRow([f"Bond {n}", f"{n}.0"]) for n in range(40)]
deck.add_slide([FullWidth(content=DataTable(["Issue", "Weight"], rows))], "Every holding")
print(overflowing_slides(deck))
```

**Result:** `['slide 6: Every holding']`. Shorten the table, or split it across two slides.
`python -m pyhermes.check` reports the same thing as a `slide-overflow` error.

## Why a deck looks the way it does

- **The type is larger than in an email.** A deck uses the `presentation` size setting,
  made to be read on a projected slide. Only a deck can use it. You can still choose
  `"size_theme": "spacious"` or another setting for a deck.
- **There is no PowerPoint file.** A deck is shared as a PDF, as a report is. Your charts
  are pictures either way.
- **Footnotes are not allowed on a slide**, because the footer takes the bottom of the
  slide. Give the slide a `source=` line, or put the source in a table's or chart's own.
- **The handout is not a PowerPoint notes page.** It is the same slides, shrunk, with the
  notes you already wrote; there is still no `.pptx`.
- **The same slides work elsewhere.** A `Slide` added to an email or a report shows its
  sections and nothing else, so you can reuse them.
