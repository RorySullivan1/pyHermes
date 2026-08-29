---
paths:
  - "svc/delivery/**/*"
  - "svc/gmail/**/*"
  - "svc/outlook/**/*"
---

# Delivery and the send adapters

## Architecture — `svc/delivery`

The builder **declares** a CID embed; delivery **performs** it. `Email.render()` gives the
HTML, `Email.text()` the plain-text projection and `Email.assets()` the manifest;
[build_message()](../../svc/delivery/message.py) turns those three into a sendable `EmailMessage`.

```python
from svc.delivery import build_message, save_eml

message = build_message(email, sender="research@example.com",
                        to=["reader@example.com"])   # subject defaults from the email
save_eml(message, "output/preview.eml")     # dry run — no transport, no credentials
```

- **Structure** — every message is a `multipart/alternative` since #111:

  ```
  multipart/alternative            (an email with no CID images)
  ├── text/plain
  └── text/html

  multipart/alternative            (an email with CID images)
  ├── text/plain
  └── multipart/related
      ├── text/html
      └── image/*  × N
  ```

  **Text first, HTML last** — RFC 2046 §5.1.4 orders an alternative by *increasing*
  preference. Getting it backwards is silent: every graphical client still shows the HTML,
  and only the readers who need the fallback see the wrong thing.

  **The seat was reserved, not discovered.** This file and the module docstring both said the
  HTML part would become half of an alternative and the related subtree would nest inside
  unchanged — which is exactly what happened, byte for byte, one level deeper.

  **The images relate to the HTML part, not to the alternative.** They are resources of the
  HTML specifically; relating them one level up would attach them to the text part too, which
  is how a text-only reader ends up with a paperclip for art they cannot see.

  **A message now carries at least one random MIME boundary, and two when it has CID
  images.** A snapshot comparison must normalise *every* one — code written against the old
  single-boundary shape normalises the first and still differs on the second, which fails for
  a reason that has nothing to do with what it is checking.
- **There is no HTML-only opt-out**, deliberately. The text part is derived and costs nothing,
  and a flag to suppress it would be a deliverability and accessibility regression a caller
  reaches for by accident.
- **The consumer adds the decorations.** `ImageAsset.content_id` is bare, so assembly emits
  `Content-ID: <id>` — Python's `add_related()` stores whatever it is given, and a bare id is
  an RFC-invalid header. It also passes `disposition="inline"` explicitly, because supplying
  a `filename` alone yields `attachment` and shows inline art as a paperclip.
- **The seam is now checked, not just documented** — and the two directions are deliberately
  asymmetric. Assembly cross-checks the HTML's `cid:` references against the manifest: a
  referenced-but-unattached id is a broken image the reader sees, so it raises `MessageError`;
  an attached-but-unreferenced asset only costs message weight, so it warns. **The check is
  scoped to the HTML part**: the text part carries URLs as text and never a `cid:` reference,
  so copy that happens to say `cid:` — `image_matrix` titles a section "Attached (cid:)" — is
  neither read as a reference nor able to satisfy one. Making the second
  fatal would turn any gap in reference collection into a *rejected valid email*. Collection
  covers attributes, `url(cid:…)` in CSS (including `<style>` blocks), `srcset` lists, and
  markup inside `<!--[if mso]>` conditional comments.
- **Assembly is pure**: no credentials, no network, no clock, so it is testable without either.
  It stamps no `Date`/`Message-ID` and accepts no `Bcc` (that header travels with the message
  and leaks the blind-copy list) — both are transport concerns for the adapters. Output is
  byte-identical for a given input **except** the MIME boundary on a `multipart/related`
  result: the stdlib draws a fresh random one per call, so a snapshot test (#58) must
  normalize it. `svc/delivery/message.py`'s docstring says exactly what to normalize.
- **Errors are a separate hierarchy.** `DeliveryError` is a **sibling** of `EmailBuilderError`,
  not a child: a send failure is not a build failure. `MessageError` covers assembly.
- **`subject` is optional and falls back to [Email.metadata](../../svc/builder/email.py)'s
  `email_subject`**, which `validate()` already requires. An explicit `subject=` always wins,
  and an explicitly blank one is still an error rather than a silent fallback — a caller who
  passed something meant it. `Email.metadata` is read-only and deliberately not a copy: the
  object was never really private (an `Email` built from an `EmailMetadata` stores the
  caller's own instance), and a copy would let a mutation silently do nothing.

### Writing a delivery consumer

Two adapters exist, and the rules below are what they have in common — the shape a third one
(a generic SMTP sender, say) should transplant rather than re-derive. **An adapter transmits;
it never rebuilds.** Concretely:

1. **Take an authorized transport, not credentials.** Define a one-method `Protocol` and let
   the caller satisfy it. This is why pyHermes has no provider SDK in its dependency tree —
   `svc/gmail` and `svc/outlook` import nothing from Google or Microsoft, and a test in each
   parses the module's **AST** to keep it that way. Token acquisition, refresh and revocation
   stay with the caller, where an application's secret handling already lives.
2. **Serialise with [to_wire_bytes()](../../svc/delivery/message.py)**, never `message.as_bytes()`
   directly. One path means the bytes you transmit equal the bytes `save_eml()` writes, which
   is the only reason the dry run is a preview rather than an approximation. Each adapter
   asserts that equality in its own suite.
3. **Reuse [retry_with_backoff()](../../svc/delivery/retry.py); supply your own `is_transient`.**
   The policy is shared because it is transport-neutral; the classification is not, because
   only you know what your provider's rate-limit error looks like. If your provider sends a
   `Retry-After`, pass a `delay_hint` too. Leave the numeric arguments alone unless your
   provider genuinely needs a different ladder — omitted, they come from
   [Config](../../svc/config.py), so a deployment can retune every adapter at once.
4. **Never retry an unrecognised failure.** On a send path an unknown error may already have
   delivered, and a blind retry risks a duplicate. Retry only what you positively identify.
5. **Map every failure to `TransportError`, chaining the provider's exception** with
   `raise ... from exc`. Callers catch `DeliveryError` for "the email was fine, sending it
   was not".
6. **Name where your provider differs, in the module docstring.** The adapters look alike
   enough that a real difference can be "harmonised" away by mistake — Graph needing standard
   base64 where Gmail needs URL-safe, and returning no message id, are both pinned by tests
   for exactly that reason.
7. **Test against a fake transport.** No adapter test may require a live mailbox, a network,
   or recorded HTTP fixtures — fixtures drift, and a suite nobody can run locally stops being
   run. A fake is a class with one method.

**If the builder's contract turns out to be insufficient, file it against the builder** — do
not reach into private state from delivery code. That rule produced two findings (#72, #73),
both since fixed in the builder rather than worked around in delivery: `Email.metadata` is now
a read-only accessor, and `images.py` no longer claims delivery qualifies a Content-ID.

### Deliberate non-features

Recorded as decisions, so they are not re-litigated as oversights:

| Not done | Why |
|---|---|
| `Date` / `Message-ID` in assembly | Transport's job; omitting them keeps assembly pure and its output comparable |
| `Bcc` header | It travels with the message and leaks the blind-copy list — an envelope concern for adapters |
| Size re-check in assembly | `render()` already applied the 102 KB limit, and CID bytes cost *message* size, not HTML size |
| OAuth flows in adapters | Deliberately the caller's; see rule 1 above |
| Campaign management | No scheduling, recipient lists, batching or send-time analytics — this layer delivers one message to addressees the caller supplies |
| Open tracking / link rewriting | A product decision far beyond transport |
| **Any compliance policy** | pyHermes does not decide what an email must *say*. Disclaimer language, unsubscribe links and every other compliance question are the caller's judgement: the library cannot know whether an email is a commercial newsletter, an internal note or a receipt, and each answers differently — a library that guessed would be wrong for two of the three. What it guarantees instead is narrower and checkable: a region *variant* will not silently drop content the caller supplied (`REQUIRED_SLOTS`), and what renders is shape- and safety-valid (hex colours, URL schemes). `LinkRow(links=[])` and an empty `disclaimer` are both valid |
| `Retry-After` as an HTTP-date | Legal but rare; degrades to the computed backoff instead of crashing |

## Architecture — `svc/gmail`

Delivery assembles bytes; an adapter transmits them. `svc/gmail` owns Gmail's **wire
contract** — the base64url `raw` encoding, the `users.messages.send` shape, which failures
are worth retrying — and deliberately does **not** own authentication.

```python
from googleapiclient.discovery import build      # the caller's dependency, not ours
from svc.delivery import build_message
from svc.gmail import GoogleApiTransport, send_message

service = build("gmail", "v1", credentials=creds)          # caller authenticates
message = build_message(email, subject=..., sender=..., to=[...])
message_id = send_message(message, transport=GoogleApiTransport(service))
```

- **The adapter takes an authorized transport, not credentials.** `GmailTransport` is a
  `Protocol` with one method, so a real `googleapiclient` service, a stub, or anything else
  with `send_raw` satisfies it. Consequences, all deliberate: pyHermes imports nothing from
  Google and gains **no dependency** (a test asserts this by parsing the module's AST); no
  credential ever touches this package; and the whole send path is testable with **no
  mailbox, no network, and no recorded fixtures to drift**. Token acquisition, refresh and
  revocation stay with the caller, where an application's secret handling already lives.
  `GoogleApiTransport` is a duck-typed three-line shim so callers needn't rewrite it.
- **Retry policy is shared, classification is not.** [retry_with_backoff()](../../svc/delivery/retry.py)
  is transport-neutral and lives in `svc/delivery`, so the Outlook adapter (#70) reuses it
  rather than growing a second copy. Each adapter supplies its own `is_transient`, because
  only it knows what its provider's rate-limit error looks like. Gmail retries 429 and the
  5xx family plus network interruptions; **an unrecognised failure is not retried**, because
  on a send path it may already have delivered and a blind retry risks a duplicate.
- **`sleep` is injected**, so tests exercise the real backoff ladder without spending it.
- **The bytes sent are the bytes `save_eml()` writes** — both go through
  [to_wire_bytes()](../../svc/delivery/message.py), and a test asserts the equality. That is what
  makes the dry run a faithful preview rather than an approximation.
- **`TransportError`** (a `DeliveryError`) covers every send failure, always chaining the
  provider's own exception. It is distinct from `MessageError` on purpose: an unbuildable
  message is the caller's data problem, while an unsendable one may be worth retrying later
  with the exact same bytes.

## Architecture — `svc/outlook`

The second adapter, and the proof the seam generalises: it transplants
[svc/gmail](../../svc/gmail/sender.py)'s shape — injected transport, `TransportError` mapping,
shared retry — and differs only where Microsoft Graph genuinely differs from Gmail.

```python
import requests                                # the caller's dependency, not ours
from svc.delivery import build_message
from svc.outlook import GraphApiTransport, send_message

session = requests.Session()                   # caller authenticates
session.headers["Authorization"] = f"Bearer {token}"
send_message(build_message(email, ...), transport=GraphApiTransport(session))
```

**Transport chosen: Microsoft Graph**, over the two alternatives. SMTP needs no SDK but is
not *Outlook* — it is a generic protocol that happens to reach Microsoft 365, and Microsoft
has been retiring basic auth for it; a generic SMTP adapter would be a fine thing to add
later and could reuse `retry_with_backoff` unchanged. `win32com` is Windows-only and needs a
running Outlook install — wrong for a library. Graph won decisively because **`sendMail`
accepts a whole RFC 822 message as base64**, so the bytes sent stay identical to what
`save_eml()` writes; decomposing into Graph's JSON `message` schema would put that equality,
and the dry run's usefulness, at risk.

**Where Graph differs from Gmail** — named in the module docstring rather than quietly
diverged from, because the adapters otherwise look alike:

| | Gmail | Graph |
|---|---|---|
| base64 alphabet | URL-safe | **standard** (URL-safe is rejected) |
| success response | message id | **`202 Accepted`, empty body** |
| `send_message` returns | the id | **`None`** — there is nothing to return |
| meaning of success | message created | **accepted for processing, not delivered** |

**`Retry-After` is honoured, and that is not politeness.** Microsoft's guidance is that
throttled requests keep accruing against the quota, so a client that guesses a shorter delay
stays throttled *longer*. `retry_with_backoff()` therefore takes an optional `delay_hint`;
Outlook supplies one that reads the header, Gmail passes none and keeps the computed ladder.
An `HTTP-date` form of the header degrades to the ladder rather than crashing.
