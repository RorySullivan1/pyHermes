"""
The medium: who owns the skeleton, the slot contract and the constraints.

Three claims are load-bearing and none is visible in a golden — the
constraint set belongs to the medium rather than to ``Email``, the slots come
from the region classes rather than a second list, and the medium reaches a
template the way the other three namespaces do.
"""

import shutil
from dataclasses import replace

import pytest

from svc.builder import Email, FullWidth, TextBlock
from svc.builder.engine import TemplateEngine
from svc.builder.exceptions import SizeError
from svc.builder.images import EmailImage
from svc.builder.medium import DEFAULT_MEDIUM, Medium
from svc.builder.regions import Banner, Footer, Header
from svc.email.medium import _SIZE_LIMIT_KB, EMAIL_MEDIUM, validate_gmail_size

#: A medium identical to the shipped one but for its (absent) constraints.
UNCHECKED = Medium(
    name="unchecked",
    skeleton=EMAIL_MEDIUM.skeleton,
    region_types=EMAIL_MEDIUM.region_types,
)


def oversized(valid_metadata, medium=None) -> Email:
    """An email whose rendered HTML is comfortably past the Gmail limit."""
    email = Email(valid_metadata, medium=medium) if medium else Email(valid_metadata)
    filler = "x" * ((_SIZE_LIMIT_KB + 10) * 1024)
    email.add_section(FullWidth(content=TextBlock(f"<p>{filler}</p>")))
    return email


class TestTheMediumOwnsTheConstraint:
    def test_the_shipped_medium_still_enforces_the_gmail_limit(self, valid_metadata):
        # The behaviour that must not change while its owner moves.
        with pytest.raises(SizeError, match="Gmail clipping limit"):
            oversized(valid_metadata).render()

    def test_a_medium_without_constraints_renders_the_same_document(self, valid_metadata):
        # The proof the check is the medium's, not Email's: same email, same
        # skeleton, no constraint, no raise.
        html = oversized(valid_metadata, medium=UNCHECKED).render()
        assert len(html.encode("utf-8")) / 1024 > _SIZE_LIMIT_KB

    def test_constraints_run_in_order_and_receive_the_hint(self):
        seen = []
        medium = Medium(
            name="probe",
            skeleton="base.html",
            constraints=(
                lambda html, hint="": seen.append(("first", hint)),
                lambda html, hint="": seen.append(("second", hint)),
            ),
        )
        medium.validate("<html></html>", "a hint")
        assert seen == [("first", "a hint"), ("second", "a hint")]

    def test_the_inline_image_hint_still_reaches_the_failure(self, valid_metadata, png_bytes):
        # _inline_image_hint now feeds a constraint rather than a private
        # method, so the guidance a caller gets has to survive the move.
        email = oversized(valid_metadata)
        email.set_banner(Banner(logo_url=EmailImage.inline(png_bytes, alt="Logo", width=100)))
        with pytest.raises(SizeError, match="inlined image"):
            email.render()

    def test_the_check_is_importable_from_the_medium_that_owns_it(self):
        with pytest.raises(SizeError):
            validate_gmail_size("x" * ((_SIZE_LIMIT_KB + 1) * 1024))


class TestTheSlotsComeFromTheRegions:
    def test_the_email_medium_derives_its_slots_from_its_region_classes(self):
        assert EMAIL_MEDIUM.region_types == (Header, Banner, Footer)
        assert EMAIL_MEDIUM.slots == Header.SLOTS + Banner.SLOTS + Footer.SLOTS

    def test_the_skeleton_names_every_slot_the_medium_claims(self, engine):
        # A slot the skeleton does not name renders a whole region into
        # nothing, silently. StrictUndefined catches the opposite case only.
        skeleton = (engine.template_dir / EMAIL_MEDIUM.skeleton).read_text(encoding="utf-8")
        for slot in EMAIL_MEDIUM.slots:
            assert f"{{{{ {slot}_html }}}}" in skeleton

    def test_render_loads_the_skeleton_the_medium_names(self, valid_metadata, engine, tmp_path):
        # The literal "base.html" is gone from render(); this is what proves
        # it, and it is the mechanism every later medium arrives through.
        templates = tmp_path / "templates"
        shutil.copytree(engine.template_dir, templates)
        (templates / "probe.html").write_text("PROBE {{ sections_html }}", encoding="utf-8")
        email = Email(
            valid_metadata,
            template_dir=templates,
            medium=replace(EMAIL_MEDIUM, skeleton="probe.html"),
        )
        assert email.render().startswith("PROBE")

    def test_the_body_is_not_a_region(self, engine):
        # The ordered section list is deliberately not a region, so it is not
        # a slot -- though the skeleton still names it.
        skeleton = (engine.template_dir / EMAIL_MEDIUM.skeleton).read_text(encoding="utf-8")
        assert "{{ sections_html }}" in skeleton
        assert "sections" not in EMAIL_MEDIUM.slots


class TestTheMediumRidesTheBinder:
    def test_the_engine_guarantees_a_medium_with_nothing_bound(self, engine):
        # The fourth namespace's floor, exactly as theme, size and font have
        # one: rendering a component on its own stays a one-liner.
        assert engine.render_string("{{ medium.name }}", {}) == DEFAULT_MEDIUM.name

    def test_the_floor_is_neither_paged_nor_email(self, engine):
        # A component rendered outside any document must not emit email-only
        # markup on the strength of a default.
        assert engine.render_string("{{ medium.email }}{{ medium.paged }}", {}) == "FalseFalse"

    def test_a_bound_medium_wins_over_the_floor(self, tmp_path):
        (tmp_path / "probe.html").write_text("{{ medium.name }}", encoding="utf-8")
        engine = TemplateEngine(tmp_path)
        assert engine.render("probe.html", {}) == DEFAULT_MEDIUM.name
        assert engine.bound(medium=EMAIL_MEDIUM).render("probe.html", {}) == "email"

    def test_render_binds_the_documents_own_medium(self, valid_metadata, monkeypatch):
        captured = {}
        original = TemplateEngine.bound

        def spy(self, **shared):
            captured.update(shared)
            return original(self, **shared)

        monkeypatch.setattr(TemplateEngine, "bound", spy)
        Email(valid_metadata).render()
        assert captured["medium"] is EMAIL_MEDIUM

    def test_the_medium_is_read_only(self, valid_metadata):
        email = Email(valid_metadata)
        assert email.medium is EMAIL_MEDIUM
        with pytest.raises(AttributeError):
            email.medium = DEFAULT_MEDIUM
