"""Responsible for ~/.omada.cfg"""
from configparser import ConfigParser, SectionProxy
from dataclasses import dataclass
from pathlib import Path

from tplink_omada_client import OmadaClient

_CONFIG_FILE: Path = Path.home() / '.omada.cfg'
_CONTROLLER_SECTION_PREFIX: str = 'controller:'
_CLI_SECTION: str = "cli"
_DEFAULT_TARGET: str = "default_target"

@dataclass
class ControllerConfig:
    """Holds config needed to issue calls to Omada controller"""
    url: str
    username: str
    password: str
    site: str
    verify_ssl: bool

def _parse_controller_config(config: SectionProxy) -> ControllerConfig:
    """Parse controller config section"""
    return ControllerConfig(
            config["url"],
            config["username"],
            config["password"],
            config["site"],
            config.get("verify_ssl", "True").lower() == "true"
        )

def get_targets() -> list[tuple[str, ControllerConfig, bool]]:
    """Get all the controllers in config file"""
    config_parser = _read_config_file()
    default_target = config_parser[_CLI_SECTION][_DEFAULT_TARGET] if _CLI_SECTION in config_parser else ""
    targets = []



    for (target, config) in config_parser.items():
        if target.startswith(_CONTROLLER_SECTION_PREFIX):
            name = target[len(_CONTROLLER_SECTION_PREFIX):]
            targets.append((name, _parse_controller_config(config), name == default_target))

    return targets


def get_target_config(name: str) -> ControllerConfig:
    """Using controller name to create Omada site client"""
    config = _read_config_file()

    if name == "":
        if _CLI_SECTION in config:
            name = config[_CLI_SECTION][_DEFAULT_TARGET]
        if not name:
            raise ValueError(f"No target specified, and no default target has been configured.")
        
    stored_name = _to_stored_name(name)
    if config.has_section(stored_name):
        stored_config = config[stored_name]
        return _parse_controller_config(stored_config)
    raise ValueError(f"Could not find target named '{name}'")

def set_target_config(name: str, config: ControllerConfig, set_default: bool) -> None:
    """Stores controller config in users's config file"""
    stored_name = _to_stored_name(name)
    config_parser = _read_config_file()
    config_parser.remove_section(stored_name)
    config_parser.add_section(stored_name)
    config_parser.set(stored_name, "url", config.url)
    config_parser.set(stored_name, "username", config.username)
    config_parser.set(stored_name, "password", config.password)
    config_parser.set(stored_name, "site", config.site)
    config_parser.set(stored_name, "verify_ssl", str(config.verify_ssl))
    if set_default:
        if _CLI_SECTION not in config_parser:
            config_parser[_CLI_SECTION] = {}
        config_parser[_CLI_SECTION][_DEFAULT_TARGET] = name

    _write_config_file(config_parser)

def set_default_target(name: str) -> None:
    config_parser = _read_config_file()
    if _CLI_SECTION not in config_parser:
        config_parser[_CLI_SECTION] = {}
    config_parser[_CLI_SECTION][_DEFAULT_TARGET] = name
    _write_config_file(config_parser)

def delete_target_config(name: str) -> None:
    config = _read_config_file()
    stored_name = _to_stored_name(name)
    if config.has_section(stored_name):
        config.remove_section(stored_name)
        _write_config_file(config)

def to_omada_connection(config: ControllerConfig) -> OmadaClient:
    """Create a OmadaClient based on a ControllerConfig object"""
    return OmadaClient(config.url, username=config.username, password=config.password, verify_ssl=config.verify_ssl)

def _read_config_file() -> ConfigParser:
    """Read's the user's config file"""
    config = ConfigParser()
    if _CONFIG_FILE.exists():
        with _CONFIG_FILE.open() as file:
            config.read_file(file)
    return config

def _write_config_file(config_parser):
    """Write the user's config file"""
    with _CONFIG_FILE.open(mode='w') as file:
        config_parser.write(file)


def _to_stored_name(name: str) -> str:
    return _CONTROLLER_SECTION_PREFIX + name
