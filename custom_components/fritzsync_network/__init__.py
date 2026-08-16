"""Die Integration fritzsync_network."""

from __future__ import annotations

import logging
import os

import voluptuous as vol
from fritzconnection import FritzConnection
from fritzconnection.core.exceptions import (
    FritzAuthorizationError,
    FritzConnectionException,
    FritzSecurityError,
)
from fritzconnection.lib.fritzhosts import FritzHosts
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import RequestException

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_COMMENT,
    ATTR_MAC,
    ATTR_NAME,
    ATTR_IP,
    ATTR_DNS_NAMES,
    ATTR_OLD_RECORD,
    CARD_FILENAME,
    CARD_URL,
    CONF_PIHOLE_DOMAIN,
    CONF_PIHOLE_ENABLED,
    CONF_PIHOLE_HOST,
    CONF_PIHOLE_PASSWORD,
    CONF_USE_TLS,
    DEFAULT_PIHOLE_DOMAIN,
    DEFAULT_PIHOLE_HOST,
    DEFAULT_USE_TLS,
    DOMAIN,
    PLATFORMS,
    SERVICE_SET_DEVICE_NAME,
    SERVICE_SET_COMMENT,
    SERVICE_ACKNOWLEDGE_DEVICE,
    SERVICE_WAKE_ON_LAN,
    SERVICE_PIHOLE_ADD_RECORD,
    SERVICE_PIHOLE_UPDATE_RECORD,
    SERVICE_PIHOLE_DELETE_RECORD,
    SERVICE_PIHOLE_SYNC_ALL,
    SERVICE_CLEANUP_STALE_HOSTS,
    URL_BASE,
    VERSION,
)
from .coordinator import FritzSyncNetworkCoordinator
from .hosts import build_hosts, normalize_mac
from .pihole import PiholeApiError, PiholeClient, fqdn
from .fritzbox_web import FritzBoxWebClient, FritzBoxWebError

_LOGGER = logging.getLogger(__name__)

type FritzSyncNetworkConfigEntry = ConfigEntry[FritzSyncNetworkCoordinator]

MAC_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MAC): cv.string,
        vol.Optional(ATTR_NAME): cv.string,
    }
)
COMMENT_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MAC): cv.string,
        vol.Optional(ATTR_COMMENT, default=""): cv.string,
    }
)
PIHOLE_ADD_SCHEMA = vol.Schema(
    {vol.Required(ATTR_IP): cv.string, vol.Required(ATTR_DNS_NAMES): cv.string}
)
PIHOLE_UPDATE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_OLD_RECORD): cv.string,
        vol.Required(ATTR_IP): cv.string,
        vol.Required(ATTR_DNS_NAMES): cv.string,
    }
)
PIHOLE_DELETE_SCHEMA = vol.Schema({vol.Required(ATTR_OLD_RECORD): cv.string})


async def async_setup_entry(
    hass: HomeAssistant, entry: FritzSyncNetworkConfigEntry
) -> bool:
    """Richtet einen Konfigurationseintrag ein."""

    def _connect() -> FritzHosts:
        connection = FritzConnection(
            address=entry.data[CONF_HOST],
            user=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
            use_tls=entry.data.get(CONF_USE_TLS, DEFAULT_USE_TLS),
        )
        return FritzHosts(fc=connection)

    try:
        fritz_hosts = await hass.async_add_executor_job(_connect)
    except (FritzSecurityError, FritzAuthorizationError) as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except (FritzConnectionException, RequestsConnectionError) as err:
        raise ConfigEntryNotReady(
            f"FRITZ!Box unter {entry.data[CONF_HOST]} nicht erreichbar: {err}"
        ) from err

    coordinator = FritzSyncNetworkCoordinator(hass, entry, fritz_hosts)
    await coordinator.async_load_comments()
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await _async_register_card(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _async_register_services(hass)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: FritzSyncNetworkConfigEntry
) -> bool:
    """Entlaedt einen Konfigurationseintrag."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded and not hass.config_entries.async_loaded_entries(DOMAIN):
        for service in (
            SERVICE_SET_DEVICE_NAME,
            SERVICE_WAKE_ON_LAN,
            SERVICE_SET_COMMENT,
            SERVICE_ACKNOWLEDGE_DEVICE,
            SERVICE_PIHOLE_ADD_RECORD,
            SERVICE_PIHOLE_UPDATE_RECORD,
            SERVICE_PIHOLE_DELETE_RECORD,
            SERVICE_PIHOLE_SYNC_ALL,
            SERVICE_CLEANUP_STALE_HOSTS,
        ):
            hass.services.async_remove(DOMAIN, service)
    return unloaded


async def _async_update_listener(
    hass: HomeAssistant, entry: FritzSyncNetworkConfigEntry
) -> None:
    """Laedt den Eintrag nach Aenderung der Optionen neu."""
    await hass.config_entries.async_reload(entry.entry_id)


# ---------------------------------------------------------------------------
# Dashboard-Karte
# ---------------------------------------------------------------------------


async def _async_register_card(hass: HomeAssistant) -> None:
    """Stellt die Karten-Datei bereit und traegt sie als Ressource ein."""
    card_path = os.path.join(os.path.dirname(__file__), "www", CARD_FILENAME)
    if not os.path.exists(card_path):
        _LOGGER.warning("Karten-Datei %s nicht gefunden", card_path)
        return

    if URL_BASE not in hass.data.setdefault(f"{DOMAIN}_static_paths", set()):
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    URL_BASE, os.path.join(os.path.dirname(__file__), "www"), False
                )
            ]
        )
        hass.data[f"{DOMAIN}_static_paths"].add(URL_BASE)

    await _async_ensure_lovelace_resource(hass)


async def _async_ensure_lovelace_resource(hass: HomeAssistant) -> None:
    """Traegt die Karte einmalig in die Lovelace-Ressourcen ein.

    Bewusst KEIN ``add_extra_js_url()`` zusaetzlich: ein Browser fuehrt
    eine Modul-URL nur einmal aus, ein doppelter Ladeweg laesst die Karte
    stumm scheitern. Ein vorhandener Eintrag wird aktualisiert statt
    dupliziert, damit der Versionsparameter den Browser-Cache umgeht.
    """
    versioned_url = f"{CARD_URL}?v={VERSION}"
    lovelace = hass.data.get("lovelace")
    if lovelace is None:
        _LOGGER.debug("Lovelace noch nicht geladen, Ressource nicht eingetragen")
        return

    resources = getattr(lovelace, "resources", None)
    if resources is None and isinstance(lovelace, dict):
        resources = lovelace.get("resources")
    if resources is None:
        return

    # Im YAML-Modus verwaltet der Nutzer die Ressourcen selbst.
    if getattr(resources, "store", None) is None:
        _LOGGER.info(
            "Lovelace laeuft im YAML-Modus. Bitte '%s' manuell als Modul-Ressource "
            "eintragen",
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
            _LOGGER.debug("Lovelace-Ressource auf %s aktualisiert", versioned_url)
        return

    await resources.async_create_item({"res_type": "module", "url": versioned_url})
    _LOGGER.debug("Lovelace-Ressource %s angelegt", versioned_url)


# ---------------------------------------------------------------------------
# Dienste
# ---------------------------------------------------------------------------


def _async_register_services(hass: HomeAssistant) -> None:
    """Meldet die Dienste an (einmalig, unabhaengig von der Anzahl der Boxen)."""

    def _first_coordinator() -> FritzSyncNetworkCoordinator:
        entries = hass.config_entries.async_loaded_entries(DOMAIN)
        if not entries:
            raise HomeAssistantError("Keine eingerichtete FRITZ!Box gefunden")
        return entries[0].runtime_data

    async def _handle_set_device_name(call: ServiceCall) -> None:
        coordinator = _first_coordinator()
        mac = normalize_mac(call.data[ATTR_MAC])
        name = call.data.get(ATTR_NAME, "")
        if not name:
            raise HomeAssistantError("Es wurde kein neuer Name uebergeben")
        current_host = next(
            (
                host
                for host in (coordinator.data or {}).get("hosts", [])
                if normalize_mac(host.get("mac")) == mac
            ),
            None,
        )
        old_name = str((current_host or {}).get("name") or "").strip()
        current_ip = str((current_host or {}).get("ip") or "").strip()
        try:
            web = FritzBoxWebClient(
                str(coordinator.entry.data[CONF_HOST]),
                str(coordinator.entry.data[CONF_USERNAME]),
                str(coordinator.entry.data[CONF_PASSWORD]),
                bool(coordinator.entry.data.get(CONF_USE_TLS, DEFAULT_USE_TLS)),
            )
            await hass.async_add_executor_job(web.rename, mac, name)
        except (FritzConnectionException, FritzBoxWebError, RequestException) as err:
            raise HomeAssistantError(
                f"Umbenennen von {mac} fehlgeschlagen: {err}"
            ) from err
        options = coordinator.entry.options
        pihole_error: Exception | None = None
        if options.get(CONF_PIHOLE_ENABLED, False):
            password = str(options.get(CONF_PIHOLE_PASSWORD, ""))
            if not password:
                raise HomeAssistantError(
                    "FRITZ!Box wurde umbenannt, aber das Pi-hole-Passwort fehlt"
                )
            client = PiholeClient(
                str(options.get(CONF_PIHOLE_HOST, DEFAULT_PIHOLE_HOST)),
                password,
                str(options.get(CONF_PIHOLE_DOMAIN, DEFAULT_PIHOLE_DOMAIN)),
            )
            try:
                await hass.async_add_executor_job(
                    client.sync_rename, current_ip, old_name, name
                )
            except (PiholeApiError, RequestException) as err:
                pihole_error = err
        await coordinator.async_request_refresh()
        if pihole_error is not None:
            raise HomeAssistantError(
                "FRITZ!Box wurde umbenannt, Pi-hole-Synchronisierung "
                f"fehlgeschlagen: {pihole_error}"
            ) from pihole_error

    async def _handle_wake_on_lan(call: ServiceCall) -> None:
        coordinator = _first_coordinator()
        mac = normalize_mac(call.data[ATTR_MAC])

        def _wake() -> None:
            coordinator.fritz_hosts.fc.call_action(
                "Hosts1", "X_AVM-DE_WakeOnLANByMACAddress", NewMACAddress=mac
            )

        try:
            await hass.async_add_executor_job(_wake)
        except FritzConnectionException as err:
            raise HomeAssistantError(
                f"Aufwecken von {mac} fehlgeschlagen: {err}"
            ) from err

    async def _handle_set_comment(call: ServiceCall) -> None:
        coordinator = _first_coordinator()
        await coordinator.async_set_comment(
            normalize_mac(call.data[ATTR_MAC]), call.data[ATTR_COMMENT]
        )

    async def _handle_acknowledge_device(call: ServiceCall) -> None:
        coordinator = _first_coordinator()
        await coordinator.async_acknowledge_device(normalize_mac(call.data[ATTR_MAC]))

    async def _pihole_write(method: str, call: ServiceCall) -> None:
        coordinator = _first_coordinator()
        client = coordinator.pihole_client()
        try:
            if method == "add":
                await hass.async_add_executor_job(
                    client.add_record, call.data[ATTR_IP], call.data[ATTR_DNS_NAMES]
                )
            elif method == "update":
                await hass.async_add_executor_job(
                    client.replace_record,
                    call.data[ATTR_OLD_RECORD],
                    call.data[ATTR_IP],
                    call.data[ATTR_DNS_NAMES],
                )
            else:
                await hass.async_add_executor_job(
                    client.delete_record, call.data[ATTR_OLD_RECORD]
                )
        except (PiholeApiError, RequestException) as err:
            raise HomeAssistantError(f"Pi-hole-Änderung fehlgeschlagen: {err}") from err
        await coordinator.async_request_refresh()

    async def _handle_pihole_add(call: ServiceCall) -> None:
        await _pihole_write("add", call)

    async def _handle_pihole_update(call: ServiceCall) -> None:
        await _pihole_write("update", call)

    async def _handle_pihole_delete(call: ServiceCall) -> None:
        await _pihole_write("delete", call)

    async def _handle_pihole_sync_all(call: ServiceCall) -> None:
        coordinator = _first_coordinator()
        options = coordinator.entry.options
        domain = str(options.get(CONF_PIHOLE_DOMAIN, DEFAULT_PIHOLE_DOMAIN))
        desired: list[str] = []
        for host in (coordinator.data or {}).get("hosts", []):
            if host.get("stale_ip_duplicate"):
                continue
            ip = str(host.get("ip") or "").strip()
            name = str(host.get("name") or "").strip()
            if not ip or not name:
                continue
            try:
                desired.append(f"{ip} {fqdn(name, domain)}")
            except PiholeApiError:
                continue
        try:
            await hass.async_add_executor_job(
                coordinator.pihole_client().sync_all, desired
            )
        except (PiholeApiError, RequestException) as err:
            raise HomeAssistantError(f"Pi-hole-Gesamtabgleich fehlgeschlagen: {err}") from err
        await coordinator.async_request_refresh()

    async def _handle_cleanup_stale_hosts(call: ServiceCall) -> None:
        coordinator = _first_coordinator()

        def _cleanup() -> int:
            # Direkt vor dem Loeschen neu einlesen. Ausschliesslich weiterhin
            # inaktive Verlierer einer mehrfach belegten IP sind Kandidaten.
            fresh = build_hosts(coordinator.fritz_hosts.get_hosts_attributes())
            candidates = [
                host for host in fresh
                if host.get("stale_ip_duplicate") and not host.get("active")
            ]
            web = FritzBoxWebClient(
                str(coordinator.entry.data[CONF_HOST]),
                str(coordinator.entry.data[CONF_USERNAME]),
                str(coordinator.entry.data[CONF_PASSWORD]),
                bool(coordinator.entry.data.get(CONF_USE_TLS, DEFAULT_USE_TLS)),
            )
            for host in candidates:
                web.delete_device(str(host["mac"]))
            return len(candidates)

        try:
            await hass.async_add_executor_job(_cleanup)
        except (FritzConnectionException, FritzBoxWebError, RequestException) as err:
            raise HomeAssistantError(
                f"Bereinigung der FRITZ!Box-Geräteliste fehlgeschlagen: {err}"
            ) from err
        await coordinator.async_request_refresh()

    if not hass.services.has_service(DOMAIN, SERVICE_SET_DEVICE_NAME):
        hass.services.async_register(
            DOMAIN, SERVICE_SET_DEVICE_NAME, _handle_set_device_name, schema=MAC_SCHEMA
        )
    if not hass.services.has_service(DOMAIN, SERVICE_WAKE_ON_LAN):
        hass.services.async_register(
            DOMAIN, SERVICE_WAKE_ON_LAN, _handle_wake_on_lan, schema=MAC_SCHEMA
        )
    if not hass.services.has_service(DOMAIN, SERVICE_SET_COMMENT):
        hass.services.async_register(
            DOMAIN, SERVICE_SET_COMMENT, _handle_set_comment, schema=COMMENT_SCHEMA
        )
    if not hass.services.has_service(DOMAIN, SERVICE_ACKNOWLEDGE_DEVICE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_ACKNOWLEDGE_DEVICE,
            _handle_acknowledge_device,
            schema=MAC_SCHEMA,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_PIHOLE_ADD_RECORD):
        hass.services.async_register(
            DOMAIN, SERVICE_PIHOLE_ADD_RECORD, _handle_pihole_add,
            schema=PIHOLE_ADD_SCHEMA,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_PIHOLE_UPDATE_RECORD):
        hass.services.async_register(
            DOMAIN, SERVICE_PIHOLE_UPDATE_RECORD, _handle_pihole_update,
            schema=PIHOLE_UPDATE_SCHEMA,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_PIHOLE_DELETE_RECORD):
        hass.services.async_register(
            DOMAIN, SERVICE_PIHOLE_DELETE_RECORD, _handle_pihole_delete,
            schema=PIHOLE_DELETE_SCHEMA,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_PIHOLE_SYNC_ALL):
        hass.services.async_register(
            DOMAIN, SERVICE_PIHOLE_SYNC_ALL, _handle_pihole_sync_all
        )
    if not hass.services.has_service(DOMAIN, SERVICE_CLEANUP_STALE_HOSTS):
        hass.services.async_register(
            DOMAIN, SERVICE_CLEANUP_STALE_HOSTS, _handle_cleanup_stale_hosts
        )
