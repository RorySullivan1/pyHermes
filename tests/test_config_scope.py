"""
A config travels with the work, not the process (#249).

Three levels, innermost wins: the process-wide default from ``set_config``, a
context's ``config_override``, and the object a ``Document`` or
``build_message`` is given.
"""

from __future__ import annotations

import threading
import warnings

import pytest

from svc.brochure import Brochure, Panel
from svc.builder import DataTable, Email, EmailBuilder, FullWidth, ImageBlock, TextBlock
from svc.builder.exceptions import PrintQualityWarning, SizeError, SizeWarning, ValidationError
from svc.builder.images import EmailImage
from svc.builder.models import TableRow
from svc.config import Config, config_override, get_config, set_config
from svc.delivery import Attachment, build_message

#: Small enough that any email fails it; the inline cap may not exceed the limit.
TINY = Config(size_limit_kb=1, size_warn_kb=1, inline_image_limit_kb=1)


def _email(metadata: dict, config: Config | None = None) -> Email:
    email = Email(metadata, config=config)
    email.add_section(FullWidth(content=TextBlock("<p>Body</p>"), title="Section"))
    return email


class TestTwoThreads:
    def test_concurrent_renders_each_read_their_own_limit(self, valid_metadata):
        # Both overrides are live at once: each thread enters its own, then
        # waits for the other before rendering and again before leaving.
        entered, rendered = threading.Barrier(2), threading.Barrier(2)
        outcome: dict[str, object] = {}

        def run(name: str, limit: Config) -> None:
            with config_override(limit):
                entered.wait()
                outcome[f"{name}-limit"] = get_config().size_limit_kb
                try:
                    _email(valid_metadata).render()
                    outcome[name] = "rendered"
                except SizeError:
                    outcome[name] = "refused"
                rendered.wait()

        threads = [
            threading.Thread(target=run, args=("tiny", TINY)),
            threading.Thread(target=run, args=("roomy", Config(size_limit_kb=500))),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert outcome == {
            "tiny-limit": 1,
            "tiny": "refused",
            "roomy-limit": 500,
            "roomy": "rendered",
        }

    def test_an_override_here_is_invisible_to_another_thread(self):
        seen: list[int] = []
        with config_override(size_limit_kb=500):
            worker = threading.Thread(target=lambda: seen.append(get_config().size_limit_kb))
            worker.start()
            worker.join()
            assert get_config().size_limit_kb == 500
        assert seen == [Config().size_limit_kb]


class TestADocumentsOwnConfig:
    def test_it_applies_its_limit_and_leaves_the_ambient_one_alone(self, valid_metadata):
        before = get_config()
        with pytest.raises(SizeError, match="exceeds 1 KB"):
            _email(valid_metadata, config=TINY).render()
        assert get_config() is before

    def test_it_beats_an_ambient_override(self, valid_metadata):
        with config_override(TINY):
            _email(valid_metadata, config=Config(size_limit_kb=500)).render()
            with pytest.raises(SizeError):
                _email(valid_metadata).render()

    def test_it_is_in_force_at_construction(self, valid_metadata):
        dense = {**valid_metadata, "size_theme": "dense"}
        with pytest.raises(ValidationError, match="allow_custom_email_density"):
            Email(dense)
        Email(dense, config=Config(allow_custom_email_density=True))

    def test_it_reaches_both_projections(self, valid_metadata):
        email = Email(valid_metadata, config=Config(exhibit_separator=": "))
        table = DataTable(
            ["Factor", "1M"], [TableRow(["Value", "+1.8%"])], caption="Returns", label="Exhibit"
        )
        email.add_section(FullWidth(content=table))
        assert "Exhibit 1: Returns" in email.render()
        assert "Exhibit 1: Returns" in email.text()

    def test_the_builder_hands_it_to_the_email(self, valid_metadata):
        email = EmailBuilder(config=TINY).metadata(valid_metadata).build()
        assert email.config is TINY

    def test_a_brochure_checks_print_resolution_against_it(self):
        from qa.fixtures._png import solid_png

        image = EmailImage.attached(solid_png(600, 10, (1, 2, 3)), alt="Chart", width=300)
        panels = [Panel([FullWidth(TextBlock(f"<p>{n}</p>"))]) for n in range(6)]
        panels[2] = Panel([FullWidth(ImageBlock(image))])
        facts = {"firm_name": "Hermes", "campaign_name": "Brochure"}
        with warnings.catch_warnings():
            warnings.simplefilter("error", PrintQualityWarning)
            Brochure(facts, panels, config=Config(print_dpi=150))
        with pytest.warns(PrintQualityWarning):
            Brochure(facts, panels)

    def test_anything_but_a_config_is_refused(self, valid_metadata):
        with pytest.raises(TypeError, match="Config"):
            Email(valid_metadata, config={"size_limit_kb": 500})  # type: ignore[arg-type]


class TestBuildMessage:
    def test_its_config_sets_the_attachment_budget(self, valid_metadata):
        tight = Config(attachment_limit_kb=64, attachment_warn_kb=1)
        email = _email(valid_metadata)
        envelope = {"sender": "a@example.com", "to": "b@example.com"}
        with pytest.warns(SizeWarning, match="target < 1 KB"):
            build_message(email, **envelope, attachments=[_file()], config=tight)
        with warnings.catch_warnings():
            warnings.simplefilter("error", SizeWarning)
            build_message(email, **envelope, attachments=[_file()])


class TestTheProcessWideDefault:
    def test_an_override_wins_over_it_until_it_exits(self):
        original = get_config()
        try:
            with config_override(retry_max_attempts=5):
                set_config(Config(retry_max_attempts=9))
                assert get_config().retry_max_attempts == 5
            assert get_config().retry_max_attempts == 9
        finally:
            set_config(original)

    def test_an_override_takes_a_whole_config_and_keywords_over_it(self):
        with config_override(TINY, retry_max_attempts=7) as active:
            assert (active.size_limit_kb, active.retry_max_attempts) == (1, 7)

    def test_an_override_refuses_anything_but_a_config(self):
        with pytest.raises(TypeError, match="Config"):
            config_override({"size_limit_kb": 1})  # type: ignore[arg-type]


def _file() -> Attachment:
    return Attachment(b"x" * 2048, "notes.txt", "text/plain")
