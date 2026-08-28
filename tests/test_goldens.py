"""
The golden snapshots, and proof that the harness that checks them bites (#58).

Two halves, and the second matters as much as the first:

* every gallery fixture matches its checked-in golden — the byte-identity bar
  the migration epics (#33, #41, #42, #49) all promise to hold;
* the harness *detects* drift, demonstrated by perturbing a real template and
  a real fixture and asserting the report names the right fixture and the
  right location. A golden test nobody has seen fail is decoration — the same
  discipline as ``TestTheWiringIsLive`` in ``test_config.py``.

``kitchen_sink`` doubles as #32's characterization email: exhaustive over
``EmailMetadata``, spanning every container ratio, with a hosted logo and an
attached image. #58 required one harness rather than two; #32 had not started,
so this is it.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from qa.fixtures import all_fixtures
from qa.goldens import (
    GOLDEN_DIR,
    GoldenMismatch,
    artifacts,
    check_fixture,
    html_path,
    render_manifest,
    text_path,
    write_fixture,
)
from svc.builder import AuthorBlock, Email, FullWidth, TextBlock
from svc.builder.engine import TemplateEngine

FIXTURE_NAMES = sorted(all_fixtures())


@pytest.fixture(params=FIXTURE_NAMES)
def fixture_name(request: pytest.FixtureRequest) -> str:
    return str(request.param)


def _perturbed_templates(tmp_path: Path, old: str, new: str) -> Path:
    """
    A copy of the packaged templates with one substitution applied.

    Renders through this are otherwise identical, so whatever the harness
    reports is caused by the substitution and nothing else.
    """
    destination = tmp_path / "templates"
    shutil.copytree(TemplateEngine().template_dir, destination)
    base = destination / "base.html"
    source = base.read_text(encoding="utf-8")
    assert old in source, f"{old!r} is no longer in base.html; pick another anchor."
    base.write_text(source.replace(old, new, 1), encoding="utf-8")
    return destination


def _line_of(text: str, needle: str) -> int:
    """The 1-based line number where ``needle`` first appears."""
    return text[: text.index(needle)].count("\n") + 1


class TestEveryFixtureMatchesItsGolden:
    def test_every_artifact_is_unchanged(self, fixture_name, request):
        """
        The drift gate. With ``--update-goldens`` this rewrites instead of
        asserting — the only regeneration path there is.
        """
        email = all_fixtures()[fixture_name]()
        if request.config.getoption("--update-goldens"):
            written = write_fixture(fixture_name, email)
            pytest.skip(f"regenerated {', '.join(p.name for p in written)}")
        mismatches = check_fixture(fixture_name, email)
        assert not mismatches, "\n\n".join(str(m) for m in mismatches)

    def test_every_golden_is_checked_in(self, fixture_name):
        """
        A fixture with no golden is a fixture nobody is watching. Named
        separately from the comparison so the failure says which of the two
        situations it is.

        Read off :func:`qa.goldens.artifacts` rather than a list of paths, so
        a fourth artifact is covered the day it is added rather than the day
        somebody remembers this test.
        """
        email = all_fixtures()[fixture_name]()
        for _, path, _ in artifacts(fixture_name, email):
            assert path.is_file(), f"{path} is missing; run `pytest --update-goldens`."


class TestTheHarnessDetectsDrift:
    """
    Detection, proved rather than assumed.

    Each case renders a genuinely altered email and asserts the harness names
    the fixture, the artifact, and the line the change landed on.
    """

    def test_a_template_edit_is_caught_and_located(self, tmp_path):
        """
        The headline case: one attribute changed in ``base.html``, which is
        exactly the kind of edit the header epic (#38) makes repeatedly.

        The anchor is an attribute rather than a number because #42 left
        ``base.html`` with no width literal to perturb — every one of them
        now reads ``size.frame.width``. The rendered side still checks a
        number, since that is what the golden holds.

        The needle carries **both** spellings of the alignment since #125,
        which paired every ``align`` attribute with a ``text-align`` style.
        Perturbing only the attribute is still a genuine template edit and
        still the edit this test is about — it simply no longer describes
        the whole of what that element says about its alignment.
        """
        templates = _perturbed_templates(tmp_path, 'align="center"', 'align="left"')
        email = all_fixtures()["minimal"](template_dir=templates)

        mismatches = check_fixture("minimal", email)

        assert len(mismatches) == 1, "only the HTML moved; the manifest should be untouched"
        (mismatch,) = mismatches
        assert mismatch.fixture == "minimal"
        assert mismatch.artifact == "rendered HTML"
        expected_line = _line_of(
            html_path("minimal").read_text(encoding="utf-8"),
            '<td align="center" style="padding:28px 0; text-align:center;">',
        )
        assert f"line {expected_line}," in mismatch.report
        assert 'align="left"' in mismatch.report

    def test_a_fixture_data_change_is_caught_and_located(self, monkeypatch):
        """
        The other direction: the templates are untouched and a metadata value
        moved. Same report, located at the line the value renders on.

        Since #110 this moves **two** artifacts, and that is the stronger
        claim: ``issue_label`` is a fact the email owns, so both projections
        carry it and both must notice. A change that moved only one of them
        would mean the two parts had come to disagree about what the email
        says.
        """
        from qa.fixtures import kitchen_sink

        original = kitchen_sink._metadata()
        moved = dict(original, issue_label="Issue 002")
        monkeypatch.setattr(kitchen_sink, "_metadata", lambda: moved)

        mismatches = check_fixture("kitchen_sink", kitchen_sink.build())

        assert [m.artifact for m in mismatches] == ["rendered HTML", "plain text"]
        for mismatch, path in zip(mismatches, (html_path, text_path), strict=True):
            golden = path("kitchen_sink").read_text(encoding="utf-8")
            assert f"line {_line_of(golden, 'Issue 001')}," in mismatch.report

    def test_the_report_shows_both_versions_of_the_line(self, tmp_path):
        """
        A bare "bytes differ" on a 90 KB document wastes the next hour, so the
        report must carry the old and new text, not just a position.
        """
        templates = _perturbed_templates(tmp_path, "</html>", "</html><!-- moved -->")
        email = all_fixtures()["minimal"](template_dir=templates)

        (mismatch,) = check_fixture("minimal", email)

        assert "- expected" in mismatch.report and "+ actual" in mismatch.report
        assert "<!-- moved -->" in mismatch.report
        assert "byte offset" in mismatch.report

    def test_a_truncation_is_located_at_the_end_of_the_golden(self, monkeypatch):
        """
        One text being a strict prefix of the other must not read as
        "identical" — the comparison runs out of characters before it runs
        out of differences. Driven through the manifest, where a prefix is
        the natural shape of the failure: an asset simply stops being
        aggregated.
        """
        email = all_fixtures()["kitchen_sink"]()
        kept = email.assets()[:-1]
        monkeypatch.setattr(type(email), "assets", lambda self: kept)

        (mismatch,) = check_fixture("kitchen_sink", email)

        assert mismatch.artifact == "asset manifest"
        assert "<end of file>" in mismatch.report


class TestTheManifestSnapshotDetectsDrift:
    """
    The manifest half. The header epic moves image aggregation between
    classes, so a dropped or duplicated ``ImageAsset`` is the failure mode
    #32 named — and it can happen with the HTML byte-identical.
    """

    @staticmethod
    def _with_assets(monkeypatch, email: Email, assets: list) -> Email:
        monkeypatch.setattr(type(email), "assets", lambda self: assets)
        return email

    def test_a_dropped_asset_is_caught(self, monkeypatch):
        email = all_fixtures()["image_matrix"]()
        kept = email.assets()[:-1]
        self._with_assets(monkeypatch, email, kept)

        mismatches = check_fixture("image_matrix", email)

        assert [m.artifact for m in mismatches] == ["asset manifest"]

    def test_a_duplicated_asset_is_caught(self, monkeypatch):
        """
        Dedupe is what keeps one image from being attached twice, so its
        failure must not be silent — and it is invisible in the HTML, which
        goes on referencing the same ``cid:`` either way.
        """
        email = all_fixtures()["image_matrix"]()
        doubled = email.assets() * 2
        self._with_assets(monkeypatch, email, doubled)

        mismatches = check_fixture("image_matrix", email)

        assert [m.artifact for m in mismatches] == ["asset manifest"]

    def test_reordering_is_caught(self):
        """Order is recorded, not sorted — aggregation order is part of the contract."""
        email = all_fixtures()["kitchen_sink"]()
        recorded = render_manifest(email)
        assert len(recorded.splitlines()) > 1, (
            "kitchen_sink needs 2+ assets for this to mean anything"
        )
        reversed_manifest = "".join(f"{line}\n" for line in reversed(recorded.splitlines()))
        assert reversed_manifest != recorded

    def test_the_manifest_records_id_type_length_and_name(self):
        email = all_fixtures()["image_matrix"]()
        asset = email.assets()[0]
        (record,) = render_manifest(email).splitlines()
        assert record.split("\t") == [
            asset.content_id,
            asset.mime_type,
            str(len(asset.data)),
            asset.filename,
        ]

    def test_an_email_with_no_assets_records_an_empty_manifest(self):
        assert render_manifest(all_fixtures()["minimal"]()) == ""


class TestTheTextGoldenDetectsDrift:
    """
    The harness must *bite* on the new artifact, tested the way the HTML side
    already is rather than assumed.

    The perturbation here is deliberately a **component's projection** rather
    than a fact: since #109 the text part is a second projection of the tree,
    so a ``text()`` can change with the HTML byte-identical. That is precisely
    the drift no other golden in the gallery can see, and the reason this is a
    third file rather than a section of the first.
    """

    def test_a_changed_projection_moves_only_the_text_golden(self, monkeypatch):
        monkeypatch.setattr(AuthorBlock, "text", lambda self: "PERTURBED BYLINE")

        mismatches = check_fixture("kitchen_sink", all_fixtures()["kitchen_sink"]())

        assert [m.artifact for m in mismatches] == ["plain text"]

    def test_it_is_located_at_the_line_that_moved(self, monkeypatch):
        monkeypatch.setattr(AuthorBlock, "text", lambda self: "PERTURBED BYLINE")

        mismatch = check_fixture("kitchen_sink", all_fixtures()["kitchen_sink"]())[0]

        golden = text_path("kitchen_sink").read_text(encoding="utf-8")
        assert f"line {_line_of(golden, 'A. Analyst')}," in mismatch.report
        assert "PERTURBED BYLINE" in mismatch.report
        assert "--update-goldens" in mismatch.report

    def test_a_deleted_text_golden_fails_rather_than_recreating_itself(self, monkeypatch, tmp_path):
        """
        The same rule the other two artifacts carry, and worth pinning for
        this one separately: a golden that writes itself on first run pins
        whatever happened to be true that day.
        """
        shutil.copytree(GOLDEN_DIR, tmp_path / "goldens")
        monkeypatch.setattr("qa.goldens.GOLDEN_DIR", tmp_path / "goldens")
        (tmp_path / "goldens" / "minimal.txt").unlink()

        mismatches = check_fixture("minimal", all_fixtures()["minimal"]())

        assert [m.artifact for m in mismatches] == ["plain text"]
        assert "no plain text golden is checked in" in mismatches[0].report
        assert not (tmp_path / "goldens" / "minimal.txt").exists()


class TestAMissingGoldenFails:
    """
    A golden is never created implicitly. One that writes itself on first run
    pins whatever happened to be true that day, and the reviewer never sees it.
    """

    def test_it_reports_the_missing_path_and_the_flag(self, monkeypatch, tmp_path):
        monkeypatch.setattr("qa.goldens.GOLDEN_DIR", tmp_path)
        email = Email(
            metadata={
                "email_subject": "Unpinned",
                "firm_name": "Hermes Research",
                "campaign_name": "unpinned",
            }
        )
        email.add_section(FullWidth(content=TextBlock("<p>Nothing pins this.</p>")))

        mismatches = check_fixture("unpinned", email)

        assert [m.artifact for m in mismatches] == [a for a, _, _ in artifacts("unpinned", email)]
        assert all(isinstance(m, GoldenMismatch) for m in mismatches)
        assert all("--update-goldens" in m.report for m in mismatches)

    def test_write_fixture_creates_the_directory(self, monkeypatch, tmp_path):
        target = tmp_path / "nested" / "goldens"
        monkeypatch.setattr("qa.goldens.GOLDEN_DIR", target)
        email = all_fixtures()["minimal"]()
        written = write_fixture("minimal", email)
        assert written == [path for _, path, _ in artifacts("minimal", email)]
        assert all(path.is_file() for path in written)
