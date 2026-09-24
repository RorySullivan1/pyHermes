# Live-host probes — outlook-html-specifications (issue #43)

Five claims in `../SKILL.md` are labelled **field-settled**: consistently observed across
the email-dev field, absent from the Microsoft pages the skill cites. Only a render in
**classic Outlook for Windows** settles them. This folder is that render, packaged as a
perturbation experiment: two emails whose bodies are identical except for the mitigations,
so every observed difference is attributable to a specific delta.

| Claim | Where to look |
|---|---|
| Font stack falls to Times New Roman without the `[if mso]` gate | S1, A vs B |
| data-URI/base64 images don't display | S2 (both) |
| Animated GIFs show frame 1 only | S3 (both) |
| The `o:PixelsPerInch` block fixes display-scaling tears | S4 at 125/150%, A vs B |
| A single table past ~1,790px splits with a visible seam | S5, A vs B |

`probe-b-mitigated.html` is **generated from** `probe-a-baseline.html` (three deltas:
head block, table split, labels — verified 29 changed lines, both parse clean). Don't
hand-edit B; regenerate it from A if A changes, or the "identical body" premise dies.

## Sending (~10 minutes, needs classic Outlook on Windows)

1. Fill the two `{{…}}` placeholders in **both** files: any hosted static image URL, and
   a hosted **animated GIF whose first frame is visibly distinct** (a countdown GIF is
   ideal — a frozen "9" is unambiguous).
2. Send each file as an HTML email to a mailbox read in **classic Outlook for Windows**.
   Two easy routes: paste the HTML via a VBA one-liner
   (`MailItem.HTMLBody = <file contents>` — see the vba-development family), or send
   through any SMTP tool that accepts raw HTML bodies. Don't compose-and-forward — that
   re-processes the HTML before it ever renders.
3. Read both emails at **100% Windows display scaling**, then again at **125% or 150%**
   (Settings → Display → Scale; restart Outlook after changing).

## Recording — per section, per email

- **S1 font:** which typeface actually renders in A (Georgia's round serifs vs Times'
  narrow ones — the `Igq10` reference letters differ visibly)? In B it must be Arial;
  if it isn't, the gate itself failed — record that separately.
- **S2 base64:** does the red box render, or does alt text show? (Same expected in both.)
- **S3 GIF:** animating, or frozen on frame 1? (Same expected in both.)
- **S4 scaling canary:** at 100%, do the blue (attribute-width) and red (CSS-width) bars
  align in both? At 125/150%, do they still align in **A**? In **B**? The claim predicts
  A tears and B doesn't.
- **S5 tall table:** in **A**, scan the 120 numbered rows for a horizontal seam or stripe
  misalignment and record the row number. In **B** (split at row 061) there should be
  none. If A shows no seam either, the ~1,790px figure is refuted or version-bound —
  record the Outlook build number (File → Office Account → About).
- Note the exact client: classic Outlook build, Windows version, scaling factor. The
  same emails viewed in new Outlook / OWA are a useful cross-check (most differences
  should vanish there) but are not evidence about the Word engine.

## Closing the loop

Per `claim-grounding` (deliberate promotion, never silent): each claim gets **CONFIRMED**
(upgrade its field-settled label in `../SKILL.md` to probe-confirmed with build + date) or
**REFUTED** (fix the skill text at the source — the defensive guidance may survive, the
stated behavior must match the observation). Either way add ledger rows
(`../../claim-grounding/reviews/ledger.jsonl`, shape per
`../../claim-grounding/references/ledger-schema.md`) with
`grounded_by: "probe:outlook-html-specifications/probes"`, and replace the standing
"no live host" coverage-gap row with one recording this run. Paste the observation notes
into issue #43 verbatim — observations first, verdicts after.
