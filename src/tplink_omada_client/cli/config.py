"""Responsible for ~/.omada.ini"""
from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path

from tplink_omada_client.omadaclient import OmadaClient

_CONFIG_FILE: Path = Path.home() / '.omada.cfg'
_CONTROLLER_SECTION_PREFIX: str = 'controller:'

@dataclass
class ControllerConfig:
    """Holds config needed to issue calls to Omada controller"""
    url: str
    username: str
    password: str
    site: str

def get_targets() -> list[tuple[str, str]]:
    """Get all the controllers in config file"""
    config_parser = _read_config_file()
    targets = []
    for (target, config) in config_parser.items():
        if target.startswith(_CONTROLLER_SECTION_PREFIX):
            name = target[len(_CONTROLLER_SECTION_PREFIX):]
            targets.append((name, config["url"]))
    return targets

def get_target_config(name: str) -> ControllerConfig:
    """Using controller name to create Omada site client"""
    config = _read_config_file()
    stored_name = _to_stored_name(name)
    if config.has_section(stored_name):
        stored_config = config[stored_name]
        return ControllerConfig(**stored_config)
    raise ValueError(f"Could not find target named '{name}'")

def set_target_config(name: str, config: ControllerConfig) -> None:
    """Stores controller config in users's config file"""
    stored_name = _to_stored_name(name)
    config_parser = _read_config_file()
    config_parser.remove_section(stored_name)
    config_parser.add_section(stored_name)
    config_parser.set(stored_name, "url", config.url)
    config_parser.set(stored_name, "username", config.username)
    config_parser.set(stored_name, "password", config.password)
    config_parser.set(stored_name, "site", config.site)
    with _CONFIG_FILE.open(mode='w') as file:
        config_parser.write(file)

def to_omada_connection(config: ControllerConfig) -> OmadaClient:
    """Create a OmadaClient based on a ControllerConfig object"""
    return OmadaClient(config.url, username=config.username, password=config.password)

def _read_config_file() -> ConfigParser:
    """Read's the user's config file"""
    config = ConfigParser()
    if _CONFIG_FILE.exists():
        with _CONFIG_FILE.open() as file:
            config.read_file(file)
    return config

def _to_stored_name(name: str) -> str:
    return _CONTROLLER_SECTION_PREFIX + name
