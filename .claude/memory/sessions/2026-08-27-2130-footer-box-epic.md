# 2026-08-27 · footer box epic (#98)

Same branch as #87 (`claude/review-open-issues-rr8quq`, off `main` @ `e581ffb`).
Three commits: #99, #100, #101.

## What shipped

| | |
|---|---|
| #99 | `BoxSurface` mixin — `align` / `background_color` / `text_color`, mixed into **both** `Header` and `Footer`. `background_color`'s resolution moved out of a Jinja `default()` and into `theme_context()` |
| #100 | `LinkRow(copyright, links)` + `FooterLink(label, url)`. `Footer.link_row=None` builds the default row from the email's facts |
| #101 | `custom_footer` fixture + golden; the symmetric-boxes docs; the "compliance floor" correction |

## Decisions worth not re-deriving

**`REQUIRED_SLOTS` is about variants, not callers.** It was documented as a "compliance
floor" — which over-claims in exactly the direction that erodes into "the footer requires an
unsubscribe link". pyHermes does not decide what an email must *say*; it guarantees a variant
will not silently drop content the caller supplied, and that what renders is shape- and
safety-valid. Now a *Deliberate non-feature* entry so it is not re-litigated.

**Bounded colour deviation is a closed list of three**, and one sentence covers all of them:
*the caller supplies the ground.* `Container.background_color` (a band), `BannerPalette` (a
photograph), `BoxSurface`'s pair (the outer boxes). A fourth must name a ground the caller
supplies. **The pair never ships alone** — a background without the text colour on it is half
a decision.

**Parity of fields, not of tokens.** The mixin makes drift structurally impossible; the two
boxes still keep their own `theme_context()` and fall back to different tokens. Forcing one
token set on both would be parity as costume, and a test pins that they resolve differently.

**The `&copy;` entity stays in the default copyright.** A bare U+00A9 mis-decoded as latin-1
renders as a mojibake pair. The resolver emits the entity for the default and escapes a
caller's plain text, so the template reads one already-HTML key and never branches — which is
what let byte-identity and a safe (non-raw-HTML) caller surface both hold.

## Measured, against the issues' own claims — both false

- #98 warned the legal block "renders outside the main container", so a custom background
  would colour a wrapper-level band. It carries `class="email-container"` at `frame.width`:
  body and footer are **both 680px at x=160**.
- #99 hedged that accent links might fail on a custom ground. On a dark one they read at
  **3.87:1** — *better* than the **3.35:1** they get on the theme's own wrapper. (Neither
  clears 4.5:1; that is a pre-existing palette property, and contrast is a recommendation
  here, not a validated rule.)

## Traps

- **`{% endif +%}`** disables `trim_blocks` for one tag. Without it the newline after the
  inline separator conditional is eaten and the copyright joins the first link.
- The epic was filed before PR #86 and described a two-slot footer with a `MinimalFooter`.
  **Reconciled in a comment on #98, not by rewriting the body** — the original intent stays
  readable and each deviation is attributable. #100's *title* still says "compliance floor
  enforced at construction", contradicting its own corrected body; #101's AC references
  `_public_footers()`, which went away with `MinimalFooter`.
- `Footer.image` renders **above** the disclaimer (image → disclaimer → copyright, each
  independently optional and collapsing). Its docstring said only "above the copyright line",
  which is true but was read as ambiguous; corrected.

## Next

#53 (plain-text alternative) and #56 (typography) are the only parents left. The branch
carries #95–#101 and has no PR yet.
