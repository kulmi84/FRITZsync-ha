"""Datenabruf fuer fritzsync_network."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from fritzconnection.core.exceptions import (
    FritzAuthorizationError,
    FritzConnectionException,
    FritzSecurityError,
    FritzServiceError,
)
from fritzconnection.lib.fritzhosts import FritzHosts

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ADDRESS_SOURCE_INTERVAL,
    CONF_SCAN_INTERVAL,
    CONF_TRACK_ADDRESS_SOURCE,
    CONF_PIHOLE_DOMAIN,
    CONF_PIHOLE_ENABLED,
    CONF_PIHOLE_HOST,
    CONF_PIHOLE_PASSWORD,
    DEFAULT_ADDRESS_SOURCE_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TRACK_ADDRESS_SOURCE,
    DEFAULT_PIHOLE_DOMAIN,
    DEFAULT_PIHOLE_HOST,
    DOMAIN,
    CONF_USE_TLS,
    DEFAULT_USE_TLS,
)
from .fritzbox_web import FritzBoxWebClient, fixed_ipv4_assignment
from .hosts import (
    apply_fritzsync_fields,
    build_hosts,
    mac_key,
    resolve_ptr_map,
    summarize,
)
from .pihole import PiholeApiError, PiholeClient, fqdn, split_record

_LOGGER = logging.getLogger(__name__)


class FritzSyncNetworkCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Haelt die Geraeteliste der FRITZ!Box aktuell.

    Die eigentliche Hostliste kommt mit EINEM SOAP-Aufruf
    (``X_AVM-DE_GetHostListPath``). Die Angabe DHCP/statisch steht dort
    nicht drin - sie ist nur ueber ``GetSpecificHostEntry`` je Geraet zu
    bekommen. Diese teure Abfrage laeuft deshalb in einem eigenen,
    deutlich langsameren Takt und ihr Ergebnis wird zwischengespeichert.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        fritz_hosts: FritzHosts,
    ) -> None:
        """Initialisiert den Coordinator."""
        self.entry = entry
        self.fritz_hosts = fritz_hosts
        self._address_sources: dict[str, dict[str, Any]] = {}
        self._address_source_scan: datetime | None = None
        self._address_source_failed = False
        self._ptr_records: dict[str, list[str]] = {}
        self._ptr_scan: datetime | None = None
        self._pihole_records: list[str] = []
        self._pihole_error: str = ""
        self._comments: dict[str, str] = {}
        self._comment_store = Store(
            hass, 1, f"{DOMAIN}.{entry.entry_id}.device_comments"
        )
        self._acknowledged_macs: set[str] = set()
        self._new_devices_initialized = False
        self._new_device_store = Store(
            hass, 1, f"{DOMAIN}.{entry.entry_id}.acknowledged_devices"
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(
                seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )

    # -- Optionen ---------------------------------------------------------

    @property
    def track_address_source(self) -> bool:
        """Ob DHCP/statisch mit erfasst werden soll."""
        return self.entry.options.get(
            CONF_TRACK_ADDRESS_SOURCE, DEFAULT_TRACK_ADDRESS_SOURCE
        )

    @property
    def address_source_interval(self) -> timedelta:
        """Abstand zwischen zwei IP-Typ-Abfragen."""
        return timedelta(
            minutes=self.entry.options.get(
                CONF_ADDRESS_SOURCE_INTERVAL, DEFAULT_ADDRESS_SOURCE_INTERVAL
            )
        )

    # -- Abruf ------------------------------------------------------------

    def _address_sources_due(self) -> bool:
        """Prueft, ob die langsame IP-Typ-Abfrage jetzt faellig ist."""
        if not self.track_address_source:
            return False
        if self._address_source_scan is None:
            return True
        return dt_util.utcnow() - self._address_source_scan >= self.address_source_interval

    def _ptr_records_due(self) -> bool:
        """Refresh PTR data on the same slow cadence as address-source data."""
        if self._ptr_scan is None:
            return True
        return dt_util.utcnow() - self._ptr_scan >= self.address_source_interval

    async def async_refresh_all(self) -> None:
        """Aktualisiert auch die langsam getakteten IP-Typ- und PTR-Felder."""
        self._address_source_scan = None
        self._ptr_scan = None
        # ``async_request_refresh`` laeuft durch den Coordinator-Debouncer und
        # kann mit einem bereits geplanten Abruf zusammenfallen. Nach einer
        # Umbenennung bzw. einem manuellen Aktualisieren muessen PTR 1/2 jedoch
        # sicher aus einer neuen FRITZ!Box-DNS-Abfrage stammen.
        await self.async_refresh()

    def _fetch_address_sources(self, macs: list[str]) -> None:
        """Holt DHCP/statisch je Geraet (ein SOAP-Aufruf pro MAC-Adresse)."""
        sources: dict[str, dict[str, Any]] = {}
        for mac in macs:
            if not mac:
                continue
            try:
                entry = self.fritz_hosts.get_specific_host_entry(mac)
            except FritzConnectionException as err:
                # Einzelne Geraete koennen der FRITZ!Box unbekannt sein
                # (z. B. Mesh-Clients hinter einem Repeater). Das ist kein
                # Grund, die gesamte Aktualisierung scheitern zu lassen.
                _LOGGER.debug("IP-Typ fuer %s nicht abrufbar: %s", mac, err)
                continue
            sources[mac_key(mac)] = {
                "address_source": entry.get("NewAddressSource"),
                "lease_time_remaining": entry.get("NewLeaseTimeRemaining"),
            }
        # TR-064 meldet bei einer reservierten DHCP-Adresse weiterhin
        # AddressSource=DHCP. Das Checkbox-Feld gibt es nur in der WebUI.
        try:
            web = FritzBoxWebClient(
                str(self.entry.data[CONF_HOST]),
                str(self.entry.data[CONF_USERNAME]),
                str(self.entry.data[CONF_PASSWORD]),
                bool(self.entry.data.get(CONF_USE_TLS, DEFAULT_USE_TLS)),
            )
            for summary in web.devices():
                device = web.detail(summary)
                key = mac_key(web._mac(device))
                fixed = fixed_ipv4_assignment(device)
                if key and fixed is not None:
                    sources.setdefault(key, {})["static_ip"] = fixed
        except Exception as err:  # WebUI ist eine optionale Zusatzquelle
            _LOGGER.debug("Dauerhafte IPv4-Zuweisungen nicht abrufbar: %s", err)
        self._address_sources = sources

    def pihole_client(self) -> PiholeClient:
        """Erzeugt den Pi-hole-Client aus den gespeicherten Optionen."""
        options = self.entry.options
        if not options.get(CONF_PIHOLE_ENABLED, False):
            raise PiholeApiError("Pi-hole-Synchronisierung ist nicht aktiviert")
        password = str(options.get(CONF_PIHOLE_PASSWORD, ""))
        if not password:
            raise PiholeApiError("Pi-hole-Kennwort fehlt")
        return PiholeClient(
            str(options.get(CONF_PIHOLE_HOST, DEFAULT_PIHOLE_HOST)),
            password,
            str(options.get(CONF_PIHOLE_DOMAIN, DEFAULT_PIHOLE_DOMAIN)),
        )

    def _fetch(self) -> tuple[list[dict[str, Any]], bool, bool]:
        """Blockierender Teil des Abrufs, laeuft im Executor."""
        tr064_hosts = self.fritz_hosts.get_hosts_attributes()
        try:
            web = FritzBoxWebClient(
                str(self.entry.data[CONF_HOST]),
                str(self.entry.data[CONF_USERNAME]),
                str(self.entry.data[CONF_PASSWORD]),
                bool(self.entry.data.get(CONF_USE_TLS, DEFAULT_USE_TLS)),
            )
            raw_hosts = web.authoritative_hosts(tr064_hosts)
            _LOGGER.debug(
                "FRITZ!Box-Geräteliste: %d IPv4-Einträge aus WebUI/netDev",
                len(raw_hosts),
            )
        except Exception as err:
            # Lesefehler der undokumentierten WebUI duerfen die Integration
            # nicht lahmlegen. Der Fallback wird unten nochmals streng
            # bereinigt, damit keine PC-MAC-Karteileichen verarbeitet werden.
            _LOGGER.warning(
                "WebUI/netDev nicht verfügbar, verwende TR-064-Fallback: %s", err
            )
            raw_hosts = tr064_hosts
        refreshed = False
        query_hosts = build_hosts(raw_hosts)
        if self._address_sources_due():
            macs = [str(host.get("mac") or "") for host in query_hosts]
            self._fetch_address_sources(macs)
            refreshed = True
        ptr_refreshed = False
        if self._ptr_records_due():
            ips = [str(host.get("ip") or "") for host in query_hosts]
            dns_server = str(self.entry.data[CONF_HOST]).strip()
            dns_server = dns_server.removeprefix("http://").removeprefix("https://")
            dns_server = dns_server.split("/", 1)[0].split(":", 1)[0]
            self._ptr_records = resolve_ptr_map(ips, dns_server)
            ptr_refreshed = True
        if self.entry.options.get(CONF_PIHOLE_ENABLED, False):
            try:
                self._pihole_records = self.pihole_client().list_records()
                self._pihole_error = ""
            except Exception as err:
                # Die FRITZ!Box-Liste bleibt auch bei einem Pi-hole-Fehler nutzbar.
                self._pihole_error = str(err)
                _LOGGER.warning("Pi-hole-DNS-Einträge nicht abrufbar: %s", err)
        else:
            self._pihole_records = []
            self._pihole_error = ""
        return raw_hosts, refreshed, ptr_refreshed

    def _ha_device_map(self) -> dict[str, dict[str, str]]:
        """Bildet MAC-Adressen auf Home-Assistant-Geraete ab.

        Grundlage ist die Geraeteregistrierung: jedes Geraet, das eine
        Verbindung vom Typ ``mac`` hinterlegt hat, wird ueber genau diese
        MAC-Adresse zugeordnet. Es wird nichts geraten - Geraete ohne
        MAC-Verbindung bleiben in der Karte einfach ohne HA-Namen.
        """
        registry = dr.async_get(self.hass)
        mapping: dict[str, dict[str, str]] = {}
        for device in registry.devices.values():
            if device.disabled_by is not None:
                continue
            name = device.name_by_user or device.name or ""
            for connection_type, connection_value in device.connections:
                if connection_type != dr.CONNECTION_NETWORK_MAC:
                    continue
                key = mac_key(connection_value)
                if not key or key in mapping:
                    continue
                mapping[key] = {
                    "name": name,
                    "device_id": device.id,
                    "area": device.area_id or "",
                }
        return mapping

    async def _async_update_data(self) -> dict[str, Any]:
        """Holt die Geraeteliste und reichert sie an."""
        try:
            raw_hosts, refreshed, ptr_refreshed = await self.hass.async_add_executor_job(self._fetch)
        except (FritzSecurityError, FritzAuthorizationError) as err:
            raise ConfigEntryAuthFailed(
                "Das FRITZ!Box-Konto hat keine ausreichenden Rechte. Benoetigt wird "
                "die Berechtigung 'FRITZ!Box Einstellungen'."
            ) from err
        except FritzServiceError as err:
            raise UpdateFailed(
                "Der Dienst 'Hosts' ist auf dieser FRITZ!Box nicht verfuegbar. "
                "Ist 'Zugriff fuer Anwendungen zulassen' aktiviert?"
            ) from err
        except FritzConnectionException as err:
            raise UpdateFailed(f"Abruf der Geraeteliste fehlgeschlagen: {err}") from err

        if refreshed:
            self._address_source_scan = dt_util.utcnow()
        if ptr_refreshed:
            self._ptr_scan = dt_util.utcnow()

        hosts = build_hosts(
            raw_hosts,
            self._address_sources if self.track_address_source else None,
            self._ha_device_map(),
        )
        apply_fritzsync_fields(
            hosts,
            self._ptr_records,
            self._comments,
            str(self.entry.data[CONF_HOST]),
        )
        current_macs = {mac_key(host.get("mac")) for host in hosts if mac_key(host.get("mac"))}
        if not self._new_devices_initialized:
            # Beim ersten Start bilden die vorhandenen Geraete den Ausgangsbestand.
            self._acknowledged_macs.update(current_macs)
            self._new_devices_initialized = True
            await self._new_device_store.async_save(
                {"initialized": True, "acknowledged": sorted(self._acknowledged_macs)}
            )
        for host in hosts:
            host["is_new"] = mac_key(host.get("mac")) not in self._acknowledged_macs

        domain = str(
            self.entry.options.get(CONF_PIHOLE_DOMAIN, DEFAULT_PIHOLE_DOMAIN)
        )
        managed: set[str] = set()
        for host in hosts:
            try:
                if host.get("ip") and host.get("name"):
                    managed.add(f"{host['ip']} {fqdn(str(host['name']), domain)}")
            except PiholeApiError:
                continue
        pihole_entries = []
        for record in self._pihole_records:
            item = split_record(record)
            item["managed"] = record.lower() in managed
            pihole_entries.append(item)
        pihole_manual = [item for item in pihole_entries if not item["managed"]]

        return {
            "hosts": hosts,
            "summary": summarize(hosts),
            "last_scan": dt_util.utcnow().isoformat(),
            "address_source_scan": (
                self._address_source_scan.isoformat()
                if self._address_source_scan
                else None
            ),
            "track_address_source": self.track_address_source,
            "pihole_records": pihole_manual,
            "pihole_entries": pihole_entries,
            "pihole_error": self._pihole_error,
            "pihole_enabled": bool(
                self.entry.options.get(CONF_PIHOLE_ENABLED, False)
            ),
        }

    async def async_invalidate_address_sources(self) -> None:
        """Erzwingt beim naechsten Durchlauf eine neue IP-Typ-Abfrage."""
        self._address_source_scan = None

    async def async_load_comments(self) -> None:
        """Load MAC-based device comments from Home Assistant storage."""
        stored = await self._comment_store.async_load()
        if isinstance(stored, dict):
            self._comments = {
                mac_key(key): str(value)[:250]
                for key, value in stored.items()
                if mac_key(key) and str(value).strip()
            }

        new_state = await self._new_device_store.async_load()
        if isinstance(new_state, dict) and new_state.get("initialized"):
            self._new_devices_initialized = True
            self._acknowledged_macs = {
                mac_key(value)
                for value in new_state.get("acknowledged", [])
                if mac_key(value)
            }

    async def async_set_comment(self, mac: str, comment: str) -> None:
        """Persist or remove a device comment and refresh the sensor."""
        key = mac_key(mac)
        if not key:
            raise ValueError("Ungueltige MAC-Adresse")
        value = str(comment).strip()[:250]
        if value:
            self._comments[key] = value
        else:
            self._comments.pop(key, None)
        await self._comment_store.async_save(self._comments)
        await self.async_request_refresh()

    async def async_acknowledge_device(self, mac: str) -> None:
        """Mark a newly detected MAC address as reviewed."""
        key = mac_key(mac)
        if not key:
            raise ValueError("Ungueltige MAC-Adresse")
        self._acknowledged_macs.add(key)
        self._new_devices_initialized = True
        await self._new_device_store.async_save(
            {"initialized": True, "acknowledged": sorted(self._acknowledged_macs)}
        )
        await self.async_request_refresh()
