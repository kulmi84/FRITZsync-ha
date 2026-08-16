"""Aufbereitung der FRITZ!Box-Hostliste.

Dieses Modul enthaelt bewusst KEINE Home-Assistant- und keine
fritzconnection-Importe. Dadurch laesst sich die gesamte Aufbereitungs-
logik ohne laufende Home-Assistant-Instanz mit ``unittest`` pruefen.

Eingabe ist die Liste, die ``FritzHosts.get_hosts_attributes()`` liefert:
je Host ein Dictionary mit den ROHEN XML-Tagnamen der FRITZ!Box als
Schluessel (``IPAddress``, ``MACAddress``, ``X_AVM-DE_Speed`` usw.).

Wichtig und in fritzconnection 1.15.1 verifiziert: nur ``Index``,
``X_AVM-DE_Port`` und ``X_AVM-DE_Speed`` kommen als ``int`` an und nur
``Active``, ``X_AVM-DE_UpdateAvailable``, ``X_AVM-DE_Guest``,
``X_AVM-DE_VPN`` und ``X_AVM-DE_Disallow`` als ``bool``. Alle uebrigen
Felder - auch klar boolesche wie ``X_AVM-DE_IsMeshable`` oder
``X_AVM-DE_Priority`` - kommen als String ``"0"``/``"1"`` an. Deshalb
werden hier durchgaengig ``as_bool()``/``as_int()`` verwendet, die beide
Faelle abdecken. Fehlende Tags fehlen im Dictionary komplett, daher
ueberall ``.get()``.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import ipaddress
import os
import socket
import struct
from typing import Any

TRUE_STRINGS = {"1", "true", "yes", "on", "granted"}

# Verbindungsarten, wie die FRITZ!Box sie in ``InterfaceType`` meldet.
CONNECTION_LAN = "lan"
CONNECTION_WLAN = "wlan"
CONNECTION_POWERLINE = "powerline"
CONNECTION_UNKNOWN = "unbekannt"

WAN_GRANTED = "granted"
WAN_DENIED = "denied"

ADDRESS_SOURCE_STATIC = "Static"
ADDRESS_SOURCE_DHCP = "DHCP"


def as_bool(value: Any) -> bool:
    """Wandelt FRITZ!Box-Wahrheitswerte in echte ``bool`` um.

    Akzeptiert ``bool``, ``int`` und String-Varianten (``"0"``/``"1"``).
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in TRUE_STRINGS
    return False


def as_int(value: Any, default: int = 0) -> int:
    """Wandelt einen Wert in ``int`` um, ohne bei Muell zu scheitern."""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def normalize_mac(mac: Any) -> str:
    """Vereinheitlicht eine MAC-Adresse auf Grossbuchstaben mit Doppelpunkten."""
    if not mac:
        return ""
    raw = "".join(ch for ch in str(mac) if ch.isalnum()).upper()
    if len(raw) != 12:
        return str(mac).strip().upper()
    return ":".join(raw[i : i + 2] for i in range(0, 12, 2))


def mac_key(mac: Any) -> str:
    """Vergleichsschluessel fuer MAC-Adressen (klein, ohne Trennzeichen)."""
    if not mac:
        return ""
    return "".join(ch for ch in str(mac) if ch.isalnum()).lower()


def ip_sort_key(ip: Any) -> tuple[int, ...]:
    """Sortierschluessel, der IPv4-Adressen numerisch statt alphabetisch ordnet.

    ``192.168.178.9`` liegt damit korrekt vor ``192.168.178.10``.
    Nicht parsebare oder leere Adressen wandern ans Ende.
    """
    text = str(ip or "").strip()
    parts = text.split(".")
    if len(parts) != 4:
        return (1, 0, 0, 0, 0)
    try:
        octets = tuple(int(part) for part in parts)
    except ValueError:
        return (1, 0, 0, 0, 0)
    if any(octet < 0 or octet > 255 for octet in octets):
        return (1, 0, 0, 0, 0)
    return (0, *octets)


def connection_kind(interface_type: Any) -> str:
    """Ordnet ``InterfaceType`` einer der internen Verbindungsarten zu."""
    text = str(interface_type or "").strip().lower()
    if text.startswith("ethernet"):
        return CONNECTION_LAN
    if text.startswith("802.11"):
        return CONNECTION_WLAN
    if text.startswith("homeplug"):
        return CONNECTION_POWERLINE
    return CONNECTION_UNKNOWN


def connection_label(kind: str, port: int, guest: bool) -> str:
    """Erzeugt die Anzeigebezeichnung der Verbindung, z. B. ``"LAN 2"``."""
    if kind == CONNECTION_LAN:
        label = f"LAN {port}" if port else "LAN"
    elif kind == CONNECTION_WLAN:
        label = "WLAN"
    elif kind == CONNECTION_POWERLINE:
        label = "Powerline"
    else:
        label = "—"
    if guest and kind != CONNECTION_UNKNOWN:
        return f"{label} (Gast)"
    if guest:
        return "Gast"
    return label


def display_name(raw: dict[str, Any]) -> str:
    """Bester verfuegbarer Anzeigename des Geraets.

    Reihenfolge: vom Nutzer vergebener Name (FriendlyName) vor dem vom
    Geraet gemeldeten Hostnamen, zuletzt die MAC-Adresse.
    """
    for key in ("X_AVM-DE_FriendlyName", "HostName"):
        value = str(raw.get(key) or "").strip()
        if value:
            return value
    mac = normalize_mac(raw.get("MACAddress"))
    return mac or "Unbekanntes Geraet"


def normalize_host(raw: dict[str, Any]) -> dict[str, Any]:
    """Uebersetzt einen Roh-Hosteintrag in das Format der Dashboard-Karte."""
    mac = normalize_mac(raw.get("MACAddress"))
    kind = connection_kind(raw.get("InterfaceType"))
    port = as_int(raw.get("X_AVM-DE_Port"))
    guest = as_bool(raw.get("X_AVM-DE_Guest"))
    wan_access = str(raw.get("X_AVM-DE_WANAccess") or "unknown").strip().lower()

    return {
        "index": as_int(raw.get("Index")),
        "name": display_name(raw),
        "host_name": str(raw.get("HostName") or "").strip(),
        "friendly_name": str(raw.get("X_AVM-DE_FriendlyName") or "").strip(),
        "name_writeable": as_bool(raw.get("X_AVM-DE_FriendlyNameIsWriteable")),
        "ip": str(raw.get("IPAddress") or "").strip(),
        "mac": mac,
        "active": as_bool(raw.get("Active")),
        "connection": kind,
        "connection_label": connection_label(kind, port, guest),
        "port": port,
        "speed": as_int(raw.get("X_AVM-DE_Speed")),
        "guest": guest,
        "vpn": as_bool(raw.get("X_AVM-DE_VPN")),
        "meshable": as_bool(raw.get("X_AVM-DE_IsMeshable")),
        "priority": as_bool(raw.get("X_AVM-DE_Priority")),
        "model": str(raw.get("X_AVM-DE_Model") or "").strip(),
        "device_class": str(raw.get("X_AVM-DE_DeviceClass") or "").strip(),
        "device_class_user": str(raw.get("X_AVM-DE_DeviceClassUser") or "").strip(),
        "update_available": as_bool(raw.get("X_AVM-DE_UpdateAvailable")),
        "update_state": str(raw.get("X_AVM-DE_UpdateSuccessful") or "unknown").strip(),
        "info_url": str(raw.get("X_AVM-DE_InfoURL") or "").strip(),
        "url": str(raw.get("X_AVM-DE_URL") or "").strip(),
        "wan_access": wan_access,
        # ``Disallow`` ist das Flag hinter "Internetzugang gesperrt".
        # ``WANAccess == denied`` wird zusaetzlich ausgewertet, weil aeltere
        # FRITZ!OS-Staende nur eines von beiden zuverlaessig fuellen.
        "blocked": as_bool(raw.get("X_AVM-DE_Disallow")) or wan_access == WAN_DENIED,
        "filter_profile": str(raw.get("X_AVM-DE_FilterProfileID") or "").strip(),
        # Wird - falls aktiviert - nachtraeglich aus GetSpecificHostEntry
        # ergaenzt, siehe ``apply_address_sources()``.
        "address_source": None,
        "static_ip": None,
        "lease_time_remaining": None,
        # Wird in ``apply_ha_devices()`` ergaenzt.
        "ha_name": "",
        "ha_device_id": "",
        "ha_area": "",
        # Von FritzSync uebernommene Zusatzfelder.
        "network": "",
        "zone": "",
        "ptr1": "",
        "ptr2": "",
        "comment": "",
    }


def _dns_read_name(packet: bytes, offset: int, depth: int = 0) -> tuple[str, int]:
    """Read a possibly compressed DNS name from a response packet."""
    if depth > 20:
        raise ValueError("DNS compression recursion is too deep")
    labels: list[str] = []
    while offset < len(packet):
        length = packet[offset]
        if length == 0:
            return ".".join(labels), offset + 1
        if length & 0xC0 == 0xC0:
            if offset + 1 >= len(packet):
                raise ValueError("Incomplete DNS compression pointer")
            pointer = ((length & 0x3F) << 8) | packet[offset + 1]
            pointed, _ = _dns_read_name(packet, pointer, depth + 1)
            if pointed:
                labels.append(pointed)
            return ".".join(labels), offset + 2
        if length & 0xC0:
            raise ValueError("Unknown DNS label format")
        offset += 1
        end = offset + length
        if end > len(packet):
            raise ValueError("Incomplete DNS label")
        labels.append(packet[offset:end].decode("utf-8", errors="replace"))
        offset = end
    raise ValueError("Incomplete DNS name")


def query_ptr_records(ip_text: str, dns_server: str, timeout: float = 1.2) -> list[str]:
    """Query up to all PTR answers directly from the FRITZ!Box DNS server."""
    try:
        reverse_name = ipaddress.ip_address(ip_text).reverse_pointer
    except ValueError:
        return []
    query_id = int.from_bytes(os.urandom(2), "big")
    qname = b"".join(
        bytes([len(part)]) + part.encode("ascii") for part in reverse_name.split(".")
    ) + b"\x00"
    query = (
        struct.pack("!HHHHHH", query_id, 0x0100, 1, 0, 0, 0)
        + qname
        + struct.pack("!HH", 12, 1)
    )
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            sock.sendto(query, (dns_server, 53))
            packet, _ = sock.recvfrom(4096)
    except OSError:
        return []
    if len(packet) < 12:
        return []
    response_id, flags, qdcount, ancount, _, _ = struct.unpack("!HHHHHH", packet[:12])
    if response_id != query_id or flags & 0x000F:
        return []
    offset = 12
    try:
        for _ in range(qdcount):
            _, offset = _dns_read_name(packet, offset)
            offset += 4
        records: list[str] = []
        for _ in range(ancount):
            _, offset = _dns_read_name(packet, offset)
            if offset + 10 > len(packet):
                break
            record_type, record_class, _ttl, data_length = struct.unpack(
                "!HHIH", packet[offset : offset + 10]
            )
            offset += 10
            data_offset = offset
            offset += data_length
            if record_type == 12 and record_class == 1:
                value, _ = _dns_read_name(packet, data_offset)
                value = value.rstrip(".")
                if value and value.casefold() not in {item.casefold() for item in records}:
                    records.append(value)
        return records
    except (ValueError, struct.error):
        return []


def resolve_ptr_map(ips: list[str], dns_server: str) -> dict[str, list[str]]:
    """Resolve PTR records concurrently without blocking once per device."""
    valid_ips = sorted({str(ip).strip() for ip in ips if str(ip).strip()})
    if not valid_ips:
        return {}
    result: dict[str, list[str]] = {}
    with ThreadPoolExecutor(max_workers=min(16, len(valid_ips))) as pool:
        futures = {pool.submit(query_ptr_records, ip, dns_server): ip for ip in valid_ips}
        for future in as_completed(futures):
            ip = futures[future]
            try:
                result[ip] = future.result()
            except Exception:
                result[ip] = []
    return result


def apply_fritzsync_fields(
    hosts: list[dict[str, Any]],
    ptr_records: dict[str, list[str]] | None,
    comments: dict[str, str] | None,
    router_address: str,
) -> list[dict[str, Any]]:
    """Attach network, PTR and locally stored comment fields."""
    try:
        router_ip = ipaddress.ip_address(router_address)
        primary_network = ipaddress.ip_network(f"{router_ip}/24", strict=False)
    except ValueError:
        primary_network = None
    for host in hosts:
        ip_text = str(host.get("ip") or "").strip()
        try:
            address = ipaddress.ip_address(ip_text)
            network = ipaddress.ip_network(f"{address}/24", strict=False)
            host["network"] = str(network)
            host["zone"] = (
                "Heimnetz" if primary_network is not None and address in primary_network
                else "Gast"
            )
        except ValueError:
            host["network"] = ""
            host["zone"] = ""
        records = (ptr_records or {}).get(ip_text, [])
        host["ptr1"] = records[0] if records else ""
        host["ptr2"] = records[1] if len(records) > 1 else ""
        host["comment"] = str((comments or {}).get(mac_key(host.get("mac")), ""))
    return hosts


def apply_address_sources(
    hosts: list[dict[str, Any]], sources: dict[str, dict[str, Any]] | None
) -> list[dict[str, Any]]:
    """Ergaenzt DHCP/statisch und Lease-Restzeit anhand des MAC-Schluessels.

    ``sources`` bildet ``mac_key`` auf ein Dictionary mit den Schluesseln
    ``address_source`` und ``lease_time_remaining`` ab. Ist fuer einen Host
    nichts hinterlegt, bleiben die Felder ``None`` - die Karte zeigt dann
    bewusst "—" statt einer geratenen Angabe.
    """
    if not sources:
        return hosts
    for host in hosts:
        entry = sources.get(mac_key(host["mac"]))
        if not entry:
            continue
        source = str(entry.get("address_source") or "").strip()
        if source:
            host["address_source"] = source
            # AddressSource=DHCP beschreibt nur, wie die Adresse bezogen wird.
            # Die FRITZ!Box-Option „dauerhaft zuweisen“ kommt separat aus der WebUI.
            host["static_ip"] = source.lower() == ADDRESS_SOURCE_STATIC.lower()
        if isinstance(entry.get("static_ip"), bool):
            host["static_ip"] = entry["static_ip"]
        lease = entry.get("lease_time_remaining")
        if lease is not None:
            host["lease_time_remaining"] = as_int(lease)
    return hosts


def apply_ha_devices(
    hosts: list[dict[str, Any]], devices: dict[str, dict[str, str]] | None
) -> list[dict[str, Any]]:
    """Ergaenzt den Home-Assistant-Geraetenamen anhand des MAC-Schluessels."""
    if not devices:
        return hosts
    for host in hosts:
        entry = devices.get(mac_key(host["mac"]))
        if not entry:
            continue
        host["ha_name"] = entry.get("name", "")
        host["ha_device_id"] = entry.get("device_id", "")
        host["ha_area"] = entry.get("area", "")
    return hosts


def build_hosts(
    raw_hosts: list[dict[str, Any]],
    address_sources: dict[str, dict[str, Any]] | None = None,
    ha_devices: dict[str, dict[str, str]] | None = None,
) -> list[dict[str, Any]]:
    """Baut die vollstaendige, sortierte Hostliste fuer das Sensorattribut.

    Sortiert wird nach IP-Adresse (numerisch). Eintraege ohne MAC-Adresse
    werden verworfen - sie sind Karteileichen der FRITZ!Box und wuerden in
    der Karte nur eine leere Zeile erzeugen.
    """
    hosts = []
    for raw in raw_hosts or []:
        if not normalize_mac(raw.get("MACAddress")):
            continue
        host = normalize_host(raw)
        # TR-064 kann veraltete, inaktive Platzhalter ohne IPv4 liefern. Diese
        # duerfen weder als Geraet erscheinen noch durch Zusatzabfragen weiter
        # verarbeitet werden. Echte benannte Offline-Geraete bleiben erhalten.
        mac_name = f"PC-{host['mac'].replace(':', '-')}"
        if (
            not host["ip"]
            and not host["active"]
            and host["name"].casefold() == mac_name.casefold()
        ):
            continue
        hosts.append(host)
    apply_address_sources(hosts, address_sources)
    apply_ha_devices(hosts, ha_devices)
    mark_stale_ip_duplicates(hosts)
    hosts.sort(key=lambda host: ip_sort_key(host["ip"]))
    return hosts


def _host_quality(host: dict[str, Any]) -> tuple[int, ...]:
    """Bewertet konkurrierende Datensaetze derselben IP deterministisch."""
    name = str(host.get("name") or "").strip().lower()
    ip = str(host.get("ip") or "").strip()
    placeholder = name == f"pc-{ip.replace('.', '-')}".lower()
    return (
        int(bool(host.get("active"))),
        int(not placeholder),
        int(bool(host.get("friendly_name"))),
        int(bool(host.get("name_writeable"))),
        int(host.get("connection") != CONNECTION_UNKNOWN),
        int(bool(host.get("ha_name"))),
        as_int(host.get("index")),
    )


def mark_stale_ip_duplicates(hosts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Markiert eindeutig veraltete, inaktive Datensaetze je belegter IP.

    Geloescht wird hier bewusst nichts. Die Markierung dient der bestaetigten
    Bereinigungsaktion; der Gewinner ist immer der qualitativ beste Datensatz.
    """
    groups: dict[str, list[dict[str, Any]]] = {}
    for host in hosts:
        host["stale_ip_duplicate"] = False
        ip = str(host.get("ip") or "").strip()
        if ip:
            groups.setdefault(ip, []).append(host)
    for group in groups.values():
        if len(group) < 2:
            continue
        winner = max(group, key=_host_quality)
        for host in group:
            if host is not winner and not host.get("active"):
                host["stale_ip_duplicate"] = True
    return hosts


def summarize(hosts: list[dict[str, Any]]) -> dict[str, int]:
    """Zaehlt die Kennzahlen, die als eigene Sensorattribute erscheinen."""
    active = sum(1 for host in hosts if host["active"])
    return {
        "total": len(hosts),
        "active": active,
        "inactive": len(hosts) - active,
        "guests": sum(1 for host in hosts if host["guest"]),
        "blocked": sum(1 for host in hosts if host["blocked"]),
        "updates": sum(1 for host in hosts if host["update_available"]),
        "static": sum(1 for host in hosts if host["static_ip"]),
    }
