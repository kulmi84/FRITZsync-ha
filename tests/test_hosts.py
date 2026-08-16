"""Tests for FRITZ!Box host normalization."""

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "custom_components" / "fritzsync_network"))

from hosts import (
    apply_fritzsync_fields,
    build_hosts,
    merge_ptr_maps,
    normalize_host,
    normalize_mac,
    summarize,
)


class HostTests(unittest.TestCase):
    def test_merge_ptr_maps_prefers_first_resolver_and_deduplicates(self):
        merged = merge_ptr_maps(
            {"192.0.2.250": ["switch.fritz.box"]},
            {"192.0.2.250": ["old-name.fritz.box", "SWITCH.fritz.box"]},
        )
        self.assertEqual(
            merged["192.0.2.250"],
            ["switch.fritz.box", "old-name.fritz.box"],
        )

    def test_normalize_mac(self):
        self.assertEqual(normalize_mac("aa-bb-cc-dd-ee-ff"), "AA:BB:CC:DD:EE:FF")

    def test_normalize_host(self):
        host = normalize_host({
            "Index": 3,
            "HostName": "Laptop",
            "IPAddress": "192.168.178.20",
            "MACAddress": "aa:bb:cc:dd:ee:ff",
            "Active": "1",
            "InterfaceType": "802.11",
            "X_AVM-DE_Disallow": True,
        })
        self.assertEqual(host["name"], "Laptop")
        self.assertEqual(host["connection"], "wlan")
        self.assertTrue(host["active"])
        self.assertTrue(host["blocked"])

    def test_build_hosts_sorts_ip_and_summarizes(self):
        hosts = build_hosts([
            {"HostName": "Ten", "IPAddress": "192.168.178.10", "MACAddress": "00:00:00:00:00:10"},
            {"HostName": "Nine", "IPAddress": "192.168.178.9", "MACAddress": "00:00:00:00:00:09", "Active": True},
        ])
        self.assertEqual([host["name"] for host in hosts], ["Nine", "Ten"])
        self.assertEqual(summarize(hosts)["active"], 1)

    def test_fritzsync_network_ptr_and_comment_fields(self):
        hosts = build_hosts([
            {"HostName": "NAS", "IPAddress": "192.168.9.44", "MACAddress": "24:5E:BE:00:00:44"},
            {"HostName": "Guest", "IPAddress": "192.168.10.5", "MACAddress": "24:5E:BE:00:00:05"},
        ])
        apply_fritzsync_fields(
            hosts,
            {"192.168.9.44": ["nas.fritz.box", "nas.local"]},
            {"245ebe000044": "Vorratskeller"},
            "192.168.9.1",
        )
        self.assertEqual(hosts[0]["zone"], "Heimnetz")
        self.assertEqual(hosts[0]["network"], "192.168.9.0/24")
        self.assertEqual(hosts[0]["ptr1"], "nas.fritz.box")
        self.assertEqual(hosts[0]["ptr2"], "nas.local")
        self.assertEqual(hosts[0]["comment"], "Vorratskeller")
        self.assertEqual(hosts[1]["zone"], "Gast")

    def test_marks_inactive_placeholder_duplicates_but_keeps_active_device(self):
        hosts = build_hosts([
            {"Index": 1, "HostName": "PC-192-168-9-77", "IPAddress": "192.168.9.77", "MACAddress": "00:00:00:00:00:01"},
            {"Index": 2, "HostName": "mk-nb22", "IPAddress": "192.168.9.77", "MACAddress": "00:00:00:00:00:02", "Active": True},
            {"Index": 3, "HostName": "PC-192-168-9-77", "IPAddress": "192.168.9.77", "MACAddress": "00:00:00:00:00:03"},
        ])
        self.assertEqual(sum(host["stale_ip_duplicate"] for host in hosts), 2)
        self.assertFalse(next(host for host in hosts if host["active"])["stale_ip_duplicate"])

    def test_does_not_mark_entries_without_ip(self):
        hosts = build_hosts([
            {"HostName": "A", "MACAddress": "00:00:00:00:00:01"},
            {"HostName": "B", "MACAddress": "00:00:00:00:00:02"},
        ])
        self.assertFalse(any(host["stale_ip_duplicate"] for host in hosts))

    def test_filters_inactive_pc_mac_placeholder_without_ip(self):
        hosts = build_hosts([
            {
                "HostName": "PC-2C-71-FF-09-5A-27",
                "MACAddress": "2C:71:FF:09:5A:27",
                "Active": False,
            },
            {
                "HostName": "Drucker",
                "MACAddress": "00:11:22:33:44:55",
                "Active": False,
            },
        ])
        self.assertEqual([host["name"] for host in hosts], ["Drucker"])

    def test_keeps_active_pc_mac_name(self):
        hosts = build_hosts([
            {
                "HostName": "PC-2C-71-FF-09-5A-27",
                "IPAddress": "192.168.9.20",
                "MACAddress": "2C:71:FF:09:5A:27",
                "Active": True,
            }
        ])
        self.assertEqual(len(hosts), 1)


if __name__ == "__main__":
    unittest.main()
