---
paths:
  - "qa/**/*"
  - "tests/**/*"
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
epic #54). Fourteen fixtures, each a `build()` returning a built `Email`, enumerated through
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
| `minimal_footer` | A minimal-footer build (#66), the same argument at the other end. Paired with the **default** header on purpose: the two region choices are independent, and swapping both at once could not say which one moved a byte |

**Determinism is the rule the gallery rests on**, and it is not a style preference: Content-IDs
are `sha256(bytes)[:16]`, so a fixture image that varies changes the `cid:` references in the
HTML and fails every downstream golden for a reason unrelated to the change under review.
Hence fixed strings, no clock, no `random`, and PNG bytes generated from constants by
[qa/fixtures/_png.py](../../qa/fixtures/_png.py) rather than checked in as binaries.

**`qa/` is a top-level package, not `svc/qa` and not `tests/fixtures`** — the decision #57 left
to its PR. It is out of `svc/` because the wheel ships `packages = ["svc"]` and the gallery is
test data that would be dead weight for every installing user; it is out of `tests/` because
`tests/` is not importable from an installed position and the epic's later tools (#59
screenshots, #60 lint, #61 the `preview` CLI) are not tests. A root
[conftest.py](../../conftest.py) puts the repo root on `sys.path` so `import qa` does not depend on
hatchling's editable-install strategy happening to expose it. `qa/` **is** type-checked —
`mypy` runs over `["svc", "qa"]`.

**Adding a component means adding it to `kitchen_sink()`; so does adding an `EmailMetadata`,
`Banner` or `Footer` field.** Four completeness tests introspect rather than hand-list: one
over every public `Component` subclass exported from `svc.builder`, one over
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

## Lint pass — `qa/lint.py`

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
| `empty-url` | error | `url()` with nothing in it; a client may resolve it against the message body |
| `table-role` | error | A layout table with no `role`, **and** a data table carrying one (#114) |
| `size-budget` | warn/error | The 90/102 KB thresholds, **attributing the bytes to section-marker regions** |

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
  function returns. Split on the **last** colon, so a Windows drive letter is not mistaken for
  the separator. The output name is `{module_stem}-{callable}`, so two files both defining
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
