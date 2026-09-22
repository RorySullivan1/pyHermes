"""
Tests for the package configuration.

Two halves, and the second is the point. The first checks the `Config`
object itself — validation, environment parsing, install/restore. The
second proves each tunable is actually *reachable* from the code that
should honour it: a config nobody reads is decoration, and the only way to
know the wiring is live is to change a value and watch behaviour follow.
"""

import base64
from dataclasses import replace

import pytest

from svc.builder.exceptions import SizeError
from svc.builder.images import EmailImage
from svc.config import Config, config_override, get_config, set_config
from svc.delivery.retry import retry_with_backoff
from svc.email.medium import validate_gmail_size
from svc.outlook import GraphApiTransport


class TestValidation:
    def test_defaults_construct(self):
        assert Config().size_limit_kb == 102

    def test_is_frozen(self):
        with pytest.raises(Exception):  # noqa: B017 - dataclasses raises FrozenInstanceError
            Config().size_limit_kb = 1  # type: ignore[misc]

    @pytest.mark.parametrize(
        "field",
        [
            "size_limit_kb",
            "size_warn_kb",
            "inline_image_limit_kb",
            "retry_initial_delay",
            "retry_max_delay",
            "retry_max_hint_delay",
        ],
    )
    def test_non_positive_values_are_rejected(self, field):
        with pytest.raises(ValueError, match=field):
            Config(**{field: 0})

    def test_a_warning_threshold_above_the_hard_limit_is_rejected(self):
        # It would never fire -- the hard failure gets there first.
        with pytest.raises(ValueError, match="size_warn_kb"):
            Config(size_limit_kb=100, size_warn_kb=101)

    def test_an_inline_cap_above_the_whole_budget_is_rejected(self):
        with pytest.raises(ValueError, match="inline_image_limit_kb"):
            Config(size_limit_kb=100, inline_image_limit_kb=101)

    def test_backoff_factor_below_one_is_rejected(self):
        # A factor under 1 shrinks each wait, which is not backoff.
        with pytest.raises(ValueError, match="retry_backoff_factor"):
            Config(retry_backoff_factor=0.5)

    def test_zero_attempts_is_rejected(self):
        with pytest.raises(ValueError, match="retry_max_attempts"):
            Config(retry_max_attempts=0)

    def test_a_none_timeout_is_allowed_but_zero_is_not(self):
        assert Config(request_timeout_seconds=None).request_timeout_seconds is None
        with pytest.raises(ValueError, match="request_timeout_seconds"):
            Config(request_timeout_seconds=0)


class TestFromEnv:
    def test_unset_variables_leave_defaults_alone(self, monkeypatch):
        monkeypatch.delenv("PYHERMES_SIZE_LIMIT_KB", raising=False)
        assert Config.from_env() == Config()

    def test_reads_a_prefixed_variable(self, monkeypatch):
        monkeypatch.setenv("PYHERMES_INLINE_IMAGE_LIMIT_KB", "64")
        assert Config.from_env().inline_image_limit_kb == 64

    def test_an_empty_variable_means_leave_it_alone(self, monkeypatch):
        monkeypatch.setenv("PYHERMES_INLINE_IMAGE_LIMIT_KB", "   ")
        assert Config.from_env().inline_image_limit_kb == Config().inline_image_limit_kb

    def test_none_is_accepted_for_the_timeout_specifically(self, monkeypatch):
        # "no timeout" is a real setting, not an absent one.
        monkeypatch.setenv("PYHERMES_REQUEST_TIMEOUT_SECONDS", "none")
        assert Config.from_env().request_timeout_seconds is None

    def test_an_unparseable_value_names_the_variable(self, monkeypatch):
        # Silently ignoring a typo is how a setting appears to do nothing.
        monkeypatch.setenv("PYHERMES_RETRY_MAX_ATTEMPTS", "lots")
        with pytest.raises(ValueError, match="PYHERMES_RETRY_MAX_ATTEMPTS"):
            Config.from_env()

    def test_an_invalid_combination_still_fails_validation(self, monkeypatch):
        monkeypatch.setenv("PYHERMES_SIZE_WARN_KB", "9999")
        with pytest.raises(ValueError, match="size_warn_kb"):
            Config.from_env()

    def test_overrides_apply_on_top_of_a_supplied_base(self, monkeypatch):
        monkeypatch.setenv("PYHERMES_SIZE_WARN_KB", "10")
        base = Config(retry_max_attempts=7)
        result = Config.from_env(base=base)
        assert result.size_warn_kb == 10
        assert result.retry_max_attempts == 7


class TestTheExhibitSeparator:
    """#181's house-style constant: the one string field, so the one text cast."""

    def test_it_defaults_to_a_middle_dot(self):
        assert Config().exhibit_separator == " · "

    def test_a_blank_one_is_refused(self):
        with pytest.raises(ValueError, match="exhibit_separator"):
            Config(exhibit_separator="   ")

    def test_the_environment_supplies_it_verbatim(self, monkeypatch):
        monkeypatch.setenv("PYHERMES_EXHIBIT_SEPARATOR", " — ")
        assert Config.from_env().exhibit_separator == " — "


class TestActiveConfig:
    def test_set_and_get_round_trip(self):
        original = get_config()
        try:
            set_config(Config(retry_max_attempts=9))
            assert get_config().retry_max_attempts == 9
        finally:
            set_config(original)

    def test_set_config_rejects_a_non_config(self):
        with pytest.raises(TypeError):
            set_config({"size_limit_kb": 10})  # type: ignore[arg-type]

    def test_override_restores_the_previous_config(self):
        before = get_config()
        with config_override(retry_max_attempts=5):
            assert get_config().retry_max_attempts == 5
        assert get_config() is before

    def test_override_restores_even_when_the_body_raises(self):
        before = get_config()
        with pytest.raises(RuntimeError):
            with config_override(retry_max_attempts=5):
                raise RuntimeError("boom")
        assert get_config() is before


class TestTheWiringIsLive:
    """Each tunable, proven reachable from the code that should honour it."""

    def test_size_limit_is_read_from_config(self):
        html = "x" * (20 * 1024)  # 20 KB: fine by default, over a 10 KB limit
        validate_gmail_size(html)
        # inline_image_limit_kb comes along because Config refuses to let a
        # single image be allowed to outweigh the whole email.
        with config_override(size_limit_kb=10, size_warn_kb=5, inline_image_limit_kb=5):
            with pytest.raises(SizeError, match="10 KB"):
                validate_gmail_size(html)

    def test_inline_image_cap_is_read_from_config(self, png_bytes):
        EmailImage.inline(png_bytes, alt="Chart")  # fine by default
        with config_override(inline_image_limit_kb=1, size_limit_kb=102):
            oversized = png_bytes + b"\x00" * (2 * 1024)
            with pytest.raises(SizeError, match="per-image cap"):
                EmailImage.inline(oversized, alt="Chart")

    def test_retry_ladder_is_read_from_config(self):
        waits: list[float] = []

        def always_fail():
            raise TimeoutError("nope")

        with config_override(
            retry_max_attempts=3, retry_initial_delay=5.0, retry_backoff_factor=3.0
        ):
            with pytest.raises(TimeoutError):
                retry_with_backoff(always_fail, is_transient=lambda _: True, sleep=waits.append)
        assert waits == [5.0, 15.0]

    def test_an_explicit_argument_still_beats_the_config(self):
        waits: list[float] = []

        def always_fail():
            raise TimeoutError("nope")

        with config_override(retry_initial_delay=5.0):
            with pytest.raises(TimeoutError):
                retry_with_backoff(
                    always_fail,
                    is_transient=lambda _: True,
                    max_attempts=2,
                    initial_delay=0.25,
                    sleep=waits.append,
                )
        assert waits == [0.25]

    def test_request_timeout_is_read_from_config(self):
        class _Session:
            def __init__(self):
                self.timeouts = []

            def post(self, url, *, data, headers, timeout):
                self.timeouts.append(timeout)
                return type("R", (), {"status_code": 202, "headers": {}, "text": ""})()

        session = _Session()
        with config_override(request_timeout_seconds=7.5):
            GraphApiTransport(session).send_mime(base64.b64encode(b"x").decode())
        assert session.timeouts == [7.5]

    def test_an_explicit_timeout_still_beats_the_config(self):
        class _Session:
            def __init__(self):
                self.timeouts = []

            def post(self, url, *, data, headers, timeout):
                self.timeouts.append(timeout)
                return type("R", (), {"status_code": 202, "headers": {}, "text": ""})()

        session = _Session()
        with config_override(request_timeout_seconds=7.5):
            # None is a real setting -- "no timeout" -- not "unspecified",
            # so it must survive rather than falling back to the config.
            GraphApiTransport(session, timeout=None).send_mime("eA==")
        assert session.timeouts == [None]

    def test_error_body_excerpt_length_is_read_from_config(self):
        from svc.outlook.sender import GraphApiError

        class _Session:
            def post(self, url, *, data, headers, timeout):
                return type("R", (), {"status_code": 400, "headers": {}, "text": "E" * 900})()

        with config_override(error_body_excerpt_chars=20):
            with pytest.raises(GraphApiError) as caught:
                GraphApiTransport(_Session()).send_mime("eA==")
        assert "E" * 20 in str(caught.value)
        assert "E" * 21 not in str(caught.value)

    def test_defaults_reproduce_the_previous_constants(self):
        # The whole change must be behaviour-preserving out of the box.
        from svc.builder.images import INLINE_LIMIT_KB
        from svc.email.medium import _SIZE_LIMIT_KB, _SIZE_WARN_KB
        from svc.outlook.sender import DEFAULT_TIMEOUT_SECONDS

        config = Config()
        assert (_SIZE_LIMIT_KB, _SIZE_WARN_KB, INLINE_LIMIT_KB) == (102, 90, 48)
        assert (config.size_limit_kb, config.size_warn_kb) == (102, 90)
        assert config.inline_image_limit_kb == 48
        assert DEFAULT_TIMEOUT_SECONDS == 30.0
        assert replace(config) == config
