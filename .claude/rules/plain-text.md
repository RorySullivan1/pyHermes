---
paths:
  - "svc/builder/textgen.py"
  - "svc/builder/email.py"
---

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
