"""Tests fuer die Pi-hole-Namens- und Antwortaufbereitung."""

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "custom_components" / "fritzsync_network"))

from pihole import (
    PiholeApiError,
    dns_name,
    fqdn,
    normalize_record,
    rename_candidates,
    records_from_response,
    split_record,
)


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

    def test_normalize_manual_record_with_aliases(self):
        self.assertEqual(
            normalize_record(
                "192.168.9.108",
                "Samsung-SM600-Tablet.Fritz.Box tablet.fritz.box",
            ),
            "192.168.9.108 samsung-sm600-tablet.fritz.box tablet.fritz.box",
        )

    def test_rejects_invalid_manual_record(self):
        with self.assertRaises(PiholeApiError):
            normalize_record("192.168.9.999", "host.fritz.box")
        with self.assertRaises(PiholeApiError):
            normalize_record("192.168.9.10", "ungültig!.fritz.box")

    def test_split_manual_record(self):
        self.assertEqual(
            split_record("192.168.9.201 wireguard-s20-dk.fritz.box"),
            {
                "record": "192.168.9.201 wireguard-s20-dk.fritz.box",
                "ip": "192.168.9.201",
                "names": "wireguard-s20-dk.fritz.box",
            },
        )

    def test_rename_finds_existing_record_by_same_ip(self):
        records = [
            "192.168.9.12 nuc-alt.fritz.box",
            "192.168.9.13 anderes.fritz.box",
        ]
        self.assertEqual(
            rename_candidates(records, "192.168.9.12", "nuc.fritz.box", "fritz.box"),
            ["192.168.9.12 nuc-alt.fritz.box"],
        )


if __name__ == "__main__":
    unittest.main()
