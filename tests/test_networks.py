"""Tests for network data models."""


from tplink_omada_client.networks import DhcpReservation, LanNetwork


def test_dhcp_reservation():
    """Smoke test: DhcpReservation reads from raw data dict."""
    data = {
        "id": "res-1",
        "mac": "AA-BB-CC-11-22-33",
        "ip": "192.168.1.100",
        "description": "web-server",
        "status": True,
        "netId": "net-1",
        "netName": "Main",
    }
    r = DhcpReservation(data)
    assert r.id == "res-1"
    assert r.mac == "AA-BB-CC-11-22-33"
    assert r.ip == "192.168.1.100"
    assert r.description == "web-server"
    assert r.status is True
    assert r.net_id == "net-1"
    assert r.net_name == "Main"
    assert r.raw_data == data


def test_dhcp_reservation_optional_fields_default_to_none():
    """Optional fields return None when not present in the API response."""
    r = DhcpReservation({"id": "res-2", "mac": "11-22-33-44-55-66", "ip": "10.0.0.10"})
    assert r.description is None
    assert r.status is None
    assert r.net_id is None
    assert r.net_name is None
    assert r.client_name is None
    assert r.export_to_ip_mac_binding is None


def test_dhcp_reservation_optional_fields():
    """All optional fields populate correctly."""
    data = {
        "id": "res-3",
        "mac": "AA-BB-CC-DD-EE-FF",
        "ip": "10.0.0.50",
        "description": "printer",
        "status": False,
        "netId": "net-2",
        "netName": "Guest",
        "clientName": "HPLaserJet",
        "exportToIpMacBinding": True,
    }
    r = DhcpReservation(data)
    assert r.description == "printer"
    assert r.status is False
    assert r.net_id == "net-2"
    assert r.net_name == "Guest"
    assert r.client_name == "HPLaserJet"
    assert r.export_to_ip_mac_binding is True


def test_dhcp_reservation_repr():
    """repr() includes property names and values, not raw_data."""
    r = DhcpReservation({"id": "r1", "mac": "AA-BB-CC-11-22-33", "ip": "10.0.0.1", "description": "test"})
    rep = repr(r)
    assert "DhcpReservation" in rep
    assert "id=r1" in rep
    assert "mac=AA-BB-CC-11-22-33" in rep
    assert "ip=10.0.0.1" in rep
    assert "description=test" in rep
    assert "_data" not in rep


def test_lan_network_exposes_listing_fields():
    """LanNetwork exposes the fields returned by the LAN-network endpoint."""
    network = LanNetwork(
        {
            "id": "network-1",
            "name": "IOT",
            "purpose": "interface",
            "vlan": 30,
            "gatewaySubnet": "192.168.30.1/24",
            "dhcpSettings": {"enable": True},
        }
    )

    assert network.id == "network-1"
    assert network.name == "IOT"
    assert network.purpose == "interface"
    assert network.vlan_id == 30
    assert network.gateway_subnet == "192.168.30.1/24"
    assert network.dhcp_enabled is True


def test_lan_network_allows_missing_optional_listing_fields():
    """LanNetwork reports absent optional controller fields as None."""
    network = LanNetwork(
        {
            "id": "network-2",
            "name": "No DHCP",
            "purpose": "interface",
        }
    )

    assert network.vlan_id is None
    assert network.gateway_subnet is None
    assert network.dhcp_enabled is None
