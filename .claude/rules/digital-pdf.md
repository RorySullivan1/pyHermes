---
paths:
  - "svc/pdf/**/*"
  - "svc/delivery/message.py"
  - "tests/test_digital_pdf.py"
  - "tests/test_pdf_profile.py"
  - "tests/test_attachments.py"
---

# The digital PDF: a paged document finished for the screen and sent (#193)

Epic #193 took the paged medium's PDF and made it something that can go out by email and be
read on a screen. It added four things: metadata from the facts, a `PdfProfile`, attachments
in `build_message`, and a size budget on the message. Tagged PDF was measured and left opt-in.

## It is not a medium, and what would reopen that

A screen PDF changes no skeleton, no slot set and no constraint. The paged medium already
carries the cover, contents, running boxes, back matter, apparatus and both orientations. So
this is **a rendering profile on the existing exporter plus a delivery path**, not
`svc/screen/`. #172's test for a medium applies in reverse: a brochure needed fold geometry,
imposition and print prep, and a screen PDF needs none of them.

**The test that would reopen it:** a change the screen needs in the skeleton, the slots or the
constraints. A different margin is not one, since `PageFormat` already takes any margin. A
hyperlinked contents sheet is not one, since the contents entries are live links already.

## The profile — `svc/pdf/profile.py`

`PdfProfile(name, dpi, jpeg_quality, optimize_images, variant, identifier)` is frozen and
validated at construction. A bad field raises `ProfileError`, which is a `PdfError` for the
exporter's contract and a `ValueError` because a profile is setup, as a `Config` field is.

| Preset | dpi | JPEG quality | Lossless pass | Variant | Default of |
|---|---|---|---|---|---|
| `PRINT` | none | none | off | none | `render_pdf`, `save_pdf`, `layout` |
| `SCREEN` | 150 | 85 | on | none | `pdf_attachment` |

- **`PRINT` is `render_pdf`'s default so no caller's bytes moved.** It is WeasyPrint's own
  defaults, and `TestTheProfileAgreesWithTheBackend` holds each option to `DEFAULT_OPTIONS`.
  Every fixture's PRINT render was checked byte-identical to the render before the profile.
- **`SCREEN` is `pdf_attachment`'s default** because a PDF built to be attached is built to be
  read on a screen. The two defaults differ on purpose, and each names the job.
- **`dpi` caps an image where it is shown.** WeasyPrint measures the drawn size, so an image
  already under the cap is untouched, and a CSS background is capped like an `img`. The
  brochure's 1150 × 2625 cover ground became 767 × 1750.
- **`jpeg_quality` re-encodes JPEG sources only.** A PNG keeps its lossless encoding, because
  a lossy step on a chart's flat colour costs clarity and saves little.
- **150 and 85 are the preset's own numbers, not `Config`'s.** They describe a preset, as
  `A4_PORTRAIT`'s margin does. A caller who wants others builds a profile.
- **A brochure may be written under `SCREEN`.** The result is a proof for a screen, not a
  press file. A press wants the images untouched.
- **`PDF_VARIANTS` is a literal list**, so a profile validates with `[pdf]` absent. A test
  holds it to WeasyPrint's own list whenever the backend is installed.

What the profile must not touch is read back under both presets: the text layer, every link
annotation and its target, the bookmarks, and the alt text of a tagged pair.

Sizes, PRINT to SCREEN, measured when the profile landed:

| Fixture | PRINT bytes | SCREEN bytes | Saved |
|---|---|---|---|
| `a4_portrait` | 37 301 | 37 184 | 0.3% |
| `a4_long_table` | 46 161 | 46 161 | 0.0% |
| `a4_editorial` | 23 935 | 23 060 | 3.7% |
| `slide_16_9` | 41 181 | 41 181 | 0.0% |
| `tri_fold_letter` | 43 503 | 35 171 | 19.2% |

The gallery's images are flat-colour PNGs, which compress to almost nothing. A realistic one
tells the story better: a 2400 × 1600 noise image shown at the column's width went from
2 990 525 to 156 839 bytes as a JPEG (95%) and from 9 731 251 to 800 206 as a PNG (92%).

## Determinism — the identifier and the date

**The PDF bytes for one document are identical on every call.** The goldens rest on this, and
so would any PDF golden, which would have to be per profile since downsampling moves bytes.

- **No creation or modification date.** The skeleton emits no `dcterms.created`, and a test
  reads both fields back empty.
- **The identifier is `None` in both presets, by measurement.** The issue assumed WeasyPrint
  writes a random `/ID`. WeasyPrint 70 writes none at all unless a variant requires one, and
  then it derives the ID from the file's own md5. A fixed identifier in `PRINT` would have
  moved every render for no gain.
- **Determinism needs HarfBuzz-Subset.** Without it WeasyPrint subsets fonts through
  fontTools, and `TTFont.save()` stamps the clock into each font's `head` table. Renders then
  differ whenever they straddle a second. CI's `pdf` job installs `libharfbuzz-subset0`.

## Metadata from the facts (#195)

Author is `firm_name`. Subject is `campaign_name`, `department` and `date_range` joined on
" · ". Keywords are `department` and `issue_label`, joined on a comma because the PDF splits
keywords on one. Title and `Lang` were already the skeleton's. Every value comes from
`DocumentMetadata` through three `meta` lines in the head, and no exporter argument restates
one. `media.md` has the skeleton side.

## Attachments and the size budget (#197, #198)

`Attachment(data, filename, mime_type, size_hint)` is a sibling of `ImageAsset`, not the same
class: an asset is referenced by `cid:` and rendered in place, while an attachment is
referenced by nothing and shown as a file. With attachments, `build_message` wraps the
alternative in a `multipart/mixed` and carries each file after it. The related subtree keeps
its shape one level deeper. With none, the message is byte-identical to before, checked across
the whole email gallery.

- **The adapters changed by zero lines.** They serialise through `to_wire_bytes()` and never
  look inside. A test sends through each adapter's `send_message` and finds the file intact.
- **`svc.delivery` never learns what a PDF is.** `svc.pdf.pdf_attachment` builds the
  `Attachment`, and the dependency runs that one way. `size_hint` is how the exporter tells the
  delivery layer what would shrink a file without the delivery layer knowing profiles exist.
- **The budget is on the message, not the PDF**, because servers count encoded wire bytes.
  `config.md` has the two thresholds and why the lower default won.

## Tagged PDF (#199): measured, and left opt-in

WeasyPrint 70 writes `pdf/ua-1` through `pdf_variant`. It was measured on every printed
fixture under `SCREEN`:

| Fixture | Untagged bytes | Tagged bytes | Cost | Seconds, untagged | Seconds, tagged | Warnings |
|---|---|---|---|---|---|---|
| `a4_portrait` | 37 184 | 45 167 | +21.5% | 0.41 | 0.37 | 0 |
| `a4_long_table` | 46 161 | 62 669 | +35.8% | 0.83 | 0.91 | 0 |
| `a4_editorial` | 23 060 | 26 177 | +13.5% | 0.21 | 0.23 | 0 |
| `slide_16_9` | 41 181 | 52 991 | +28.7% | 0.54 | 0.56 | 0 |
| `tri_fold_letter` | 35 171 | 40 033 | +13.8% | 0.67 | 0.61 | 0 |

The cost is small. The tagged file is deterministic, marked, has a structure tree and a
catalog `Lang`, and every image carries its alt text. **What stopped it being the default is
what it tags wrongly**, and none of it is the markup:

| Fixture | Tables | Layout, `role="presentation"` | Data | Tagged `/Table` |
|---|---|---|---|---|
| `a4_portrait` | 21 | 20 | 1 | 21 |
| `a4_long_table` | 16 | 15 | 1 | 31, split across sheets |
| `a4_editorial` | 13 | 13 | 0 | 13 |
| `slide_16_9` | 21 | 20 | 1 | 24 |
| `tri_fold_letter` | 31 | 31 | 0 | 31 |

- **WeasyPrint 70 tags by element name and never reads `role`.** Every layout table becomes a
  `/Table` with rows and cells, so a screen reader announces twenty grids that hold no data.
  The email's table layout is not negotiable, since Outlook's Word engine reads nothing else.
- **A decorative image becomes a `/Figure` with no `/Alt`**, not an artifact, and WeasyPrint
  logs "has no required alt description" as it writes it. The markup says `alt=""` and
  `role="presentation"`, which is correct. PDF/UA forbids a figure without alternate text.

A file that declares PDF/UA-1 while doing both would claim a conformance it does not have,
which is worse than declaring none. So **`SCREEN.variant` stays `None`**, and a caller who
wants the tags sets `variant="pdf/ua-1"` on a profile of their own. `PRINT` stays `None`
regardless: a press file's conformance concern is PDF/X, a non-goal here.

`TestWhatKeepsTheScreenProfileUntagged` pins both blockers. When either test fails, the
blocker has moved: revisit this decision rather than updating the numbers. The fix paths are
in #202. Retagging through WeasyPrint's `finisher` hook reaches internals the pin
protects but a minor release could move. An upstream change is the other route.

**The checks are structural, and say so.** pypdfium2 cannot validate PDF/UA. The tests check
that `/MarkInfo`, `/StructTreeRoot`, the catalog `Lang` and each `/Alt` are present. Full
conformance needs veraPDF, a Java tool this repository will not carry.
