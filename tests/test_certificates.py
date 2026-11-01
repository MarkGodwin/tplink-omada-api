"""Certificate upload and CLI regression tests."""
# pylint: disable=protected-access
import asyncio
import json
from argparse import ArgumentParser
from unittest.mock import AsyncMock

import pytest

from tplink_omada_client.cli import command_certificate
from tplink_omada_client.omadaclient import OmadaClient


@pytest.mark.parametrize("cert_type", ["PFX", "PEM", "JKS"])
def test_upload(tmp_path, cert_type):
    """Inspect multipart bytes and ensure settings reference uploaded files."""
    cert = tmp_path / "cert"
    key = tmp_path / "key"
    cert.write_bytes(b"certificate contents")
    key.write_bytes(b"private key contents")
    requests = []

    async def request(method, url, **kwargs):
        requests.append((method, url, kwargs))
        if method == "post":
            parts = list(kwargs["data"])
            is_key = url.endswith("/key")
            prefix = "key" if is_key else "cer"
            assert len(parts) == 2
            assert parts[0][0]._value == (b"private key contents" if is_key else b"certificate contents")
            assert 'name="file"' in parts[0][0].headers["Content-Disposition"]
            assert json.loads(parts[1][0]._value) == {prefix + "Name": "key" if is_key else "cert"}
            return {prefix + "Id": prefix + "-id", prefix + "Name": "server-" + prefix}
        return {}

    client = OmadaClient("https://example.com", "user", "pass")
    client._api = AsyncMock()
    client._api.format_url = lambda endpoint: endpoint
    client._api.request.side_effect = request
    options = {"key_file": str(key)} if cert_type == "PEM" else {"cert_type": cert_type}
    # Exercise the original positional PFX call as well as the new formats.
    if cert_type == "PFX":
        options = {}
    asyncio.run(client.set_certificate(str(cert), "" if cert_type == "PEM" else "secret", **options))
    expected = {"cerId": "cer-id", "cerName": "server-cer", "cerType": cert_type, "enable": True}
    if cert_type == "PEM":
        expected.update(keyId="key-id", keyName="server-key")
    else:
        expected["keyPassword"] = "secret"
    assert requests[-1] == ("patch", "controller/setting", {"json": {"certificate": expected}})
    assert len(requests) == (3 if cert_type == "PEM" else 2)


@pytest.mark.parametrize("options", [
    {"cert_type": "PEM"}, {"cert_type": "invalid"},
    {"cert_type": "PFX", "key_file": "key"}, {"key_file": "key", "cert_password": "secret"},
])
def test_invalid_arguments(options):
    """Reject incompatible inputs before files or network are accessed."""
    client = OmadaClient("https://example.com", "user", "pass")
    client._api = AsyncMock()
    with pytest.raises(ValueError):
        asyncio.run(client.set_certificate("missing", **options))
    client._api.request.assert_not_called()


def test_missing_key_does_not_upload(tmp_path):
    """A missing local key must not leave an uploaded certificate behind."""
    cert = tmp_path / "cert"
    cert.write_bytes(b"cert")
    client = OmadaClient("https://example.com", "user", "pass")
    client._api = AsyncMock()
    with pytest.raises(FileNotFoundError):
        asyncio.run(client.set_certificate(str(cert), key_file=str(tmp_path / "missing")))
    client._api.request.assert_not_called()


@pytest.mark.parametrize("arguments, expected_type, expected_password", [
    (["cert", "--key-file", "key"], "PEM", ""),
    (["cert", "--password", ""], "PFX", ""),
    (["cert"], "PFX", "prompted"),
    (["cert", "--format", "jks"], "JKS", "prompted"),
])
def test_cli(monkeypatch, arguments, expected_type, expected_password):
    """PEM never prompts; explicit empty passwords are preserved."""
    parser = ArgumentParser()
    command_certificate.arg_parser(parser.add_subparsers())
    args = vars(parser.parse_args(["set-certificate", *arguments]))
    client = AsyncMock()
    client.__aenter__.return_value = client
    monkeypatch.setattr(command_certificate, "get_target_argument", lambda args: "target")
    monkeypatch.setattr(command_certificate, "get_target_config", lambda target: None)
    monkeypatch.setattr(command_certificate, "to_omada_connection", lambda config: client)

    def prompt():
        assert expected_password == "prompted"
        return "prompted"

    monkeypatch.setattr(command_certificate.getpass, "getpass", prompt)
    assert asyncio.run(command_certificate.command_certificate(args)) == 0
    client.set_certificate.assert_awaited_once_with(
        "cert", expected_password, key_file=args["key_file"], cert_type=expected_type
    )
