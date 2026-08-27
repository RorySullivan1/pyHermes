# 2026-08-27 · banner region epic (#88), end to end

Branch `claude/review-open-issues-rr8quq`, six commits on `main` @ `03f5c69`. No PR opened —
the user reviewed each sub-issue by screenshot instead.

## What shipped

| | |
|---|---|
| #89 | Split the masthead from the disclaimer strip. One region, **two slots** (`header_bar`, `banner`); `MinimalBanner` composes `TEMPLATE_PATHS` so the shared strip cannot drift. Golden movement: one line (a de-duplicated marker comment) |
| #90 | `Header` → `Banner` across the public API, **no deprecated alias** — the name is reserved for #87's strip region, so a shim would collide rather than ease migration. Protected tokens that must NOT move: `header_bar`, `header_disclaimer`, `header_bg_image_url`, `regions/header-bar.html`, `palette.header_bg`. Golden movement: one `<title>` |
| #91 | `Banner.title` / `.subtitle`, resolving *explicit → firm_name / campaign_name* into **`banner_title` / `banner_subtitle`** |
| #92 | `EmailMetadata.department`, a **fact**, joining `BANNER_FACTS` |
| — | (user request) The masthead became a **2×2 grid**: title\|logo, subtitle\|department |
| #93 | `BannerPalette` — eight roles, `None` meaning the theme's token |
| #94 | `custom_banner` fixture + golden, CLAUDE.md, README, this memory |

## Decisions worth not re-deriving

**Resolve into a key of your own when the fallback is a fact.** `Region.context()` layers
facts *over* presentation, so `title` resolving into `firm_name` would be a region shadowing a
fact — and it would render correctly for every email that never sets a title, which is exactly
why it needs a grep test rather than a convention.

**Resolve to a *total* object.** `BannerPalette.resolved(theme)` leaves no `None`, so the
template reads one object per colour with no per-colour fallback, and an override reaches the
markup by the same path an inherited token does. That is what made "unset renders
byte-identically" a property of the mechanism: repointing all eight sites with no fixture
opting in left every golden green, which covers all eight roles at once.

**Repoint first, opt in second.** Every sub-issue ran the goldens green with the templates
edited and no fixture changed, *then* moved a fixture. It is what makes the resulting diff
attributable to the feature.

**A Jinja comment, never an HTML one**, for notes inside a template — an HTML comment renders
and moves every golden for a line only maintainers read.

**The exception has a reason, not a shape.** `BannerPalette` is the standing
no-per-component-colour rule's single named exception because the masthead is the one place a
*caller* supplies the surface. The scoping is enforced: the palette covers the banner **slot**,
and the strip in the same region keeps the theme's tokens, with a test asserting it. "Now every
region gets a palette" is the failure mode, not the roadmap.

## Measurements (do not re-derive)

- **VML hero box.** `masthead_vml_height` is a `v:rect` the content cannot grow
  (`mso-fit-shape-to-text:false`). Stacked, the masthead measured **178.6 / 207.5 / 244.6px**
  against boxes of 150 / 180 / 220 — overflowing at every density, ~46px over with a
  department. Paired (2×2), **143.0 / 163.9 / 190.6px** — inside the box everywhere, and the
  department costs nothing because it shares a row. Overflow degrades quietly: the photograph
  stops, the flat band continues (the cell behind carries `palette.header_bg` as colour,
  `bgcolor` and the `v:fill` colour).
- **`white-space:nowrap` on the department reproduced #76.** "Global Macro, Rates and
  Cross-Asset Strategy Desk — EMEA" pushed a 375px viewport to **572px**. Wrapping costs the
  pairing nothing; now a regression test.
- **Alignment**, both variants × three densities: department right edge == logo right edge
  (Δ 0.0), title bottom == logo bottom, subtitle centre == department centre.

## Traps hit

- **The goldens cannot see layout.** Every layout question this epic raised was byte-identical.
  Alignment tests live with the screenshots and measure *edges*; `align="right"` sitting in the
  markup is what the goldens already pin and says nothing about where a box lands.
- **A size token that never renders fails its own test.** Merging the masthead rows killed
  `masthead_title_top` and `masthead_department_top`; they were deleted and `masthead_logo_top`
  became `masthead_top`. `NEVER_RENDERED` is the exemption list and wants a reason.
- **`kitchen_sink`'s banner had to become explicit.** The region-field completeness test reads
  the *built* region and demands every field differ from its default — and `title`/`subtitle`/
  `palette` have no flat spelling, since the flat keywords exist for a pre-split call site. The
  golden coverage that cost was replaced by `test_both_spellings_render_the_same_bytes`, which
  is stronger: a golden pins each spelling's own bytes and would not notice them diverging.
- **Three theming tests met #93 and each said something worth keeping** rather than being
  loosened: the colour audit gained a third legitimate source (read off the fixtures, not
  hand-listed); "every template reads the theme namespace" now admits `banner_palette`; and
  `test_a_theme_built_from_scratch_renders_everywhere` had to clear the fixture's override
  first, or an override would answer for the scrim and the test would prove nothing.
- **`PYHERMES_CHROMIUM`** is how to run the browser tests here — Playwright wants build 1234,
  the environment supplies 1194 at `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`.
- **CLAUDE.md had drifted**: `Email.header` survived #90's rename in prose. Caught by scripting
  the identifier check rather than reading — worth repeating on any docs pass.

## Next

**#87** — the strip becomes its own `Header` region, and it is the region mechanism's own test:
the strip already renders from its own template into its own slot, so promoting it should be a
change of *owner*, not of markup. `header_disclaimer` travels with it as a fact.
Then #98 (footer symmetry, needs reconciling against PR #86's merged code — it still cites
`MinimalFooter` and the two-slot footer, neither of which exists), #53, #56.
