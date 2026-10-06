---
paths:
  - "qa/**/*"
  - "tests/**/*"
  - "pyhermes/check/**/*"
---

# The QA harness — gallery, goldens, screenshots, lint, preview

CI runs the first four on every PR, plus a `screenshots` job and the `wheel` job
([.github/workflows/ci.yml](.github/workflows/ci.yml)). `[dev]` alone must stay browser-free:
the screenshot tests skip rather than fail, and that is what proves `[qa]` is optional.

**To eyeball a change, run `preview`** — it is the loop, and it replaced the hand-rolled one
these docs used to prescribe:

```bash
python -m qa.preview kitchen_sink --lint --screenshot --open
python -m qa.preview drafts/weekly.py:build --lint      # your own draft, same command
```

Four things now stand behind that one command, and they answer different questions:

| | Answers |
|---|---|
| **The gallery** (`qa/fixtures/`) | *What do I render?* Four canonical emails, deterministic by rule, so every tool below has stable input |
| **The goldens** (`qa/fixtures/goldens/`) | *Did anything move?* Byte-identity on HTML **and** the asset manifest, for the whole gallery |
| **Screenshots** (`qa/screenshots.py`) | *How does it look?* Two viewports through headless Chromium — a review artifact, not a gate |
| **The lint pass** (`qa/lint.py`) | *Will it survive a real client?* The portability rules, with the size budget attributed to sections |

The `tests/` pytest suite remains the automated safety net, and it now carries the harness:
the goldens fail on any drift, and every fixture is linted on every run.

Slash commands (from the `.claude/` library): `/version-set`, `/version-ship`, `/reindex`.

## The fixture gallery — `qa/fixtures`

The shared set of representative emails every later QA tool consumes (#57, the first step of
epic #54). Sixteen fixtures, each a `build()` returning a built `Email`, enumerated through
`all_fixtures()` so a consumer never imports them one by one:

| Fixture | What it is for |
|---|---|
| `minimal` | The smallest valid email. Its value is negative space — it renders the skeleton with every optional region empty, so it catches a change to `base.html`'s defaults that a richer fixture masks by supplying the value itself |
| `kitchen_sink` | Every public component in every container ratio, `highlight=True` included, **and every `EmailMetadata`, `Banner` and `Footer` field set to a distinctive non-default value**. The fixture the golden is worth the most on, and #32's characterization email |
| `image_matrix` | All three embed strategies, plus the same attached image referenced twice — the shortest proof that `assets()` reports exactly the `cid:` references the HTML contains |
| `minimal_banner` | The `MinimalBanner` variant (#36, renamed in #90). Differs from the others in one argument, so its golden pins that a region swap changes the masthead and nothing else — no VML, no `background-image`, every email-level fact still present, and a CID logo attached exactly once through the region's own `images()` |
| `slate_theme` | The `slate` preset (#50). Differs from `kitchen_sink` in one metadata field, so its golden pins that a palette reaches *everywhere* — every component, every ratio, the dark-mode forcing block and the mobile media query — and that a caller's own `KpiItem` colour survives while an unset `Card.color` takes the theme's neutral |
| `compact_size` / `spacious_size` | The two density presets (#43). Each renders **`kitchen_sink`'s own content** at one non-default `size_theme` rather than restating it, so the pair diffs as a true A/B where every difference is the density: type, spacing, the component sizes that do not follow the global scale, the frame padding every column width is computed from, and `base.html`'s `@media` block moving with the rest. They are what retires `kitchen_sink`'s `size_theme` exemption — that fixture holds the field at its default on purpose, because it is the epic's byte-identity reference |
| `custom_banner` | Every banner axis at once (#94), which is what closes epic #88 — free-form `title`/`subtitle`, a `department`, an **attached** background image and a `BannerPalette` tuned to it. The one fixture a *cross-axis* regression shows up in, since no per-axis test can see an interaction. It also covers the only embed path the gallery otherwise lacked: a `cid:` background, reaching the manifest through `Banner.images()`' walk of `IMAGE_FIELDS` and appearing in both the CSS `background-image` and the VML `v:fill`. Its body is short on purpose — `kitchen_sink` exercises the component library, and a fat body here would make this golden noisy for reasons unrelated to the masthead |
| `no_header` | The `EmptyHeader` variant (#96) — a region that fills **no** slot, so the strip is genuinely absent rather than blank. Differs from `minimal` in one argument, and pairs the **default** banner on purpose (`minimal_footer`'s reasoning: two region choices swapped at once could not say which moved a byte). Its `header_disclaimer` is *set*, which is the point — an empty one would leave the strip absent either way, and the golden could not tell "the variant omitted it" from "there was nothing to render" |
| `custom_footer` | Both footer axes at once (#101), closing epic #98 — the coloured box surface (`align`, `background_color`, `text_color`) and a custom `LinkRow` with a link set that is neither the default pair nor the same length. Paired with the **default header** on purpose, so the two boxes are independent in the diff and their contrast is visible in a screenshot; it also carries the only `mailto:` link in the gallery, since a scheme check must keep passing what it allows and not only reject what it does not |
| `modern_fonts` | The `modern` preset (#107), the third axis's A/B. Renders **`kitchen_sink`'s own content** at one non-default `font_theme`, the `compact_size` shape exactly. It is the first artifact that can show `heading` and `body` are separate **roles**: they share a stack in the default, so until a preset moved one and held the other, nothing could tell them apart. It also pins that the `[if mso]` fallback moves with the rest — a literal there would leave an email custom-faced in Gmail and Georgia in Outlook, the half-themed failure in the client hardest to check. Its diff against `kitchen_sink` is *only* `font-family` values, and a test asserts that by stripping them and comparing the rest byte for byte |
| `rich_table` | Every `DataTable` axis at once (#121), closing epic #116 — a caption, a second **text** column, a **centred** column, per-cell colours *and* backgrounds, an alignment override, `subhead` groupings and a `total`. **Two tables on purpose**: the second has a **numeric first column**, which is the only way a golden can show that the row-header rule keys on the column's resolved *kind* rather than on position — with one table, "the first cell is a row header" and "a text first column is a row header" pin identically. Its body is short for `custom_banner`'s reason, and its theme, size and font stay default so no preset moves alongside a table axis |
| `aligned_layout` | Every alignment axis at once (#128), closing epic #124 — a centred section whose **title follows**, a component **overriding** its container, a **right-aligned** band holding a `CardGroup` and a `DataTable` that do not move, and aligned two- and three-column splits. The band is right-aligned on purpose: a centred one could not tell "the KPI strip kept its own alignment" from "it inherited the section's". Body short, theme/size/font default, for `rich_table`'s reasons. It also carries the gallery's only explicit `Container.background_color` — widening the field-completeness rule to containers found that the **original** entry in the closed colour list had never been set by any fixture |
| `composed_layout` | Every composition axis at once (#261): a `Stack` of text, a table and a note under one title; a 60-40 split at weights no preset names, with a `Stack` in its narrow column; the epic's acceptance case, a `Stack` of text, a table and figures in one column of a split with a `Columns` nested inside it; and a `FourColumn` row with one slot left empty. Theme, size and font default, so every line of its golden is composition. The screenshot tests' 375px overflow check covers it as a gallery member |
| `surfaced_layout` | Every surface axis at once (#265): a dark band whose type turns light by itself, with a table and a button on it; a split in the caller's own `text_color`, framed in a `border_color`, with figures keeping their own surface; a highlighted band framed on four sides; and a `Callout` in each tone, then a `Divider` and a right-aligned `Button`. Theme, size and font default, so every line of its golden is a surface. Its first screenshot found the table's caption dark on navy, which no test had seen |
| `minimal_footer` | A minimal-footer build (#66), the same argument at the other end. Paired with the **default** header on purpose: the two region choices are independent, and swapping both at once could not say which one moved a byte |

**There is a second gallery since #162**, `all_paged_fixtures()` — `a4_portrait` and
`slide_16_9`, the same content one `PageFormat` apart, and since #176 `a4_long_table`, which
exists to cross sheets. It is a separate registry rather than a
wider one on purpose: `all_fixtures()` feeds a dozen test modules whose assertions are about
*emails* (Outlook rules, a phone viewport, the `kitchen_sink` completeness rules keyed to
`EmailMetadata`), and widening it would drag every one of them onto a paged render before the
harness knows what a medium is. #165 is where the two become one registry keyed by medium.
`qa.preview` already spans both, because a viewer has no reason to refuse one.

**What the email lint makes of a paged document, measured rather than predicted** (#162): a
realistic paged render is **clean** against all ten rules — the shared component markup already
satisfies them and the Outlook-only rules are suppressed inside the conditional comments they
live in. Exactly one misfires, past a threshold nothing enforces here: `size-budget` is Gmail's
102 KB, and nothing clips a PDF. That is #165's problem, stated as a number.

**Determinism is the rule the gallery rests on**, and it is not a style preference: Content-IDs
are `sha256(bytes)[:16]`, so a fixture image that varies changes the `cid:` references in the
HTML and fails every downstream golden for a reason unrelated to the change under review.
Hence fixed strings, no clock, no `random`, and PNG bytes generated from constants by
[qa/fixtures/_png.py](../../qa/fixtures/_png.py) rather than checked in as binaries.

**`qa/` is a top-level package, not `pyhermes/qa` and not `tests/fixtures`** — the decision #57 left
to its PR. It is out of `pyhermes/` because the wheel ships `packages = ["pyhermes"]` and the gallery is
test data that would be dead weight for every installing user; it is out of `tests/` because
`tests/` is not importable from an installed position and the epic's later tools (#59
screenshots, #60 lint, #61 the `preview` CLI) are not tests. A root
[conftest.py](../../conftest.py) puts the repo root on `sys.path` so `import qa` does not depend on
hatchling's editable-install strategy happening to expose it. `qa/` **is** type-checked —
`mypy` runs over `["pyhermes", "qa"]`.

**Adding a component means adding it to `kitchen_sink()`; so does adding an `EmailMetadata`,
`Banner` or `Footer` field.** Four completeness tests introspect rather than hand-list: one
over every public `Component` subclass exported from `pyhermes.builder`, one over
`dataclasses.fields(EmailMetadata)`, a third asserting each metadata value *differs from its
own default*, and a fourth doing both at once over each **region** — parametrized across
header and footer, and read off the *built* region, so it holds however the fixture chooses
to supply it. A field set to its
default is one the golden cannot pin, because the render would not move if the default changed
underneath it. Only exemptions are named, in `DEPRECATED_COMPONENTS` (today: `KpiStrip`, whose
markup duplicates a section already in the gallery and which warns on construction), plus
`EmailMetadata.banner` and `EmailMetadata.footer` themselves — `kitchen_sink` builds both
regions **explicitly**, so their own fields are pinned by the per-region test rather than by
the metadata one — plus `ANCHORED_TO_THE_DEFAULT`, today `size_theme` and `font_theme`. Those
two are the one case where holding the default is the *point*: this fixture is what every
migration's byte-identity claim is measured against, so its density and its faces have to be
the ones the claim is about. Their non-default paths are pinned by `compact_size` /
`spacious_size` and `modern_fonts`, which render this same email one field apart. The flat, pre-split banner keywords used to be pinned by this fixture's
golden and are no longer: #91 gave the banner two fields with no flat spelling (the keywords
exist for a pre-split call site, and a field added after the split has none), so the coverage
moved to `TestTheFlatKeywordsStillWork` — where it is *stronger*, because a golden pins each
spelling's own bytes and would not notice the two diverging, while the test asserts they
**converge**.

Each `build()` also takes an optional `template_dir`, threaded to `EmailBuilder`, so the whole
gallery can be rendered against a *candidate* template set — which is the question a template
migration actually asks ("does this edit move any email?"), and how the golden harness's
detection test perturbs a real template instead of only the compared text. It stays out of the
`FixtureBuilder` alias deliberately: consumers must be able to call a builder with no arguments.

## Golden snapshots — `qa/goldens.py` + `qa/fixtures/goldens/`

The byte-identity bar the migration epics (#33, #41, #42, #49) all promise to hold, made
mechanical (#58). Three artifacts per fixture, because a render, its attachments and its
plain-text projection all drift independently:

| File | What it pins |
|---|---|
| `goldens/<name>.html` | The rendered HTML, byte for byte, no normalization |
| `goldens/<name>.assets.txt` | One tab-separated record per `ImageAsset`, **in manifest order** — content-id, MIME type, byte length, filename |
| `goldens/<name>.txt` | The plain-text projection (#110), byte for byte |

**What is pinned lives in one list.** `artifacts(name, email)` returns the `(label, path,
content)` triples, and `check_fixture()` and `write_fixture()` both walk it — so a fourth
artifact cannot end up checked but never written, or written but never checked.

Five decisions worth not re-litigating:

- **The manifest stores no image bytes.** They already live in the fixture that generates them,
  and a Content-ID is `sha256(bytes)[:16]` — different bytes cannot keep the same id, so id plus
  length catches everything a second copy would, at none of the repo weight.
- **Order is preserved, not sorted.** The header epic moves image aggregation between classes;
  a reordered `assets()` is a real change, and #32 asked for it to fail. A dropped or duplicated
  asset can also happen with the HTML *byte-identical*, which is why this artifact is separate.
- **Regeneration is opt-in and reviewed**: `pytest --update-goldens` is the only path (registered
  in the root [conftest.py](../../conftest.py), because pytest reads `pytest_addoption` only from the
  rootdir conftest). Nothing regenerates implicitly, and **a missing golden fails rather than
  being created** — one that writes itself on first run pins whatever happened to be true that
  day. *A golden diff in a PR is a claim that the visual change is intended*, and it is reviewed
  as one.
- **The text golden is a third file, not a section of the first.** Since #109 the text part
  is a *second projection of the section tree* rather than a degradation of the render, so a
  component's `text()` can change with the HTML byte-identical and vice versa — neither golden
  can see the other's drift. A test perturbs a component's projection and asserts only the
  `.txt` artifact moves; another perturbs a *fact* and asserts **both** do, which is the
  stronger claim, since a fact the email owns must reach both parts or they have come to
  disagree about what the email says.
- **A mismatch must be diagnosable.** "Bytes differ" on a 47 KB document costs the next reader an
  hour, so the report names the fixture, the artifact, the line, the byte offset, three lines of
  context and both versions of the line that moved. That the harness *bites* is tested by
  perturbing a real template and a real fixture and asserting the reported location, not assumed.

`qa/goldens.py` imports no pytest, so #61's `preview` CLI can check goldens without pulling in a
test framework.

**#32 is satisfied here, not separately.** #58 required that the two resolve to one harness;
#32 had not started, so `kitchen_sink` became the representative email it specified — exhaustive
over `EmailMetadata`, every container ratio, a hosted logo and an attached image. Do not add a
second `tests/test_golden_render.py`.

## Screenshots — `qa/screenshots.py`

Renders the gallery through headless Chromium at two viewports (#59), so a visual change is
reviewable without checking out the branch. `python -m qa.screenshots [fixture ...]` writes
PNGs plus a `run.json` into `output/screenshots/` (gitignored).

**The decision that shapes everything else: these are *checks*, not artifacts.** Nobody
diffs them, nothing commits them, and no test compares them to a stored copy. That is why
the browser build is **recorded rather than pinned** — buying cross-machine reproducibility
with a pinned container image costs more than the guarantee is worth for an image a human
glances at. What *is* pinned is what makes two runs on one machine comparable: viewport
sizes, `device_scale_factor=1`, full-page capture. `run.json` carries the Chromium build,
the Playwright version, the platform and the resolved executable — so if pixel-diff gating
is ever wanted (an explicit non-goal of #54's first cut), that recording is what says
whether two sets are even comparable, and pinning becomes a deliberate act rather than one
inherited by accident.

- **375px is the supported floor, and #133 is where that was decided rather than
  implied.** `SUPPORTED_WIDTHS` is the claim; a test asserts no gallery email exceeds any
  width in it, separately from the one that measures the captured screenshots — the two
  would drift the moment a supported width stopped being a captured one. Measured when the
  floor was set: 360px fails for `spacious_size` alone, by 6px, and 320px for five fixtures
  by 19–46px. **The obvious global fix is disqualified, not deferred**: adding
  `img { width:auto; max-width:100% }` under the breakpoint clears 360 outright, and with
  images blocked — Outlook desktop's default — it collapses every image to its alt-text box
  (128px to 63, 320 to 339, 80 to 165), destroying the display width `img-width-attr`
  exists as an *error* to enforce. A narrower floor needs per-image work, not one rule.
- **`cid:` is rewritten to a data URI for the screenshot only.** A browser has no MIME
  message, so every attached image would otherwise be a broken-image icon and the screenshot
  could not do its one job. The bytes come from `Email.assets()`, so the substitution is
  exact. `render()` and the goldens are untouched, and a test asserts that separation.
  Only `src` attributes are rewritten, never bare text — `image_matrix` titles a section
  "Attached (cid:)", and substituting on the substring would corrupt copy.
- **External requests are blocked**, so a run never waits on DNS for `example.com` and the
  render shows what a reader with images off sees — which is Outlook's default state.
- **The filenames say `chromium-desktop` / `chromium-mobile`, not `gmail` / `outlook`.**
  Chromium approximates Gmail in a browser and says nothing about Outlook's Word engine.
  Client compatibility belongs to the lint pass (#60), not to these images.
- **Playwright is the optional `[qa]` extra.** `pip install -e ".[dev]"` + `pytest` must
  stay browser-free — that is what proves the extra is genuinely optional, so the capture
  tests *skip* rather than fail, and CI's `screenshots` job is the only place they run.
  `PYHERMES_CHROMIUM` points the runner at a browser the environment supplies instead of one
  Playwright manages (read at use time, never at import).

## Lint pass — `pyhermes/check/lint.py`, re-exported as `qa.lint`

**It ships in the package since #278.** #57 kept `qa/` out of the wheel as test data, and
that holds for the gallery, the goldens and the screenshots. The rules are product behaviour
an installed copy needs, so they moved to `pyhermes/check/`, stdlib only.
`python -m pyhermes.check path.py:callable` builds a draft, writes its two parts and prints
the findings with `qa.preview`'s exit codes; `qa.preview` loads drafts through the same
`load_target`, so there is one path. `qa.lint` re-exports the module by its `__all__`, and a
test holds that each name is the same object. The wheel job runs the command from each
installed artefact. The command prints, so `test_warnings` exempts a `__main__.py` by name,
and a second test holds that no library module reaches one.

The portability rules the repo *documented* but only enforced where someone remembered a
test (#60). `lint_html(html)` returns `Finding(rule_id, severity, location, message)`;
`lint_email(email)` is the convenience wrapper. The suite lints every gallery fixture, and
#61's `preview` CLI reuses the same entry point on arbitrary HTML.

| Rule | Severity | What it catches |
|---|---|---|
| `img-width-attr` | error | An `<img>` with no integer `width=`. Outlook's Word engine ignores CSS `max-width`, so the display width must be an attribute |
| `img-alt` | error | Missing or blank `alt` — all a reader gets when images are blocked, which is Outlook desktop's default |
| `no-external-css` | error | `<link rel=stylesheet>` or `@import`, including inside an mso conditional |
| `outlook-unsupported-css` | error | `display:flex/grid`, `position:absolute/fixed` in an inline style |
| `outlook-line-height` | error | A **unitless** `line-height`; Outlook Classic ignores it. `0` is allowed |
| `outlook-transparent-background` | error | `background-color` carrying an alpha channel — Outlook demotes it to a background image |
| `outlook-caption` | error | A `caption` Outlook can see, **emails only** (#403). The Word engine draws a nested table's caption above the copy before it and outside its frame; hide it with `mso-hide:all` and give Outlook an `[if mso]` copy. Suppressed inside `<!--[if !mso]><!-->` |
| `empty-url` | error | `url()` with nothing in it; a client may resolve it against the message body |
| `table-role` | error | A layout table with no `role`, **and** a data table carrying one (#114) |
| `table-structure` | error | A data table with no `thead`, **paged documents only** (#176). A print engine repeats only a `thead` on each sheet |
| `table-header-tier` | error | A `colspan` outside a `thead`, a header tier whose spans miscount the columns, or a spanning `th` without `scope="colgroup"` — every medium (#223) |
| `vml-fill-empty-src` | error | A `v:fill` with `src=""` inside `[if mso]` (#150) — `empty-url`'s case, in the one place that rule cannot reach |
| `vml-fill-frame-without-src` | error | A `v:fill` claiming `type="frame"` with no `src` (#150). Outlook paints a broken-image placeholder over the shape rather than falling back to `color`/`opacity` |
| `size-budget` | warn/error | The 90/102 KB thresholds, **attributing the bytes to each body section and to the section-marker regions** (#259) |
| `slide-overflow` | error, or warn | A slide whose copy runs past its body, **decks only** (#297). It needs a layout, so `layout_findings(document)` runs it, from `lint_document`, the check and `preview --lint`; without `[pdf]` it is one warning saying the deck was not measured |

Seven decisions worth not re-litigating:

- **`table-role` fires in both directions, and that is what makes it a rule rather than a
  chore.** A check that only demanded `role="presentation"` would be satisfied by marking
  *every* table — which strips the semantics from the one table a screen reader should
  actually navigate. So an unmarked layout table is an error and a marked *data* table is an
  error, and `th` is the discriminator: it distinguishes the two kinds in this codebase
  exactly, and it is the same signal a reader uses. The check runs at the **closing** tag,
  because that is when the verdict is known, but reports the opening one, because that is
  where a reader has to go. The open tables are a stack: the gallery's one real data table
  renders inside two layout tables, and a flat flag would mark all three as data.
- **It parses, it never greps.** The repo learned this the expensive way — a `grep` for
  `Contact Us` matched inside a section-marker comment and produced a confident, wrong
  answer. `html.parser.HTMLParser` is stdlib, so the check costs no dependency.
- **Every rule carries its source**, in `SOURCES`, and a test asserts every rule that can
  fire has one. A rule asserting something about a mail client that nobody can trace is a
  preference wearing a rule's clothes. Most citations are Microsoft's own Outlook Classic
  troubleshooting document; the two image rules cite the repo's own established decisions.
- **`max-width` is deliberately NOT denied.** The templates pair it with a `width=`
  attribute on purpose, so a blanket rule would fire on correct code — and a noisy rule gets
  switched off, which is worse than no rule. `img-width-attr` covers what actually matters.
- **`DEFERRED_RULES` is a recorded decision, not an oversight — and it is now empty.** #60
  shipped green by *filing* the three findings the templates violated rather than arriving
  red, because a linter that arrives red teaches everyone to ignore it. All three were #78
  and all three are fixed, so all three rules moved into `SOURCES`. The mechanism stays for
  the next such finding, which belongs there rather than shipped red or quietly dropped. Two
  tests hold the shape: nothing may sit in both places, and the three rules #78 unblocked
  must be *shipping* rather than merely gone.
- **An Outlook rule does not fire on markup Outlook cannot see.** `<!--[if !mso]><!-->` is
  *downlevel-revealed* — the comment ends immediately, so what follows is real HTML to any
  parser, correctly, since every client but Outlook renders it. The rules in
  `_OUTLOOK_ONLY_RULES` are suppressed between such a conditional and its `<![endif]`. The
  set is **named, not matched on the `outlook-` prefix**: `img-width-attr` is motivated by
  Outlook too and deliberately keeps firing there, because a width attribute is good practice
  in every client. This is what lets the masthead scrim satisfy
  `outlook-transparent-background` by being hidden from Outlook rather than made opaque —
  which would have painted over the very photograph it exists to darken.
- **`size-budget` extends `_validate_size`, it does not reshape it.** That method is a
  `@staticmethod` on purpose and its messages are asserted by existing tests. The linter adds
  the part `render()` never had: *which region* spent the budget. Regions run marker to
  marker, and a marker must contain a letter — the templates also use `<!-- ══════ -->` as
  decorative rules, and counting those made the heaviest "region" a row of box-drawing
  characters, a breakdown that names nothing.

**Markup inside `<!--[if mso]>` is not linted** as standard HTML. `HTMLParser` hands a
conditional comment over as text rather than tags, which is the behaviour wanted: the block
carries Outlook-only VML, so judging it by standard-HTML rules would fire on markup that is
correct *because* it is non-standard. `no-external-css` still reads comment text, since an
`@import` hidden in a conditional is just as external.

**The two VML rules are the second such exception, and the shape is the rule** (#150). They
reach into comment text for two named defects rather than opening the block to linting — the
policy above is right, and a rule that grew into judging VML generally would fire on markup
that is correct precisely because it is non-standard. `vml-fill-empty-src` exists because
`empty-url` already denies `url('')` in the CSS half two lines away, and the VML half went
unguarded — a rule that stops at the edge of a comment is a rule the same defect walks around.
**It caught all eight affected gallery fixtures** when run against the pre-fix templates, which
is how it was checked rather than assumed.

**`vml-fill-frame-without-src` is what the first fix needed and did not have.** Gating `src`
alone satisfied `vml-fill-empty-src` and still destroyed the masthead: `type="frame"` with
nothing to frame makes the Word engine paint a broken-image placeholder over the whole shape —
no band, no scrim, dark title text on white. A rule that is satisfied while the banner is
visibly broken is a rule with a hole in it, so the companion rule closes it. Its scope is
pinned the same way: the frame-with-no-`src` fires, a real `src` passes, a solid fill (the
shape the fix now emits) passes, and a `v:rect` is untouched. **Both rules were checked by
running them against the markup they describe**, not by argument — which is also how the
underlying defect was found.

## The preview CLI — `qa/preview.py`

One entry point for the loop the docs used to prescribe by hand (#61):

```bash
python -m qa.preview --list
python -m qa.preview kitchen_sink --lint --screenshot
python -m qa.preview drafts/weekly.py:build --lint --open
```

It writes **both** projections — `output/<name>.html` and `output/<name>.txt` (#110). An email
has two readable parts, and writing only the HTML would leave out the half no screenshot and no
lint rule can show you.

**It composes; it never reimplements.** Fixtures come from `all_fixtures()`, findings from
`lint_html()`, images from `capture_emails()`. Tests assert the HTML it writes equals
`Email.render()` byte for byte **and** the text equals `Email.text()`, because the one thing
that would make this tool worse than useless is being a second rendering path — and since
#109 there are two projections it could be a second path for.

That rule earned its keep immediately: `capture_gallery()` could only screenshot names in the
registry, and **a user's draft never is one** — so `qa/screenshots.py` gained
`capture_emails(mapping)`, keyed by email rather than by fixture name, and `capture_gallery`
became a thin wrapper resolving names through the registry. The gap was fixed in the module
that owned it rather than routed around in the CLI.

Four decisions:

- **Two target forms, told apart by the `:`** — a bare name is a gallery fixture; a
  `path/to/module.py:callable` is any zero-argument callable returning an `Email` *or* an
  `EmailBuilder`. Both are public API, so a caller should not have to remember which their own
  function returns. Split on the **last** colon after any Windows drive (`C:/` or `C:\`) is
  taken off, so a drive letter is never the separator, even with no callable (#372). The output name is `{module_stem}-{callable}`, so two files both defining
  `build()` do not collide in `output/`.
- **Exit codes are the interface**: `0` clean, `1` lint errors, `2` unbuildable or
  unresolvable. Warnings alone do not fail. That is what lets it run in a hook rather than be
  read by a human every time.
- **A missing browser is a skip, not a failure.** `[qa]` is optional by design, so
  `--screenshot` reports and carries on — and a test asserts that skip does *not* mask a lint
  error, since the two flags are independent.
- **A builder error prints its own message and exits 2** — no traceback wall for what is
  nearly always a data mistake. `EmailBuilderError` raised while *importing* a target module
  propagates as itself rather than being flattened into "failed to import": the builder names
  the field, and that is the useful message.

**No console script**, deliberately. #57 put `qa/` outside the wheel because the gallery is
test data; an installed `preview` entry point would contradict that, so the module form is the
interface. This is the placement decision #61 said to inherit.

- **The QA harness (#54) is complete**, and it changes how the visual epics discharge their
  own acceptance criteria:
  - **A visual epic gets its eyeball artifacts from the screenshot runner**, not from ad-hoc
    `.save()` calls. `python -m qa.preview <fixture> --screenshot` locally; CI uploads the
    whole gallery on every PR. Side-by-side theme review is two runs of one command, and
    #43's density claim is legible straight off the image heights: 2516 / 3030 / 3731 px for
    the same email at compact / standard / spacious.
  - **Migration PRs cite gallery-wide goldens, not a single email.** "Byte-identical" means
    every gallery fixture plus its asset manifest — a container-template edit that one
    email's ratios never exercise no longer slips through. Both theme epics discharged their
    claim this way: #46 moved one comment and nothing else; #45 moved nothing at all.
  - **A theme lands with a fixture.** Epic #54 anticipated "one per theme as themes land",
    and all five now exist — `slate_theme` for the palette, `compact_size` / `spacious_size`
    for the two densities, `modern_fonts` for the faces, with `minimal_banner` the worked
    example of a fixture that pins one region variant. #88 added the other kind: `custom_banner` pins a *combination* rather than
    a variant, because each of its four axes has its own tests and none of them can see an
    interaction.

- **The golden characterization test (#32/#58) has landed** — the gate every template
  migration waited on is now in the suite. Everything touching `base.html` or `EmailMetadata`
  still sequences rather than interleaves (several epics contend on those two surfaces), but
  each of them now inherits byte-identity proof for free: change a template, and the gallery
  tells you which email moved and where. The delivery epic (#52) is complete and contends
  with none of them.

- **The two findings the harness surfaced are closed** (#76, #78) — the first work in a
  while whose *point* was a golden diff rather than its absence. Both had been deferred by
  every epic for the same reason: each changes rendered output, and every epic claimed the
  gallery stays byte-identical at each step. What they leave behind:
  - **Only a browser could have caught #76.** The HTML was byte-identical to its golden the
    whole time the mobile KPI strip overflowed its viewport, the size gate passed, and no
    unit test measures layout. The regression test therefore lives with the screenshots, and
    it asserts *equality* with the viewport where the old one asserted `>=`.
  - **Measure the fix, do not reason about it.** #76's issue recommended dropping
    `width:100%` on the grounds that a `display:block` element fills its container. In
    Chromium a `<td>` re-displayed as block inside a table shrink-wraps instead, collapsing
    the cell to a ~120px stub. `box-sizing:border-box` was the fix; the measurement is in the
    commit.
  - **A rule can be satisfied by scope, not only by value.** #78's `rgba()` scrim could not
    be made opaque — it exists to darken a photograph, and an opaque colour would paint over
    it. Outlook already draws that scrim from `v:fill`, so the CSS copy is now
    downlevel-revealed, and the linter learned to model `<!--[if !mso]><!-->` rather than
    the rule being weakened.
  - **The size epic made #78's biggest finding small.** 107 unitless `line-height`
    occurrences would have been a template-wide sweep before #45; afterwards leading is a
    token, so it was one `percent` filter at the boundary. The care was all in *inheritance*
    — a unitless value is inherited as a number and recomputed per element, a percentage as
    the computed px — which is why the nine elements that inherited their leading now state
    it explicitly, and why the change is pixel-neutral rather than merely legal.

## The golden harness — the three artifacts and why each is pinned separately

Moved out of `qa/goldens.py`'s module docstring by #138: the module states its purpose, and the reasoning that produced it lives here.

```
Golden snapshots over the fixture gallery (#58) — and #32's characterization test.

Three artifacts are pinned per fixture, because a render, its attachments and
its plain-text projection all drift independently:

``goldens/<name>.html``
    The rendered HTML, byte for byte, with no normalization. This is the
    byte-identity bar every migration epic promises to hold (#33, #41, #42,
    #49 all say "golden test unchanged").

``goldens/<name>.assets.txt``
    The asset manifest: one tab-separated record per ``ImageAsset``, in
    manifest order — ``content_id``, ``mime_type``, byte length, filename.
    The *bytes* are deliberately absent: they already live in the fixture that
    generates them, and storing them twice would double the repo's image
    weight to catch nothing extra. Length plus the content-addressed id is
    enough, since a Content-ID is ``sha256(bytes)[:16]`` — different bytes
    cannot keep the same id. Order is preserved rather than sorted, so a
    reordering of ``Email.assets()`` is a failure, which is what #32 asked
    for: image aggregation moves between classes during the header epic.

``goldens/<name>.txt``
    The plain-text projection (#110), byte for byte. It is a *separate*
    artifact for the same reason the manifest is: since #109 the text part is
    a second projection of the section tree rather than a degradation of the
    render, so a component's ``text()`` can change with the HTML byte-identical
    and vice versa. Neither golden can see the other's drift.

    Its first regeneration is reviewed as what it is — the initial pin of the
    house format, where the diff *is* the feature.

**One harness, not two.** #58 required that this and #32 resolve to a single
mechanism. #32 had not started, so it is satisfied here: ``kitchen_sink`` is
the representative email it specified, exhaustive over ``EmailMetadata`` for
exactly that reason.

**Regeneration is opt-in and reviewed.** ``pytest --update-goldens`` is the
only path — nothing regenerates automatically, and a missing golden fails
rather than being silently created, because a golden that writes itself on
first run pins whatever happened to be true that day. *A golden diff in a pull
request is a claim that the change is intended*, and the reviewer reads it as
one.

This module is deliberately free of pytest: the gallery's later tools (#61's
``preview`` CLI in particular) can check goldens without importing a test
framework.
```

## The preview CLI — the manual loop it replaced

Moved out of `qa/preview.py`'s module docstring by #138: the module states its purpose, and the reasoning that produced it lives here.

```
The ``preview`` CLI (#61): build → save → lint → screenshot, in one command.

Since #110 it writes **both** projections — ``<name>.html`` and ``<name>.txt``.
An email has two readable parts, and this is the loop for eyeballing one, so
writing only the HTML would leave out the half no screenshot and no lint rule
can show you.

The workflow the docs prescribed was manual — write a scratch script, build the
email, ``.save()`` it into ``output/``, open a browser, repeat. With the gallery
(#57), the goldens (#58), the screenshot runner (#59) and the lint pass (#60) in
place, that loop gets one entry point, and it serves a real newsletter draft as
readily as a fixture::

    python -m qa.preview --list
    python -m qa.preview kitchen_sink --lint --screenshot
    python -m qa.preview drafts/weekly.py:build --lint --open

**It composes; it does not reimplement.** Fixtures come from
:func:`qa.fixtures.all_fixtures`, findings from :func:`qa.lint.lint_html`,
images from :func:`qa.screenshots.capture_emails`. Anything it needed that they
did not expose was a gap fixed *in them* — that rule is what produced
``capture_emails``, since ``capture_gallery`` could only ever screenshot things
already in the registry, and a user's draft never is.

**No console script**, deliberately. #57 put ``qa/`` outside the wheel because
the gallery is test data; a ``preview`` entry point on the installed package
would contradict that, so the module form is the interface.

Exit codes, so the command composes in a shell:

===  ====================================================================
0    the email built, and nothing asked for was refused
1    ``--lint`` found errors (warnings alone do not fail)
2    the email could not be built, or the target could not be resolved
===  ====================================================================

A missing browser is **not** a failure: ``--screenshot`` says so and carries on,
because the ``[qa]`` extra is optional by design.
```

## The lint pass — the rules, their sources, and the deferred-rule mechanism

Moved out of `qa/lint.py`'s module docstring by #138: the module states its purpose, and the reasoning that produced it lives here.

```
Email-client lint pass (#60): portability checks over rendered HTML.

The constraints that actually break emails are documented prose, not checks.
Outlook's Word engine ignores ``max-width``, so every ``<img>`` needs a
``width=`` attribute — a rule :mod:`pyhermes.builder.images` follows and nothing
verified end to end. ``alt`` is required at construction, but nothing asserted
it survived into the markup. This module turns those into findings.

Usage::

    from qa.lint import lint_html, lint_email

    findings = lint_email(email)                 # rules + the size breakdown
    errors = [f for f in findings if f.severity is Severity.ERROR]

Four commitments shape it:

**It parses, it does not grep.** The repo learned this the expensive way: a
``grep`` for ``Contact Us`` matched inside an HTML section-marker comment and
produced a confident, wrong answer. :class:`html.parser.HTMLParser` is stdlib,
so the check costs no dependency.

**It observes, it never patches.** Findings fail or warn; nothing rewrites
HTML. Epic #54's first principle.

**Every rule carries its source.** An unsourced rule does not ship — see
``SOURCES`` below. A rule asserting something about a mail client that nobody
can trace is indistinguishable from a rule asserting a preference.

**It lands green.** A linter that arrives red teaches everyone to ignore it, so
a rule whose finding cannot be fixed today is *filed and deferred*, never
downgraded into a permanent warning. See ``DEFERRED_RULES``.
```

## The screenshot runner — what is pinned versus merely recorded

Moved out of `qa/screenshots.py`'s module docstring by #138: the module states its purpose, and the reasoning that produced it lives here.

```
Screenshot runner: render the gallery through headless Chromium (#59).

Reviewing a visual change should not require checking out the branch, building
an email by hand and opening it in a browser. This renders every fixture in the
gallery at two viewports and writes PNGs, so a reviewer sees the change without
leaving the pull request.

Usage::

    python -m qa.screenshots                    # the whole gallery
    python -m qa.screenshots kitchen_sink       # named fixtures only
    python -m qa.screenshots --out /tmp/shots

**What is pinned, and what is merely recorded.** Viewport sizes, the device
scale factor and the full-page capture mode are pinned here, so a rerun on the
same machine is comparable. The *browser build* is deliberately **not** pinned:
these screenshots are checks a human looks at, never artifacts that get diffed
or committed, so buying reproducibility with a pinned container image would cost
more than the guarantee is worth. Instead every run records exactly what
produced it — Chromium's build string, Playwright's version, the platform — in
``run.json`` beside the images. If pixel-diff gating is ever wanted (an explicit
non-goal of epic #54's first cut), that recording is what tells you whether two
sets are even comparable, and pinning becomes a decision made on purpose rather
than inherited by accident.

**Fidelity, stated honestly.** The files are named ``chromium-desktop`` and
``chromium-mobile`` rather than "gmail" or "outlook" because that is all they
are. Chromium approximates Gmail-in-a-browser at best; it says nothing about
Outlook's Word engine, which is the client most likely to break a layout. Client
compatibility belongs to the lint pass (#60), not to these images.

Playwright is an optional extra (``pip install -e ".[qa]"``), so the core
install and the unit suite stay browser-free.
```

## Why 375px is the supported floor — #133's measurements

Moved out of `qa/screenshots.py`'s `SUPPORTED_WIDTHS` note by #139: the constant states the rule, the measurement that established it lives here.

```
#: The viewport widths pyHermes claims to render without a horizontal
#: scrollbar. **375 is the floor**, and #133 is where that was decided rather
#: than left implied — the harness had asserted 375 for as long as it had
#: existed, and nothing said whether anything narrower was supported.
#:
#: Measured across the gallery at the time of that decision:
#:
#: ===== ==========================================================
#: width fixtures overflowing
#: ===== ==========================================================
#: 1000  none
#: 375   none
#: 360   ``spacious_size`` by 6px
#: 320   five, by 19–46px
#: ===== ==========================================================
#:
#: The 360px failure is one image four pixels too wide for that density's
#: mobile content box — ``kitchen_sink``'s chart is 320px inside a 316px
#: box once ``spacious`` has taken its 22px of padding a side. It is not a
#: structural limit, and it is *not* the masthead, which is what the first
#: diagnosis assumed before the element was isolated by removal.
#:
#: **The obvious fix is disqualified, not merely deferred.** Adding
#: ``img { width:auto !important; max-width:100% !important; }`` under the
#: breakpoint clears 360 outright and 320 for everything but a five-column
#: table (#132). It also destroys the display width: with images blocked —
#: Outlook desktop's default, and this harness's state — every image
#: collapses to its alt-text box, measured at 128px to 63, 320 to 339, 80 to
#: 165. The ``width`` attribute is the one thing ``img-width-attr`` exists as
#: an *error* to enforce, because the Word engine ignores ``max-width``. A
#: narrower floor therefore needs per-image work, not a global rule.
```

## The alignment fixture — the four situations it was built to hold

Moved out of `qa/fixtures/aligned_layout.py`'s module docstring by #138: the module states its purpose, and the reasoning that produced it lives here.

```
Every alignment axis at once — the fixture that closes epic #124.

#125 normalised the two spellings, #126 gave a container an ``align`` and
#127 gave five prose components one. Each landed with its own tests, and each
is invisible in a golden until an email actually uses it — so this is the
email a *cross-axis* regression shows up in, the way ``custom_banner`` is for
the masthead and ``rich_table`` for the table.

Four situations, because no fewer can carry the epic honestly:

* **a centred section whose title follows** — the specific thing #126 showed
  does not happen by itself. The heading and the content are sibling tables
  in ``full-width.html``, not parent and child, so the declaration has to
  land twice; a centred section with a left heading reads as a bug, and only
  this fixture makes it visible at a glance;
* **a component overriding its container** — a right-aligned block inside a
  centred section, which is what shows the cascade *as* a cascade rather
  than as a single setting. Nothing in Python resolves it: the component's
  declaration sits on a descendant of the cell carrying the container's, and
  inheritance is the weakest source;
* **a structural component inside an aligned section** — a ``CardGroup``
  and a ``DataTable`` in a **right**-aligned band, sitting unmoved. This is
  the epic's boundary rendered as an image, and the band is right-aligned on
  purpose: a centred one could not tell "the KPI strip kept its own
  alignment" from "the KPI strip inherited the section's";
* **an aligned split** — ``columns.html`` applies the declaration per column
  cell, which is a different shape from a centred full-width band.

The body is short for ``custom_banner``'s reason: ``kitchen_sink`` exercises
the component library, and a fat body here would make this golden noisy for
reasons unrelated to alignment. Theme, size and font stay **default** — a
preset moving alongside an alignment axis would leave a golden diff nobody
can attribute.

It also carries one thing that is **not** an alignment axis: an explicit
``Container.background_color``. Widening the field-completeness rule to
containers found that field — the original entry in the closed colour list —
had never been set by any fixture at all, so nothing pinned how a
caller-supplied band colour renders. A brand-new fixture is the cheapest
place to close that, since no existing golden has to move for it.

This fixture shipped one commit ahead of #129, when a column's content cell
still shrink-wrapped to its copy instead of filling its column — so a
split's alignment reached every cell correctly and had nowhere to show. Its
docstring predicted that fixing #129 would move this golden, and it did, by
five lines. The two columns are still written long enough to fill their
width: that was a workaround then and is honest content now, and shortening
them would only make the golden pin less.
```

## The banner fixture — what each axis pins

Moved out of `qa/fixtures/custom_banner.py`'s module docstring by #138: the module states its purpose, and the reasoning that produced it lives here.

```
Every banner axis at once — the fixture that closes epic #88.

Each axis landed with its own tests, but the epic's promise is the
*combination*, and a per-axis test cannot see an interaction. This is the
email a cross-axis regression shows up in:

* **free-form copy** (#91) — a ``title`` and ``subtitle`` that are neither
  ``firm_name`` nor ``campaign_name``, so the golden pins that the masthead
  says one thing while every other site still says the other;
* **a department** (#92) — sharing the subtitle's row, which is what the 2x2
  masthead exists for;
* **an attached background image** — a ``cid:`` reference in a CSS
  ``background-image`` *and* in the VML ``v:fill``, which is the one embed
  path no other fixture covers. ``image_matrix`` pins that ``assets()``
  matches the HTML's references and ``minimal_banner`` pins a CID *logo*;
  nothing until now attached a CID **background**, and it reaches the
  manifest through ``Banner.images()``' walk of ``IMAGE_FIELDS`` rather than
  through a component;
* **a `BannerPalette`** (#93) — all eight roles, chosen *for the image
  underneath them* rather than as arbitrary distinctive values, because the
  whole reason the exception exists is a backdrop the theme cannot see.

The body is deliberately short. Its job is to put the masthead in a real
email rather than to re-exercise the component library — ``kitchen_sink``
already does that, and a fat body here would make this golden noisy for
reasons that have nothing to do with the banner.

**The theme stays ``classic``.** A preset *and* a palette moving at once
would leave a golden diff nobody can attribute, and ``slate_theme`` already
pins the preset path.
```

## The footer fixture — the two axes and the shared surface

Moved out of `qa/fixtures/custom_footer.py`'s module docstring by #138: the module states its purpose, and the reasoning that produced it lives here.

```
Both footer axes at once — the fixture that closes epic #98.

#99 gave the footer's box the shared surface and #100 made its copyright row
an object; each landed with its own tests, but the epic's promise is the
*combination*, and a per-axis test cannot see an interaction. This is the
email a cross-axis regression shows up in:

* **the box surface** — ``align``, ``background_color`` and ``text_color``,
  the same three fields the header strip takes, so this golden is the one
  place both boxes are visible at once and the parity is legible rather than
  merely asserted;
* **a custom `LinkRow`** — its own copyright wording and a link set that is
  neither the default pair nor the same length, which is the whole reason the
  row became an object;
* **a `mailto:` link**, because the scheme check is a safety rule that must
  keep passing the schemes it allows, not only rejecting the ones it does
  not.

Paired with the **default header** on purpose, per ``minimal_footer``'s
worked reasoning: the two boxes are independent, and an email that recoloured
both at once could not say which one moved a byte. The strip above therefore
renders on the theme's own tokens, which is also what makes the contrast
between the two boxes visible in a screenshot.

The theme stays ``classic``. A preset and a box override moving together
would leave a golden diff nobody can attribute; ``slate_theme`` already pins
the preset path.
```

## The typography A/B — why one preset needs a second fixture

Moved out of `qa/fixtures/modern_fonts.py`'s module docstring by #138: the module states its purpose, and the reasoning that produced it lives here.

```
``kitchen_sink`` at the ``modern`` font theme — the axis's A/B.

The third design-system axis gets the proof its two siblings already have: a
preset nobody can compare against is a refactor, not a seam. This fixture
differs from ``kitchen_sink`` in exactly one metadata field — ``font_theme``
— and reuses its content rather than restating it, exactly as
``compact_size`` and ``slate_theme`` do, so the two goldens diff as a pure
A/B where **every difference is a typeface**.

What this one pins that no other golden can:

* **the role vocabulary was cut in the right place.** ``heading`` and
  ``body`` share a stack in the default, so nothing until now could show
  they are separate roles. Here the masthead title, the ``<h2>`` section
  titles, the item titles, the list ordinals, the contact heading and the
  author name all move to the sans while the prose, the standfirsts and the
  KPI values stay serif — which is only expressible because the roles are
  named by the job a face does rather than by which face does it;
* **the `[if mso]` fallback moves with everything else**, so the email is
  not custom-faced in Gmail and Georgia in Outlook — the half-themed
  failure the axis's standing rule exists to prevent, in the client hardest
  to check;
* **``numeric`` holds**, so the data table's figure columns still align.

Sizes do not move: a font swap changes no px, which is the epic's
orthogonality principle. Rendered line *lengths* do move with the metrics,
and that is what the screenshots judge rather than the golden.
```

## The DataTable fixture — why two tables

Moved out of `qa/fixtures/rich_table.py`'s module docstring by #138: the module states its purpose, and the reasoning that produced it lives here.

```
Every ``DataTable`` axis at once — the fixture that closes epic #116.

#117 gave columns an alignment and a kind, #118 gave cells a colour, a
background and an override, #119 gave rows a kind, and #120 gave the table a
name and row headers. Each landed with its own tests, and each is invisible
in a golden until an email actually uses it — so this is the email a
*cross-axis* regression shows up in, and the one that stops these properties
being added, never exercised, and quietly rotting.

Two tables, because one cannot carry the whole surface honestly:

* **the sleeve table** — a caption, a second **text** column (unreachable
  before #117 at any argument), a **centred** column, per-cell colours *and*
  backgrounds, `subhead` groupings and a `total`. Its first column is text,
  so every row gets a ``th scope="row"``;
* **the ranking table** — a **numeric first column**, which is the only way
  a golden can show that the row-header rule keys on the column's resolved
  *kind* rather than on position. Without it, "the first cell is a row
  header" and "a text first column is a row header" pin identically.

**The body is short on purpose.** ``kitchen_sink`` exercises the component
library; a fat body here would make this golden noisy for reasons unrelated
to the table, which is ``custom_banner``'s reasoning and applies unchanged.

Theme, size and font stay at their defaults for the same reason: a preset
moving alongside a table axis would leave a diff nobody can attribute, and
the three design axes already have fixtures of their own.
```

## The compact-density fixture

Moved out of `qa/fixtures/compact_size.py`'s module docstring by #138: the module states its purpose, and the reasoning that produced it lives here.

```
``kitchen_sink`` at the ``compact`` density.

Denser: smaller type from the top of the scale down, tighter leading,
and — where most of the density actually comes from — less padding
everywhere. ``label`` and ``micro`` do not move: 9.5px fine print is the
readability floor, and a compact theme that made a disclaimer unreadable
would be broken rather than dense.

The fixture differs from ``kitchen_sink`` in exactly one metadata field —
``size_theme`` — and reuses its content rather than restating it, so the
two goldens diff as a pure A/B. What this one pins that no other golden
can:

* every layer of the scheme is live at once: type, spacing, the
  component sizes that do not follow the global scale, and the frame
  padding that every column width is computed from;
* ``base.html``'s ``@media`` block moves with the rest, so the email is
  not desktop-compact and mobile-standard;
* the columns still fill the content width to the pixel at a frame whose
  padding is not 32.

It also retires an exemption: ``kitchen_sink`` holds ``size_theme`` at its
default on purpose — it is the epic's byte-identity reference — so the
distinctive value has to live here. Same shape as ``slate_theme``.
```

## The spacious-density fixture

Moved out of `qa/fixtures/spacious_size.py`'s module docstring by #138: the module states its purpose, and the reasoning that produced it lives here.

```
``kitchen_sink`` at the ``spacious`` density.

Airier: type grows across the whole scale, leading opens further than
type does, and the frame gives up 8px of side padding on each edge. The
gutter widens to 24px, which is what pushes a two-up split just under
300px — and is why this theme is the only one that moves
``frame.narrow_column``, down rather than up.

The fixture differs from ``kitchen_sink`` in exactly one metadata field —
``size_theme`` — and reuses its content rather than restating it, so the
two goldens diff as a pure A/B. What this one pins that no other golden
can:

* every layer of the scheme is live at once: type, spacing, the
  component sizes that do not follow the global scale, and the frame
  padding that every column width is computed from;
* ``base.html``'s ``@media`` block moves with the rest, so the email is
  not desktop-spacious and mobile-standard;
* the columns still fill the content width to the pixel at a frame whose
  padding is not 32.

It also retires an exemption: ``kitchen_sink`` holds ``size_theme`` at its
default on purpose — it is the epic's byte-identity reference — so the
distinctive value has to live here. Same shape as ``slate_theme``.
```

## The slate-preset fixture

Moved out of `qa/fixtures/slate_theme.py`'s module docstring by #138: the module states its purpose, and the reasoning that produced it lives here.

```
The ``slate`` preset, in the gallery.

The colour epic's counterpart to ``minimal_banner`` / ``minimal_footer``: a
fixture that exists to pin one *choice*. It differs from ``kitchen_sink`` in
exactly one metadata field — ``theme`` — and its golden is what proves the
palette is live in every corner of a rendered email rather than only in the
inline styles a spot-check would look at.

What this golden pins that no other one can:

* the second preset renders at all, and renders *completely*: no token
  falls back to a classic value anywhere, including inside the dark-mode
  forcing block and the mobile media query, which used to carry their own
  hardcoded copies of surface and text colours;
* both halves of the Outlook scrim move together — the CSS ``rgba()`` and
  the VML ``color``/``opacity`` attribute pair;
* an unset ``Card.color`` resolves against *this* theme's neutral, while a
  caller's explicit colour survives untouched — the semantic-vs-presentation
  boundary, in one email.

It also retires an exemption: ``kitchen_sink`` could not set ``theme`` to a
distinctive value while only one preset existed, so the metadata
completeness test skipped the field. This fixture is what makes it real.
```

## The omitted-header fixture

Moved out of `qa/fixtures/no_header.py`'s module docstring by #138: the module states its purpose, and the reasoning that produced it lives here.

```
An email with no strip at all — the ``EmptyHeader`` variant, in the gallery.

The variant that proves the seam, and a seam with one implementation is a
refactor. This differs from ``minimal`` in exactly one argument —
``EmailBuilder.header(EmptyHeader())`` — so its golden pins that a region
which fills *no* slot renders genuinely nothing: no band, no empty ``<tr>``,
no trace of the strip's markup at all.

Two deliberate pairings:

* **The default banner**, per ``minimal_footer``'s worked reasoning. The two
  region choices are independent, and an email swapping both at once could
  not say which one moved a byte. So the masthead below is byte-identical to
  the way a default ``Header`` renders it.
* **A `header_disclaimer` that is set.** ``minimal`` already covers the empty
  one, and an empty one here would prove nothing — the strip would be
  absent either way, and the golden could not tell "the variant omitted it"
  from "there was nothing to render". Copy the email owns, and a region that
  declines to display it, is the whole distinction.
```

## The minimal-banner fixture

Moved out of `qa/fixtures/minimal_banner.py`'s module docstring by #138: the module states its purpose, and the reasoning that produced it lives here.

```
The ``MinimalBanner`` variant, in the gallery.

The proof that a region is a seam and not a refactor: this email differs from
the others in exactly one argument — ``EmailBuilder.banner(MinimalBanner(...))``
— and nothing about the skeleton, the body, or the email's own facts moves
with it.

What the golden on this fixture pins that no other one can:

* the variant renders **no** ``v:rect``/``v:fill``/``v:textbox`` and no
  ``background-image``, which is the whole reason it exists;
* the email-level facts still flow down — firm name, campaign name, date
  range, issue label and the header disclaimer all appear, from
  ``EmailMetadata``, exactly as they do under the default header;
* a **CID logo** on a variant reaches ``assets()`` once, through the region's
  own ``images()`` rather than through the metadata.
```


## The harness became medium-aware (#165)

Three things moved, and each had a failure mode a green suite would have hidden.

**Every lint rule declares the media it applies to**, in `RULE_MEDIA` beside `SOURCES`, and a
test fails if a rule in one is missing from the other — so a rule added later cannot quietly
apply everywhere or nowhere. The question an entry answers is not "could this fire here" but
*is the claim behind it true here*: a rule about Outlook's Word engine says nothing about a
sheet of paper, and running it there produces findings a reader learns to ignore, which is how
a lint pass dies. `lint_document(document)` is the entry point that reads the medium off the
document; `lint_email` is kept as the name every existing caller uses and returns exactly what
it always did.

The split was **measured, not predicted** (#162): ten rules for email, six for a paged
document (seven since #176 added `table-structure`), and only one rule had to be *taken away* rather than merely being quiet —
`size-budget` is Gmail's 102 KB and nothing clips a PDF. The size *report* stays available
everywhere, because knowing where the bytes went is useful for any document; it is the
threshold that is a fact about one mail client. Two paged-only rules arrived, and both came
from a defect a real PDF produced rather than from reading a specification: `page-size-declared`
(no `@page size` means the engine picks its own page and says nothing) and `paged-table-width`
(a print engine does not map a table's `width` attribute, so an unmapped one shrink-wraps —
measured at 188px inside a 794px page).

**Goldens are keyed by medium**: `goldens/<medium>/<name>.*`. Two media may hold a fixture of
one name, and before this the second would have overwritten the first's snapshot. The move was
48 pure renames with no content change, which is what made it reviewable.

**A paged fixture is photographed from its PDF**, one PNG per sheet, through `pypdfium2` — a
self-contained wheel, because rasterising through Poppler would put a *system* binary inside an
extra that is meant to be `pip install` and nothing else. The default scale reconciles units
rather than choosing a resolution: a PDF is 72 dpi and a `PageFormat` is px at 96, so an
unscaled A4 raster comes back 596px wide for a page laid out at 794 — close enough to look
right and wrong enough to measure. A test asserts every sheet rasters at exactly its
`PageFormat`.

`qa.preview` spans both media on one command: it lints a document by its own medium's rules,
writes a PDF beside the HTML for a paged one, photographs sheets instead of viewports, and
`--open` opens the PDF — showing a paged document's HTML in a browser would show a page
without pages.


## The long-table fixture — engineered boundaries (#176)

`a4_long_table` is the third paged fixture and the teeth for epic #169. Before it, no paged
fixture had a table that crossed a sheet, so nothing in the harness could see a lost header.
It carries a 60-row holdings table with a subhead and a total, a chart with a subtitle, source
and disclosure, and a section title. Its three lead-in paragraph counts are **tuned, not
chosen**. Each puts one boundary exactly at a sheet edge, so that the defect occurs when the
paged skeleton's break rules are removed:

| Constant | Boundary | Defect without the rules |
|---|---|---|
| `INTRO_PARAGRAPHS` | The table's end | The total opens a sheet with no data row above it |
| `LEAD_IN_PARAGRAPHS` | The chart | The disclosure opens a sheet, away from its chart |
| `RUN_ON_PARAGRAPHS` | The "Outlook" section | Its title ends a sheet without its first line |

- **The tests read the PDF's text back, sheet by sheet**, through pypdfium2. They need both
  `[pdf]` and `[qa]` and skip without either. `TestALongTableCrossesSheetsIntact` holds the
  claims: the headers on every sheet the table occupies, the total with its last row, the
  subhead with its first, the title with its first line, and the chart with its subtitle and
  fine print.
- **`TestTheFixtureIsEngineeredRatherThanLucky` strips the rules and asserts each defect
  appears.** Without it, the tests above could pass because a boundary drifted rather than
  because a rule held. When layout moves and one of these goes green, retune the constant.
  Do not delete the test. The tuning loop is a search over one constant at a time, in document
  order, since each boundary depends only on what precedes it.
- **The `thead` removal is a committed test**, not a one-off check. `TestRemovingTheTheadIsCaught`
  renders the fixture against a template copy with no `thead`. It asserts that the lint rule
  fires and that the headers vanish from the table's second sheet. The lint half runs without
  WeasyPrint, so the `[dev]`-only CI job enforces the structure too.


## The brochure gallery, and the editorial page (#172)

**A third registry**, `all_brochure_fixtures()`, for `all_paged_fixtures()`' reason: the
paged tests read the cover, running boxes and back matter off every fixture they are given,
and a brochure has none. `tri_fold_letter` is its one fixture. Each face opens on a marker no
other face carries (`MARKERS`), so a test can find every face on the sheet by its text.
`qa.preview` spans all three registries, and CI's `pdf` job renders and photographs both
printed galleries. A brochure's raster is its **media box**, trim plus bleed plus slug, so
1128 × 888 for a letter sheet, where a paged fixture's is exactly its `PageFormat`.

**`a4_editorial` is a paged fixture for the editorial primitives**, apart from `a4_portrait`
because that fixture's sheet counts are claims other tests make. Adding one pull quote moved
A4 to six sheets.

**CI's `pdf` job now names every module that reads a PDF back**: `test_pdf`,
`test_medium_aware_harness`, `test_apparatus`, `test_brochure_pdf` and `test_examples`. Each
skips without the extras, so the check job passes them by, and a module missing from that
line is never run anywhere. `test_apparatus` had been missing since #171.

**A fourth registry**, `all_deck_fixtures()` (#296), holds `pitch_16_9`, for the brochure's
reason: the paged tests read a cover and running boxes off every fixture. A deck's goldens
gain a fourth artifact, `goldens/deck/NAME.notes.txt`, the speaker notes, through the same
`artifacts()` list. `test_deck_pdf` joins the `pdf` job's line, and the job photographs the
deck one image a sheet. `deck.md` has the medium.

**Two print rules and a severity.** `print-marks` (error) fires when a brochure's `@page`
lacks `bleed` or `marks`. `rgb-only` is the first `INFO` finding: a fact no edit can change,
stated once per brochure and never failing a build. Both apply to the brochure only, and the
paged rules all apply to it too, because the same engine prints it.


## The dense monitor (#209)

`letter_dense` is the sixth paged fixture: two Letter portrait sheets at `size_theme="dense"`,
with `spacing` on a page, a section (including `pad_x`, which only paper allows), a split, a
KPI strip, a list and one of its two identical tables. The other table keeps the preset, so
the raster shows the override against the density it derives from. `SHEETS = 2` is asserted
from the PDF in `test_spacing.py`, and the sheets are photographed there as well as in CI's
`pdf` job. Its facts hold `dense` because the email gallery cannot: an `Email` refuses it.

## The landscape report (#200)

`letter_landscape_report` is the fifth paged fixture and the digital PDF's (#193): US Letter
landscape, a centred cover, a contents sheet, a running header that follows the section, an
eight-column table, a wrapped figure, a pull quote and a disclosures sheet, in copy of its own.
It exists to show the landscape reading layout, not to A/B against A4. It is also the gallery's
first centred cover, and its first raster found the cover logo stranded at the left, fixed in
`document/regions/cover.html`. `digital-pdf.md` has the tests that read it back.


## The equations sheet (#232)

`a4_equations` is the eighth paged fixture: three labelled equations on `solid_png` bytes at a
real render's pixel size, so no golden depends on matplotlib. `LEAD_IN_PARAGRAPHS` engineers the
second at a sheet's foot. `tests/test_math_paged.py` holds image and caption on one sheet,
splits them with `.figure` stripped, and checks each equation is centred. `math.md` has the rest.

## The research note (#312)

`a4_research_note` is the ninth paged fixture and `research_note` the email gallery's
seventeenth: one set of sections (`qa/fixtures/_research.py`) in both media, so their goldens
pin that every exhibit number, appendix letter and citation agrees across them. It carries a
cover, a contents sheet and an `ExhibitsPage`, three body sections with author-year
citations, glossary links and a key-takeaways `Callout`, then a `Bibliography`, a `Glossary`
and `Appendices` holding A.1 and B.1. `tests/test_research_note.py` compares the two text
parts' apparatus and reads both lists' page numbers back from the PDF. Its first raster showed
the running header reading "Appendix A: Data sources" on the appendix sheet.

## The factor book (#228)

`letter_quant_table` is the seventh paged fixture and epic #217's proof. It is a Letter portrait
returns table that crosses from sheet one to sheet two with a three-row head: groups, column
heads and units. It uses every table word the epic added. `tests/test_quant_fixture.py` asserts
`SHEETS = 2` from the PDF and reads the whole head back from every sheet the table occupies. It
photographs each sheet too, and CI's `pdf` job runs it. `a4_long_table.build_grouped()` is the
other half: the same engineered boundaries, re-measured under the tiered head, with its own
`GROUPED_PARAGRAPHS`.

## Every extra-gated test runs somewhere (#239)

Each extras job installed a different subset and ran a hand-kept module list, and `check`
installs none. So a test needing two extras no one job paired, or a module left off a list,
skipped everywhere and green: three had never run in CI (the factsheet's two-sheet layout
needs `[pdf]` and `[charts]` together; `test_chromium_puts_the_points_in_one_column` and
`test_it_captures_through_the_same_runner` were on no browser job's list). `addopts = "-q"`
hid the skip reasons, so nothing in a log showed it.

- **`all-extras` installs every extra and every system library** (Pango, Cairo,
  HarfBuzz-Subset, fonts, Chromium) and runs the whole suite with `-rs`, which prints every
  skip that remains and its reason.
- **`PYHERMES_REQUIRE_EXTRAS=1` turns a skip naming an extra into a failure.** The plugin is
  `qa/require_extras.py`, registered in the root conftest; its test is the reason string, so
  every skip names its extra in the house form (`the "[pdf]" extra`, `pyhermes[data]`).
  `tests/test_require_extras.py` runs a throwaway suite with and without the variable, and
  checks the pattern covers every extra `pyproject.toml` declares.
- **It catches a skip at every stage.** A `skipif` mark skips at setup and `pytest.skip` in
  the body; both come through `pytest_runtest_makereport`. A module-level `importorskip`
  (`test_frames.py` without pandas) skips the whole module at *collection*, which that hook
  never sees; the first draft missed it, found by a `[dev]`-only scratch run, and
  `pytest_make_collect_report` now covers it. A collection failure stops pytest before any
  test runs, so the job passes `--continue-on-collection-errors`: every test still reports
  and the run still fails. A setup or collection failure shows as an error, not a failure.
- **A new extra-gated test needs no list edit.** The `pdf`, `data` and `screenshots` jobs
  keep their lists to prove each extra works with only its neighbours; a module missing
  from one is still run by `all-extras`.
- **Measured here**: with every extra installed, the three orphans pass, and the only skips
  left are six `test_sizing.py` tokens "resolved in Python, never emitted", which name no
  extra and stay skips. In a `[dev]`-only venv the variable fails `test_frames.py` and both
  Chromium decimal tests by name; without it the whole suite is green.
- **Two reasons were untagged and now name their extra**: `test_math.py`'s bare
  `importorskip("weasyprint")` and `importorskip("pypdfium2")`, whose default reason names a
  module, not an install.

## The size report names each section (#259)

The body used to be one region. Containers emit no marker since #137 cut shipped comments, so
every section's bytes landed in `SECTIONS: Insert containers here`, and `preview --lint` never
printed even that above 102 KB, because `render()` raised first.

- **The attribution comes from the section tree, not from new comments.**
  `Document.rendered_sections()` renders each body section through the same bound engine and
  section list as `render()`, labelled `section N: Title` (or the class when untitled).
  `size_report(html, sections)` finds each one in the markup in order, gives it its own
  region and takes its bytes out of the marker region around it, so the regions still sum to
  the total. Every golden is byte-identical, which is the proof the email is unchanged.
- **Without `sections` the report is exactly what it was.** `TestTheSizeBudgetStillNamesItsRegions`
  still asserts the body marker is the heaviest region of the bare report.
- **The two have to stay one render.** `PagedDocument` drops a first page's leading break.
  That lived in `_body_context`, so the standalone first `Page` of `letter_dense` did not
  match and was silently left unattributed. It now lives in `_body_sections`, which both paths
  call. `TestEverySectionIsFound` checks every email and paged fixture, and moving the rule back
  fails it by name. A paged document has no markers, so what its sections leave is one
  `(rest of document)` region.
- **A brochure is not attributed.** Its panels are imposed onto two sides, so no section's
  standalone markup appears in the page. The report falls back to the markers, and a test holds
  that this degrades without error.
- **`SizeError.html` carries the refused markup**, and `pyhermes.check.render_for_check()`
  returns it instead of raising. `render()` still refuses, the check always measures, and
  `preview` measures only with `--lint`. Without it, an over-limit draft still exits 2 and the
  message says to run with `--lint`.

## The examples are held to their committed output (#281)

`examples/README.md` promised each `.html` was its script's output. Nothing checked it, and
three of four had drifted: `quarterly-review` since #157, and the two emails since #282's
one-line `@media` change, which regenerated the goldens but not the examples.

- **`TestTheCommittedOutputIsCurrent`** in `test_examples.py` renders each example and compares
  it to the committed file. Its failure is the golden harness's report, through
  `qa.goldens.difference_report`, with the example's own remedy: run the script, not
  `--update-goldens`. An example that needs an absent extra skips, as its build test does.
- **A Content-ID is masked before comparing.** It hashes a chart's PNG, and `matplotlib~=3.11`
  lets CI resolve a different release than the machine that committed the file. The markup
  around it is still compared byte for byte; a changed title was checked to fail.
- **The PDFs are not compared**, for the same reason their determinism tests need
  HarfBuzz-Subset: their bytes are the printing machine's. Regenerate one when its HTML moves.
- **A builder change that moves an example now fails the suite**, which is the point: the
  regeneration lands in the same PR as the change, where #282's did not.

## Placement across media (#367)

`placed_layout` (email) and `a4_placed_layout` (paged) build one set of sections
(`qa/fixtures/_placed.py`) carrying every control epic #361 added: a reversed split, an
unstacked figure pair and label-value pair, a reversed nested `Columns`, an email-only `Button`
in `Only`, a print-only `OnlySections` page note with an attached image, a kept section and a
`break_before` one. So the email's goldens pin that paper's controls cost it no byte and its
manifest lacks the note's image, and the paged golden the reverse. `pitch_16_9` gains a sidebar
slide. `kitchen_sink`'s button is wrapped in `Only(..., media="email")`, which renders it
unchanged, so rule 1 holds with its goldens byte-identical. The gallery's 375px tests cover the
new email, and `tests/test_stacking.py` measures where each column lands at 1000 and 375px.

## Placement within a block's space (#360)

`_placed.py` gains #354's controls after its fresh-sheet section, so no engineered break above
them moves: a paper-only split aligned middle (in `OnlySections`, since an email refuses it), a
chart and an equation hosted as floats, a callout, a table, a figures pair and a contents list
each at a share of the column, placed centre or right by their section, and a narrow measure.
So `placed_layout` pins the email's fallbacks and `a4_placed_layout` the floats and the split.
`pitch_16_9` gains a middle-anchored title slide, divider and slide, a measured paragraph and a
0.6 table; `tri_fold_letter` a bottom-anchored cover. The field tests count a `MathBlock` hosted
as a figure, the only place its `wrap` means anything. The five new test modules join the `pdf`
job's line, and `test_cell_share` the screenshot job's.

## The suite runs on Windows (#372)

The owner's Windows 11 run (PR #371) failed 14 tests on `main`, from three causes, none of them
this repo's Linux CI could see.

- **Text I/O names its encoding.** A bare `read_text()` reads the locale's encoding, cp1252 on
  Windows, and a template holding an em dash failed there. `tests/test_encoding.py` walks the
  syntax tree of `pyhermes/`, `qa/` and `tests/` and fails on any `read_text` or `write_text`
  without `encoding=`, naming file and line. The tree is checked rather than grepped, so a
  call split over lines is seen.
- **A drive letter is never the target's separator.** `load_target` split on the last colon,
  so `C:/x/weekly.py` with no callable reported `No such file: C`. A drive (`C:/` or `C:\`) is
  now taken off first; the tests run on any OS, since the split never touches the filesystem.
- **The engineered boundaries are Liberation Serif's.** CI installs `fonts-liberation`, which
  stands in for the body stack's `'Times New Roman'` with no Georgia present, and
  `a4_long_table`'s paragraph counts were tuned in it. In real Georgia the breaks fall
  elsewhere. The counterfactual tests now skip, naming both faces, when the engine embeds
  another body face; the skip names no extra, so `all-extras` is unaffected, and in CI they
  still run. The embedded-face check accepts any face the body stack names, or a serif
  standing in for its generic, so an embedded Georgia passes.

## Labels and status (#328)

`labelled_layout` (email) and `a4_labelled_layout` (paged) build one set of sections
(`qa/fixtures/_labelled.py`): badged cards in three tones, a recommendation table with badged
ratings beside a status column, a badged split on a dark band and a twelve-tag row. CI's `pdf`
job photographs the paged one with the rest of the paged gallery, and the gallery's 375px
tests cover the email. `kitchen_sink` gains a two-tag `TagRow` only, because a status column
put it over the 90 KB warning; `TestTheTokensAreLive` now renders `labelled_layout` beside it
for `status_dot` (`design-axes.md` has the numbers).

## Organising content (#334)

`organised_layout` (email) and `a4_organised_layout` (paged) build one set of sections
(`qa/fixtures/_organised.py`): a two-column fact list under a kicker, a six-event timeline in
every state beside a toned fact list, a three-column fact list on a dark band, a three-across
teaser list with thumbnails and tags, a one-column one, and a closing note. `pitch_16_9`'s
sidebar slide gains a fact list under its cards and a kicker over its title. `kitchen_sink`
carries one of each object in *Three Equal* and a kicker over it, and four of its sections
became two to pay for them (`design-axes.md` has the numbers). `tests/test_organising.py`
holds the claims, including a browser measure of the rule meeting every marker and two PDF
read-backs; it joins the `pdf` and `screenshots` jobs' lines. Nothing set, every other golden
is byte-identical.

## Exhibits that group (#339)

The research-note pair carries epic #335: Exhibit 3 is a two-panel grid with a key, cited at
its panel (b) by a cross-reference; *Results* has one source line for its two exhibits, citing
and calling a note; Appendix B gains B.2, a grid with a column key, a tone and a hex. So both
goldens pin the panel anchors and the lettered numbering in each medium, and
`tests/test_grouped_exhibits.py` reads the panel reference's page back from the PDF.
`kitchen_sink`'s chart became a grid of a chart and a picture with a two-entry key, and the
two equations joined it in one section to pay for it: `modern_fonts` is at 89.7 KB, 323 bytes
under the warning. The container-field test lists `source`, `as_of` and `source_notes`, which
`research_note` sets; the spacing sentinel instances carry a source on every section.

## Page-level presentation (#345)

`a4_wide_appendix` is the paged gallery's page-level fixture (#340): a portrait report with a
DRAFT stamp, an aside in its summary, a landscape page holding a ten-column table that crosses
three turned sheets, and a portrait method note after it, with two cross-references whose page
numbers the PDF test reads back. `tri_fold_letter` gains an aside in its inside-left panel and
a QR code on its back cover; `pitch_16_9` a CONFIDENTIAL stamp, so `test_deck_pdf` reads each
slide's folio as the word before the stamp; the research-note pair an aside, so the email
gallery shows its callout form. CI's `pdf` job photographs all of them with the rest of the
printed galleries, and installs `[qr]` for the adapter's own decode test.

**`kitchen_sink` paid for its stamp and QR code by untitling its three wide `ThreeColumn`
ratios**, which also drops their contents entries: 2,040 bytes back. The stamp costs 187 and
the code's button about 1,500, so `modern_fonts` is at 91,198 bytes, 962 under the warning.
Its code's image never reaches the email manifest, which `test_qr` asserts.

## Brand tones (#387)

`toned_layout` (email) and `a4_toned_layout` (paged) build one set of sections
(`qa/fixtures/_toned.py`) on a theme declaring two brand tones: a gold fact box, a sky box beside
an untoned one, toned and badged cards, a hero figure, a table with brand-toned cells and status
dots, a bar list and a key. `kitchen_sink` is untouched, because it is at its size ceiling and a
brand tone is a theme setting, not a component. Nothing set, every other golden is byte-identical.
#390 dashes a box, the table and a section there and rules off the table's label column, which
is where `TestComponentFieldsAreExercised` finds `Column.rule_after` and `DataTable.frame`.
