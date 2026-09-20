---
paths:
  - "svc/builder/textgen.py"
  - "svc/builder/email.py"
  - "svc/builder/document.py"
---

**Since #162 the projection is `Document.text()`, not `Email.text()`.** The mechanism is
unchanged — a second projection of the same section tree, no template loaded, no theme, size
or font resolved — but it is shared by every medium, and a region's `text()` is what each
supplies. `.claude/rules/media.md` has the medium model; the element table and the policy
below are unchanged.

# The plain-text projection — a second walk of the same tree

### The plain-text projection — a second walk of the same tree

A production email is `multipart/alternative`: an HTML part and a `text/plain` part. Epic #53
built the second one, and the shape of it is the whole decision — the text part is a **second
projection of the section tree**, not a degradation of the render.

```python
html = email.render()      # the first projection
text = email.text()        # the second — header → banner → sections → footer
```

Generating text by stripping the rendered HTML is the obvious approach and it produces garbage
for exactly the components that matter most: a KPI strip becomes a column of orphaned numbers
and a data table loses the alignment that is the only reason to have one. So each class
projects itself, the same way each already renders itself and declares its own images. **A test
monkeypatches `TemplateEngine.render` to raise and projects every gallery fixture** — the claim
is asserted, not trusted.

- **Absence fails loudly** (standing rule 10) — the `images()` rule with the opposite default.
- **Generated, never hand-authored.** There is no `text_override`, and a test introspects every
  exported class to keep it that way: derived text cannot drift from the HTML's content.
- **Raw HTML degrades through one small parser.** The five blessed surfaces
  ([textgen.py](../../svc/builder/textgen.py)) reach text through `html_to_text()`, whose tag set is
  **closed** and says so in its docstring — the epic named it as the scope magnet.
- **Regions project their *resolved* state**, never raw fields: `resolved_title()`,
  `resolved_copyright_html()`, `resolved_links()`. An email that renames its masthead says the
  new name in both parts. Reading `title` directly would work for every email that sets one and
  print nothing for every email that does not.
- **A variant that fills no slot projects nothing**, checked once in `Region.text()` — the same
  rule `render_slots()` applies, so `EmptyHeader` omits the strip from both parts without
  anyone remembering to make it.
- **Chrome projects to nothing; content projects its alt text.** A logo, a masthead background
  and a footer sign-off mark are decoration. An `ImageBlock` or `ChartBlock` is the section's
  content, and `alt` is required at construction precisely so that projection is never empty.
- **The `&copy;` entity inverts, from one source.** The footer degrades
  `resolved_copyright_html()` back to text rather than branching, so the entity the HTML needs
  against latin-1 mojibake and the character the charset-declared MIME part needs come from one
  method that cannot drift.

**The formatting policy is decided once**, in [textgen.py](../../svc/builder/textgen.py)'s docstring
— 78 columns for prose, one blank line between blocks and two between sections, `=` under the
masthead and `-` under a section title, `format_link` inline and `link_line` in a list. The
alternative is a house format that drifts one projection at a time.

**Tables do not wrap, and that is the one place the policy yields.** Column widths come from
the widest cell; the first column is left-aligned and the rest right-aligned — not a guess
about the data, but the convention the HTML template already encodes with `loop.first`, read
off the same rule so the two projections cannot disagree about which column is the label. A
table wider than 78 columns overflows the line-width policy rather than corrupting the
alignment that is the only reason to render it.

**The three design axes do not reach the text part**, and a test asserts it: colour, density and
typeface are HTML concerns by construction, so one email projects identically under every
preset. That is what makes "one house format" a property rather than a coincidence — and it is
why this epic and #56 could have run in parallel, touching no surface in common.

- **The plain-text epic (#53) is complete** — #108 the degrader, #109 the projections, #110 the
  text goldens, #111 the `multipart/alternative` assembly. Four things it leaves:
  - **A second projection beats a degradation, and the test is what says so.** Stripping the
    render was the obvious approach and produces garbage for exactly the components that
    matter most. `TemplateEngine.render` is monkeypatched to raise while every fixture
    projects, so "structure, never the rendered HTML" is asserted rather than intended.
  - **The reserved seam worked.** `message.py`'s docstring had said for two epics that the HTML
    part would become half of an alternative and the related subtree would nest inside
    unchanged. It did, byte for byte, one level deeper, and **the adapters changed by zero
    lines** — both serialise through `to_wire_bytes()`. A seam named in prose and left alone is
    worth more than one discovered late.
  - **An orthogonal epic is one that shares no surface.** #53 touched no template and #56
    touched only templates, which is why the same email projects identically at every colour,
    density and font theme — a test asserts it, and it is what makes "one house format" a
    property rather than a coincidence.
  - **The `&copy;` question inverts between the two parts, and one method answers both.** The
    HTML needs the entity against latin-1 mojibake; the charset-declared MIME part needs the
    character. The footer degrades `resolved_copyright_html()` rather than branching, so the
    two spellings cannot drift.

## The blessed element set, and the formatting policy in full

Moved out of `svc/builder/textgen.py`'s module docstring by #138: the module states its purpose, and the reasoning that produced it lives here.

```
The HTML-subset degrader (#108): the builder's blessed raw HTML, as plain text.

Five surfaces in this package are raw caller HTML by documented contract —
``TextBlock.content``, ``Card.body``, ``NumberedItem.body``,
``Footer.disclaimer`` and ``header_disclaimer``. Every other value reaches a
template through ``escape_html``. The plain-text part (#53) therefore needs
exactly one converter, and only for those five::

    from svc.builder.textgen import html_to_text

    html_to_text("<p>Past performance is <strong>not</strong> a guide.</p>")
    # 'Past performance is not a guide.'

**It parses; it never greps.** ``qa/lint.py`` records what a regex costs here:
a ``grep`` for ``Contact Us`` matched inside an HTML comment and produced a
confident, wrong answer. :class:`html.parser.HTMLParser` is stdlib, so the
conversion costs no dependency — the same foundation and the same reason.

**The blessed set is closed, and that is a decision rather than a to-do.**
Epic #53 names this converter as its scope magnet, so the set is written down
here and refuses to grow:

===================  =========================================================
element              projection
===================  =========================================================
``p``                a paragraph break
``br``               a line break
``a``                carries its URL — see ``format_link``
``strong`` ``b``     markers **dropped**; plain text has no emphasis, and
``em`` ``i``         ``*stars*`` are a Markdown affectation, not house style
``ul`` ``ol`` ``li`` one ``- `` item per line
===================  =========================================================

An element outside that set **contributes its text and vanishes as markup**.
So a table pasted into a disclaimer degrades to its cell text run together —
imperfect, acceptable, and documented. The two exceptions are ``script`` and
``style``, whose content is dropped whole: a browser renders no text for
either, so keeping it would be *less* faithful rather than more, and a script
body reaching a plain-text reader is a defect rather than a degradation.

The alternative to a closed set is a converter that grows one caller's tag at
a time until it is a second rendering engine, which is the failure the set
exists to prevent. The one surface that *does*
carry ordinals — ``NumberedList`` — never routes through here: it holds them
as data and projects them itself (#109), which is why ``ol`` can take the same
``- `` as ``ul`` without losing anything a caller expressed.

**Character references decode to the characters themselves**, and this is
#100's decision deliberately inverted. That issue kept ``&copy;`` as an entity
in the HTML because U+00A9 mis-decoded as latin-1 renders as a mojibake pair.
The text part travels as a MIME part whose charset ``EmailMessage`` declares,
so the real character is correct there — and an undecoded ``&copy;`` reaching
a plain-text reader would be the actual bug. ``convert_charrefs=True`` does
this in the parser, before any of this module's logic sees the text.

**Output is deterministic**, byte for byte, for identical input. #110's text
goldens depend on it, and so does the whole golden discipline behind them.

The formatting policy
---------------------

Decided **once, here** (#109), rather than per component — the alternative is
a house format that drifts one projection at a time. Every ``text()`` in the
package composes these helpers instead of spelling their decisions itself:

``LINE_WIDTH = 78``
    Prose wraps here, one column under RFC 5322's 78-character soft limit for
    a line of a message. **Tables never wrap** — see :func:`table`.

*One* blank line between blocks, *two* between sections
    :func:`join_blocks` and :func:`join_sections`. The rhythm is what gives a
    plain-text email its structure, since it has no other typography.

Links: :func:`format_link` inline, :func:`link_line` on a line of its own
    Parentheses read better inside a sentence, a colon better in a list of
    destinations. A link with no URL emits its label alone, because an email
    is free to carry none.

A section title sits over a rule of its own length
    :func:`underline` — ``-`` for a section, ``=`` for the masthead, so the
    email's one top-level heading reads as one. Nothing else is decorated.

Chrome images project to nothing; content images project their alt text
    A logo, a masthead background and a footer sign-off mark are decoration a
    text reader loses nothing by missing. An ``ImageBlock`` or a
    ``ChartBlock`` is the section's *content*, and its ``alt`` is required at
    construction precisely so this projection is never empty.
```

## textgen.table — the three decisions, and how a row kind projects

Moved out of `svc/builder/textgen.py`'s `table` docstring by #138: the function keeps its contract, the reasoning lives here.

```
Aligned monospace columns: the epic's named fiddly spot.

    Three decisions, and the third is the one worth stating:

    * **Width comes from the widest cell in each column**, header included.
    * **Alignment is handed in, not guessed** (#117). ``aligns`` carries one
      of ``left`` / ``center`` / ``right`` per column, resolved by
      :meth:`~svc.builder.components.DataTable.resolved_columns` — the *same*
      call the markup reads, which is what keeps the two projections from
      disagreeing about which column is the label. Omitted, it falls back to
      the pre-#117 convention (first column left, the rest right), so a
      caller composing a table by hand still gets sensible output.
    * **Nothing wraps inside a cell.** A table wider than
      :data:`LINE_WIDTH` overflows the line-width policy rather than
      corrupting its own alignment — a wrapped cell destroys the column that
      is the entire reason to render a table as text at all. The policy
      yields to the alignment here, deliberately, and this is where it says so.

    A row's **kind** shows here too (#119), because a total that is
    indistinguishable from a data row in the text part is a total only half
    the readers can find:

    * ``total`` — a rule above it, matching the header's, so it is findable
      without counting rows.
    * ``subhead`` — its label alone on its own line, unpadded. Plain text has
      no merged cell to give it, and padding a heading into columns would
      read as a data row with two empty fields.

    Args:
        headers: One label per column.
        rows:    Cells per row, each row the same length as ``headers``.
        aligns:  One alignment per column, or ``None`` for the default.
        kinds:   One :class:`~svc.builder.enums.RowKind` per row, or ``None``
                 to treat every row as data.

    Returns:
        The header row, a rule, and one line per row. Empty if there are no
        headers.
```
