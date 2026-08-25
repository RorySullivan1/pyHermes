"""
The screenshot runner (#59).

Split deliberately in two:

* the **pure** half — CID inlining, PNG measurement, fixture selection, the
  error paths — runs everywhere, because it is ordinary code that happens to
  serve a browser;
* the **capture** half skips when no browser is available, since screenshots
  are an optional extra (``pip install -e ".[qa]"``) and the core suite must
  stay browser-free. Skipping is the required behaviour, not a concession:
  ``pip install -e ".[dev]" && pytest`` is what CI's main job runs.
"""

from __future__ import annotations

import base64
import json

import pytest

from qa.fixtures import all_fixtures
from qa.screenshots import (
    DEVICE_SCALE_FACTOR,
    VIEWPORTS,
    ScreenshotError,
    available,
    capture_gallery,
    inline_cid_images,
    png_size,
)
from svc.delivery import collect_cid_references

requires_browser = pytest.mark.skipif(
    not available(),
    reason='no browser; screenshots are the optional "[qa]" extra',
)


class TestCidInlining:
    """
    A browser has no MIME message, so ``cid:`` references cannot resolve. The
    runner substitutes the manifest's own bytes — otherwise every attached
    image is a broken-image icon and the screenshot cannot do its one job.
    """

    def test_no_cid_reference_survives(self):
        email = all_fixtures()["kitchen_sink"]()
        html = email.render()
        assert collect_cid_references(html), "fixture must have cid: refs for this to mean anything"

        assert not collect_cid_references(inline_cid_images(html, email))

    def test_it_substitutes_the_manifest_bytes_exactly(self):
        """A stand-in image would make the screenshot a picture of the wrong thing."""
        email = all_fixtures()["image_matrix"]()
        asset = email.assets()[0]

        inlined = inline_cid_images(email.render(), email)

        expected = base64.b64encode(asset.data).decode("ascii")
        assert f"data:{asset.mime_type};base64,{expected}" in inlined

    def test_a_repeated_reference_is_substituted_everywhere(self):
        """image_matrix references one attachment twice; both must resolve."""
        email = all_fixtures()["image_matrix"]()
        html = email.render()
        assert html.count('src="cid:') >= 2

        inlined = inline_cid_images(html, email)

        assert not collect_cid_references(inlined)
        assert 'src="cid:' not in inlined

    def test_prose_saying_cid_is_left_alone(self):
        """
        Only ``src`` attributes are rewritten. image_matrix titles a section
        "Attached (cid:)" — substituting on the bare substring would corrupt
        copy, and it is why this rewrites references rather than text.
        """
        email = all_fixtures()["image_matrix"]()
        html = email.render()
        assert "Attached (cid:)" in html, "fixture copy changed; pick another anchor"

        assert "Attached (cid:)" in inline_cid_images(html, email)

    def test_an_unknown_id_is_left_alone(self):
        """
        A reference with no manifest entry stays broken on purpose: it is what
        the reader would see, and build_message() already rejects it loudly.
        """
        email = all_fixtures()["minimal"]()
        html = '<img src="cid:nosuchid" alt="x">'

        assert inline_cid_images(html, email) == html

    def test_it_does_not_touch_the_email_itself(self):
        """
        The substitution is screenshot-only. The goldens (#58) still pin the
        real cid: markup, so a leak here would move them.
        """
        email = all_fixtures()["kitchen_sink"]()
        before = email.render()

        inline_cid_images(before, email)

        assert email.render() == before
        assert collect_cid_references(email.render())


class TestFixtureSelection:
    def test_an_unknown_fixture_is_rejected_by_name(self, tmp_path):
        with pytest.raises(ScreenshotError, match="nosuchfixture"):
            capture_gallery(["nosuchfixture"], tmp_path)

    def test_the_error_lists_what_is_available(self, tmp_path):
        with pytest.raises(ScreenshotError, match="kitchen_sink"):
            capture_gallery(["nosuchfixture"], tmp_path)


class TestPngMeasurement:
    def test_it_reads_the_ihdr(self, tmp_path):
        from qa.fixtures._png import solid_png

        path = tmp_path / "x.png"
        path.write_bytes(solid_png(37, 11, (1, 2, 3)))

        assert png_size(path) == (37, 11)

    def test_a_non_png_is_rejected(self, tmp_path):
        path = tmp_path / "x.png"
        path.write_bytes(b"not a png at all, but long enough to slice")

        with pytest.raises(ScreenshotError, match="not a PNG"):
            png_size(path)


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    """One capture of one fixture, shared — launching a browser is not cheap."""
    if not available():
        pytest.skip('no browser; screenshots are the optional "[qa]" extra')
    out = tmp_path_factory.mktemp("shots")
    return capture_gallery(["image_matrix"], out) + (out,)


@requires_browser
class TestCapture:
    def test_it_writes_one_png_per_viewport(self, run):
        shots, _, out = run
        assert {shot.viewport for shot in shots} == set(VIEWPORTS)
        for shot in shots:
            assert shot.path.is_file()
            assert shot.path.parent == out
            assert shot.path.stat().st_size > 0

    def test_the_names_say_chromium_not_gmail(self, run):
        """
        Fidelity in the filename: this approximates Gmail in a browser and says
        nothing about Outlook's Word engine (epic #54, principle 3).
        """
        shots, _, _ = run
        assert {shot.path.name for shot in shots} == {
            "image_matrix-chromium-desktop.png",
            "image_matrix-chromium-mobile.png",
        }

    def test_width_is_at_least_the_viewport(self, run):
        """
        A full-page capture is as wide as the document. Equal means the email
        fits; wider is a real finding — the reader would scroll sideways.
        """
        shots, _, _ = run
        for shot in shots:
            assert shot.width >= VIEWPORTS[shot.viewport][0]

    def test_dimensions_are_the_images_own(self, run):
        shots, _, _ = run
        for shot in shots:
            assert png_size(shot.path) == (shot.width, shot.height)

    def test_the_run_records_the_browser_build(self, run):
        """
        The browser is recorded rather than pinned, so the recording is the
        whole guarantee — without it nobody can tell whether two sets of
        images are even comparable.
        """
        _, environment, out = run
        stored = json.loads((out / "run.json").read_text(encoding="utf-8"))

        assert stored == environment
        assert stored["browser"], "no Chromium build recorded"
        assert stored["playwright"]
        assert stored["device_scale_factor"] == DEVICE_SCALE_FACTOR
        assert set(stored["viewports"]) == set(VIEWPORTS)
        assert "Outlook" in stored["note"], "the fidelity caveat travels with the images"
