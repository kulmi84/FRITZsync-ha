"""Kleine Pi-hole-v6-Anbindung fuer verwaltete lokale DNS-Eintraege."""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import quote
from typing import Any


class PiholeApiError(RuntimeError):
    """Fehler bei Anmeldung oder Schreiben ueber die Pi-hole-API."""


def dns_name(value: str) -> str:
    """Erzeugt exakt wie FRITZSync ein DNS-taugliches Host-Label."""
    replacements = {
        "ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
        "Ä": "ae", "Ö": "oe", "Ü": "ue",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9-]+", "-", value)
    return re.sub(r"-+", "-", value).strip("-")[:63]


def fqdn(name: str, domain: str) -> str:
    """Verbindet normalisierten Geraetenamen und lokale Domain."""
    label = dns_name(name)
    suffix = str(domain or "").strip().strip(".").lower()
    if not label or not suffix:
        raise PiholeApiError("Gerätename oder lokale DNS-Domain ist leer")
    return f"{label}.{suffix}"


def records_from_response(payload: object) -> list[str]:
    """Liest dns.hosts aus der Antwort von GET /api/config/dns/hosts."""
    if not isinstance(payload, dict):
        return []
    config = payload.get("config")
    if not isinstance(config, dict):
        return []
    dns = config.get("dns")
    if not isinstance(dns, dict):
        return []
    hosts = dns.get("hosts")
    return [" ".join(str(item).split()) for item in hosts] if isinstance(hosts, list) else []


class PiholeClient:
    """Synchronisiert genau einen lokalen DNS-Eintrag ueber die Pi-hole-v6-API."""

    def __init__(self, address: str, password: str, domain: str, timeout: int = 15) -> None:
        address = str(address).strip().rstrip("/")
        if not address.startswith(("http://", "https://")):
            address = f"http://{address}"
        self.base_url = f"{address}/api"
        self.password = password
        self.domain = domain
        self.timeout = timeout

    def _request(self, session: Any, method: str, path: str, **kwargs):
        response = session.request(
            method, f"{self.base_url}{path}", timeout=self.timeout, **kwargs
        )
        if response.status_code >= 400:
            detail = response.text[:300].strip() or response.reason
            raise PiholeApiError(f"Pi-hole API: HTTP {response.status_code}: {detail}")
        return response

    def sync_rename(self, ip: str, old_name: str, new_name: str) -> str:
        """Ersetzt nur den exakten alten lokalen DNS-Namen."""
        import requests

        ip = str(ip or "").strip()
        if not ip:
            raise PiholeApiError("Das Gerät besitzt keine IP-Adresse")
        old_fqdn = fqdn(old_name, self.domain)
        new_fqdn = fqdn(new_name, self.domain)
        desired = f"{ip} {new_fqdn}"

        with requests.Session() as session:
            auth = self._request(
                session, "POST", "/auth", json={"password": self.password}
            ).json()
            api_session = auth.get("session", {}) if isinstance(auth, dict) else {}
            if not api_session.get("valid") or not api_session.get("sid"):
                raise PiholeApiError("Anmeldung an Pi-hole fehlgeschlagen")
            session.headers["X-FTL-SID"] = str(api_session["sid"])

            payload = self._request(session, "GET", "/config/dns/hosts").json()
            records = records_from_response(payload)
            if desired in records and old_fqdn == new_fqdn:
                return desired

            old_records = [
                record for record in records
                if len(record.split()) >= 2 and old_fqdn in record.split()[1:]
            ]
            conflicting = [
                record for record in records
                if len(record.split()) >= 2
                and new_fqdn in record.split()[1:]
                and record != desired
                and record not in old_records
            ]
            if conflicting:
                raise PiholeApiError(
                    f"DNS-Name {new_fqdn} ist bereits einer anderen IP zugeordnet"
                )

            for record in old_records:
                encoded = quote(record, safe="")
                self._request(
                    session, "DELETE", f"/config/dns/hosts/{encoded}?restart=false"
                )

            if desired not in records:
                encoded = quote(desired, safe="")
                self._request(
                    session, "PUT", f"/config/dns/hosts/{encoded}?restart=true"
                )
            return desired
