"""Tests fuer die Pi-hole-Namens- und Antwortaufbereitung."""

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "custom_components" / "fritzsync_network"))

from pihole import dns_name, fqdn, records_from_response


class PiholeTests(unittest.TestCase):
    def test_dns_name_matches_fritzsync(self):
        self.assertEqual(dns_name("Küche & Öl"), "kueche-oel")
        self.assertEqual(dns_name("NAS04_VM01"), "nas04-vm01")

    def test_fqdn_uses_existing_domain(self):
        self.assertEqual(fqdn("AC-Keller", ".fritz.box."), "ac-keller.fritz.box")

    def test_records_from_config_response(self):
        payload = {"config": {"dns": {"hosts": ["192.168.9.3   ac-keller.fritz.box"]}}}
        self.assertEqual(
            records_from_response(payload), ["192.168.9.3 ac-keller.fritz.box"]
        )


if __name__ == "__main__":
    unittest.main()
