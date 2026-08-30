"""Tests fuer die reine FRITZ!OS-WebUI-Datenaufbereitung."""

import sys
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parents[1] / "custom_components" / "fritzsync_network"))

from fritzbox_web import (
    FritzBoxWebClient,
    FritzBoxWebError,
    _AccessProfileParser,
    fixed_ipv4_assignment,
    webui_ipv4,
)


class FritzBoxWebTests(unittest.TestCase):
    PROFILE_HTML = """
      <table id="uiDevices">
        <tr><th>Gerät</th></tr>
        <tr>
          <td title="Kinder-iPad"><span>Kinder-iPad</span></td>
          <td><a class="js-device-block" data-blocked="false" data-uid="landevice8123">Sperren</a></td><td></td>
          <td><select name="profile:landevice4711">
            <option value="filtprof1">Standard</option>
            <option value="filtprof9" selected>Kinder</option>
            <option value="filtprof4">Gesperrt</option>
          </select></td><td></td>
        </tr>
      </table>
    """

    def test_access_profile_parser_reads_devices_and_all_profiles(self):
        parser = _AccessProfileParser()
        parser.feed(self.PROFILE_HTML)
        self.assertEqual(
            parser.profiles,
            {"filtprof1": "Standard", "filtprof9": "Kinder", "filtprof4": "Gesperrt"},
        )
        self.assertEqual(parser.devices, [{
            "name": "Kinder-iPad",
            "device_id": "landevice4711",
            "profile_id": "filtprof9",
            "block_id": "landevice8123",
            "blocked": "false",
        }])

    def test_access_profile_device_rejects_duplicate_name_fallback(self):
        snapshot = {"devices": [
            {"name": "iPhone", "device_id": "user1", "profile_id": "filtprof1"},
            {"name": "iPhone", "device_id": "user2", "profile_id": "filtprof2"},
        ]}
        with self.assertRaises(FritzBoxWebError):
            FritzBoxWebClient._access_profile_device(snapshot, "landevice9", "iPhone")

    def test_access_profile_device_uses_exact_block_id_before_duplicate_name(self):
        wanted = {
            "name": "iPhone", "device_id": "user1", "block_id": "landevice9",
            "profile_id": "filtprof1",
        }
        snapshot = {"devices": [
            wanted,
            {"name": "iPhone", "device_id": "user2", "block_id": "landevice8",
             "profile_id": "filtprof2"},
        ]}
        self.assertIs(
            FritzBoxWebClient._access_profile_device(snapshot, "landevice9", "iPhone"),
            wanted,
        )

    @patch("fritzbox_web.time.sleep", return_value=None)
    def test_set_access_profile_posts_and_verifies(self, _sleep):
        client = object.__new__(FritzBoxWebClient)
        client.base = "http://fritz.box"
        client.sid = "1234567890abcdef"
        client.session = Mock()
        client.session.post.return_value = Mock(raise_for_status=Mock())
        client.device = lambda _mac: {
            "UID": "landevice4711", "name": "Kinder-iPad",
        }
        initial = {
            "profiles": {"filtprof1": "Standard", "filtprof9": "Kinder"},
            "devices": [{
                "name": "Kinder-iPad", "device_id": "landevice4711",
                "profile_id": "filtprof1",
            }],
        }
        verified = {
            "profiles": initial["profiles"],
            "devices": [{
                "name": "Kinder-iPad", "device_id": "user8123",
                "profile_id": "filtprof9",
            }],
        }
        client.access_profiles = Mock(side_effect=[initial, verified])

        self.assertEqual(
            client.set_access_profile("AA:BB:CC:DD:EE:FF", "filtprof9"), "Kinder"
        )
        posted = client.session.post.call_args.kwargs["data"]
        self.assertEqual(posted["profile:landevice4711"], "filtprof9")
        self.assertIn("apply", posted)

    @patch("fritzbox_web.time.sleep", return_value=None)
    def test_set_internet_block_posts_and_verifies(self, _sleep):
        client = object.__new__(FritzBoxWebClient)
        client.base = "http://fritz.box"
        client.sid = "1234567890abcdef"
        client.session = Mock()
        client.session.post.return_value = Mock(raise_for_status=Mock())
        client.device = lambda _mac: {
            "UID": "landevice8123", "name": "Kinder-iPad",
        }
        initial_device = {
            "name": "Kinder-iPad", "device_id": "landevice4711",
            "profile_id": "filtprof9", "block_id": "landevice8123",
            "blocked": "false",
        }
        verified_device = {**initial_device, "blocked": "true"}
        client.access_profiles = Mock(side_effect=[
            {"profiles": {"filtprof9": "Kinder"}, "devices": [initial_device]},
            {"profiles": {"filtprof9": "Kinder"}, "devices": [verified_device]},
        ])

        client.set_internet_block("AA:BB:CC:DD:EE:FF", True)
        call = client.session.post.call_args
        self.assertEqual(call.args[0], "http://fritz.box/internet/kids_userlist.lua")
        self.assertEqual(call.kwargs["data"]["uid"], "landevice8123")
        self.assertEqual(call.kwargs["data"]["toBeBlocked"], "true")

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
