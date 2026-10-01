"""
An attached or inline picture far wider than it is shown warns at construction (#276).
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest

from pyhermes.builder import SizeWarning
from pyhermes.builder.images import EmailImage
from pyhermes.config import Config, config_override, get_config, set_config
from qa.fixtures import all_brochure_fixtures, all_fixtures, all_paged_fixtures
from qa.fixtures._png import solid_png

PHOTO = solid_png(4000, 3000, (90, 110, 130))


def _warnings(build) -> list[warnings.WarningMessage]:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        build()
    return [w for w in caught if issubclass(w.category, SizeWarning)]


def test_a_phone_photo_at_thumbnail_size_warns_once_at_the_callers_line():
    caught = _warnings(lambda: EmailImage.attached(PHOTO, alt="Desk photo", width=300))
    assert len(caught) == 1
    message = str(caught[0].message)
    for fact in ("'Desk photo'", "4000x3000px", "300px wide", "13.3 times", "600px", "938px"):
        assert fact in message
    assert Path(caught[0].filename).name == Path(__file__).name


@pytest.mark.parametrize("factory", [EmailImage.attached, EmailImage.inline])
def test_it_checks_both_kinds_that_carry_bytes(factory):
    small = solid_png(2000, 100, (1, 2, 3))
    assert len(_warnings(lambda: factory(small, alt="Strip", width=300))) == 1


@pytest.mark.parametrize("pixels", [600, 1350])
def test_twice_the_width_and_up_to_the_threshold_are_quiet(pixels):
    image = solid_png(pixels, 40, (1, 2, 3))
    assert not _warnings(lambda: EmailImage.attached(image, alt="Fine", width=300))


def test_an_image_with_no_display_width_and_a_hosted_one_are_not_checked():
    assert not _warnings(lambda: EmailImage.attached(PHOTO, alt="Full width"))
    assert not _warnings(
        lambda: EmailImage.hosted("https://example.com/p.png", alt="Hosted", width=10)
    )


def test_the_galleries_render_with_no_size_warning():
    """Equations render at 4x and print images at 3.125x on purpose; neither warns."""
    for registry in (all_fixtures, all_paged_fixtures, all_brochure_fixtures):
        for name, build in registry().items():
            assert not _warnings(lambda build=build: build().render()), name


class TestTheThresholdIsConfig:
    def _quiet(self) -> bool:
        image = solid_png(1200, 40, (1, 2, 3))
        return not _warnings(lambda: EmailImage.attached(image, alt="Four times", width=300))

    def test_the_default_lets_four_times_through(self):
        assert get_config().oversize_image_ratio == 4.5
        assert self._quiet()

    def test_a_context_tightens_it(self):
        with config_override(oversize_image_ratio=2.5):
            assert not self._quiet()

    def test_the_process_default_tightens_it(self):
        previous = get_config()
        set_config(Config(oversize_image_ratio=2.5))
        try:
            assert not self._quiet()
        finally:
            set_config(previous)

    def test_the_environment_sets_it(self, monkeypatch):
        monkeypatch.setenv("PYHERMES_OVERSIZE_IMAGE_RATIO", "2.5")
        assert Config.from_env().oversize_image_ratio == 2.5

    def test_a_host_can_promote_it_to_an_error(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error", SizeWarning)
            with pytest.raises(SizeWarning):
                EmailImage.attached(PHOTO, alt="Desk photo", width=300)

    @pytest.mark.parametrize("ratio", [0, -1])
    def test_it_must_be_positive(self, ratio):
        with pytest.raises(ValueError, match="oversize_image_ratio"):
            Config(oversize_image_ratio=ratio)
