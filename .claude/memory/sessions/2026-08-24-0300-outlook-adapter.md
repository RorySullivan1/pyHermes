# 2026-08-24 03:00 · outlook-adapter

**Goal:** Ship #70 — the Outlook send adapter, closing the code half of epic #52.

## What happened
- **Grounded the API contract before writing a line of durable docstring.** Used the Microsoft Learn MCP server to confirm, first-party: the `/me/sendMail` + `/users/{id}/sendMail` endpoints, `Content-Type: text/plain` as the MIME-mode selector, the whole RFC 822 message base64-encoded in the body, `202 Accepted` with an **empty response body**, `400` + `ErrorMimeContentInvalidBase64String` for malformed input, and the throttling guidance. Nothing about Graph was asserted from memory.
- **Transport decision recorded (the thing #70 exists to decide): Microsoft Graph.**
  - Graph won decisively because `sendMail` accepts a whole RFC 822 message as base64 — preserving the `to_wire_bytes` equality #69 established. Decomposing into Graph's JSON `message` schema would have put that (and the dry run's usefulness) at risk.
  - SMTP rejected: generic-not-Outlook, and MS is retiring basic auth. Noted as a sensible *future addition* that could reuse `retry_with_backoff` unchanged.
  - `win32com` rejected: Windows-only, needs a running Outlook — wrong for a library.
- **Four Gmail/Graph differences named in the module docstring** rather than quietly diverged from: standard vs URL-safe base64; 202-empty-body so `send_message` returns `None`; 202 = accepted ≠ delivered; `Retry-After` authoritative.
- **Extended the shared retry policy** with an optional `delay_hint`. Outlook supplies a `Retry-After` reader, Gmail passes none — the "shared policy, per-adapter classification" split from #69 held under its first real test. Gmail's suite proved no regression.
- 42 new tests, **510 total**. Both adapters verified end-to-end from a clean wheel install.

## Gotchas & dead ends
- **Honouring `Retry-After` is correctness, not courtesy.** Microsoft's docs are explicit that throttled requests keep accruing against the quota, so a client guessing a shorter delay stays throttled *longer*. This is what justified touching shared code rather than special-casing inside the adapter.
- Graph returning **no message id** is a genuine API asymmetry, not an oversight: the Gmail adapter's `-> str` return could not be copied. Returning `None` and documenting that a clean return means *accepted*, not *delivered*, is the honest shape.
- `Retry-After` may legally be an HTTP-date rather than seconds. Parsing that was judged out of scope; it degrades to the computed ladder instead of crashing, with a test pinning that.

## State at end
- Branch `claude/review-open-issues-rr8quq`; `main` still `07d5609`. 510 tests, ruff/format/mypy green, wheel verified for both adapters.
- **pyHermes can now build an email and send it** — the original gap epic #52 was filed to close.

## Open threads
- **#71 (docs) is all that remains in #52.** CLAUDE.md already carries per-module architecture sections for delivery/gmail/outlook, so #71 is largely the consumer-side seam write-up + adapter setup guides — with no secrets, tenant ids, or internal hostnames.
- #72 / #73 (builder-side findings) still await decisions.
- A generic SMTP adapter is the natural next transport if one is ever wanted.
