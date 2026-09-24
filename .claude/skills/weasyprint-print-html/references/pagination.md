# Pagination — breaks, tables, and running content

Everything here is about one question: **what happens at the boundary between two pages?**
Screen CSS never has to answer it, which is why screen-first markup fails in print in ways
that look like styling bugs.

## The fragmentation hierarchy

Ordered by how dependably each construct survives a page break. Prefer the top.

1. **Block flow** (`div`, `p`, `section`) — fragments cleanly. The default for anything
   whose length you do not control.
2. **Tables with `<thead>`** — fragment cleanly *and* repeat their header. The only
   construct that does both; this is why tabular data belongs in a real table.
3. **Flex / grid inside a `break-inside: avoid` box that fits on one page** — safe because
   it never has to fragment.
4. **Flex / grid that must cross a boundary** — do not. They render (see `css-support.md`)
   but the fragmentation is not something to design against.

## Tables

```css
thead { display: table-header-group; }   /* repeats on every continuation page */
tfoot { display: table-footer-group; }
tr    { break-inside: avoid; }           /* never split a row across pages */
```

`display: table-header-group` is what makes the repeat happen, and it has nothing to act on
unless the markup actually has a `<thead>`. A header row left loose in `<tbody>` appears
once and then the continuation pages are columns of unlabelled numbers — lint **W003**.

Do **not** put `break-inside: avoid` on `table` itself. A long table *should* split; it is
the rows that must not. Verified: a 59-row table split 27/32 across two pages with the
header repeated on page 2.

## Break control

| Declaration | Use for |
|---|---|
| `break-before: page` | starting a section on a fresh page (`.page-break-before`) |
| `break-after: avoid` | **every heading level** — the highest-value rule here |
| `break-inside: avoid` | figures, key-facts blocks, stat rows, any table row |
| `orphans` / `widows` | how many lines may be left behind or carried over (3 is a good floor) |

A heading stranded at the foot of a page with its content overleaf is the most common
paged-media defect, and `break-after: avoid` on `h1…h4` fixes it. `print-base.css` sets it
on all four levels; a brand layer that redefines headings must keep it.

## Running headers and footers

Repeating content belongs in a `@page` margin box, never in a `position: fixed` element.

```css
@page {
  @bottom-right { content: "Page " counter(page) " of " counter(pages); }
  @bottom-left  { content: string(footer-label); }
}
.running-footer-label { string-set: footer-label content(); }
```

`counter(pages)` resolves to the real total, and `string-set` + `string()` carries text from
the document body into the margin box — that is how a distribution label or a product name
gets onto every page from one declaration. Verified working on both pages of a two-page
render.

## Sizing so nothing is taller than a page

`aspect-ratio` is **dropped** by WeasyPrint (`css-support.md`), so a figure sized by ratio
silently becomes its intrinsic size. Size in mm against the printable area instead:

- A4 portrait with the shipped 15mm side margins leaves **180mm** of usable width
  (`--content-width`).
- Usable height is 297 − 16 − 18 = **263mm**, and a running footer eats into it.
- **No single `break-inside: avoid` block may be taller than the printable height.** It
  cannot break and it will not shrink — it overflows and is clipped.

When a block is unavoidably tall, drop the `avoid` and let it fragment, or split the content
into two blocks yourself.

## Debugging a bad break

1. `scripts/render.py --json` — is the page count what you expected?
2. `scripts/snapshot.py` — rasterise and **look at the boundary pages**. No static check
   sees a bad break; this is the only step that does.
3. Add `break-inside: avoid` to the straddling block; if it then overflows, the block is
   simply too tall and must be split.
4. If a table is misbehaving, check `<thead>` exists before anything else.
