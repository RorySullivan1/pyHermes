# Environment — installing and troubleshooting WeasyPrint here

Two sets of facts below, kept apart on purpose. **Field-settled** entries came from the
target JupyterHub environment and are recorded as reported, not re-verified. **Probe-settled**
entries were measured in a session and say what was measured. Never promote one to the other.

## Field-settled (locked-down JupyterHub / Kubernetes, reported 2026-09-15)

- No `apt` access. Packages come from an **internal Nexus conda mirror**.
- WeasyPrint **69.0** installs with `conda install weasyprint`.
- **Do not pass `-c conda-forge`.** The shorthand expands against the channel alias and
  returns 404; the default configured channels already resolve the conda-forge mirror.
- Install companions with **conda, not pip**, to avoid mixing compiled dependencies:
  `conda install matplotlib jinja2 poppler`. `poppler` is what provides `pdftoppm` and
  `pdffonts`, which `scripts/snapshot.py` needs.
- Verify with `python -m weasyprint --info`.
- **Works in the terminal but not the notebook?** Compare `sys.executable` in both. The
  kernel is frequently a different environment from the login shell. That mismatch is why
  `render.py` takes `--python` / `$WEASYPRINT_PYTHON` instead of assuming its own
  interpreter.
- Minimal container images ship few fonts. Check with `fc-list | wc -l` and **always bundle
  the fonts you name** — an unembedded family falls back silently.
- **Pin exact versions in `environment.yml`** once templates are approved. Minor releases
  move layout, and a factsheet that repaginates between runs is a compliance problem, not a
  cosmetic one.

## Probe-settled (measured 2026-09-15, WeasyPrint 69.0)

- WeasyPrint 69.0 installs from PyPI wheels and imports with **no system libraries added**
  in a plain Debian-based container, and renders real multi-page PDFs there. So a sandbox
  without conda can still run the full write → lint → render loop.
- **poppler is NOT pip-installable.** `pdftoppm`/`pdffonts` are system binaries; without
  them `snapshot.py` refuses and reports a missing precondition. There is no Python
  fallback wired in — rasterisation is the one step that needs the conda `poppler` package
  (or any other poppler on `PATH`).
- The two loggers are `weasyprint` (warnings, errors) and `weasyprint.progress` (info).
  Attach a handler to `weasyprint` at `WARNING` to capture problems without progress noise.
- `FatalURLFetchingError` subclasses **`BaseException`, not `Exception`** — so
  `except Exception` does not catch it. See DECISIONS.md.

## Which interpreter will `render.py` use?

In order: `--python PATH`, then `$WEASYPRINT_PYTHON`, then the current interpreter if
`import weasyprint` succeeds in it. If none works it exits **2** and prints each candidate
it tried. Set the env var once per session:

```bash
export WEASYPRINT_PYTHON="$(conda run -n <env> which python)"
```

## Diagnosing "it looks different on the server"

Almost always fonts. In order:

1. `pdffonts report.pdf` — is the family you asked for listed, and is `emb` = `yes`?
2. A `DejaVu`, `Liberation`, `Nimbus` or `URW` family in that list is the signature of a
   fallback: an `@font-face` failed and WeasyPrint substituted silently.
   `scripts/snapshot.py` flags these by name.
3. `fc-list | grep -i <family>` on both machines — but do not *fix* it by installing the
   font. Bundle the file and declare `@font-face` with a relative `src`, so the document
   stops depending on the host at all.
4. Re-render with `render.py`; a font that cannot be loaded appears in the **fonts**
   warning bucket as ``Font-face 'X' cannot be loaded``.
5. Still different? Compare `python -m weasyprint --info` on both. A minor-version
   difference is enough to change line breaking, and therefore pagination.
