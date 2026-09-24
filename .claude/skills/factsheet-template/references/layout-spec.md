# Layout spec — the two-page factsheet

A4 portrait. With `print-base.css`'s margins the printable area is **180mm × 263mm**, and a
running footer eats into the bottom of that. Verified with the sample context at two pages.

## Page 1 — the product

| Order | Block | Notes |
|---|---|---|
| 1 | **Masthead** | Product name, identifier · currency, **Data as of**, optional inception and rebalance, optional logo (32mm). Accent rule beneath. `break-inside: avoid`. |
| 2 | **Strategy** + **Key facts** | Two columns, 62% / 38%. Approved prose left; the key-facts table right. |
| 3 | **Performance chart** | `.figure`, full 180mm width. SVG only. |
| 4 | **Period returns** + **Risk statistics** | Two columns. Side by side **by necessity**, not taste — stacked, they pushed page 1 over its printable height and stranded the risk table alone on a page of its own. |

## Page 2 — the method and the legals

| Order | Block | Notes |
|---|---|---|
| 1 | **Methodology** | String or list of paragraphs. Starts the page via `.page-break-before`. |
| 2 | **Composition** | Name · weight · gradient bar. The bar is a background-color div, not an image and not `box-shadow`. |
| 3 | **Notes** | Optional numbered footnotes. |
| 4 | **Important information** | Approved blocks, verbatim. **Must be allowed to fragment** — never put `break-inside: avoid` on the disclaimer; long legal copy that cannot break overflows and is clipped. |

## Running footer, both pages

`audience_label · product.identifier` at bottom-left, `Page N of M` at bottom-right. The
label reaches the margin box through `string-set` on `.running-footer-label`, so it is
declared once and appears on every page — including pages added later as content grows.

## The mandatory blocks

The **audience label**, the **as-of date**, the **product identifier** and the **disclaimer**
are part of the layout, not optional fields. There is no code path that omits them. A
factsheet missing one of them is not a lighter-weight factsheet; it is a compliance
incident, which is why they are structural in the template and required in the contract.

## Chart specification

- **SVG only**, pre-rendered by the data layer. matplotlib is the default.
- Keep matplotlib's **`svg.fonttype = "path"` default** so chart text becomes outlines. This
  is what stops the chart depending on fonts installed on the rendering host — the chart is
  then immune to the font-fallback problem that affects the rest of the page.
- Size the figure so its intrinsic width matches the text column: **`figsize=(7.087, H)`**
  inches is 180mm wide. Then `width: 100%` in `.figure` scales nothing and the aspect ratio
  is whatever you chose. Around 2.5in tall keeps page 1 within budget.
- Do **not** rely on `aspect-ratio` in CSS — WeasyPrint drops it.
- 7pt tick and axis labels match the page's `--font-micro`.

## Growing the layout

Two pages is the target, not a constraint the template enforces. If content grows:

- The footer's `counter(pages)` updates itself; nothing to change.
- Long tables (composition especially) fragment correctly and repeat their header.
- **Watch the `break-inside: avoid` blocks.** Masthead, `.columns` rows and `.figure` cannot
  break. If one grows taller than the printable height it overflows rather than splitting —
  split the content yourself, or drop the `avoid`.
- Re-run the loop and **look at the page images**. Page count alone does not tell you a
  break landed well.
