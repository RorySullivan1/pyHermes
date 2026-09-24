# CSS support in WeasyPrint — what works, what doesn't, what to use instead

Measured against **WeasyPrint 69.0** on 2026-09-15 by rendering one declaration at a time
and capturing the `weasyprint` logger, not copied from a blog post. The probe is
`../probes/probe_css_support.py`; re-run it after any WeasyPrint upgrade, because this table
is the linter's rule set and a stale table produces confidently wrong advice.

There are **three** outcomes, and conflating them is the usual source of bad guidance:

| Outcome | What WeasyPrint does | How you find out |
|---|---|---|
| **Supported** | Renders it | Nothing to see |
| **Dropped** | Rejects the declaration | Logs ``Ignored `prop:value` … unknown property`` |
| **Inert** | Parses and stores it, then it does nothing on paper | **Nothing.** Silence. |

The inert set is the dangerous one: the CSS looks accepted, so an author assumes intent was
honoured.

## Dropped — the declaration does not exist

| Property | Use instead |
|---|---|
| `box-shadow` | a `0.4pt` border, or a `.band` background-color block |
| `text-shadow` | a solid colour with real contrast |
| `filter` | pre-process the image, or overlay a background-color |
| `backdrop-filter` | a solid or gradient background-color |
| `mix-blend-mode`, `background-blend-mode` | one background-color, or a `linear-gradient` |
| `clip-path` | `border-radius` (supported), or crop before embedding |
| `mask` | crop the image before embedding |
| `perspective`, `transform-style` | nothing — 3D has no meaning on paper |
| **`aspect-ratio`** | **explicit mm dimensions** — this is exactly why `.figure` sizes in mm |
| `writing-mode` | nothing supported; restructure the content |
| `position: sticky` | a `@page` margin box, or `<thead>` for table headers |

`position: sticky` is rejected as an *invalid value*, not an unknown property — other
`position` values are fine.

## Inert — parses, warns about nothing, achieves nothing

`animation`, `transition`, `will-change`, `scroll-behavior`. Delete them. A PDF page does
not animate, interact, composite, or scroll. Lint reports these as **W007** precisely
because WeasyPrint will not.

## Supported — measured working, so do not avoid these

`transform` (2D), `border-radius`, `linear-gradient` backgrounds, `opacity`, `gap`,
`display: grid` + `grid-template-columns`, `display: flex`, `float`, `object-fit`,
`hyphens`, `orphans` / `widows`, `break-before` / `break-after` / `break-inside`,
`string-set`, `bookmark-level`, `columns`.

Two notes on that list:

- **`transform` is supported.** Advice to avoid all transforms in WeasyPrint is wrong and
  costs you design range for nothing.
- **`flex` and `grid` being supported is not permission to lay out a page with them.**
  They render; they do not *fragment* dependably across a page boundary. That is a
  pagination constraint, not a support one — see `pagination.md`.

## The rule that follows from all this

**Never infer support from the absence of a warning.** Dropped properties announce
themselves; inert ones do not; and a *supported* property can still produce a wrong page if
it has to break across one. The only check that sees the actual result is rasterising the
PDF and looking at the pages (`scripts/snapshot.py`).
