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

## Outlook: why Graph, and how it differs from Gmail

Moved out of `svc/outlook/sender.py`'s module docstring by #138: the module states its purpose, and the reasoning that produced it lives here.

```
Outlook send adapter, over Microsoft Graph.

Transport choice
----------------
Outlook has three plausible transports, and picking by default is how a
delivery layer rots. This adapter uses **Microsoft Graph**:

- **Microsoft Graph** *(chosen)*. OAuth2, works for any Microsoft 365 tenant,
  needs nothing installed locally — and, decisively, ``sendMail`` accepts a
  whole RFC 822 message as base64 rather than making the caller decompose it
  into Graph's JSON ``message`` schema. That keeps the bytes we send
  identical to the bytes :func:`svc.delivery.save_eml` writes, so inline CID
  images and every header survive exactly as assembled. Re-encoding through
  a JSON schema would put that equality — and the dry run's usefulness —
  at risk.
- **SMTP.** Needs no SDK, but it is not *Outlook*: it is a generic protocol
  that happens to reach Microsoft 365, and Microsoft has been retiring basic
  auth for it. A generic SMTP adapter is a reasonable thing to want, and it
  could reuse :func:`~svc.delivery.retry.retry_with_backoff` unchanged — it
  is simply not this module.
- **``win32com`` / local Outlook automation.** Windows-only and requires a
  running Outlook install. Wrong for a library, ruled out.

*What would change the answer:* if pyHermes ever needed to send from a
desktop Outlook profile rather than a tenant identity, or a caller could not
obtain Graph ``Mail.Send`` permission, the SMTP path would be worth building
alongside this one rather than replacing it.

Where Graph differs from Gmail
------------------------------
Named here rather than quietly diverged from, because the two adapters look
alike and the differences bite:

1. **Standard base64, not URL-safe.** Gmail's ``raw`` field wants the
   URL-safe alphabet; Graph wants ordinary base64 and rejects the message
   with ``ErrorMimeContentInvalidBase64String`` otherwise.
2. **No message id comes back.** ``sendMail`` answers ``202 Accepted`` with
   an empty body, so :func:`send_message` returns ``None`` where the Gmail
   adapter returns an id. There is nothing to return, and inventing one
   would be a lie.
3. **202 means *accepted*, not *delivered*.** Microsoft is explicit that the
   status does not indicate processing has completed. A caller that needs
   proof of delivery must look elsewhere; this function returning cleanly is
   not it.
4. **``Retry-After`` is authoritative.** Microsoft's guidance is that
   throttled requests keep accruing against the quota, so ignoring the hint
   and guessing a backoff actively *prolongs* the throttling. This adapter
   reads the header and lets it override the computed ladder.

Authentication is not this module's job — see :mod:`svc.gmail.sender` for the
same boundary and the reasoning behind it. Bring an authorized session.

Usage::

    import requests                             # the caller's dependency
    from svc.delivery import build_message
    from svc.outlook import GraphApiTransport, send_message

    session = requests.Session()                # caller authenticates
    session.headers["Authorization"] = f"Bearer {token}"

    message = build_message(email, subject=..., sender=..., to=[...])
    send_message(message, transport=GraphApiTransport(session))
```

## MIME assembly — the ordering rules and the boundary-randomness caveat

Moved out of `svc/delivery/message.py`'s module docstring by #138: the module states its purpose, and the reasoning that produced it lives here.

```
Transport-neutral MIME assembly for a built email.

The builder composes and *declares*; this module assembles.
:meth:`~svc.builder.email.Email.render` gives the HTML and
:meth:`~svc.builder.email.Email.assets` gives the manifest of images that
HTML references as ``cid:`` — this turns that pair into an
:class:`~email.message.EmailMessage` an adapter can hand to a transport.

Nothing here authenticates, opens a socket, or reads the clock, and nothing
here calls ``random`` directly — but the result is not byte-identical call
to call. Since #111 every message is a ``multipart/alternative``, so there
is always **at least one** random MIME boundary, and an email with CID
images carries a **second** for the nested ``multipart/related``. Since
nothing in this module calls ``set_boundary``, the stdlib draws each
multipart a fresh random boundary the first time the message is serialised
(inside
``email.generator.Generator``, via ``Message.set_boundary()``) — and that
call *persists* the boundary onto the message object, so every subsequent
``.as_bytes()``/``.as_string()`` on the *same* ``EmailMessage`` returns the
identical boundary and therefore identical bytes. It is drawn once per
:func:`build_message` call (each call constructs a fresh ``EmailMessage``),
not once per serialisation — which is exactly what lets
:func:`to_wire_bytes` and :func:`save_eml` agree byte-for-byte on one
message. Two separate :func:`build_message` calls on the same email
therefore differ only in those boundary tokens and the ``--<token>``
delimiter lines built from them; part order and every part's bytes are
otherwise identical. A snapshot test comparing multipart output across two
such calls must normalize **every** boundary — e.g. replace each
``boundary="..."`` and each delimiter line with a fixed placeholder —
before asserting equality. Note the count changed with #111: code written
against the old single-boundary shape will normalize one and still differ
on the other.

Everything that varies per send — ``Date``, ``Message-ID``, envelope
recipients — belongs to the adapter that sends.

Structure produced::

    multipart/alternative            (an email with no CID images)
    ├── text/plain
    └── text/html

    multipart/alternative            (an email with CID images)
    ├── text/plain
    └── multipart/related
        ├── text/html
        └── image/*  × N    Content-ID: <id>, Content-Disposition: inline

**Text first, HTML last** — RFC 2046 §5.1.4 orders the parts of an
alternative by *increasing* preference, so a client that understands HTML
renders it and a text-mode client falls back to the part before it. Getting
this order backwards is silent: every graphical client still shows the HTML,
and only the readers who need the fallback see the wrong thing.

The seat for this was reserved rather than discovered — the sentence that
stood here until #111 said the HTML part would become one half of an
alternative and this structure would nest inside unchanged, which is exactly
what happened: the ``multipart/related`` subtree below is byte-for-byte what
it was, one level deeper.
```

## Gmail: what the adapter owns, and the three things the credential boundary buys

Moved out of `svc/gmail/sender.py`'s module docstring by #138: the module states its purpose, and the reasoning that produced it lives here.

```
Gmail send adapter: puts an assembled message on the wire.

What this module owns is Gmail's *wire contract* — the base64url ``raw``
encoding, the ``users.messages.send`` shape, which of Gmail's failures are
worth retrying, and how they map onto this package's exception hierarchy.

What it deliberately does **not** own is authentication. It takes an already
authorized transport and calls it. That boundary buys three things:

1. **pyHermes gains no dependency.** Nothing here imports Google's client
   libraries — the transport is a structural type, so a real
   ``googleapiclient`` service, a stub, or anything else with the right
   method all satisfy it. The project's only runtime dependency stays Jinja2.
2. **No credential ever touches this package.** Token acquisition, storage,
   refresh and revocation stay with the caller, which is where an
   application's secret handling already lives. OAuth token lifecycle is
   where naive adapters rot, and the cheapest way not to rot is not to own it.
3. **Tests need no mailbox.** A fake transport is a class with one method, so
   the whole send path — including the retry ladder — is exercised in CI with
   no account, no network, and no recorded fixtures to drift.

Usage::

    from googleapiclient.discovery import build      # caller's dependency
    from svc.delivery import build_message
    from svc.gmail import GoogleApiTransport, send_message

    service = build("gmail", "v1", credentials=creds)   # caller authenticates
    message = build_message(email, subject=..., sender=..., to=[...])
    message_id = send_message(message, transport=GoogleApiTransport(service))
```

## The retry split — why policy is shared and classification is not

Moved out of `svc/delivery/retry.py`'s module docstring by #138: the module states its purpose, and the reasoning that produced it lives here.

```
Bounded retry with exponential backoff, shared by every send adapter.

The split here is deliberate and is what lets the second adapter reuse the
first one's work:

- The **policy** — how many attempts, how long to wait between them — is
  transport-neutral and lives here.
- The **classification** — which failures are worth retrying at all — is
  transport-specific and is supplied by the caller, because only the adapter
  knows what its own provider's rate-limit error looks like.

Retrying a *permanent* failure is not merely useless, it is harmful: it turns
a fast, clear error (a revoked credential) into a slow one, and on a send
path a blind retry risks delivering the same message twice. So the default is
to give up, and only a failure the adapter positively identifies as transient
is retried.
```

## The delivery package front door, in full

Moved out of `svc/delivery/__init__.py`'s module docstring by #138: the module states its purpose, and the reasoning that produced it lives here.

```
pyHermes delivery layer — transport-neutral MIME assembly.

The builder declares a CID embed; it never performs one. Attaching a MIME
part is a transport act, so ``svc.builder`` emits two things and this package
consumes both::

    from svc.delivery import build_message, save_eml

    message = build_message(
        email,
        subject="Weekly Market Wrap",
        sender="research@example.com",
        to=["reader@example.com"],
    )
    save_eml(message, "output/weekly-wrap.eml")   # dry run, no transport

:func:`~svc.delivery.message.build_message` is pure — no credentials, no
network, no clock — so it is fully testable on its own. Sending is the job of
the per-service adapters (``svc.gmail``, ``svc.outlook``), which consume the
message this package builds.
```

## build_message — the Bcc decision and the determinism caveat

Moved out of `svc/delivery/message.py`'s `build_message` docstring by #138: the function keeps its contract, the reasoning lives here.

```
Assemble a built email into a sendable MIME message.

    Args:
        email:    Anything with ``render()`` and ``assets()`` — an ``Email``
            or an ``EmailBuilder``.
        subject:  Subject header. Optional: when omitted it falls back to the
            email's own ``email_subject`` via :attr:`Email.metadata`, which
            ``validate()`` already requires to be non-empty. Pass it
            explicitly to send under a subject that differs from the one the
            email renders into its ``<title>``.
        sender:   ``From`` header.
        to:       One recipient address or a sequence of them.
        cc:       Optional carbon-copy recipients.
        reply_to: Optional ``Reply-To`` header.

    Returns:
        An :class:`~email.message.EmailMessage`: ``text/html`` when the email
        has no CID images, ``multipart/related`` when it does.

    Raises:
        MessageError: On a missing subject, sender or recipient; on a
            control character (CR or LF) in any envelope field; on an asset
            with an unusable MIME type; or when the HTML's ``cid:``
            references and the asset manifest disagree.
        EmailBuilderError: Propagated unchanged from ``render()`` — a build
            failure is not a delivery failure.

    Note:
        No ``Date`` or ``Message-ID`` is stamped — the transport adds them.
        ``Bcc`` is deliberately not accepted — a ``Bcc`` header travels with
        the message and leaks the blind-copy list, so blind copy is an
        envelope concern for adapters.

        Output is deterministic for a given input **except** the MIME
        boundary on a ``multipart/related`` result (an email with CID
        images): the stdlib draws it a fresh random token per
        :func:`build_message` call (it then persists on that
        ``EmailMessage``, which is why repeated serialisation of the *same*
        message is still byte-identical). See the module docstring for
        exactly what that means for a byte comparison across two calls.

    Example::

        message = build_message(
            email, subject="Weekly Market Wrap",
            sender="research@example.com", to=["reader@example.com"],
        )
        save_eml(message, "output/preview.eml")
```

## retry_with_backoff — why a hint outranks the computed backoff, and why it has its own ceiling

Moved out of `svc/delivery/retry.py`'s `retry_with_backoff` docstring by #138: the function keeps its contract, the reasoning lives here.

```
Call ``operation``, retrying only failures ``is_transient`` accepts.

    Args:
        operation:      The zero-argument call to attempt.
        is_transient:   Predicate deciding whether a raised exception is
            worth retrying. Anything it rejects propagates immediately.
        max_attempts:   Total attempts including the first. ``1`` disables
            retrying without needing a separate code path. ``None`` --
            like every numeric argument here -- takes the value from
            :func:`svc.config.get_config`, so the ladder is tunable
            without editing this module.
        initial_delay:  Seconds to wait after the first failure.
        backoff_factor: Multiplier applied to the delay after each failure.
        max_delay:      Ceiling on a *computed* wait — the client's own
            backoff guess — so a long retry chain cannot stall a caller
            indefinitely.
        delay_hint:     Optional reader that extracts a server-specified wait
            from the exception — a ``Retry-After`` header, typically. When it
            returns a value, that wins over the computed backoff, because a
            server saying *how long* to wait knows better than a client
            guessing. Some providers count ignored — or under-honoured —
            hints against a quota, so guessing short is not merely impolite,
            it prolongs the throttling. A hint is clamped by
            ``max_hint_delay``, not ``max_delay``: real providers routinely
            ask for more than a client's own backoff ceiling (Microsoft Graph
            commonly hints 60 seconds or more), so honouring it needs the
            larger bound.
        max_hint_delay: Ceiling on a *hinted* wait specifically. Deliberately
            far above ``max_delay`` so a legitimate hint is always honoured
            in full, but still finite: the hint comes from response data the
            caller does not control, and an unbounded wait on a malformed or
            hostile value would hang the caller indefinitely.
        sleep:          Injected so tests can run the real backoff sequence
            without spending the wall-clock time it describes. Pass a
            recorder to assert the delays.

    Returns:
        Whatever ``operation`` returns on its first success.

    Raises:
        ValueError: If ``max_attempts`` is below 1 — a programming error in
            the call, not rejected data, so it is not a ``DeliveryError``.
        BaseException: The last exception raised by ``operation``, re-raised
            unchanged once attempts are exhausted or the failure is not
            transient. Wrapping it is the adapter's job, which has the
            context to say what it means.
```


## The PDF exporter — the third one, and what it added to the contract (#164)

`svc/pdf/` is an exporter on exactly the terms `svc/gmail` and `svc/outlook` hold: it takes
what the builder produces, owns its own wire format, and owns nothing else. WeasyPrint is the
optional `[pdf]` extra, imported lazily, and an AST test holds that nothing under `svc/builder`,
`svc/document` or `svc/email` imports it.

What it *adds* to the adapter contract is a **resource policy**, and it is the security-relevant
part: the exporter makes **no network requests**. `cid:` references are served from the
document's own manifest, `data:` URIs resolve themselves, and every other URL is refused by name
with a message saying what to do instead. Two settings carry it rather than convention —
`allowed_protocols=("data",)` leaves the inherited opener nowhere to go, and
`fail_on_errors=True` makes a refusal *stop the render*, because WeasyPrint's default is to warn
and carry on, which would drop a chart out of a compliance document and still hand back a PDF
that looks finished.

Four things that phase established, each of which cost a render to find:

- **A document with hosted images cannot be printed**, and that is the policy working rather
  than a gap. The paged fixtures attach their cover art for exactly this reason.
- **The exporter presents its own exception tree.** `fail_on_errors=True` makes WeasyPrint wrap
  the cause in its own `FatalURLFetchingError` on the way out, so a caller catching `PdfError`
  — the documented contract — would have missed it. The exporter unwraps and re-raises, cause
  chained, the way the send adapters do.
- **A print engine does not map a table's `width` attribute.** The component templates carry
  widths as attributes because Outlook's Word engine reads nothing else; without the paged
  skeleton's one mapping rule every table shrink-wrapped to its content — 188px inside a 794px
  page, rendering perfectly and looking like a different document.
- **`@page cover { margin: 0 }` does not suppress a margin box.** It renders anyway, clipped
  against the page edge, which is how the first PDF put a folio on its own cover. Only
  `content: none` removes it, and the region that placed the box is what blanks it.

The pin is `weasyprint~=70.0` rather than a range: version 70 replaced the `url_fetcher`
contract (a `URLFetcher` subclass returning a `URLFetcherResponse`, where every earlier version
took a callable returning a dict), and it is the fetcher that carries the no-network policy — so
a range spanning that change would land the failure on the part that matters most.
