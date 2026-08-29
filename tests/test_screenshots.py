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
    SUPPORTED_WIDTHS,
    VIEWPORTS,
    ScreenshotError,
    _launch,
    _load_playwright,
    available,
    capture_gallery,
    inline_cid_images,
    png_size,
)
from svc.builder.sizing import resolve_size_scheme
from svc.delivery import collect_cid_references

FIXTURE_NAMES = sorted(all_fixtures())

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


#: Where a container's own content starts, relative to the frame.
#:
#: Headings, plus the left-most content cell of every section row — grouped
#: by row so a *second* column's cell, which legitimately starts mid-frame,
#: is not mistaken for a left margin. A component may indent further inside
#: its own box (a card's border, a numbered list's ordinal column); that is
#: the component's business, not the container's.
_LEFT_MARGIN_PROBE = """() => {
  const frame = document.querySelector('.email-container').getBoundingClientRect();
  const out = [];
  document.querySelectorAll('h2').forEach(h => out.push(
      ['heading "' + h.textContent.trim().slice(0, 24) + '"',
       Math.round(h.getBoundingClientRect().left - frame.left)]));
  const rows = new Map();
  document.querySelectorAll('td.mobile-pad').forEach(td => {
      const box = td.getBoundingClientRect();
      const left = box.left - frame.left + parseFloat(getComputedStyle(td).paddingLeft);
      const row = Math.round(box.top);
      if (!rows.has(row) || left < rows.get(row)) rows.set(row, left);
  });
  rows.forEach(left => out.push(['content cell', Math.round(left)]));
  return out;
}"""


@pytest.fixture(scope="module")
def section_anchors():
    """
    Every fixture measured in one browser session.

    One launch rather than one per fixture, and the session is closed before
    the capture tests below start their own — sync Playwright cannot nest in
    a single thread.
    """
    if not available():
        pytest.skip('no browser; screenshots are the optional "[qa]" extra')

    # The module's own launcher, so PYHERMES_CHROMIUM handling and the
    # ScreenshotError message are not reimplemented here just to measure a
    # layout. Private, but this is that module's test.
    measured = {}
    with _load_playwright()() as playwright:
        browser = _launch(playwright)
        for name in FIXTURE_NAMES:
            email = all_fixtures()[name]()
            page = browser.new_page(viewport={"width": 1000, "height": 900})
            page.route("**/*", lambda route: route.abort())
            page.set_content(email.render())
            measured[name] = (
                resolve_size_scheme(email.metadata.size_theme).frame.pad_x,
                page.evaluate(_LEFT_MARGIN_PROBE),
            )
            page.close()
        browser.close()
    return measured


@requires_browser
class TestEverySectionSharesOneLeftMargin:
    """
    #85, made an invariant rather than a fixed accident.

    A section heading and the text under it must agree about where the left
    margin is. They did not: the multi-column band was never inset by
    ``frame.pad_x``, so its content sat 12-16px left of its own heading while
    a full-width section's sat at 32, and the band left ~60px of dead space
    on the right. The goldens could not see it — correct markup, laid out
    wrongly — which is why the check belongs here.

    It is expressed against the token rather than against 32, because that is
    what makes it hold for all three densities.
    """

    @pytest.mark.parametrize("name", FIXTURE_NAMES)
    def test_headings_and_content_start_at_the_frame_padding(self, name, section_anchors):
        expected, anchors = section_anchors[name]
        assert anchors, f"{name}: nothing to measure"
        offenders = [f"{what} at {left}px" for what, left in anchors if left != expected]
        assert not offenders, (
            f"{name}: expected every section to start at frame.pad_x "
            f"({expected}px), got " + ", ".join(sorted(set(offenders)))
        )

    def test_the_margin_follows_the_density_rather_than_a_constant(self, section_anchors):
        """
        The three themes inset by different amounts, so a test hardcoding 32
        would pass on `standard` and prove nothing about the other two.
        """
        measured = {expected for expected, _ in section_anchors.values()}
        assert measured == {24, 32, 40}


#: The four boxes the masthead's alignment claim is about.
#:
#: Measured as *edges* rather than inferred from ``align="right"`` being
#: present in the markup — which is what the goldens already pin, and which
#: says nothing about where the text actually lands.
_MASTHEAD_PROBE = """() => {
  const find = t => [...document.querySelectorAll('p')]
      .find(e => e.textContent.trim() === t);
  const dept = find('Rates Strategy'), title = find('Q3 Outlook');
  const sub = find('What the curve is pricing');
  const logo = document.querySelector('img[alt="Hermes Research"]');
  if (!dept || !title || !sub || !logo) return null;
  const r = e => e.getBoundingClientRect();
  return {
    dept_right: r(dept).right, logo_right: r(logo).right,
    title_bottom: r(title).bottom, logo_bottom: r(logo).bottom,
    sub_centre: r(sub).top + r(sub).height / 2,
    dept_centre: r(dept).top + r(dept).height / 2,
    title_left: r(title).left, sub_left: r(sub).left,
    dept_above_sub_bottom: r(sub).bottom - r(dept).top,
  };
}"""


def _masthead_email(variant, size_theme):
    """A one-section email whose only interesting feature is its masthead."""
    from svc.builder import Banner, EmailBuilder, FullWidth, MinimalBanner, TextBlock

    region = Banner if variant == "banner" else MinimalBanner
    return (
        EmailBuilder()
        .metadata(
            {
                "email_subject": "Masthead",
                "firm_name": "Hermes Research",
                "campaign_name": "masthead",
                "department": "Rates Strategy",
                "size_theme": size_theme,
            }
        )
        .banner(
            region(
                logo_url="https://cdn.example.com/logo.png",
                logo_alt="Hermes Research",
                title="Q3 Outlook",
                subtitle="What the curve is pricing",
            )
        )
        .section(FullWidth(content=TextBlock("<p>body</p>")))
        .build()
    )


@pytest.fixture(scope="module")
def masthead_boxes():
    """Both banner variants at all three densities, in one browser session."""
    if not available():
        pytest.skip('no browser; screenshots are the optional "[qa]" extra')

    measured = {}
    with _load_playwright()() as playwright:
        browser = _launch(playwright)
        for variant in ("banner", "minimal"):
            for size_theme in ("compact", "standard", "spacious"):
                page = browser.new_page(viewport={"width": 1000, "height": 900})
                page.route("**/*", lambda route: route.abort())
                page.set_content(_masthead_email(variant, size_theme).render())
                measured[variant, size_theme] = page.evaluate(_MASTHEAD_PROBE)
                page.close()
        browser.close()
    return measured


VARIANTS = [
    (variant, size_theme)
    for variant in ("banner", "minimal")
    for size_theme in ("compact", "standard", "spacious")
]


@requires_browser
@pytest.mark.parametrize("variant,size_theme", VARIANTS)
class TestTheMastheadPairsItsLines:
    """
    The masthead is a 2x2 grid, and this is the claim that makes it one.

    The logo belongs to the title's row and the department to the subtitle's,
    rather than both stacking in a band above the copy. Nothing in the
    goldens can say that: the markup pins ``valign`` and ``align="right"``,
    and neither says where a box lands. So it is measured — in both variants,
    at every density, because a row that pairs correctly at ``standard`` and
    not at ``spacious`` is the failure mode a single measurement misses.
    """

    def test_the_logo_shares_the_titles_baseline(self, variant, size_theme, masthead_boxes):
        box = masthead_boxes[variant, size_theme]
        assert box is not None, f"{variant}/{size_theme}: the masthead did not render"
        assert abs(box["title_bottom"] - box["logo_bottom"]) <= 1

    def test_the_department_centres_on_the_subtitle(self, variant, size_theme, masthead_boxes):
        box = masthead_boxes[variant, size_theme]
        assert abs(box["sub_centre"] - box["dept_centre"]) <= 1

    def test_the_department_is_beside_the_subtitle_not_below_it(
        self, variant, size_theme, masthead_boxes
    ):
        """
        The centres could agree while both lines sat in one column. They
        share a row only if the department starts above where the subtitle
        ends.
        """
        assert masthead_boxes[variant, size_theme]["dept_above_sub_bottom"] > 0

    def test_the_right_hand_marks_share_one_edge(self, variant, size_theme, masthead_boxes):
        box = masthead_boxes[variant, size_theme]
        assert abs(box["dept_right"] - box["logo_right"]) <= 1

    def test_a_long_department_wraps_rather_than_scrolls(self, variant, size_theme):
        """
        #76's failure mode, one row over. The department shares a row with
        the subtitle, so a ``white-space:nowrap`` on it looked like the way
        to keep the pairing intact — and at a 375px viewport a real desk name
        ("Global Macro, Rates and Cross-Asset Strategy Desk — EMEA") pushed
        the document to 572px, which is a reader scrolling sideways to read a
        masthead. Wrapping to a second line costs the pairing nothing: the
        cell grows, and both cells in the row grow with it.

        Measured per variant and density because the frame padding the copy
        competes with is a token, not a constant.
        """
        if not available():
            pytest.skip('no browser; screenshots are the optional "[qa]" extra')
        from svc.builder import Banner, EmailBuilder, FullWidth, MinimalBanner, TextBlock

        region = Banner if variant == "banner" else MinimalBanner
        email = (
            EmailBuilder()
            .metadata(
                {
                    "email_subject": "s",
                    "firm_name": "Hermes Research",
                    "campaign_name": "c",
                    "department": "Global Macro, Rates and Cross-Asset Strategy Desk — EMEA",
                    "size_theme": size_theme,
                }
            )
            .banner(region(logo_url="https://cdn.example.com/logo.png", logo_width=128))
            .section(FullWidth(content=TextBlock("<p>body</p>")))
            .build()
        )
        with _load_playwright()() as playwright:
            browser = _launch(playwright)
            page = browser.new_page(viewport={"width": 375, "height": 800})
            page.route("**/*", lambda route: route.abort())
            page.set_content(email.render())
            width = page.evaluate("() => document.documentElement.scrollWidth")
            browser.close()
        assert width == 375, f"a reader would scroll sideways: {width}px at a 375px viewport"

    def test_the_copy_starts_at_the_frame_padding(self, variant, size_theme, masthead_boxes):
        """
        Title and subtitle are in different rows of the same table, so a
        stray padding on one cell would stagger them.
        """
        box = masthead_boxes[variant, size_theme]
        assert box["title_left"] == box["sub_left"]


#: Fixtures known to overflow their mobile viewport, each with the issue that
#: tracks it. Named rather than silently excluded, and the mechanism is
#: ``qa.lint``'s ``DEFERRED_RULES``: a check that arrives red teaches everyone
#: to ignore it, so a finding is *filed* and listed here instead.
#:
#: **Empty, and that is the point.** ``rich_table`` was the one entry, added
#: by #129 when widening this test from three fixtures to the gallery found
#: it overflowing by 24px; #132 gave the data table a tighter cell padding at
#: the breakpoint and the entry came out. The mechanism stays for the next
#: such finding, which belongs here rather than shipped red or quietly
#: dropped.
KNOWN_MOBILE_OVERFLOW: dict[str, str] = {}


@pytest.fixture(scope="module")
def kpi_shots(tmp_path_factory):
    """
    **The whole gallery**, at every viewport.

    It was three fixtures until #129 — ``kitchen_sink``, ``compact_size`` and
    ``spacious_size``, the ones carrying the horizontal ``CardGroup`` that
    #76 was about. Scoping a regression test to the fixtures that had the bug
    is how the *next* instance goes unnoticed, and one had: ``rich_table``
    overflows its mobile viewport by 24px and nothing was watching. Widened
    here, with that finding filed rather than ignored.
    """
    if not available():
        pytest.skip('no browser; screenshots are the optional "[qa]" extra')
    out = tmp_path_factory.mktemp("kpi")
    shots, _ = capture_gallery(sorted(all_fixtures()), out)
    return shots


@requires_browser
class TestNothingOverflowsItsViewport:
    """
    #76's regression test, and the reason it lives here rather than in the
    goldens: the HTML was byte-identical to its golden the whole time it was
    broken, the size gate passed, and no unit test measures layout. Only a
    browser could see it.
    """

    def test_every_capture_is_exactly_its_viewport_wide(self, kpi_shots):
        offenders = [
            f"{shot.path.name}: {shot.width} > {VIEWPORTS[shot.viewport][0]}"
            for shot in kpi_shots
            if shot.width != VIEWPORTS[shot.viewport][0]
            and not any(name in shot.path.name for name in KNOWN_MOBILE_OVERFLOW)
        ]
        assert not offenders, "a reader would scroll sideways: " + ", ".join(offenders)

    def test_each_known_overflow_still_overflows(self, kpi_shots):
        """
        The other half of the ``DEFERRED_RULES`` mechanism: an exemption that
        outlives its reason is worse than no exemption, because it hides the
        next instance. When the issue is fixed this fails, and the entry
        should be deleted rather than the test loosened.
        """
        for name in KNOWN_MOBILE_OVERFLOW:
            shots = [s for s in kpi_shots if name in s.path.name]
            assert shots, f"{name} is exempted but the gallery no longer renders it"
            assert any(s.width != VIEWPORTS[s.viewport][0] for s in shots), (
                f"{name} no longer overflows — delete its KNOWN_MOBILE_OVERFLOW entry"
            )

    def test_the_mobile_rule_keeps_its_padding_inside(self):
        """
        The mechanism, asserted separately from the measurement so a failure
        says *which* of the two broke. Email HTML sets no global
        ``box-sizing``, so under the ``content-box`` default a
        ``width:100%`` cell adds its padding on top of the full width.
        """
        html = all_fixtures()["kitchen_sink"]().render()
        rule = html[html.index(".kpi-cell {") : html.index(".kpi-cell-last")]
        assert "box-sizing:border-box !important" in rule


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


# ──────────────────────────────────────────────────────────────────────
# The alignment default, measured (#126)
# ──────────────────────────────────────────────────────────────────────

_ALIGNMENT_PROBE = """() => {
  const frame = document.querySelector('table.email-container');
  const heading = document.querySelector('h2');
  const prose = document.querySelector('p.body-text');
  const read = el => el ? getComputedStyle(el).textAlign : null;
  return {
    frame_x: frame ? Math.round(frame.getBoundingClientRect().x) : null,
    frame_w: frame ? Math.round(frame.getBoundingClientRect().width) : null,
    heading: read(heading),
    prose: read(prose),
  };
}"""


@pytest.fixture(scope="module")
def alignment_defaults():
    """Every fixture's default alignment geometry, in one browser session."""
    if not available():
        pytest.skip('no browser; screenshots are the optional "[qa]" extra')

    measured = {}
    with _load_playwright()() as playwright:
        browser = _launch(playwright)
        for name in FIXTURE_NAMES:
            page = browser.new_page(viewport={"width": 1000, "height": 900})
            page.route("**/*", lambda route: route.abort())
            page.set_content(all_fixtures()[name]().render())
            measured[name] = page.evaluate(_ALIGNMENT_PROBE)
            page.close()
        browser.close()
    return measured


@requires_browser
class TestTheDefaultAlignmentIsUnchanged:
    """
    The regression #125 actually shipped, caught here because nothing else
    could see it.

    Pairing ``base.html``'s outer cell — ``align="center"`` — with a
    ``text-align:center`` style looked like the same tidying applied to
    fifteen other cells, and the golden diff was verified to be *only*
    alignment declarations. Both were true. The render still moved, in
    every email, twice over: a browser maps that attribute to
    ``-webkit-center``, which centres the email table as a **block**, while
    the literal ``center`` centres inline content only — so the email
    un-centred in the window, and the style then inherited into every
    heading and paragraph beneath it.

    #76 established that layout regressions live with the screenshots. This
    is the second, and the lesson is sharper: a byte-verified diff is not a
    verified render.
    """

    def test_the_email_frame_stays_centred_in_the_viewport(self, alignment_defaults):
        for name, measured in alignment_defaults.items():
            expected = (1000 - measured["frame_w"]) // 2
            assert abs(measured["frame_x"] - expected) <= 1, (
                f"{name}: the email frame sits at x={measured['frame_x']}, not centred "
                f"at {expected}. base.html's outer cell centres a block — check that its "
                "align attribute has not been paired with a text-align style."
            )

    def test_copy_is_left_aligned_unless_a_section_says_otherwise(self, alignment_defaults):
        """
        No gallery fixture states an alignment, so every heading and every
        paragraph must resolve to the initial value. ``start`` is what
        Chromium reports for it in a left-to-right document.
        """
        for name, measured in alignment_defaults.items():
            for role in ("heading", "prose"):
                value = measured[role]
                if value is None:
                    continue
                assert value == "start", (
                    f"{name}: the default {role} alignment is {value!r}, not 'start'. "
                    "Something above it is declaring an alignment that inherits."
                )


# ──────────────────────────────────────────────────────────────────────
# Caller-wrapped copy keeps its component's styling (#130)
# ──────────────────────────────────────────────────────────────────────

_INHERITANCE_PROBE = """() => {
  const out = [];
  // Selected by CLASS, never by tag. Keying on 'div.body-text' would make
  // this whole check vacuous the moment someone turned the wrapper back
  // into a paragraph — the exact regression it exists to catch.
  document.querySelectorAll('.body-text').forEach(wrapper => {
    const wanted = getComputedStyle(wrapper).fontFamily;
    // Every leaf that actually shows text inside this wrapper.
    const leaves = wrapper.querySelectorAll('*');
    const nodes = leaves.length ? Array.from(leaves) : [wrapper];
    nodes.forEach(el => {
      const text = el.textContent.replace(/\\s+/g, ' ').trim();
      if (!text || el.children.length) return;
      out.push([text.slice(0, 40), wanted, getComputedStyle(el).fontFamily]);
    });
    if (!wrapper.textContent.trim()) out.push(['(EMPTY WRAPPER)', wanted, wanted]);
  });
  return out;
}"""


@pytest.fixture(scope="module")
def copy_inheritance():
    """What each fixture's body copy actually computes to, in one session."""
    if not available():
        pytest.skip('no browser; screenshots are the optional "[qa]" extra')

    measured = {}
    with _load_playwright()() as playwright:
        browser = _launch(playwright)
        for name in FIXTURE_NAMES:
            page = browser.new_page(viewport={"width": 1000, "height": 900})
            page.route("**/*", lambda route: route.abort())
            page.set_content(all_fixtures()[name]().render())
            measured[name] = page.evaluate(_INHERITANCE_PROBE)
            page.close()
        browser.close()
    return measured


@requires_browser
class TestBodyCopyKeepsItsOwnStyling:
    """
    #130. A ``p`` cannot contain a ``p``, and ``TextBlock.content`` is a
    raw-HTML field whose documented shape is the caller's own paragraph
    tags — so while the styling wrapper was a paragraph, every fixture's
    body copy escaped it and rendered in the *label* typeface.

    No golden could see it: the HTML was byte-stable and looked correct.
    Only a parser resolving the nesting reveals it, which is why the guard
    lives here beside the other layout invariants.
    """

    def test_no_styling_wrapper_is_left_empty(self, copy_inheritance):
        """
        The cheapest form of the check, and the one that would have caught
        this years earlier: if the element carrying the component's font
        holds no text, the text is somewhere else.
        """
        for name, rows in copy_inheritance.items():
            empty = [row for row in rows if row[0] == "(EMPTY WRAPPER)"]
            assert not empty, (
                f"{name}: {len(empty)} body-text wrapper(s) are empty — the copy has "
                "escaped the element that styles it. See #130."
            )

    def test_the_copy_computes_the_wrapper_s_typeface(self, copy_inheritance):
        """
        The claim epic #56 makes and could not previously keep: the body
        role reaches the body copy.
        """
        for name, rows in copy_inheritance.items():
            for text, wanted, actual in rows:
                assert actual == wanted, (
                    f"{name}: {text!r} renders in {actual} but its component "
                    f"styles it {wanted}. See #130."
                )

    def test_the_body_role_reaches_the_body_copy(self):
        """
        #56's sentinel render, extended from the markup to what a browser
        *computes* — which is the acceptance criterion #130 added, because
        the markup half already passed while the render was wrong.

        The sentinel theme names four findable families, so the copy
        resolving to anything but the ``body`` one means the wrapper is not
        an ancestor of the copy after all.
        """
        from qa.fixtures import kitchen_sink
        from svc.builder.typography import FontStack, FontTheme

        sentinel = FontTheme(
            heading=FontStack("SentinelHeading", "serif"),
            body=FontStack("SentinelBody", "serif"),
            label=FontStack("SentinelLabel", "sans-serif"),
            numeric=FontStack("SentinelNumeric", "monospace"),
        )
        email = kitchen_sink.build()
        email.metadata.font_theme = sentinel

        with _load_playwright()() as playwright:
            browser = _launch(playwright)
            page = browser.new_page(viewport={"width": 1000, "height": 900})
            page.route("**/*", lambda route: route.abort())
            page.set_content(email.render())
            families = page.evaluate("""() => {
                const out = [];
                document.querySelectorAll('.body-text').forEach(wrapper => {
                    const leaves = wrapper.querySelectorAll('*');
                    (leaves.length ? Array.from(leaves) : [wrapper]).forEach(el => {
                        if (!el.textContent.trim() || el.children.length) return;
                        out.push(getComputedStyle(el).fontFamily);
                    });
                });
                return out;
            }""")
            page.close()
            browser.close()

        assert families, "the sentinel render produced no body copy to measure"
        for family in families:
            assert family.startswith("SentinelBody"), (
                f"body copy computes {family!r} under a sentinel theme whose body role "
                "is SentinelBody. The copy is not inheriting from its own wrapper."
            )


# ──────────────────────────────────────────────────────────────────────
# A column cell fills its column (#129)
# ──────────────────────────────────────────────────────────────────────

_COLUMN_FILL_PROBE = """() => Array.from(document.querySelectorAll('table.stack-column'))
  .map(table => {
    const cell = table.querySelector('td');
    return [Math.round(table.getBoundingClientRect().width),
            Math.round(cell.getBoundingClientRect().width)];
  })"""


@pytest.fixture(scope="module")
def column_fill():
    """Every gallery column, as (column width, cell width), in one session."""
    if not available():
        pytest.skip('no browser; screenshots are the optional "[qa]" extra')

    measured = {}
    with _load_playwright()() as playwright:
        browser = _launch(playwright)
        for name in FIXTURE_NAMES:
            page = browser.new_page(viewport={"width": 1000, "height": 900})
            page.route("**/*", lambda route: route.abort())
            page.set_content(all_fixtures()[name]().render())
            measured[name] = page.evaluate(_COLUMN_FILL_PROBE)
            page.close()
        browser.close()
    return measured


@requires_browser
class TestEveryColumnCellFillsItsColumn:
    """
    #129, and it is here rather than in the goldens for the usual reason:
    the HTML was byte-stable and correct-looking the whole time 76 of the
    gallery's 88 column cells were as narrow as their own copy.

    With ``display:inline-block`` the column stops being a table box — the
    rows and cells get an anonymous table around them, and that shrink-wraps.
    ``inline-table`` keeps it a table, so the specified width reaches the
    cell. Anything depending on the cell's width had no room until then, and
    #126's alignment was the first thing to notice.
    """

    def test_no_cell_is_narrower_than_its_column(self, column_fill):
        narrow = {
            name: [(column, cell) for column, cell in rows if cell < column - 1]
            for name, rows in column_fill.items()
        }
        offenders = {name: rows for name, rows in narrow.items() if rows}
        assert not offenders, (
            f"column cells shrink-wrapped instead of filling: {offenders}. "
            "Check that columns.html still says display:inline-table — see #129."
        )

    def test_the_gallery_actually_renders_columns(self, column_fill):
        """
        Guards the guard. Every assertion above passes vacuously on an email
        with no splits, and #130's first probe already showed how easily a
        selector stops matching.
        """
        total = sum(len(rows) for rows in column_fill.values())
        assert total >= 80, f"only {total} column cells measured; the probe is not matching"


# ──────────────────────────────────────────────────────────────────────
# The supported viewport range (#133)
# ──────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def widths_measured():
    """Every fixture's document width at every supported viewport."""
    if not available():
        pytest.skip('no browser; screenshots are the optional "[qa]" extra')

    measured = {}
    with _load_playwright()() as playwright:
        browser = _launch(playwright)
        for name in FIXTURE_NAMES:
            html = all_fixtures()[name]().render()
            for width in SUPPORTED_WIDTHS:
                page = browser.new_page(viewport={"width": width, "height": 900})
                page.route("**/*", lambda route: route.abort())
                page.set_content(html)
                measured[(name, width)] = page.evaluate(
                    "() => Math.round(document.documentElement.scrollWidth)"
                )
                page.close()
        browser.close()
    return measured


@requires_browser
class TestTheSupportedViewportsAreHonoured:
    """
    #133 asked which viewports pyHermes claims, and this is the answer made
    checkable: ``SUPPORTED_WIDTHS`` is the claim, and no gallery email may
    exceed any width in it.

    Separate from ``TestNothingOverflowsItsViewport``, which measures the
    captured *screenshots*. That one asks "is the review artifact sane"; this
    one asks "does the package keep its promise", and the two would drift the
    moment a supported width stopped being a captured one.
    """

    def test_no_fixture_exceeds_a_supported_width(self, widths_measured):
        offenders = [
            f"{name} at {width}px: {got}"
            for (name, width), got in widths_measured.items()
            if got > width
        ]
        assert not offenders, (
            "a reader would scroll sideways at a width the package claims to "
            f"support: {offenders}. Either fix the email or change the claim in "
            "SUPPORTED_WIDTHS — and if the claim changes, say so in the docs."
        )

    def test_every_captured_viewport_is_a_supported_one(self):
        """
        The two lists are allowed to differ — a width can be asserted without
        being screenshotted — but not in this direction: capturing a viewport
        the package does not claim would put an overflowing image in front of
        a reviewer with nothing failing.
        """
        captured = {width for width, _ in VIEWPORTS.values()}
        assert captured <= set(SUPPORTED_WIDTHS), (
            f"captured viewports {sorted(captured - set(SUPPORTED_WIDTHS))} are not in "
            "SUPPORTED_WIDTHS"
        )
