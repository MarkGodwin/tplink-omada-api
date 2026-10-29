"""Offline regression tests for CLI password storage."""

from configparser import ConfigParser

import pytest

from tplink_omada_client.cli import config


@pytest.fixture
def config_file(tmp_path, monkeypatch):
    path = tmp_path / ".omada.cfg"
    monkeypatch.setattr(config, "_CONFIG_FILE", path)
    return path


@pytest.mark.parametrize("password", ["ordinary", "single%value", "double%%value", "%(username)s", "%", "%%", "mix%%%(missing)s%"])
def test_password_round_trip_is_literal(config_file, password):
    target = config.ControllerConfig("https://controller.invalid", "operator", password, "Default", True)
    config.set_target_config("home", target, set_default=True)

    assert config.get_target_config("home") == target
    assert config.get_target_config("") == target
    assert config.get_targets() == [("home", target, True)]
    # The stored format must also work with existing ConfigParser readers.
    legacy = ConfigParser()
    legacy.read(config_file)
    assert legacy["controller:home"]["password"] == password


@pytest.mark.parametrize("stored,expected", [
    ("ordinary", "ordinary"),
    ("single%%value", "single%value"),
    ("double%%%%value", "double%%value"),
    ("%%(username)s", "%(username)s"),
    ("%(username)s", "%(username)s"),
    ("single%value", "single%value"),
])
def test_legacy_password_is_not_interpolated(config_file, stored, expected):
    config_file.write_text(
        "[controller:home]\nurl = https://controller.invalid\nusername = operator\n"
        f"password = {stored}\nsite = Default\nverify_ssl = false\n",
        encoding="utf-8",
    )
    result = config.get_target_config("home")
    assert result.password == expected
    assert result.verify_ssl is False
    # Saving unrelated configuration must not corrupt the legacy escape representation.
    config.set_default_target("home")
    assert config.get_target_config("").password == expected


def test_updating_target_preserves_other_passwords(config_file):
    first = config.ControllerConfig("https://one.invalid", "one", "first%%secret", "First", True)
    second = config.ControllerConfig("https://two.invalid", "two", "%(username)s%", "Second", False)
    config.set_target_config("one", first, set_default=True)
    config.set_target_config("two", second, set_default=False)
    config.set_target_config("two", second, set_default=True)
    assert config.get_target_config("one") == first
    assert config.get_target_config("") == second
    config.delete_target_config("two")
    assert config.get_target_config("one") == first
