"""Undokumentierte FRITZ!OS-WebUI-Helfer fuer Funktionen ohne TR-064-API."""

from __future__ import annotations

import hashlib
import ipaddress
import time
import xml.etree.ElementTree as ET
from typing import Any


class FritzBoxWebError(RuntimeError):
    """Fehler beim Zugriff auf die lokale FRITZ!Box-WebUI."""


def _truth(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"1", "true", "yes", "on", "checked"}:
            return True
        if text in {"0", "false", "no", "off", ""}:
            return False
    return None


def fixed_ipv4_assignment(device: dict[str, Any]) -> bool | None:
    """Liest das WebUI-Feld hinter „IPv4-Adresse dauerhaft zuweisen“."""
    candidates = {
        "static_dhcp", "staticdhcp", "static_dhcp_v4", "staticdhcpv4",
        "dhcp_fixed", "dhcpfixed", "ipv4_fixed", "ipv4fixed",
        "fixed_ipv4", "fixedipv4", "always_assign", "alwaysassign",
    }

    def walk(value: Any) -> bool | None:
        if isinstance(value, dict):
            for key, item in value.items():
                normalized = str(key).replace("-", "_").lower()
                compact = normalized.replace("_", "")
                if normalized in candidates or compact in candidates:
                    result = _truth(item)
                    if result is not None:
                        return result
            for item in value.values():
                result = walk(item)
                if result is not None:
                    return result
        elif isinstance(value, list):
            for item in value:
                result = walk(item)
                if result is not None:
                    return result
        return None

    return walk(device)


def _walk_values(value: Any):
    """Durchlaeuft rekursiv alle Schluessel/Wert-Paare eines netDev-Objekts."""
    if isinstance(value, dict):
        for key, item in value.items():
            yield key, item
            yield from _walk_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_values(item)


def webui_ipv4(device: dict[str, Any]) -> str:
    """Liest die autoritative IPv4-Adresse aus einem WebUI-netDev-Objekt."""
    candidates_found: list[str] = []
    for wanted in ("ip", "ipv4", "ip_address", "address", "addr"):
        for key, value in _walk_values(device):
            if str(key).casefold() != wanted:
                continue
            candidates = value if isinstance(value, list) else [value]
            for candidate in candidates:
                try:
                    address = ipaddress.ip_address(str(candidate).strip())
                except ValueError:
                    continue
                if address.version == 4 and not address.is_unspecified:
                    text = str(address)
                    if text not in candidates_found:
                        candidates_found.append(text)
    # Das Router-Objekt kann neben seiner LAN-Adresse auch die oeffentliche
    # WAN-Adresse enthalten. Fuer ein Heimnetzgeraet ist die private Adresse
    # die richtige; die WAN-Adresse darf keinen eigenen Netzfilter erzeugen.
    return next(
        (value for value in candidates_found if ipaddress.ip_address(value).is_private),
        candidates_found[0] if candidates_found else "",
    )


def webui_name(device: dict[str, Any]) -> str:
    """Liest den in Heimnetz -> Netzwerk sichtbaren Namen."""
    for key in ("name", "friendly_name", "hostname", "host_name", "neighbour_name"):
        value = device.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def webui_active(device: dict[str, Any]) -> bool | None:
    """Liest den Onlinestatus; ``None`` bedeutet: WebUI lieferte kein Flag."""
    positive = {"active", "online", "is_active", "connected", "is_connected"}
    states = {"status", "state", "connection_state"}
    found = False
    for key, value in _walk_values(device):
        normalized = str(key).strip().casefold()
        if normalized in positive:
            parsed = _truth(value)
            if parsed is not None:
                found = True
                if parsed:
                    return True
        elif normalized in states:
            text = str(value).strip().casefold()
            if text in {"online", "active", "connected", "verbunden", "up"}:
                return True
            if text in {"offline", "inactive", "disconnected", "getrennt", "down"}:
                found = True
    return False if found else None


class FritzBoxWebClient:
    """Kleiner lokaler Client fuer FRITZ!OS 8.x."""

    def __init__(self, address: str, username: str, password: str, use_tls: bool) -> None:
        import requests

        host = address.strip().rstrip("/")
        if host.startswith(("http://", "https://")):
            self.base = host
        else:
            self.base = f"{'https' if use_tls else 'http'}://{host}"
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.verify = False
        self.sid = ""

    def login(self) -> None:
        response = self.session.get(f"{self.base}/login_sid.lua", params={"version": 2}, timeout=15)
        response.raise_for_status()
        root = ET.fromstring(response.text)
        challenge = root.findtext("Challenge", "")
        if challenge.startswith("2$"):
            parts = challenge.split("$")
            if len(parts) != 5:
                raise FritzBoxWebError("Unbekanntes FRITZ!OS-Anmeldeverfahren")
            first = hashlib.pbkdf2_hmac("sha256", self.password.encode(), bytes.fromhex(parts[2]), int(parts[1]))
            second = hashlib.pbkdf2_hmac("sha256", first, bytes.fromhex(parts[4]), int(parts[3]))
            answer = f"{parts[4]}${second.hex()}"
        else:
            answer = f"{challenge}-{hashlib.md5((challenge + '-' + self.password).encode('utf-16le')).hexdigest()}"
        response = self.session.post(
            f"{self.base}/login_sid.lua", params={"version": 2},
            data={"username": self.username, "response": answer}, timeout=15,
        )
        response.raise_for_status()
        self.sid = ET.fromstring(response.text).findtext("SID", "")
        if not self.sid or self.sid == "0000000000000000":
            raise FritzBoxWebError("FRITZ!Box-WebUI-Anmeldung fehlgeschlagen")

    def devices(self) -> list[dict[str, Any]]:
        if not self.sid:
            self.login()
        response = self.session.post(
            f"{self.base}/data.lua", params={"sid": self.sid},
            data={"xhr": 1, "xhrId": "all", "page": "netDev", "lang": "de"}, timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        found: list[dict[str, Any]] = []

        def walk(value: Any) -> None:
            if isinstance(value, dict):
                keys = {str(key).lower() for key in value}
                if keys & {"mac", "macaddress", "mac_address"}:
                    found.append(value)
                for item in value.values():
                    walk(item)
            elif isinstance(value, list):
                for item in value:
                    walk(item)
        walk(payload)
        return found

    def authoritative_hosts(
        self, tr064_hosts: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Erzeugt Hostzeilen mit WebUI-Identitaet und TR-064-Zusatzfeldern.

        FRITZ!OS liefert ueber TR-064 auch historische bzw. provisorische
        Datensaetze. Deshalb stammen MAC, IPv4 und sichtbarer Name ausschliesslich
        aus ``netDev``. TR-064 darf nur Zusatzfelder derselben exakten MAC
        beisteuern.
        """
        tr_by_mac: dict[str, dict[str, Any]] = {}
        for raw in tr064_hosts or []:
            key = self._mac(raw)
            if key:
                current = tr_by_mac.get(key)
                if current is None or bool(raw.get("Active")):
                    tr_by_mac[key] = raw

        # FRITZ!OS kann mehrere netDev-Unterobjekte fuer dieselbe IPv4 liefern
        # (z. B. temporaere Windows-/IPv6-Identitaeten). Genau wie FRITZSync
        # darf daraus nur eine autoritative Geraetezeile entstehen.
        selected: dict[str, tuple[tuple[int, int, int, int], dict[str, Any]]] = {}
        for device in self.devices():
            mac = self._mac(device)
            ip = webui_ipv4(device)
            name = webui_name(device)
            uid = str(device.get("UID") or device.get("uid") or "").strip()
            if not mac or not uid or not ip or not name:
                continue
            raw = dict(tr_by_mac.get(mac, {}))
            raw["MACAddress"] = ":".join(mac[i:i + 2] for i in range(0, 12, 2)).upper()
            raw["IPAddress"] = ip
            raw["X_AVM-DE_FriendlyName"] = name
            raw["HostName"] = name
            active = webui_active(device)
            if active is not None:
                raw["Active"] = active
            generated = name.casefold().startswith("pc-")
            first_octet = int(mac[:2], 16)
            quality = (
                int(bool(raw.get("Active"))),
                int(not generated),
                int(mac in tr_by_mac),
                int(not (first_octet & 0x02)),
            )
            current = selected.get(ip)
            if current is None or quality > current[0]:
                selected[ip] = (quality, raw)
        rows = [item[1] for item in selected.values()]
        if not rows:
            raise FritzBoxWebError("FRITZ!Box-WebUI lieferte keine IPv4-Geräte")
        return rows

    @staticmethod
    def _mac(device: dict[str, Any]) -> str:
        for key in ("mac", "MAC", "macAddress", "MACAddress", "mac_address"):
            if device.get(key):
                value = "".join(ch for ch in str(device[key]) if ch.isalnum()).lower()
                if len(value) != 12 or any(ch not in "0123456789abcdef" for ch in value):
                    continue
                # Multicast-, Null- und Broadcastadressen sind keine stabile
                # Geraeteidentitaet und tauchen in verschachtelten netDev-
                # Objekten gelegentlich faelschlich als MAC auf.
                if int(value[:2], 16) & 0x01 or value in {"000000000000", "ffffffffffff"}:
                    continue
                return value
        return ""

    def device(self, mac: str) -> dict[str, Any] | None:
        wanted = "".join(ch for ch in mac if ch.isalnum()).lower()
        return next((item for item in self.devices() if self._mac(item) == wanted), None)

    def detail(self, device: dict[str, Any]) -> dict[str, Any]:
        """Liest die Detaildaten eines WebUI-Geräts, sofern eine UID existiert."""
        uid = device.get("UID") or device.get("uid")
        if not uid:
            return device
        response = self.session.get(
            f"{self.base}/api/v0/generic/landevice/landevice/{uid}",
            headers={"Authorization": f"AVM-SID {self.sid}"}, timeout=15,
        )
        if response.status_code >= 400:
            return device
        payload = response.json()
        return {**device, **payload} if isinstance(payload, dict) else device

    def rename(self, mac: str, new_name: str) -> None:
        device = self.device(mac)
        if not device:
            raise FritzBoxWebError(f"Gerät {mac} wurde in der FRITZ!Box-WebUI nicht gefunden")
        uid = device.get("UID") or device.get("uid")
        if not uid:
            raise FritzBoxWebError(f"FRITZ!Box lieferte keine Geräte-ID für {mac}")
        response = self.session.put(
            f"{self.base}/api/v0/generic/landevice/landevice/{uid}",
            headers={
                "Authorization": f"AVM-SID {self.sid}",
                "Content-Type": "application/json",
                "Origin": self.base,
                "Referer": f"{self.base}/?sid={self.sid}",
            },
            json={
                "device_class_user": device.get("device_class_user") or "Generic",
                "friendly_name": new_name,
                "rrd": device.get("rrd") or "0",
            }, timeout=20,
        )
        response.raise_for_status()
        actual = ""
        for _ in range(8):
            verified = self.device(mac)
            actual = str((verified or {}).get("name") or (verified or {}).get("friendly_name") or "").strip()
            if actual == new_name:
                return
            time.sleep(1)
        raise FritzBoxWebError(
            f"FRITZ!Box hat den Namen nicht bestätigt (gemeldet: {actual or 'leer'})"
        )

    def delete_device(self, mac: str) -> None:
        """Loescht einen bekannten Host ueber dieselbe API wie die Weboberflaeche."""
        device = self.device(mac)
        if not device:
            raise FritzBoxWebError(f"Gerät {mac} wurde in der FRITZ!Box-WebUI nicht gefunden")
        uid = device.get("UID") or device.get("uid")
        if not uid:
            raise FritzBoxWebError(f"FRITZ!Box lieferte keine Geräte-ID für {mac}")
        response = self.session.delete(
            f"{self.base}/api/v0/generic/landevice/landevice/{uid}",
            headers={
                "Authorization": f"AVM-SID {self.sid}",
                "Origin": self.base,
                "Referer": f"{self.base}/?sid={self.sid}",
            }, timeout=20,
        )
        response.raise_for_status()
