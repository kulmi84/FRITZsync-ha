"""Tests fuer die reine FRITZ!OS-WebUI-Datenaufbereitung."""

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "custom_components" / "fritzsync_network"))

from fritzbox_web import FritzBoxWebClient, fixed_ipv4_assignment, webui_ipv4


class FritzBoxWebTests(unittest.TestCase):
    def test_static_dhcp_is_fixed_assignment(self):
        self.assertTrue(fixed_ipv4_assignment({"static_dhcp": "1"}))
        self.assertFalse(fixed_ipv4_assignment({"static_dhcp": "0"}))

    def test_nested_camel_case_field(self):
        self.assertTrue(fixed_ipv4_assignment({"ipv4": {"alwaysAssign": True}}))

    def test_missing_field_is_unknown(self):
        self.assertIsNone(fixed_ipv4_assignment({"name": "NUC"}))

    def test_private_device_ip_wins_over_nested_public_router_ip(self):
        device = {
            "wan": {"ip": "185.22.44.50"},
            "lan": {"ip": "192.168.9.1"},
        }
        self.assertEqual(webui_ipv4(device), "192.168.9.1")

    def test_webui_is_identity_master_and_drops_rows_without_ipv4(self):
        client = object.__new__(FritzBoxWebClient)
        client.devices = lambda: [
            {
                "UID": "landevice1",
                "mac": "AA:BB:CC:DD:EE:FF",
                "name": "Sichtbarer-Name",
                "ipv4": {"ip": "192.168.9.20"},
                "online": True,
            },
            {
                "UID": "landevice2",
                "mac": "2C:71:FF:09:5A:27",
                "name": "PC-2C-71-FF-09-5A-27",
            },
        ]
        rows = client.authoritative_hosts([
            {
                "MACAddress": "AA:BB:CC:DD:EE:FF",
                "IPAddress": "192.168.9.99",
                "HostName": "Alter-TR064-Name",
                "InterfaceType": "Ethernet",
            },
            {
                "MACAddress": "2C:71:FF:09:5A:27",
                "HostName": "PC-2C-71-FF-09-5A-27",
            },
        ])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["IPAddress"], "192.168.9.20")
        self.assertEqual(rows[0]["X_AVM-DE_FriendlyName"], "Sichtbarer-Name")
        self.assertEqual(rows[0]["InterfaceType"], "Ethernet")
        self.assertTrue(rows[0]["Active"])

    def test_duplicate_webui_rows_use_meaningful_device_for_same_ip(self):
        client = object.__new__(FritzBoxWebClient)
        client.devices = lambda: [
            {
                "UID": "landevice1",
                "mac": "38:22:E2:2B:09:84",
                "name": "MK-PC20",
                "ip": "192.0.2.134",
                "online": True,
            },
            {
                "UID": "landevice2",
                "mac": "9C:D0:8E:B2:88:A4",
                "name": "PC-2142F66D-D9EF",
                "ip": "192.0.2.134",
                "online": True,
            },
            {
                "UID": "landevice3",
                "mac": "09:35:D8:DA:24:E4",
                "name": "PC-ungueltige-multicast-mac",
                "ip": "192.0.2.134",
                "online": True,
            },
        ]
        rows = client.authoritative_hosts([
            {
                "MACAddress": "38:22:E2:2B:09:84",
                "IPAddress": "192.0.2.134",
                "HostName": "MK-PC20",
                "Active": True,
            }
        ])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["MACAddress"], "38:22:E2:2B:09:84")
        self.assertEqual(rows[0]["X_AVM-DE_FriendlyName"], "MK-PC20")


if __name__ == "__main__":
    unittest.main()
