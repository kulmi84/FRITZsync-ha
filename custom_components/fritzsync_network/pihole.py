"""Kleine Pi-hole-v6-Anbindung fuer verwaltete lokale DNS-Eintraege."""

from __future__ import annotations

import re
import unicodedata
import ipaddress
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


def normalize_record(ip: str, names: str) -> str:
    """Validiert und normalisiert eine Pi-hole-Hostzeile."""
    ip_text = str(ip or "").strip()
    try:
        ipaddress.ip_address(ip_text)
    except ValueError as err:
        raise PiholeApiError(f"Ungültige IP-Adresse: {ip_text}") from err
    tokens = [item.strip().lower().rstrip(".") for item in str(names or "").split() if item.strip()]
    if not tokens:
        raise PiholeApiError("Mindestens ein DNS-Name ist erforderlich")
    pattern = re.compile(r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
    invalid = next((name for name in tokens if not pattern.fullmatch(name)), None)
    if invalid:
        raise PiholeApiError(f"Ungültiger DNS-Name: {invalid}")
    return " ".join([ip_text, *tokens])


def split_record(record: str) -> dict[str, str]:
    """Zerlegt eine Pi-hole-Hostzeile fuer die Dashboard-Karte."""
    parts = str(record or "").split()
    return {
        "record": " ".join(parts),
        "ip": parts[0] if parts else "",
        "names": " ".join(parts[1:]) if len(parts) > 1 else "",
    }


def rename_candidates(
    records: list[str], ip: str, old_fqdn: str, domain: str
) -> list[str]:
    """Findet den zu überschreibenden DNS-Eintrag über Namen oder Geräte-IP."""
    suffix = "." + str(domain or "").strip().strip(".").lower()
    result: list[str] = []
    for record in records:
        parts = record.split()
        if len(parts) < 2:
            continue
        names = [name.lower().rstrip(".") for name in parts[1:]]
        exact_name = old_fqdn.lower().rstrip(".") in names
        same_device_ip = parts[0] == ip and any(
            name.endswith(suffix) or name == suffix.removeprefix(".")
            for name in names
        )
        if exact_name or same_device_ip:
            result.append(record)
    return result


class PiholeClient:
    """Synchronisiert genau einen lokalen DNS-Eintrag ueber die Pi-hole-v6-API."""

    def __init__(self, address: str, password: str, domain: str, timeout: int = 15) -> None:
        address = str(address).strip().rstrip("/")
        if not address.startswith(("http://", "https://")):
            address = f"https://{address}"
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

    def _login(self):
        """Erzeugt eine angemeldete requests-Session."""
        import requests

        session = requests.Session()
        session.verify = False
        try:
            auth = self._request(
                session, "POST", "/auth", json={"password": self.password}
            ).json()
            api_session = auth.get("session", {}) if isinstance(auth, dict) else {}
            if not api_session.get("valid") or not api_session.get("sid"):
                raise PiholeApiError("Anmeldung an Pi-hole fehlgeschlagen")
            session.headers["X-FTL-SID"] = str(api_session["sid"])
            return session
        except Exception:
            session.close()
            raise

    def _logout(self, session: Any) -> None:
        """Gibt den belegten Pi-hole-API-Sitzplatz zuverlässig wieder frei."""
        try:
            self._request(session, "DELETE", "/auth")
        except Exception:
            pass
        finally:
            session.close()

    def list_records(self) -> list[str]:
        """Liest alle lokalen DNS-Hostzeilen aus Pi-hole 6."""
        session = self._login()
        try:
            payload = self._request(session, "GET", "/config/dns/hosts").json()
            return records_from_response(payload)
        finally:
            self._logout(session)

    def add_record(self, ip: str, names: str) -> str:
        """Legt eine manuelle Hostzeile an."""
        desired = normalize_record(ip, names)
        session = self._login()
        try:
            records = records_from_response(
                self._request(session, "GET", "/config/dns/hosts").json()
            )
            if desired in records:
                return desired
            desired_names = set(desired.split()[1:])
            conflict = next(
                (record for record in records if desired_names.intersection(record.split()[1:])),
                None,
            )
            if conflict:
                raise PiholeApiError(f"DNS-Name bereits vorhanden: {conflict}")
            self._request(
                session, "PUT",
                f"/config/dns/hosts/{quote(desired, safe='')}?restart=true",
            )
            return desired
        finally:
            self._logout(session)

    def delete_record(self, record: str, restart: bool = True) -> None:
        """Löscht exakt eine vorhandene Hostzeile."""
        normalized = " ".join(str(record or "").split())
        if not normalized:
            raise PiholeApiError("Der zu löschende Eintrag ist leer")
        session = self._login()
        try:
            self._request(
                session, "DELETE",
                f"/config/dns/hosts/{quote(normalized, safe='')}?restart={'true' if restart else 'false'}",
            )
        finally:
            self._logout(session)

    def replace_record(self, old_record: str, ip: str, names: str) -> str:
        """Ersetzt eine Hostzeile und startet DNS erst nach dem neuen Eintrag."""
        old = " ".join(str(old_record or "").split())
        desired = normalize_record(ip, names)
        if old == desired:
            return desired
        session = self._login()
        try:
            records = records_from_response(
                self._request(session, "GET", "/config/dns/hosts").json()
            )
            if old not in records:
                raise PiholeApiError("Der ursprüngliche Pi-hole-Eintrag existiert nicht mehr")
            desired_names = set(desired.split()[1:])
            conflict = next(
                (record for record in records if record != old and desired_names.intersection(record.split()[1:])),
                None,
            )
            if conflict:
                raise PiholeApiError(f"DNS-Name bereits vorhanden: {conflict}")
            self._request(
                session, "DELETE",
                f"/config/dns/hosts/{quote(old, safe='')}?restart=false",
            )
            try:
                self._request(
                    session, "PUT",
                    f"/config/dns/hosts/{quote(desired, safe='')}?restart=true",
                )
            except Exception:
                # Best effort rollback, damit ein Übertragungsfehler den alten
                # DNS-Eintrag nicht still verschwinden lässt.
                self._request(
                    session, "PUT",
                    f"/config/dns/hosts/{quote(old, safe='')}?restart=true",
                )
                raise
            return desired
        finally:
            self._logout(session)

    def sync_all(self, desired_records: list[str]) -> dict[str, int]:
        """Gleicht alle übergebenen Geräte mit lokalen Pi-hole-DNS-Zeilen ab."""
        desired = list(dict.fromkeys(" ".join(item.split()).lower() for item in desired_records))
        desired = [item for item in desired if len(item.split()) >= 2]
        desired_ips = {item.split()[0] for item in desired}
        session = self._login()
        try:
            records = records_from_response(
                self._request(session, "GET", "/config/dns/hosts").json()
            )
            deletes: list[str] = []
            adds: list[str] = []
            suffix = "." + self.domain.strip().strip(".").lower()
            for target in desired:
                parts = target.split()
                ip, names = parts[0], set(parts[1:])
                for record in records:
                    old_parts = record.lower().split()
                    if len(old_parts) < 2 or record in deletes or record.lower() == target:
                        continue
                    old_names = set(old_parts[1:])
                    same_device = old_parts[0] == ip and any(
                        name.endswith(suffix) for name in old_names
                    )
                    name_conflict = (
                        bool(names.intersection(old_names))
                        and old_parts[0] not in desired_ips
                    )
                    if same_device or name_conflict:
                        deletes.append(record)
                if target not in {record.lower() for record in records}:
                    adds.append(target)

            operations = [("DELETE", item) for item in deletes] + [
                ("PUT", item) for item in adds
            ]
            for index, (method, record) in enumerate(operations):
                restart = "true" if index == len(operations) - 1 else "false"
                self._request(
                    session, method,
                    f"/config/dns/hosts/{quote(record, safe='')}?restart={restart}",
                )
            return {"devices": len(desired), "added": len(adds), "deleted": len(deletes)}
        finally:
            self._logout(session)

    def sync_rename(self, ip: str, old_name: str, new_name: str) -> str:
        """Ersetzt nur den exakten alten lokalen DNS-Namen."""
        ip = str(ip or "").strip()
        if not ip:
            raise PiholeApiError("Das Gerät besitzt keine IP-Adresse")
        old_fqdn = fqdn(old_name, self.domain)
        new_fqdn = fqdn(new_name, self.domain)
        desired = f"{ip} {new_fqdn}"

        session = self._login()
        try:
            payload = self._request(session, "GET", "/config/dns/hosts").json()
            records = records_from_response(payload)
            if desired in records and old_fqdn == new_fqdn:
                return desired

            old_records = rename_candidates(records, ip, old_fqdn, self.domain)
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
        finally:
            self._logout(session)
