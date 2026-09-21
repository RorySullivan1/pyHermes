"""
Screenshot runner: the gallery through headless Chromium (#59).

Renders every fixture at both supported viewports and writes PNGs, so a
reviewer sees a visual change without checking out the branch::

    python -m qa.screenshots                    # the whole gallery
    python -m qa.screenshots kitchen_sink       # named fixtures only

**Pinned**: the viewports, the device scale factor, the ``cid:``-to-data-URI
substitution. **Recorded, not pinned**: the browser build, in ``run.json`` —
a screenshot is a review artifact, and pinning Chromium would make it a gate.

Optional by design: `[dev]` has no browser, and the tests skip rather than
fail, which is what proves `[qa]` stays optional.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import struct
import sys
import tempfile
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from svc.builder.document import Document

from .fixtures import all_fixtures

# Playwright handles are typed ``Any``: it is an optional extra, so it is not
# installed in the environment mypy runs in (the `check` CI job takes `[dev]`
# only, which is what keeps the core suite browser-free).

#: Where the images land. Gitignored — these are ephemeral checks, not
#: reference artifacts. Nothing in the suite compares them to a stored copy.
DEFAULT_OUT_DIR = Path("output/screenshots")

#: ``base.html``'s mobile rules trigger below 700px. Desktop sits comfortably
#: above it and above the 680px table; mobile is a common phone width and well
#: under the breakpoint, so the ``.kpi-cell`` collapse and the mobile overrides
#: actually fire. Pinned, unlike the browser build.
VIEWPORTS: dict[str, tuple[int, int]] = {
    "desktop": (1000, 900),
    "mobile": (375, 800),
}

#: The viewport widths pyHermes claims to render without a horizontal
#: scrollbar. **375 is the floor**, decided in #133 rather than left implied.
#: 360 and 320 are *not* supported: the global `img { width:auto }` that would
#: clear them collapses every image to its alt-text box when images are
#: blocked, destroying the display width `img-width-attr` exists to enforce.
#: `.claude/rules/qa-harness.md` carries the measurements.
SUPPORTED_WIDTHS: tuple[int, ...] = (1000, 375)

#: Pinned: a scale factor of 2 would double every dimension and make two runs
#: incomparable for no gain at this fidelity.
DEVICE_SCALE_FACTOR = 1

#: Environment variable naming a Chromium binary to use instead of the one
#: Playwright manages. Needed wherever the browser is supplied by the image
#: rather than downloaded — a sandbox that ships Chromium and disables
#: `playwright install`, for instance, where Playwright's expected revision and
#: the installed one need not agree. Read at use time, never at import.
EXECUTABLE_ENV_VAR = "PYHERMES_CHROMIUM"

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

_CID_SRC = re.compile(r'(?P<prefix>src\s*=\s*["\'])cid:(?P<id>[^"\']+)(?P<suffix>["\'])')


@dataclass(frozen=True)
class Shot:
    """One captured image."""

    fixture: str
    viewport: str
    path: Path
    width: int
    height: int


class ScreenshotError(RuntimeError):
    """Raised when the runner cannot capture — a missing browser, usually."""


# ──────────────────────────────────────────────────────────────────────
# Preparing the HTML
# ──────────────────────────────────────────────────────────────────────


def inline_cid_images(html: str, email: Document) -> str:
    """
    Rewrite ``src="cid:X"`` to a data URI, for the screenshot only.

    A ``cid:`` reference resolves against the MIME message a delivery adapter
    assembles; a browser loading a bare HTML file has no such message, so every
    attached image would render as a broken-image icon and the screenshot would
    be worthless for the one job it has. The bytes are already in the manifest
    :meth:`Email.assets` publishes, so the substitution is exact rather than a
    stand-in.

    This touches the *screenshot copy* and nothing else: ``email.render()`` is
    unchanged, and the goldens (#58) still pin the real ``cid:`` markup. A test
    asserts that separation.

    An id with no manifest entry is left alone — ``build_message()`` already
    raises on that, and a broken image here is the honest depiction of what a
    reader would see.
    """
    by_id = {asset.content_id: asset for asset in email.assets()}

    def substitute(match: re.Match[str]) -> str:
        asset = by_id.get(match["id"])
        if asset is None:
            return match[0]
        payload = base64.b64encode(asset.data).decode("ascii")
        return f"{match['prefix']}data:{asset.mime_type};base64,{payload}{match['suffix']}"

    return _CID_SRC.sub(substitute, html)


# ──────────────────────────────────────────────────────────────────────
# Capturing
# ──────────────────────────────────────────────────────────────────────


def capture_emails(
    emails: Mapping[str, Document],
    out_dir: Path | None = None,
) -> tuple[list[Shot], dict[str, object]]:
    """
    Capture already-built emails, each under the name it is keyed by.

    The gallery is one caller; #61's ``preview`` CLI is the other, and it can
    hand over an email that is not in the registry at all — a user's
    in-progress draft. Keeping the capture keyed by *email* rather than by
    fixture name is what lets both use the same runner instead of the CLI
    growing a second one.

    Every email is rendered before the browser launches, so a build failure
    costs no browser start.

    Returns the shots and the environment record written to ``run.json``.

    Raises:
        ScreenshotError: If Playwright or its browser is unavailable.
    """
    out_dir = out_dir or DEFAULT_OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    pages = {name: inline_cid_images(email.render(), email) for name, email in emails.items()}

    sync_playwright = _load_playwright()
    shots: list[Shot] = []

    with sync_playwright() as playwright:
        browser = _launch(playwright)
        try:
            environment = _describe(browser)
            for name, html in pages.items():
                shots.extend(_capture_one(browser, name, html, out_dir))
        finally:
            browser.close()

    environment["shots"] = [{**asdict(shot), "path": shot.path.name} for shot in shots]
    (out_dir / "run.json").write_text(json.dumps(environment, indent=2) + "\n", encoding="utf-8")
    return shots, environment


def capture_gallery(
    names: list[str] | None = None,
    out_dir: Path | None = None,
) -> tuple[list[Shot], dict[str, object]]:
    """
    Render the named fixtures (or the whole gallery) at every viewport.

    A thin wrapper over :func:`capture_emails` that resolves names through the
    #57 registry.

    Raises:
        ScreenshotError: If Playwright or its browser is unavailable, or a
            requested fixture is not in the gallery.
    """
    gallery = all_fixtures()
    selected = names or sorted(gallery)
    unknown = [name for name in selected if name not in gallery]
    if unknown:
        raise ScreenshotError(f"Not in the gallery: {unknown}. Available: {sorted(gallery)}.")

    return capture_emails({name: gallery[name]() for name in selected}, out_dir)


def _capture_one(browser: Any, name: str, html: str, out_dir: Path) -> list[Shot]:
    """Capture one fixture at every viewport."""
    shots = []
    # A real file rather than set_content(), so relative and data URLs resolve
    # the way they would for a reader who saved the message.
    with tempfile.TemporaryDirectory() as workspace:
        page_file = Path(workspace) / f"{name}.html"
        page_file.write_text(html, encoding="utf-8")

        for viewport, (width, height) in VIEWPORTS.items():
            context = browser.new_context(
                viewport={"width": width, "height": height},
                device_scale_factor=DEVICE_SCALE_FACTOR,
            )
            # Hosted images point at example.com. Left alone, every run waits on
            # DNS that will never resolve; blocked, the render shows what a
            # reader with images off sees, which is Outlook's default state.
            context.route("http://**", lambda route: route.abort())
            context.route("https://**", lambda route: route.abort())
            try:
                page = context.new_page()
                page.goto(page_file.as_uri(), wait_until="load")
                path = out_dir / f"{name}-chromium-{viewport}.png"
                page.screenshot(path=str(path), full_page=True)
                # Measured from the file rather than from the DOM: the image is
                # the artifact, so its own header is the only dimension that
                # cannot disagree with what a reviewer opens.
                width, height = png_size(path)
                shots.append(
                    Shot(
                        fixture=name,
                        viewport=viewport,
                        path=path,
                        width=width,
                        height=height,
                    )
                )
            finally:
                context.close()
    return shots


def png_size(path: Path) -> tuple[int, int]:
    """
    Read ``(width, height)`` straight out of a PNG's IHDR chunk.

    A full-page capture is as wide as the *document*, not the viewport, so an
    image wider than its viewport is real information — the email overflowed
    horizontally and the reader would scroll sideways.
    """
    header = path.read_bytes()[:24]
    if not header.startswith(_PNG_SIGNATURE):
        raise ScreenshotError(f"{path} is not a PNG.")
    width, height = struct.unpack(">II", header[16:24])
    return int(width), int(height)


# ──────────────────────────────────────────────────────────────────────
# The environment, recorded rather than pinned
# ──────────────────────────────────────────────────────────────────────


def _describe(browser: Any) -> dict[str, object]:
    """
    What produced this run.

    The browser build is the field that matters: it is the one thing here that
    is not pinned, so it is the one thing a future reader needs told.
    """
    from importlib.metadata import PackageNotFoundError, version

    try:
        playwright_version = version("playwright")
    except PackageNotFoundError:  # pragma: no cover - installed by definition
        playwright_version = "unknown"

    return {
        "browser": browser.version,
        "browser_channel": "chromium",
        "executable_path": _executable_path() or "playwright-managed",
        "playwright": playwright_version,
        "platform": sys.platform,
        "device_scale_factor": DEVICE_SCALE_FACTOR,
        "viewports": {name: {"width": w, "height": h} for name, (w, h) in VIEWPORTS.items()},
        "full_page": True,
        "note": (
            "Chromium approximates Gmail in a browser and says nothing about "
            "Outlook's Word engine. The browser build is recorded, not pinned: "
            "these images are checks for a human, never diffed or committed."
        ),
    }


def _load_playwright() -> Any:
    """
    Import Playwright, or explain what to install.

    Screenshots are an optional extra, so an absent browser must produce a
    clear instruction rather than an ImportError from three frames down.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - exercised by the skip guard
        raise ScreenshotError(
            'Playwright is not installed. Run `pip install -e ".[qa]"`, then '
            "`playwright install chromium` unless your environment already "
            "provides one (PLAYWRIGHT_BROWSERS_PATH)."
        ) from exc
    return sync_playwright


def _executable_path() -> str | None:
    """The browser to launch, or ``None`` to let Playwright resolve its own."""
    return os.environ.get(EXECUTABLE_ENV_VAR) or None


def _launch(playwright: Any) -> Any:
    """Launch Chromium, turning a missing browser into a ScreenshotError."""
    executable = _executable_path()
    try:
        return playwright.chromium.launch(executable_path=executable)
    except Exception as exc:  # playwright raises its own Error type
        raise ScreenshotError(
            f"Could not launch Chromium: {exc}\n"
            "Either run `playwright install chromium`, or point "
            f"{EXECUTABLE_ENV_VAR} at a Chromium binary this machine already "
            "provides."
        ) from exc


#: Points to px at 96 dpi. A PDF is 72 dpi by definition and a
#: :class:`~svc.builder.sizing.PageFormat` is px at 96, so this is the factor
#: that makes a raster come back at the width the document was designed at.
PDF_PX_SCALE = 96 / 72


def pages_available() -> bool:
    """Whether this environment can rasterise a PDF. Used to skip, never fail."""
    try:
        import pypdfium2  # noqa: F401

        from svc.pdf import available as backend_available
    except ImportError:
        return False
    return bool(backend_available())


def capture_pages(
    documents: Mapping[str, Document],
    out_dir: Path | None = None,
    scale: float = PDF_PX_SCALE,
) -> tuple[list[Shot], dict[str, object]]:
    """
    Rasterise each paged document to one PNG per sheet.

    **A browser is the wrong instrument here.** Chromium renders a paged
    document's HTML as one long scroll, which is precisely the property the
    medium does not have. So standing rule 3 gains a third clause: the
    screenshots approximate Gmail, the lint pass owns Outlook, and **the PDF
    rasterisation owns pagination**.

    ``pypdfium2`` is a self-contained wheel deliberately — Poppler would add
    a *system* binary to an extra meant to be ``pip install`` and nothing
    else. The default ``scale`` reconciles units rather than choosing a
    resolution; see :data:`PDF_PX_SCALE`.
    """
    import pypdfium2

    from svc.pdf import render_pdf

    out_dir = out_dir or DEFAULT_OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    shots: list[Shot] = []
    for name, document in documents.items():
        pdf = pypdfium2.PdfDocument(render_pdf(document))
        for index, page in enumerate(pdf, start=1):
            image = page.render(scale=scale).to_pil()
            path = out_dir / f"{name}-page-{index}.png"
            image.save(path)
            shots.append(
                Shot(
                    fixture=name,
                    viewport=f"page-{index}",
                    path=path,
                    width=image.width,
                    height=image.height,
                )
            )
        pdf.close()

    # Recorded rather than pinned, exactly as the browser build is: what makes
    # two runs comparable is the scale and the page, not the rasteriser.
    return shots, {
        "renderer": f"pypdfium2 {pypdfium2.version.PYPDFIUM_INFO}",
        "pdfium": str(pypdfium2.PDFIUM_INFO),
        "scale": scale,
    }


def available() -> bool:
    """Whether this environment can capture. Used to skip, never to fail."""
    try:
        sync_playwright = _load_playwright()
    except ScreenshotError:
        return False
    try:
        with sync_playwright() as playwright:
            _launch(playwright).close()
    except ScreenshotError:
        return False
    return True


# ──────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m qa.screenshots",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "fixtures",
        nargs="*",
        help="Fixture names to capture. Default: the whole gallery.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUT_DIR}).",
    )
    args = parser.parse_args(argv)

    try:
        shots, environment = capture_gallery(args.fixtures or None, args.out)
    except ScreenshotError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Chromium {environment['browser']} (playwright {environment['playwright']})")
    for shot in shots:
        print(f"  {shot.path}  {shot.width}x{shot.height}")
    print(f"{len(shots)} image(s) in {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
