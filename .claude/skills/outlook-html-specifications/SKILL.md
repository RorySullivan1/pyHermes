---
name: outlook-html-specifications
description: >
  The rendering contract for HTML email in Microsoft Outlook — what classic Outlook's
  Word-based engine supports, strips, and mangles, and the MSO/VML dialect that works
  around it. Use this skill whenever HTML must survive Outlook: authoring or fixing an
  email/newsletter/OFT template that renders wrong in Outlook, deciding what CSS is safe,
  writing MSO conditional comments or `mso-` properties, adding a VML background or
  bulletproof button, fixing spacing/line-height/DPI/dark-mode differences, or answering
  "why does this look fine in the browser and broken in Outlook". Trigger on "Outlook
  renders this wrong", "MSO conditional", "VML button", "background image in Outlook",
  "[if mso]", "mso-line-height-rule", "email looks different in Outlook", "ghost table",
  "Outlook dark mode", "gaps between sections", "email shows as black". Boundaries: the
  overall email design system, cross-client (Gmail/Apple Mail) compatibility, and
  Python/VBA delivery automation are the email-newsletter skill; brand identity (colors,
  type, voice) is `branding`; driving Outlook itself from VBA is the vba-development
  family; the agent that *builds* Outlook-safe emails end-to-end is
  `outlook-html-designer`. This skill owns *what Outlook's renderer does to your HTML*.
---

# Outlook HTML — the rendering contract

Everything in this skill follows from one fact, documented by Microsoft: **classic Outlook
for Windows renders HTML mail with Microsoft Word's engine, not a browser.** Word became
Outlook's single reader *and* composer in Outlook 2007 so senders and recipients would see
the same thing (KB 2739063), and every classic desktop version since inherits it. Word's
engine is a document layout engine: it understands tables, inline formatting, and a
Microsoft-specific dialect (MSO properties, VML vector markup) — and it ignores most of the
CSS a web developer reaches for first.

Authorities to check when a claim here needs re-grounding: KB 2739063
(`learn.microsoft.com/troubleshoot/outlook/user-interface/shrink-to-fit-not-available-for-printing-emails`)
for the engine itself, and Microsoft's live catalogue of classic-Outlook rendering behavior
(`learn.microsoft.com/troubleshoot/dynamics-365/customer-insights/journeys/email/email-troubleshoot-rendering`)
plus its dark-mode guidance
(`learn.microsoft.com/dynamics365/customer-insights/journeys/email-dark-mode`).

## First — which Outlook are you targeting?

"Outlook" is several renderers wearing one name, and the contract differs:

| Client | Engine | This skill's rules |
|---|---|---|
| **Classic Outlook for Windows** (2016/2019/2021/365 desktop) | **Word** | Apply everything below |
| New Outlook for Windows, Outlook on the web | Browser-based | Modern CSS largely works; MSO conditionals are ignored (they are HTML comments to it) |
| Outlook for Mac, iOS, Android | WebKit/browser-based | Same — modern engines |

Microsoft's own rendering docs are split along exactly this line ("Outlook (Classic)" vs
the rest). The consequence: **you cannot drop the Word-engine workarounds just because new
Outlook exists** — corporate fleets run classic for years — and the workarounds must be
*additive*: MSO conditional content that classic sees and every other client skips. Ask
which clients the audience actually uses before optimizing; if classic Windows Outlook is
in the audience at all, it is the constraint that shapes the whole build.

## The support matrix — Word engine

**Honored (build with these):**
- `<table>`/`<tr>`/`<td>` layout, `width`/`height`/`align`/`valign`/`bgcolor` **HTML
  attributes**, `cellpadding`/`cellspacing`
- Inline `style=` for: fonts, colors, borders, `padding` **on `<td>`**, `text-align`,
  `line-height` (see the spacing model below), `background-color` (opaque only)
- `<img>` with explicit `width`/`height` attributes
- MSO conditional comments and `mso-` properties; VML

**Ignored or unreliable (never load-bearing):**
- `float`, `position`, flexbox, grid — no CSS positioning of any kind
- `max-width` — the single biggest responsive-email casualty; set fixed `width` and gate
  it with conditionals instead
- `margin` and `padding` on `div`/`p` — Microsoft documents the engine's support for
  standard CSS margins/padding as "limited"; **spacing lives on `<td>` padding**
- `background-image` in CSS — needs VML (below)
- `border-radius` — needs VML for buttons; square-corner fallback otherwise
- `@font-face` web fonts — falls back down the stack; see the font trap below
- Animated GIFs — classic Outlook shows the first frame only, so frame one must carry the
  message *(field-settled; consistently observed, not in the MS references above)*

The build rule that falls out: **a 600px fixed-width table skeleton, spacing as `<td>`
padding, everything inline, HTML attributes doubled up with CSS wherever both exist.**
Width 600–800px is Microsoft's own guidance; 600 is the safe end (preview panes, mobile).

## The MSO dialect

### Conditional comments — the routing mechanism

Word's engine reads conditional comments that every browser-based client treats as plain
comments. This is how Outlook-only fixes and Outlook-excluded content both work:

```html
<!--[if mso]>
  <p>Only classic Outlook (any version) renders this.</p>
<![endif]-->

<!--[if gte mso 9]>
  ... version-gated: Word engine 2007+ ...
<![endif]-->

<!--[if !mso]><!-- -->
  <p>Every client EXCEPT classic Outlook renders this.</p>
<!--<![endif]-->
```

The `[if !mso]` form needs the extra `<!-- -->` dance so browsers close the comment and
render the content. The workhorse pattern is the **ghost table**: a real multi-column
layout for modern clients, wrapped in an `[if mso]` table so Word gets columns it
understands:

```html
<!--[if mso]><table role="presentation" width="600"><tr><td width="300" valign="top"><![endif]-->
  <div style="display:inline-block; width:100%; max-width:300px; vertical-align:top;">…left…</div>
<!--[if mso]></td><td width="300" valign="top"><![endif]-->
  <div style="display:inline-block; width:100%; max-width:300px; vertical-align:top;">…right…</div>
<!--[if mso]></td></tr></table><![endif]-->
```

Modern clients see stacking-capable divs; Word sees a plain two-cell table. Neither sees
the other's markup.

### `mso-` properties worth knowing

| Property | What it does |
|---|---|
| `mso-line-height-rule: exactly;` | Makes `line-height` mean what it says (see spacing) |
| `mso-table-lspace: 0pt; mso-table-rspace: 0pt;` | Kills stray space Word adds beside tables |
| `mso-padding-alt` | Outlook-only padding value (e.g. on a button `<a>` whose padding others honor directly) |
| `mso-hide: all;` | Hides an element from Word's engine only |

## Spacing — the Word engine's model

Three documented behaviors drive every "the gaps are wrong in Outlook" report:

1. **Margins and padding on block elements are unreliable; `<td>` padding is not.**
   Microsoft's own fix is verbatim: *"add padding to the `td` elements of the tables that
   define the layout."* Structure spacing as table cells, not stacked divs with margins.
2. **Line height renders larger than in web clients** unless pinned:
   `style="line-height: 20px; mso-line-height-rule: exactly;"`. Never set `line-height`
   on a `<span>` expecting web behavior — set it on the block (`<p>`/`<td>`).
3. **Word breaks all words or none.** A long unbroken URL expands the column; and
   `&nbsp;` glues a phrase into one unbreakable "word" that does the same. Fix with
   `word-break: break-all;` on the specific `<p>`, and use `&nbsp;` deliberately.

Two spacing failure modes that surface only in the wild:

- **Forwarding inserts gaps between section tables.** Outlook pre-processes HTML on
  forward. Microsoft's workaround is an Outlook-only zero-height row appended to each
  outer section table:
  ```html
  <!--[if gte mso 9]>
  <tr style="padding:0; mso-line-height-rule:exactly; line-height:1px;" height="0"><td>&nbsp;</td></tr>
  <![endif]-->
  ```
- **Very tall single tables get split**, with visible seams, once total height runs to
  thousands of pixels (Word paginates internally; the commonly-observed threshold is
  ~1,790px per table). Keep each section its own table stacked in an outer wrapper —
  which you want anyway — and no single table ever hits the limit. *(Threshold is
  field-settled; the section-per-table structure is best practice regardless.)*

## Backgrounds and buttons — VML

**CSS background images do not render on sections/columns.** The replacement is VML, and
it carries documented constraints:

- A VML background (`<v:rect>`/`<v:fill>`) needs a **pre-calculated height** for the
  section — content of unpredictable height (personalized text) can overflow or clip it.
- **A transparent `background-color` is treated as a background *image*** by classic
  Outlook and inherits all these limitations. Use fully-opaque colors.
- **VML buttons and VML backgrounds are incompatible**: a rounded (VML) button sitting on
  a VML background loses its border radius.
- Rounded VML buttons **break when the email is forwarded** into other clients; if
  forwarding is likely, ship square buttons.

The button decision, in order of preference:

1. **Padded-`<td>` button** — a `bgcolor`ed cell with padding around a styled `<a>`.
   Square corners in classic Outlook, rounded (via CSS) everywhere else. No VML, no
   forwarding hazard. Default to this.
2. **VML `v:roundrect` button** — rounded in classic Outlook too, at the cost of the
   incompatibilities above. Use only when the design owner insists corners matter in
   classic Outlook specifically.

## Images, DPI, and fonts

- **Explicit `width`/`height` attributes on every `<img>`** — Word ignores CSS
  `max-width`, and an unsized image renders at natural size.
- **Host images externally; never base64-embed** — classic Outlook won't display
  data-URI images *(field-settled)*. Images are also blocked by default until the
  recipient allows them, so
  alt text (styled: `style="font-family:…; color:…"` on the `img`) must carry the message.
- **Windows display scaling ≠ 100% makes Outlook scale the layout** — px-defined CSS
  widths get scaled while some attribute widths don't, tearing the layout apart. The
  standard fix is the DPI normalization block in `<head>` plus width defined in *both*
  the HTML attribute and inline CSS on load-bearing elements:
  ```html
  <!--[if gte mso 9]><xml>
    <o:OfficeDocumentSettings>
      <o:AllowPNG/>
      <o:PixelsPerInch>96</o:PixelsPerInch>
    </o:OfficeDocumentSettings>
  </xml><![endif]-->
  ```
  *(Field-settled: the community-standard fix, consistently effective; not in the MS
  references above.)*
- **The web-font trap:** Word doesn't load `@font-face`, and — the trap — a font-family
  stack whose first entry it doesn't recognize can fall all the way to **Times New
  Roman**, skipping your fallbacks. Gate the safe stack for Outlook explicitly:
  ```html
  <!--[if mso]><style> * { font-family: Arial, sans-serif !important; } </style><![endif]-->
  ```
  *(Fallback-skip behavior is field-settled.)*

## Dark mode

Classic Outlook, new Outlook, and Outlook mobile all transform emails in dark mode, and
the sender cannot opt out. Microsoft's guidance:

- Clients **invert or replace background *colors* but generally preserve background
  *images*** — a brand-critical color block can be shipped as an image where it must
  survive.
- **Avoid pure `#000000` and `#FFFFFF`** — they trigger the most aggressive inversion.
  Use near-black (`#1A1A1A`) and off-white (`#F5F5F5`).
- Logos/icons: transparent backgrounds plus a subtle stroke/glow so they sit on either
  ground. Don't embed text in images — inverted grounds make it unreadable. Don't ship
  white icons on black.
- **Keep contrast at the AA bar in *both* modes** — 4.5:1 normal text, 3:1 large text and
  UI/graphics, per `branding` § *Contrast* (measure with `branding/references/contrast.py`). The
  wrinkle email adds: you author one palette but ship **two renderings**, and the dark one is
  produced by the *client*, not by you. Measuring only the colours in your HTML checks half the
  product — take the inverted rendering's actual colours off a dark-mode screenshot and measure
  those too. This is also why near-black/off-white beats pure `#000`/`#FFF`: it survives
  inversion with its ratios intact (`#1A1A1A` on `#F5F5F5` measures 15.96:1).

## Failure modes to check before blaming the design

- **The whole email body renders as solid black** → malformed HTML (unclosed tags,
  invalid nesting). Classic Outlook fails hard on syntax errors where browsers recover.
  **Parse-validate the HTML before any visual debugging.**
- Spacing wrong only in Outlook → margins on divs instead of `<td>` padding; line-height
  not pinned with `mso-line-height-rule: exactly`.
- Background/button missing only in Outlook → CSS background-image or border-radius with
  no VML path; or a transparent background color.
- Layout explodes at a colleague's desk but not yours → display scaling (DPI block +
  doubled widths); or an unbroken long URL widening a column.
- Wrong font, specifically Times New Roman → the fallback-skip trap; add the `[if mso]`
  font gate.
- Broken only after forwarding → the forwarding gap rows are missing, or rounded VML
  buttons.

## Out of scope

This skill is the *contract*, not the studio. What the email should say and look like —
layout systems, typography, the newsletter structure, cross-client (Gmail/Apple Mail)
compatibility tables, and delivery automation — is the `email-newsletter` skill; the brand
identity it applies is `branding`; automating Outlook itself (sending via `MailItem`,
`.HTMLBody`) is the vba-development family. The `outlook-html-designer` agent composes all
of those *with* this contract to build the artifact.
