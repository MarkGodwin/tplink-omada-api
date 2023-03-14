"""Responsible for ~/.omada.ini"""
from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path

from tplink_omada_client.omadaclient import OmadaClient

_config_file: Path = Path.home() / '.omada.cfg'
_CONTROLLER_SECTION_PREFIX: str = 'controller:'

@dataclass
class ControllerConfig:
    """Holds config needed to issue calls to Omada controller"""
    url: str
    username: str
    password: str
    site: str

def to_omada_connection(config: ControllerConfig) -> OmadaClient:
    """Create a OmadaClient based on a ControllerConfig object"""
    return OmadaClient(config.url, username=config.username, password=config.password)

def _read_config_file() -> ConfigParser:
    """Read's the user's config file"""
    config = ConfigParser()
    if _config_file.exists():
        with _config_file.open() as file:
            config.read_file(file)
    return config

def set_controller_config(name: str, config: ControllerConfig) -> None:
    """Stores controller config in users's config file"""
    stored_name = _CONTROLLER_SECTION_PREFIX + name
    config_parser = _read_config_file()
    config_parser.remove_section(stored_name)
    config_parser.add_section(stored_name)
    config_parser.set(stored_name, "url", config.url)
    config_parser.set(stored_name, "username", config.username)
    config_parser.set(stored_name, "password", config.password)
    config_parser.set(stored_name, "site", config.site)
    with _config_file.open(mode='w') as file:
        config_parser.write(file)