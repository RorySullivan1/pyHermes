# Examples

Worked examples of building emails with `svc.builder`. Each example is a
self-contained directory that pairs the **source script** with the **rendered
output** it produces, so you can read the builder code and see exactly what HTML
it generates.

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
