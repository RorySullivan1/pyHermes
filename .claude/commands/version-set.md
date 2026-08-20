---
description: Define or update the current version in .meta/version — a semver label plus the goals/objectives of this unit of work.
argument-hint: [vX.Y.Z] [— goal; goal; …]
---

You are labeling the current unit of work as a **version** in `.meta/version` (project root).

## 1. Settle the label

`$1` is the version label. If given, use it. If omitted, read any existing `.meta/version`
and propose the next **semantic** bump from its `version:` (patch for fixes, minor for
features, major for breaking) — and confirm with the user if the bump is ambiguous. New
projects with no `.meta/version` start at `v0.1.0` unless told otherwise.

## 2. Gather the goals

From `$ARGUMENTS` (everything after the label) and the conversation, distill the **goals**
(what this version sets out to achieve) and any **objectives / acceptance** (how you'll know
it's done). Keep them concrete and few — these become the PR's contract, so don't pad.

## 3. Write `.meta/version`

Create or update `${CLAUDE_PROJECT_DIR}/.meta/version` (create `.meta/` if absent) in this
shape — preserve `started`/`pr` if the file already exists:

```
# version: <label>
status: in-progress
started: <today, YYYY-MM-DD>
branch: claude/<label>-<short-slug>
pr:

## Goals
- <goal>

## Objectives / acceptance
- <objective>
```

The `branch` slug is a 2–4 word kebab summary of the theme. Leave `pr:` empty —
`/version-ship` fills it.

## 4. Confirm

Show the written `.meta/version` and the derived branch name. Note that running
`/version-ship` later will name and open the PR from these goals. Don't create the branch or
push here — this command only records intent.
