---
name: Bug report
about: Something is broken. Say how to see it and what should happen instead.
---

Part of #<!-- parent?: The epic's number, if this bug belongs to one. Otherwise delete this line. -->

## What happened

<!-- what_happened: The symptom, in plain words. The title should be the symptom too, specific and searchable ("Upload retries forever on 503"), never the area ("bug in uploader"). One bug per issue. -->

## Steps to reproduce

<!-- steps: A numbered list that ends with "Observe: <the symptom>". If you can't reproduce it, say so and give the conditions under which it was seen. Don't invent steps. -->

## Expected

<!-- expected: What should have happened. -->

## Environment

<!-- environment: Version, commit or tag, runtime, and OS: whatever the bug could depend on. -->

## Evidence

<!-- evidence: A log excerpt, stack trace, or failing test, in a fenced block. Trim it to the lines that matter. -->

## Acceptance

<!-- acceptance: `- [ ]` lines. Include a regression test (or a named manual check) that fails before the fix and passes after it. -->

## Done when

A PR into the default branch merges with this line in its description, where N is this issue's number:

```
Fixes #N
```

<sub>GitHub closing keywords work only from a PR description or a commit message, and only when the PR targets the default branch.</sub>
