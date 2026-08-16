"""Data coordinator and write actions."""

from __future__ import annotations

from datetime import timedelta
import logging
import socket
from typing import Any

from fritzconnection.core.exceptions import FritzConnectionException
from fritzconnection.lib.fritzhosts import FritzHosts

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN
from .model import attach_mesh_parents, build_mesh, normalize_host

_LOGGER = logging.getLogger(__name__)


class FritzSyncCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, hosts: FritzHosts) -> None:
        self.entry = entry
        self.hosts = hosts
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}-{entry.entry_id}",
            update_interval=timedelta(seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)),
        )

    def _fetch(self) -> dict[str, Any]:
        raw_hosts = self.hosts.get_hosts_attributes()
        topology_raw = None
        try:
            topology_raw = self.hosts.get_mesh_topology()
        except FritzConnectionException as err:
            _LOGGER.debug("Mesh topology unavailable: %s", err)
        hosts = [normalize_host(host) for host in raw_hosts]
        nodes, links = build_mesh(topology_raw)
        attach_mesh_parents(hosts, nodes, links)
        return {"hosts": hosts, "mesh_nodes": nodes, "mesh_links": links}

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.hass.async_add_executor_job(self._fetch)
        except FritzConnectionException as err:
            raise UpdateFailed(f"FRITZ!Box-Abfrage fehlgeschlagen: {err}") from err

    async def async_rename(self, mac: str, name: str) -> None:
        try:
            await self.hass.async_add_executor_job(self.hosts.set_host_name, mac, name)
        except FritzConnectionException as err:
            raise HomeAssistantError(f"Umbenennen fehlgeschlagen: {err}") from err
        await self.async_request_refresh()

    async def async_set_blocked(self, ip: str, blocked: bool) -> None:
        def call() -> None:
            self.hosts.fc.call_action(
                "X_AVM-DE_HostFilter1",
                "DisallowWANAccessByIP",
                NewIPv4Address=ip,
                NewDisallow=blocked,
            )
        try:
            await self.hass.async_add_executor_job(call)
        except FritzConnectionException as err:
            raise HomeAssistantError(f"Internetzugang konnte nicht geändert werden: {err}") from err
        await self.async_request_refresh()

    async def async_wake(self, mac: str) -> None:
        def send_magic_packet() -> None:
            address = bytes.fromhex(mac.replace(":", "").replace("-", ""))
            if len(address) != 6:
                raise HomeAssistantError("Ungültige MAC-Adresse")
            packet = b"\xff" * 6 + address * 16
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                sock.sendto(packet, ("255.255.255.255", 9))
        await self.hass.async_add_executor_job(send_magic_packet)
        await self.async_request_refresh()
