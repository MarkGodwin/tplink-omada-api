"""CLI configuration with XDG paths and existing legacy-file support."""

import os
from configparser import ConfigParser, Error, SectionProxy
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

from tplink_omada_client import OmadaClient

_CONTROLLER_SECTION_PREFIX: str = "controller:"
_CLI_SECTION: str = "cli"
_DEFAULT_TARGET: str = "default_target"


class ConfigError(RuntimeError):
    """Configuration failure safe to display without exposing file contents."""


def _config_exists(path: Path) -> bool:
    try:
        path.lstat()
        return True
    except FileNotFoundError:
        return False
    except OSError:
        raise ConfigError("Could not inspect CLI configuration.") from None


def _get_config_file() -> Path:
    """Prefer an existing XDG file, then legacy; create only in XDG."""
    configured = Path(os.environ.get("XDG_CONFIG_HOME", ""))
    root = configured if configured.is_absolute() else Path.home() / ".config"
    xdg = root / "omada" / "config.ini"
    legacy = Path.home() / ".omada.cfg"
    for candidate in (xdg, legacy):
        if _config_exists(candidate):
            try:
                # Keep user-managed symlinks, and bind writes to the same file as reads.
                return candidate.resolve(strict=True)
            except (OSError, RuntimeError):
                raise ConfigError("Could not resolve CLI configuration.") from None
    return xdg


@dataclass
class ControllerConfig:
    """Holds config needed to issue calls to Omada controller"""

    url: str
    username: str
    password: str
    site: str
    verify_ssl: bool


def _parse_controller_config(config: SectionProxy) -> ControllerConfig:
    """Parse controller config without expanding password placeholders."""
    try:
        password = config.get("password", raw=True)
        if password is None:
            raise KeyError("password")
        return ControllerConfig(
            config["url"],
            config["username"],
            password.replace("%%", "%"),
            config["site"],
            config.get("verify_ssl", "True").lower() == "true",
        )
    except (Error, KeyError):
        raise ConfigError("Invalid controller configuration; check required fields and percent escaping.") from None


def _get_default_target(config: ConfigParser) -> str:
    if _CLI_SECTION not in config:
        return ""
    try:
        return config[_CLI_SECTION][_DEFAULT_TARGET]
    except (Error, KeyError):
        raise ConfigError("Invalid default-target configuration.") from None


def get_targets() -> list[tuple[str, ControllerConfig, bool]]:
    """Get all the controllers in config file"""
    config_parser = _read_config_file()
    default_target = _get_default_target(config_parser)
    targets = []

    for target, config in config_parser.items():
        if target.startswith(_CONTROLLER_SECTION_PREFIX):
            name = target[len(_CONTROLLER_SECTION_PREFIX) :]
            targets.append((name, _parse_controller_config(config), name == default_target))

    return targets


def get_target_config(name: str) -> ControllerConfig:
    """Using controller name to create Omada site client"""
    config = _read_config_file()

    if name == "":
        name = _get_default_target(config)
        if not name:
            raise ValueError("No target specified, and no default target has been configured.")

    stored_name = _to_stored_name(name)
    if config.has_section(stored_name):
        stored_config = config[stored_name]
        return _parse_controller_config(stored_config)
    raise ValueError(f"Could not find target named '{name}'")


def set_target_config(name: str, config: ControllerConfig, set_default: bool) -> None:
    """Stores controller config in users's config file"""
    stored_name = _to_stored_name(name)
    path = _get_config_file()
    config_parser = _read_config_file(path)
    config_parser.remove_section(stored_name)
    config_parser.add_section(stored_name)
    config_parser.set(stored_name, "url", config.url)
    config_parser.set(stored_name, "username", config.username)
    # Keep the legacy INI escape format, but never interpret password placeholders.
    config_parser.set(stored_name, "password", config.password.replace("%", "%%"))
    config_parser.set(stored_name, "site", config.site)
    config_parser.set(stored_name, "verify_ssl", str(config.verify_ssl))
    if set_default:
        if _CLI_SECTION not in config_parser:
            config_parser[_CLI_SECTION] = {}
        config_parser[_CLI_SECTION][_DEFAULT_TARGET] = name

    _write_config_file(config_parser, path)


def set_default_target(name: str) -> None:
    """Set default target in user's config file."""
    path = _get_config_file()
    config_parser = _read_config_file(path)
    if _CLI_SECTION not in config_parser:
        config_parser[_CLI_SECTION] = {}
    config_parser[_CLI_SECTION][_DEFAULT_TARGET] = name
    _write_config_file(config_parser, path)


def delete_target_config(name: str) -> None:
    """Delete a target from the user's config file."""
    path = _get_config_file()
    config = _read_config_file(path)
    stored_name = _to_stored_name(name)
    if config.has_section(stored_name):
        config.remove_section(stored_name)
        _write_config_file(config, path)


def to_omada_connection(config: ControllerConfig) -> OmadaClient:
    """Create a OmadaClient based on a ControllerConfig object"""
    return OmadaClient(config.url, username=config.username, password=config.password, verify_ssl=config.verify_ssl)


def _read_config_file(path: Path | None = None) -> ConfigParser:
    """Read only the selected configuration; never fall back on errors."""
    if path is None:
        path = _get_config_file()
    config = ConfigParser()
    try:
        if _config_exists(path):
            with path.open(encoding="utf-8") as file:
                config.read_file(file)
    except (Error, OSError, UnicodeError):
        raise ConfigError("Could not read CLI configuration; check its syntax and permissions.") from None
    return config


def _write_config_file(config_parser: ConfigParser, path: Path) -> None:
    """Replace the selected file privately, retaining it if writing fails."""
    temporary: Path | None = None
    try:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as file:
            temporary = Path(file.name)
            config_parser.write(file)
        os.replace(temporary, path)
    except (Error, OSError, UnicodeError):
        raise ConfigError("Could not write CLI configuration; the previous file was not replaced.") from None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _to_stored_name(name: str) -> str:
    return _CONTROLLER_SECTION_PREFIX + name
