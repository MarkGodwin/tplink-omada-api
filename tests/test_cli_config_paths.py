"""Offline XDG selection, legacy compatibility and private-write tests."""

import os
import stat
import traceback

import pytest

from tplink_omada_client import cli
from tplink_omada_client.cli import command_target, config


@pytest.fixture
def paths(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(config.Path, "home", lambda: home)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    legacy = home / ".omada.cfg"
    # Protect the real config even when these tests run on the old implementation.
    monkeypatch.setattr(config, "_CONFIG_FILE", legacy, raising=False)
    return home, legacy, home / ".config" / "omada" / "config.ini"


def _write_target(path, name="home", password="synthetic%%password"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"[controller:{name}]\nurl = https://controller.invalid\nusername = operator\n"
        f"password = {password}\nsite = Default\nverify_ssl = true\n",
        encoding="utf-8",
    )


@pytest.mark.parametrize("environment", [None, "", "relative/path", "~/relative", "absolute"])
def test_new_config_uses_xdg(paths, monkeypatch, environment):
    home, legacy, expected = paths
    if environment is not None:
        value = str(home / "custom") if environment == "absolute" else environment
        monkeypatch.setenv("XDG_CONFIG_HOME", value)
        if environment == "absolute":
            expected = home / "custom" / "omada" / "config.ini"
    target = config.ControllerConfig("https://controller.invalid", "operator", "new%%%(username)s%", "Default", True)
    config.set_target_config("home", target, set_default=True)
    assert expected.is_file()
    assert not legacy.exists()
    assert config.get_target_config("") == target
    assert config.get_targets() == [("home", target, True)]


def test_xdg_preferred_without_merging_legacy(paths):
    _, legacy, xdg = paths
    _write_target(legacy, "legacy")
    legacy_bytes = legacy.read_bytes()
    _write_target(xdg, "xdg")
    assert [name for name, _, _ in config.get_targets()] == ["xdg"]
    config.set_default_target("xdg")
    assert config.get_target_config("").password == "synthetic%password"
    config.delete_target_config("xdg")
    assert config.get_targets() == []
    assert xdg.exists()
    assert legacy.read_bytes() == legacy_bytes


def test_existing_legacy_stays_selected(paths):
    _, legacy, xdg = paths
    _write_target(legacy)
    config.set_default_target("home")
    assert config.get_target_config("").password == "synthetic%password"
    replacement = config.ControllerConfig("https://other.invalid", "other", "new%password", "Other", False)
    config.set_target_config("home", replacement, set_default=False)
    assert config.get_target_config("") == replacement
    config.delete_target_config("home")
    assert config.get_targets() == []
    assert legacy.exists()
    assert not xdg.exists()


@pytest.mark.parametrize("contents", [
    "synthetic-secret-without-section",
    "[controller:home]\npassword=synthetic-secret\npassword=duplicate\n",
])
def test_invalid_xdg_does_not_fall_back_or_leak(paths, contents):
    _, legacy, xdg = paths
    _write_target(legacy)
    xdg.parent.mkdir(parents=True)
    xdg.write_text(contents, encoding="utf-8")
    before = legacy.read_bytes(), xdg.read_bytes()
    with pytest.raises(RuntimeError) as failure:
        config.get_targets()
    rendered = "".join(traceback.format_exception(failure.value))
    assert "synthetic-secret" not in rendered
    assert (legacy.read_bytes(), xdg.read_bytes()) == before


def test_invalid_xdg_stops_target_creation_before_connection(paths, monkeypatch, capsys):
    _, legacy, xdg = paths
    _write_target(legacy)
    xdg.parent.mkdir(parents=True)
    xdg.write_text("synthetic-secret-without-section", encoding="utf-8")

    def no_connection(_):
        pytest.fail("Malformed configuration must fail before connecting")
    monkeypatch.setattr(command_target, "to_omada_connection", no_connection)
    assert cli.main(["-t", "new", "target", "--url", "https://controller.invalid", "--username", "operator", "--password", "fake"]) == 1
    output = capsys.readouterr()
    assert "synthetic-secret" not in output.out + output.err
    assert xdg.read_text(encoding="utf-8") == "synthetic-secret-without-section"


def test_unreadable_xdg_does_not_fall_back(paths, monkeypatch):
    _, legacy, xdg = paths
    _write_target(legacy)
    _write_target(xdg)
    original = config.Path.open

    def deny(path, *args, **kwargs):
        if path == xdg:
            raise PermissionError("synthetic-secret")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(config.Path, "open", deny)
    with pytest.raises(RuntimeError) as failure:
        config.get_targets()
    assert "synthetic-secret" not in "".join(traceback.format_exception(failure.value))


def test_new_config_and_app_directory_are_private(paths):
    home, legacy, xdg = paths
    home_mode = stat.S_IMODE(home.stat().st_mode)
    old_mask = os.umask(0)
    try:
        config.set_target_config("home", config.ControllerConfig("https://controller.invalid", "operator", "fake", "Default", True), True)
    finally:
        os.umask(old_mask)
    assert xdg.is_file()
    assert stat.S_IMODE(xdg.stat().st_mode) == 0o600
    assert stat.S_IMODE(xdg.parent.stat().st_mode) == 0o700
    assert not legacy.exists()
    assert stat.S_IMODE(home.stat().st_mode) == home_mode  # Do not chmod a user's home.


@pytest.mark.parametrize("selected", ["legacy", "xdg"])
def test_existing_config_becomes_private_without_chmod_parent(paths, selected):
    home, legacy, xdg = paths
    path = legacy if selected == "legacy" else xdg
    _write_target(path)
    path.chmod(0o644)
    parent_mode = stat.S_IMODE(path.parent.stat().st_mode)
    config.set_default_target("home")
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(path.parent.stat().st_mode) == parent_mode
    assert home.exists()


def test_failed_write_preserves_selected_config(paths, monkeypatch):
    _, legacy, xdg = paths
    _write_target(legacy)
    before = legacy.read_bytes()

    def fail_write(self, file, *args, **kwargs):
        file.write("partial-synthetic-secret")
        raise OSError("synthetic-secret-write-error")
    monkeypatch.setattr(config.ConfigParser, "write", fail_write)
    with pytest.raises(RuntimeError) as failure:
        config.set_default_target("home")
    assert legacy.read_bytes() == before
    assert "synthetic-secret" not in "".join(traceback.format_exception(failure.value))
    assert sorted(p.name for p in legacy.parent.iterdir()) == [".omada.cfg"]
    assert not xdg.exists()


@pytest.mark.parametrize("selected", ["legacy", "xdg"])
def test_writing_symlinked_config_preserves_link(paths, selected):
    home, legacy, xdg = paths
    selected_path = legacy if selected == "legacy" else xdg
    destination = home / "managed" / "omada.ini"
    _write_target(destination)
    selected_path.parent.mkdir(parents=True, exist_ok=True)
    selected_path.symlink_to(destination)
    config.set_default_target("home")
    assert selected_path.is_symlink()
    assert "[cli]" in destination.read_text(encoding="utf-8")
    assert config.get_target_config("").password == "synthetic%password"


def test_broken_xdg_symlink_does_not_fall_back(paths):
    home, legacy, xdg = paths
    _write_target(legacy)
    xdg.parent.mkdir(parents=True)
    xdg.symlink_to(home / "missing.ini")
    with pytest.raises(RuntimeError):
        config.get_targets()
    assert xdg.is_symlink()


def test_selected_path_stays_bound_during_write(paths, monkeypatch):
    _, legacy, xdg = paths
    _write_target(legacy)
    original = config._read_config_file

    def read_then_add_xdg(path=None):
        parser = original(path)
        _write_target(xdg, "xdg")
        return parser

    monkeypatch.setattr(config, "_read_config_file", read_then_add_xdg)
    config.set_default_target("home")
    assert "[cli]" in legacy.read_text(encoding="utf-8")
    assert "[cli]" not in xdg.read_text(encoding="utf-8")


@pytest.mark.parametrize("write_fails", [False, True])
def test_target_command_uses_literal_prompt_password_and_reports_save_result(paths, monkeypatch, capsys, write_fails):
    from types import SimpleNamespace

    _, _, xdg = paths
    password = "synthetic%%%(username)s%"
    seen = []

    class FakeController:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def get_controller_name(self):
            return "Test controller"

        async def get_sites(self):
            return [SimpleNamespace(name="Default")]

    def connect(target):
        seen.append(target.password)
        return FakeController()

    monkeypatch.setattr(command_target.getpass, "getpass", lambda: password)
    monkeypatch.setattr(command_target, "to_omada_connection", connect)
    if write_fails:
        def reject_replace(*_):
            raise PermissionError("synthetic-secret")
        monkeypatch.setattr(config.os, "replace", reject_replace)
    result = cli.main(["-t", "home", "target", "--url", "https://controller.invalid", "--username", "operator", "--set-default"])
    output = capsys.readouterr().out
    assert seen == [password]
    assert password not in output
    assert "synthetic-secret" not in output
    if write_fails:
        assert result == 1
        assert "Set target" not in output
        assert not xdg.exists()
        assert list(xdg.parent.iterdir()) == []
    else:
        assert result == 0
        assert "Set target home" in output
        assert config.get_target_config("").password == password


@pytest.mark.parametrize("contents,arguments", [
    ("[controller:home]\nurl=https://controller.invalid\nusername=operator\nsite=Default\n", ["targets"]),
    ("[cli]\n", ["targets"]),
    ("[cli]\n", ["devices"]),
    ("[controller:home]\nurl=https://controller.invalid\nusername=synthetic%secret\npassword=fake\nsite=Default\n", ["targets"]),
    ("[cli]\ndefault_target=%(missing)s\n", ["targets"]),
    ("[cli]\ndefault_target=%(missing)s\n", ["devices"]),
])
def test_config_field_errors_are_safe_cli_failures(paths, capsys, contents, arguments):
    _, legacy, xdg = paths
    _write_target(legacy)
    xdg.parent.mkdir(parents=True)
    xdg.write_text(contents, encoding="utf-8")
    before = xdg.read_bytes(), legacy.read_bytes()
    assert cli.main(arguments) == 1
    output = capsys.readouterr()
    assert "configuration" in output.out.lower()
    assert "synthetic%secret" not in output.out + output.err
    assert "Traceback" not in output.out + output.err
    assert (xdg.read_bytes(), legacy.read_bytes()) == before
