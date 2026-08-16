"""Sensor platform."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import FritzSyncConfigEntry
from .const import DOMAIN
from .coordinator import FritzSyncCoordinator


async def async_setup_entry(hass, entry: FritzSyncConfigEntry, async_add_entities) -> None:
    async_add_entities([FritzSyncNetworkSensor(entry.runtime_data)])


class FritzSyncNetworkSensor(CoordinatorEntity[FritzSyncCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "FritzSync Network"
    _unrecorded_attributes = frozenset({"hosts", "mesh_nodes", "mesh_links"})

    def __init__(self, coordinator: FritzSyncCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_network"

    @property
    def native_value(self) -> int:
        return sum(1 for host in self.coordinator.data["hosts"] if host["active"])

    @property
    def extra_state_attributes(self):
        hosts = self.coordinator.data["hosts"]
        return {
            "entry_id": self.coordinator.entry.entry_id,
            "hosts": hosts,
            "mesh_nodes": self.coordinator.data["mesh_nodes"],
            "mesh_links": self.coordinator.data["mesh_links"],
            "total": len(hosts),
            "active": sum(1 for host in hosts if host["active"]),
            "blocked": sum(1 for host in hosts if host["blocked"]),
        }

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self.coordinator.entry.entry_id)}, "name": self.coordinator.entry.title, "manufacturer": "FRITZ!", "model": "Network topology"}
