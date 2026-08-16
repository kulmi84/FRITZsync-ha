"""FritzSync Network integration."""

from __future__ import annotations

from pathlib import Path

from fritzconnection import FritzConnection
from fritzconnection.lib.fritzhosts import FritzHosts
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_BLOCKED, ATTR_ENTRY_ID, ATTR_IP, ATTR_MAC, ATTR_NAME, CARD_PATH, CARD_URL,
    CONF_USE_TLS, DOMAIN, PLATFORMS, SERVICE_RENAME, SERVICE_SET_BLOCKED, SERVICE_WAKE,
)
from .coordinator import FritzSyncCoordinator

type FritzSyncConfigEntry = ConfigEntry[FritzSyncCoordinator]

RENAME_SCHEMA = vol.Schema({vol.Required(ATTR_ENTRY_ID): cv.string, vol.Required(ATTR_MAC): cv.string, vol.Required(ATTR_NAME): cv.string})
BLOCK_SCHEMA = vol.Schema({vol.Required(ATTR_ENTRY_ID): cv.string, vol.Required(ATTR_IP): cv.string, vol.Required(ATTR_BLOCKED): cv.boolean})
WAKE_SCHEMA = vol.Schema({vol.Required(ATTR_ENTRY_ID): cv.string, vol.Required(ATTR_MAC): cv.string})


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    card_dir = Path(__file__).parent / "www"
    await hass.http.async_register_static_paths([
        StaticPathConfig(CARD_URL, str(card_dir / Path(CARD_PATH).name), False)
    ])
    add_extra_js_url(hass, CARD_URL)
    return True


def _coordinator(hass: HomeAssistant, entry_id: str) -> FritzSyncCoordinator:
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.domain != DOMAIN or entry.runtime_data is None:
        raise vol.Invalid("Unbekannte FritzSync-Network-Konfiguration")
    return entry.runtime_data


async def async_setup_entry(hass: HomeAssistant, entry: FritzSyncConfigEntry) -> bool:
    def create_hosts_client() -> FritzHosts:
        connection = FritzConnection(
            address=entry.data[CONF_HOST], user=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
            use_tls=entry.data.get(CONF_USE_TLS, False), timeout=10.0,
        )
        return FritzHosts(connection)

    hosts = await hass.async_add_executor_job(create_hosts_client)
    coordinator = FritzSyncCoordinator(hass, entry, hosts)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    async def rename(call: ServiceCall) -> None:
        await _coordinator(hass, call.data[ATTR_ENTRY_ID]).async_rename(call.data[ATTR_MAC], call.data[ATTR_NAME].strip())

    async def set_blocked(call: ServiceCall) -> None:
        await _coordinator(hass, call.data[ATTR_ENTRY_ID]).async_set_blocked(call.data[ATTR_IP], call.data[ATTR_BLOCKED])

    async def wake(call: ServiceCall) -> None:
        await _coordinator(hass, call.data[ATTR_ENTRY_ID]).async_wake(call.data[ATTR_MAC])

    if not hass.services.has_service(DOMAIN, SERVICE_RENAME):
        hass.services.async_register(DOMAIN, SERVICE_RENAME, rename, schema=RENAME_SCHEMA)
        hass.services.async_register(DOMAIN, SERVICE_SET_BLOCKED, set_blocked, schema=BLOCK_SCHEMA)
        hass.services.async_register(DOMAIN, SERVICE_WAKE, wake, schema=WAKE_SCHEMA)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: FritzSyncConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_entry(hass: HomeAssistant, entry: FritzSyncConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
