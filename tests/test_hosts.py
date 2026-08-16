"""Tests for FRITZ!Box host normalization."""

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "custom_components" / "fritzsync_network"))

from hosts import build_hosts, normalize_host, normalize_mac, summarize


class HostTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
