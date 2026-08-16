"""Tests fuer die reine FRITZ!OS-WebUI-Datenaufbereitung."""

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "custom_components" / "fritzsync_network"))

from fritzbox_web import fixed_ipv4_assignment


class FritzBoxWebTests(unittest.TestCase):
    def test_static_dhcp_is_fixed_assignment(self):
        self.assertTrue(fixed_ipv4_assignment({"static_dhcp": "1"}))
        self.assertFalse(fixed_ipv4_assignment({"static_dhcp": "0"}))

    def test_nested_camel_case_field(self):
        self.assertTrue(fixed_ipv4_assignment({"ipv4": {"alwaysAssign": True}}))

    def test_missing_field_is_unknown(self):
        self.assertIsNone(fixed_ipv4_assignment({"name": "NUC"}))


if __name__ == "__main__":
    unittest.main()
