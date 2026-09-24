# fonts/ — bundled brand faces

**Ships empty on purpose.** No font file enters this repository: licensing for embedding
and for server-side rendering is per-family, and an unlicensed embed is a real liability.

## What to drop in

The CSS declares `@font-face` against these filenames. Supply the faces you have licensed
for **embedding** and for **server-side / automated** use — those are two separate grants,
and a desktop licence covers neither.

| Filename | Role | Used for |
|---|---|---|
| `brand-sans-400.woff2` | display regular | headings, table headers, footers |
| `brand-sans-600.woff2` | display semibold | page title, emphasis |
| `brand-text-400.woff2` | text regular | body copy, disclaimers |
| `brand-text-600.woff2` | text semibold | inline emphasis |

`woff2` keeps the PDF small and WeasyPrint subsets it on embed. `ttf`/`otf` also work —
rename the `src` in `factsheet.css` to match whatever you actually ship.

## Until they are here

The factsheet renders with the documented fallback stack and **says so loudly** rather than
looking finished:

- `lint_print_html.py` reports **W004** for each family with no loadable face.
- `render.py` puts ``Font-face 'X' cannot be loaded`` in its **fonts** warning bucket and
  exits **1**.
- `snapshot.py` flags fallback families (`DejaVu`, `Liberation`, `Nimbus`, `URW`) by name in
  the `pdffonts` report.

A silent fallback is the failure mode this arrangement exists to prevent. If all three of
those are quiet and you did not add fonts, something is wrong with the checks, not with the
fonts.
