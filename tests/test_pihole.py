"""Tests fuer die Pi-hole-Namens- und Antwortaufbereitung."""

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "custom_components" / "fritzsync_network"))

from pihole import (
    PiholeClient,
    PiholeApiError,
    dns_name,
    fqdn,
    managed_record,
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

    def test_managed_record_contains_short_name_and_fqdn(self):
        self.assertEqual(
            managed_record("192.168.9.44", "NAS04-MD", "fritz.box"),
            "192.168.9.44 nas04-md nas04-md.fritz.box",
        )

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

    def test_logout_releases_api_seat(self):
        class Response:
            status_code = 204
            text = ""
            reason = ""

        class Session:
            def __init__(self):
                self.calls = []
                self.closed = False

            def request(self, method, url, timeout, **kwargs):
                self.calls.append((method, url))
                return Response()

            def close(self):
                self.closed = True

        client = PiholeClient("https://192.168.9.252", "pw", "fritz.box")
        session = Session()
        client._logout(session)
        self.assertEqual(session.calls, [("DELETE", "https://192.168.9.252/api/auth")])
        self.assertTrue(session.closed)

    def test_add_record_uses_pihole_v6_hosts_endpoint(self):
        class Response:
            status_code = 200
            text = ""
            reason = ""

            def __init__(self, payload=None):
                self.payload = payload or {}

            def json(self):
                return self.payload

        class Session:
            def __init__(self):
                self.calls = []
                self.closed = False

            def request(self, method, url, timeout, **kwargs):
                self.calls.append((method, url))
                if method == "GET":
                    return Response({"config": {"dns": {"hosts": []}}})
                return Response()

            def close(self):
                self.closed = True

        client = PiholeClient("https://192.168.9.252", "pw", "fritz.box")
        session = Session()
        client._login = lambda: session
        result = client.add_record("192.168.9.178", "mk-esx20.fritz.box")
        self.assertEqual(result, "192.168.9.178 mk-esx20.fritz.box")
        self.assertEqual(session.calls[0], (
            "GET", "https://192.168.9.252/api/config/dns/hosts"
        ))
        self.assertEqual(session.calls[1], (
            "PUT",
            "https://192.168.9.252/api/config/dns/hosts/"
            "192.168.9.178%20mk-esx20.fritz.box?restart=true",
        ))
        self.assertEqual(session.calls[-1], (
            "DELETE", "https://192.168.9.252/api/auth"
        ))
        self.assertTrue(session.closed)

    def test_sync_all_upgrades_fqdn_only_and_keeps_alias(self):
        class Response:
            status_code = 200
            text = ""
            reason = ""

            def __init__(self, payload=None):
                self.payload = payload or {}

            def json(self):
                return self.payload

        class Session:
            def __init__(self):
                self.calls = []
                self.closed = False

            def request(self, method, url, timeout, **kwargs):
                self.calls.append((method, url))
                if method == "GET":
                    return Response({
                        "config": {"dns": {"hosts": [
                            "192.168.9.44 nas04-md.fritz.box storage-alias"
                        ]}}
                    })
                return Response()

            def close(self):
                self.closed = True

        client = PiholeClient("https://192.168.9.252", "pw", "fritz.box")
        session = Session()
        client._login = lambda: session
        result = client.sync_all(["192.168.9.44 nas04-md.fritz.box"])

        self.assertEqual(result, {"devices": 1, "added": 1, "deleted": 1})
        self.assertIn((
            "DELETE",
            "https://192.168.9.252/api/config/dns/hosts/"
            "192.168.9.44%20nas04-md.fritz.box%20storage-alias?restart=false",
        ), session.calls)
        self.assertIn((
            "PUT",
            "https://192.168.9.252/api/config/dns/hosts/"
            "192.168.9.44%20nas04-md%20nas04-md.fritz.box%20storage-alias?restart=true",
        ), session.calls)
        self.assertTrue(session.closed)

    def test_sync_rename_removes_old_short_name_and_keeps_alias(self):
        class Response:
            status_code = 200
            text = ""
            reason = ""

            def __init__(self, payload=None):
                self.payload = payload or {}

            def json(self):
                return self.payload

        class Session:
            def __init__(self):
                self.calls = []
                self.closed = False

            def request(self, method, url, timeout, **kwargs):
                self.calls.append((method, url))
                if method == "GET":
                    return Response({
                        "config": {"dns": {"hosts": [
                            "192.168.9.44 nas04-alt nas04-alt.fritz.box storage-alias"
                        ]}}
                    })
                return Response()

            def close(self):
                self.closed = True

        client = PiholeClient("https://192.168.9.252", "pw", "fritz.box")
        session = Session()
        client._login = lambda: session
        result = client.sync_rename("192.168.9.44", "nas04-alt", "nas04-md")

        self.assertEqual(
            result,
            "192.168.9.44 nas04-md nas04-md.fritz.box storage-alias",
        )
        self.assertIn((
            "PUT",
            "https://192.168.9.252/api/config/dns/hosts/"
            "192.168.9.44%20nas04-md%20nas04-md.fritz.box%20storage-alias?restart=true",
        ), session.calls)
        self.assertTrue(session.closed)


if __name__ == "__main__":
    unittest.main()
