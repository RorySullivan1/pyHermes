# Footer Rework — Design Spec

- **Date:** 2026-08-26
- **Status:** Draft for review
- **Supersedes:** parts of epic #55 (footer region) — see *Migration*.

## 1. Problem

The footer that epic #55 shipped is a single region holding a contact card
plus a legal block, with its wording split between the `Footer` object and
`EmailMetadata` facts. Three concrete problems surfaced in use:

1. **Too rigid.** The footer's look (background, border, an image) is not
   configurable per email; the design-system-is-not-a-parameter rule was drawn
   tightly enough that a caller cannot frame or tint the footer.
2. **Confusing naming.** `EmailMetadata.footer_disclaimer` reads as "the
   footer," but it is only the fine-print line — the footer is really contact +
   disclaimer + copyright + links.
3. **A rendering bug.** `footer_disclaimer` is raw HTML emitted *inside* a
   `<p>`. Passing block content (`<p>…</p>`) makes the browser close the styled
   wrapper early, so the disclaimer renders at UA-default 16px black instead of
   the intended 9.5px fine-print grey.

## 2. Goal

A **structured footer object with partial flexibility**: the caller controls
background color, a full-box border, an optional image, the disclaimer text,
and the link labels — but not fonts, geometry, or the block's structure. The
contact call-to-action leaves the footer and becomes ordinary body content.

## 3. Scope

**In scope:** a new `ContactBlock` body component; a reworked single-slot
`Footer` region; `base.html` footer-slot collapse; `EmailMetadata` field
changes; retirement of `MinimalFooter` and the two old footer templates;
golden/fixture updates; updating the two `examples/`.

**Out of scope:** header changes, the delivery layer, any container/component
work beyond `ContactBlock`, and reinstating a compliance floor (the disclaimer
is explicitly optional now).

## 4. Architecture

The composition model is unchanged in shape — `skeleton ← regions ← containers
← components` — but two pieces move layers:

```
BEFORE                              AFTER
body                                body
  …sections…                          …sections…
  footer.contact  (in body table)     ContactBlock          ← now a component
footer region                       footer region
  footer_contact  slot                footer  slot          ← single slot
  footer_legal    slot                  image? / disclaimer? / copyright+links
```

Moving the contact card into the body dissolves the two-parent-table problem
that forced #55's two-slot footer: the footer is now one self-contained table
below the body, which is what makes a full box drawable.

## 5. `ContactBlock` — new body component

- **Location:** `svc/builder/components.py` + template `text/contact-block.html`.
- **Fields (validated in `__init__`, escaped by the template):**
  - `heading: str` (required)
  - `description: str = ""`
  - `cta_label: str = "Contact Us"`
  - `cta_url: str` (required; scheme-validated via `models._validate_url`)
- **Markup:** the bordered/rounded contact card and the CTA button, including
  the Outlook `v:roundrect` dual-emission, migrated verbatim from
  `footer-contact.html`.
- **Usage:** `.section(FullWidth(content=ContactBlock(...)))` — placed by the
  caller, typically last, but not forced there.
- **Exports:** added to `svc.builder.__init__` `__all__`.

## 6. `Footer` — reworked region

Single slot, always rendered. Fields grouped by owner:

**Presentation (on `Footer`):**

| Field | Type | Default | Notes |
|---|---|---|---|
| `background_color` | `str` | `""` | Hex, validated; empty → `theme.palette.wrapper_bg`. |
| `border` | `bool` | `False` | Full box; opt-in so existing emails don't grow one. |
| `border_color` | `str` | `""` | Hex; empty → `theme.palette.rule`. Only used when `border`. |
| `image` | `str \| EmailImage` | `""` | Optional mark; an `IMAGE_FIELD` (flows through `images()`/`assets()`). |
| `image_alt` | `str` | `""` | Resolution: explicit → `EmailImage.alt` → `""`. |
| `image_width` | `int \| None` | `None` | Resolution: explicit → `EmailImage.width` → `DEFAULT_FOOTER_IMAGE_WIDTH` (120). |

**Wording (on `Footer`):**

| Field | Type | Default |
|---|---|---|
| `disclaimer` | `str` | `""` | Free-form HTML, emitted **raw and unwrapped**. Optional. |
| `unsubscribe_label` | `str` | `"Unsubscribe"` |
| `view_in_browser_label` | `str` | `"View in browser"` |

**Facts (stay on `EmailMetadata`, arrive via `footer_facts()`):**
`firm_name`, `current_year`, `unsubscribe_url`, `view_in_browser_url`.

**Render order (top → bottom) in `regions/footer.html`:**
1. **Image** row — centered `<img>` with a `width` attribute (Outlook ignores
   `max-width`), escaped `alt`. Rendered only when `image` is set.
2. **Disclaimer** row — the raw, **unwrapped** disclaimer in a cell styled
   `type.micro` / `text.fine_print`, centered. Rendered only when non-empty.
   Emitting it unwrapped is the fix for problem #3: plain text inherits the
   cell's small/light styling, and block markup renders correctly.
3. **Copyright + links** row — `© {year} {firm} · {Unsubscribe} · {View in
   browser}`. Always present. Links stay **text links** (not buttons).

**Box + background mechanics:**
- `background_color` → cell inline `style` **and** legacy `bgcolor` (Outlook),
  following the existing footer templates' precedent.
- `border=True` → `border:1px solid {border_color|theme.rule}` on the footer's
  outer cell. **Square corners** — no `border-radius` — for Outlook
  consistency.

**Region wiring:**
```python
CONTEXT_NAME   = "footer"
SLOTS          = ("footer",)
TEMPLATE_PATHS = {"footer": "regions/footer.html"}
REQUIRED_SLOTS = ("footer",)          # the slot is always filled
IMAGE_FIELDS   = ("image",)
```
`MinimalFooter` is removed — its only job was dropping the contact card, which
no longer lives here.

## 7. `base.html` / skeleton

- The two slots `footer_contact_html` + `footer_legal_html` collapse to a
  single **`footer_html`**, positioned below the body's "Main container" table
  in the wrapper (where the legal block already sat).
- `Email.render()` calls `self._footer.render_slots(engine,
  self._metadata.footer_facts())` and drops one slot key from the context.

## 8. `EmailMetadata` / facts

- **Remove** the flat footer/contact fields it currently hydrates a `Footer`
  from: `footer_disclaimer`, `contact_heading`, `contact_description`,
  `contact_url`, `contact_cta_label` (and any `contact_*` companions).
- **Keep** `firm_name`, `current_year`, `unsubscribe_url`,
  `view_in_browser_url`; `footer_facts()` returns exactly these four.
- The disclaimer text now lives on `Footer` (departs from "legal copy is a
  fact" — a conscious call: the footer is the structured object the caller
  configures).

## 9. Escaping & validation

- **`Footer.disclaimer`** — raw HTML field; escaping untrusted text is the
  caller's job (same contract as `TextBlock.content`). Emitted unwrapped.
- **`background_color` / `border_color`** — hex-validated at construction
  (`models._validate_color`).
- **`image`** — bare URL is scheme-validated; an `EmailImage` validated itself.
- **`ContactBlock`** — `heading`/`description`/`cta_label` escaped in template;
  `cta_url` scheme-validated at construction.
- All validation stays at **construction time**, per the repo's rule.

## 10. Migration (clean break — no compat shims)

Matching this repo's precedent (it removed `assembler.py` and `test_builder.py`
outright):

- **Delete** `MinimalFooter`, `regions/footer-contact.html`,
  `regions/footer-legal.html`.
- **Delete** the flat metadata fields listed in §8.
- **Move** the contact markup into `text/contact-block.html`.
- **Update** the two `examples/` (`market-snapshot`, `research-brief`) to the
  new API: footer disclaimers become inline text (also fixing the `<p>` bug
  seen there), and add a `ContactBlock` demonstration.
- **Regenerate** goldens; **repurpose** the `minimal_footer` fixture into a
  footer fixture that exercises `border`/`background_color`/`image`, and add a
  `ContactBlock` to `kitchen_sink`.

## 11. Testing

- **`ContactBlock`:** required-field validation, `cta_url` scheme rejection,
  rendered CTA (VML + anchor) present, escaping of heading/description.
- **`Footer`:** hex validation on colors; `image` URL/`EmailImage` handling and
  `assets()` manifest; empty vs non-empty disclaimer (row present/absent);
  `border` on/off markup; image present/absent; the footer always renders.
- **Escaping:** disclaimer raw + unwrapped; a block-level disclaimer renders
  without breaking its wrapper (regression test for problem #3).
- **Goldens:** updated snapshots; new/repurposed fixtures diff cleanly.

## 12. Resolved decisions (folded from brainstorming)

| Open item | Resolution |
|---|---|
| Links: buttons vs text | **Text links** (as today). |
| `border-radius` | **Square** everywhere (Outlook-consistent). |
| `border` default | **Off** / opt-in. |
| Footer image default width | **120px**. |
| `footer_disclaimer` on metadata | **Hard-remove.** |
| `MinimalFooter` | **Hard-remove.** |
| `contact_*` metadata fields | **Removed**, migrate to `ContactBlock`. |
| Old footer templates | **Retired** into `regions/footer.html` + `text/contact-block.html`. |
| Disclaimer location / requiredness | **On `Footer`; optional.** |

## 13. Risks

- **Golden churn is large** — every footer-bearing fixture moves. Mitigated by
  the `--update-goldens` flow and per-fixture review.
- **Outlook border/background fidelity** — solid border + `bgcolor` is
  well-supported; `border-radius` deliberately avoided.
- **Breaking change** — callers using `footer_disclaimer` / `contact_*` on
  `EmailMetadata`, or `MinimalFooter`, must migrate. Acceptable pre-1.0.
