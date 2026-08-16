"""Pure normalization helpers for FritzSync Network."""

from __future__ import annotations

from typing import Any


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "granted"}


def as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def normalize_mac(value: Any) -> str:
    raw = "".join(char for char in str(value or "") if char.isalnum()).upper()
    if len(raw) != 12:
        return str(value or "").strip().upper()
    return ":".join(raw[index : index + 2] for index in range(0, 12, 2))


def mac_key(value: Any) -> str:
    return "".join(char for char in str(value or "") if char.isalnum()).lower()


def connection_kind(value: Any, guest: bool = False) -> str:
    if guest:
        return "guest"
    text = str(value or "").lower()
    if text.startswith("ethernet"):
        return "lan"
    if text.startswith("802.11"):
        return "wlan"
    if text.startswith("homeplug"):
        return "powerline"
    return "other"


def normalize_host(raw: dict[str, Any]) -> dict[str, Any]:
    guest = as_bool(raw.get("X_AVM-DE_Guest"))
    mac = normalize_mac(raw.get("MACAddress"))
    name = str(
        raw.get("X_AVM-DE_FriendlyName")
        or raw.get("HostName")
        or mac
        or "Unbekannt"
    ).strip()
    wan_access = str(raw.get("X_AVM-DE_WANAccess") or "unknown").lower()
    return {
        "id": mac_key(mac) or f"host-{as_int(raw.get('Index'))}",
        "index": as_int(raw.get("Index")),
        "name": name,
        "ip": str(raw.get("IPAddress") or "").strip(),
        "mac": mac,
        "active": as_bool(raw.get("Active")),
        "connection": connection_kind(raw.get("InterfaceType"), guest),
        "interface": str(raw.get("InterfaceType") or "").strip(),
        "port": as_int(raw.get("X_AVM-DE_Port")),
        "speed": as_int(raw.get("X_AVM-DE_Speed")),
        "guest": guest,
        "vpn": as_bool(raw.get("X_AVM-DE_VPN")),
        "model": str(raw.get("X_AVM-DE_Model") or "").strip(),
        "vendor": str(raw.get("X_AVM-DE_Manufacturer") or "").strip(),
        "device_class": str(
            raw.get("X_AVM-DE_DeviceClassUser")
            or raw.get("X_AVM-DE_DeviceClass")
            or ""
        ).strip(),
        "blocked": as_bool(raw.get("X_AVM-DE_Disallow")) or wan_access == "denied",
        "wan_access": wan_access,
        "update_available": as_bool(raw.get("X_AVM-DE_UpdateAvailable")),
        "name_writeable": as_bool(raw.get("X_AVM-DE_FriendlyNameIsWriteable")) or bool(mac),
        "url": str(raw.get("X_AVM-DE_URL") or "").strip(),
        "mesh_parent": None,
    }


def build_mesh(raw: dict[str, Any] | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Convert the documented mesh JSON into small serializable node/link records."""
    nodes: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []
    if not isinstance(raw, dict):
        return nodes, links
    seen_links: set[str] = set()
    for item in raw.get("nodes", []):
        uid = str(item.get("uid") or "")
        if not uid:
            continue
        nodes.append({
            "id": uid,
            "name": str(item.get("device_name") or item.get("device_model") or uid),
            "model": str(item.get("device_model") or ""),
            "vendor": str(item.get("device_manufacturer") or ""),
            "mac": normalize_mac(item.get("device_mac_address")),
        })
        for interface in item.get("node_interfaces", []):
            for link in interface.get("node_links", []):
                link_uid = str(link.get("uid") or "")
                if link_uid in seen_links:
                    continue
                seen_links.add(link_uid)
                source = str(link.get("node_1_uid") or "")
                target = str(link.get("node_2_uid") or "")
                if source and target:
                    links.append({
                        "id": link_uid or f"{source}-{target}",
                        "source": source,
                        "target": target,
                        "type": str(link.get("type") or interface.get("type") or "other").lower(),
                        "state": str(link.get("state") or "").lower(),
                    })
    return nodes, links


def attach_mesh_parents(hosts: list[dict[str, Any]], nodes: list[dict[str, Any]], links: list[dict[str, Any]]) -> None:
    node_by_mac = {mac_key(node["mac"]): node["id"] for node in nodes if node.get("mac")}
    neighbours: dict[str, list[str]] = {}
    for link in links:
        neighbours.setdefault(link["source"], []).append(link["target"])
        neighbours.setdefault(link["target"], []).append(link["source"])
    infrastructure = set(node_by_mac.values())
    for host in hosts:
        node_id = node_by_mac.get(mac_key(host.get("mac")))
        if not node_id:
            continue
        candidates = [candidate for candidate in neighbours.get(node_id, []) if candidate in infrastructure]
        if candidates:
            host["mesh_parent"] = candidates[0]
