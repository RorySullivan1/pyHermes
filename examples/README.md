# Examples

Worked examples of building documents with pyHermes. Each is a self-contained
directory pairing the **source script** with the **rendered output** it
produces, so you can read the builder code and see exactly what it generates.

Both media are represented, and a test asserts that stays true: the email
examples render through `svc.email`'s four-slot skeleton, and
`quarterly-review` renders the same components onto sheets through
`svc.document` — a cover, a folio in every margin, a real page break, and a
closing disclosures sheet, plus a PDF when the `[pdf]` extra is installed.

## Layout

```
examples/
├── README.md
└── <example-name>/
    ├── <example-name>.py   — the builder script (run it to regenerate the output)
    └── <example-name>.html — the rendered email it produces
```

One directory per example, named for what it demonstrates (e.g.
`weekly-market-wrap/`). Inside:

- **`<example-name>.py`** — a runnable script that composes an `Email` through the
  fluent `EmailBuilder` API and `.save()`s the result next to itself.
- **`<example-name>.html`** — the committed output of that script, so the example
  renders without running anything. Open it in a browser to view.

## Running an example

```bash
pip install -e ".[dev]"          # once, from the project root
python examples/<example-name>/<example-name>.py
```

The script rebuilds its `.html` output in place. Re-run it after changing the
script (or the builder) and diff the HTML to see what moved.
