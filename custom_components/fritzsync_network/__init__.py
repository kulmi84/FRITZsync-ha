"""FritzSync Network integration."""

from __future__ import annotations

import logging
import os

from fritzconnection import FritzConnection
from fritzconnection.lib.fritzhosts import FritzHosts
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_BLOCKED, ATTR_ENTRY_ID, ATTR_IP, ATTR_MAC, ATTR_NAME, CARD_FILENAME,
    CARD_URL,
    CONF_USE_TLS, DOMAIN, PLATFORMS, SERVICE_RENAME, SERVICE_SET_BLOCKED, SERVICE_WAKE,
    URL_BASE, VERSION,
)
from .coordinator import FritzSyncCoordinator

type FritzSyncConfigEntry = ConfigEntry[FritzSyncCoordinator]

_LOGGER = logging.getLogger(__name__)

RENAME_SCHEMA = vol.Schema({vol.Required(ATTR_ENTRY_ID): cv.string, vol.Required(ATTR_MAC): cv.string, vol.Required(ATTR_NAME): cv.string})
BLOCK_SCHEMA = vol.Schema({vol.Required(ATTR_ENTRY_ID): cv.string, vol.Required(ATTR_IP): cv.string, vol.Required(ATTR_BLOCKED): cv.boolean})
WAKE_SCHEMA = vol.Schema({vol.Required(ATTR_ENTRY_ID): cv.string, vol.Required(ATTR_MAC): cv.string})


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
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
    await _async_register_card(hass)
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


async def _async_register_card(hass: HomeAssistant) -> None:
    """Serve the card and register it as a Lovelace module resource."""
    card_path = os.path.join(os.path.dirname(__file__), "www", CARD_FILENAME)
    if not os.path.exists(card_path):
        _LOGGER.warning("Card file %s not found", card_path)
        return

    if URL_BASE not in hass.data.setdefault(f"{DOMAIN}_static_paths", set()):
        await hass.http.async_register_static_paths(
            [StaticPathConfig(URL_BASE, os.path.dirname(card_path), False)]
        )
        hass.data[f"{DOMAIN}_static_paths"].add(URL_BASE)

    await _async_ensure_lovelace_resource(hass)


async def _async_ensure_lovelace_resource(hass: HomeAssistant) -> None:
    """Create or update the card's Lovelace module resource."""
    versioned_url = f"{CARD_URL}?v={VERSION}"
    lovelace = hass.data.get("lovelace")
    if lovelace is None:
        _LOGGER.debug("Lovelace is not loaded; card resource was not registered")
        return

    resources = getattr(lovelace, "resources", None)
    if resources is None and isinstance(lovelace, dict):
        resources = lovelace.get("resources")
    if resources is None:
        return

    if getattr(resources, "store", None) is None:
        _LOGGER.info(
            "Lovelace runs in YAML mode; add '%s' as a module resource",
            versioned_url,
        )
        return

    if not getattr(resources, "loaded", False):
        await resources.async_load()
        resources.loaded = True

    for item in resources.async_items():
        url = str(item.get("url", ""))
        if url.split("?")[0] != CARD_URL:
            continue
        if url != versioned_url:
            await resources.async_update_item(item["id"], {"url": versioned_url})
        return

    await resources.async_create_item(
        {"res_type": "module", "url": versioned_url}
    )


async def async_unload_entry(hass: HomeAssistant, entry: FritzSyncConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_entry(hass: HomeAssistant, entry: FritzSyncConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
