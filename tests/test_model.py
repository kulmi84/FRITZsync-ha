"""Tests for normalization and topology helpers."""

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "custom_components" / "fritzsync_network"))

from model import attach_mesh_parents, build_mesh, normalize_host, normalize_mac


class ModelTests(unittest.TestCase):
    def test_normalize_mac(self):
        self.assertEqual(normalize_mac("aa-bb-cc-dd-ee-ff"), "AA:BB:CC:DD:EE:FF")

    def test_normalize_host(self):
        host = normalize_host({
            "Index": 3, "HostName": "Laptop", "IPAddress": "192.168.178.20",
            "MACAddress": "aa:bb:cc:dd:ee:ff", "Active": "1",
            "InterfaceType": "802.11", "X_AVM-DE_Disallow": True,
        })
        self.assertEqual(host["name"], "Laptop")
        self.assertEqual(host["connection"], "wlan")
        self.assertTrue(host["active"])
        self.assertTrue(host["blocked"])

    def test_mesh_normalization_and_parent(self):
        raw = {"nodes": [
            {"uid": "router", "device_name": "FRITZ!Box", "device_mac_address": "00:00:00:00:00:01", "node_interfaces": [{"type": "WLAN", "node_links": [{"uid": "l1", "node_1_uid": "router", "node_2_uid": "client", "state": "CONNECTED"}]}]},
            {"uid": "client", "device_name": "Laptop", "device_mac_address": "AA:BB:CC:DD:EE:FF", "node_interfaces": []},
        ]}
        nodes, links = build_mesh(raw)
        hosts = [normalize_host({"HostName": "Laptop", "MACAddress": "AA:BB:CC:DD:EE:FF"})]
        attach_mesh_parents(hosts, nodes, links)
        self.assertEqual(hosts[0]["mesh_parent"], "router")


if __name__ == "__main__":
    unittest.main()
