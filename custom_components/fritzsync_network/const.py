"""Konstanten der Integration fritzsync_network."""

from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "fritzsync_network"
MANUFACTURER: Final = "FRITZ!"
VERSION: Final = "1.10.11"

PLATFORMS: Final = [Platform.SENSOR]

# --- Konfiguration (Config Entry) ---------------------------------------
CONF_USE_TLS: Final = "use_tls"

DEFAULT_HOST: Final = "fritz.box"
DEFAULT_USERNAME: Final = "admin"
DEFAULT_USE_TLS: Final = False

# --- Optionen (Options Flow) --------------------------------------------
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_TRACK_ADDRESS_SOURCE: Final = "track_address_source"
CONF_ADDRESS_SOURCE_INTERVAL: Final = "address_source_interval"
CONF_PIHOLE_ENABLED: Final = "pihole_enabled"
CONF_PIHOLE_HOST: Final = "pihole_host"
CONF_PIHOLE_PASSWORD: Final = "pihole_password"
CONF_PIHOLE_DOMAIN: Final = "pihole_domain"

DEFAULT_SCAN_INTERVAL: Final = 60  # Sekunden
DEFAULT_TRACK_ADDRESS_SOURCE: Final = True
DEFAULT_ADDRESS_SOURCE_INTERVAL: Final = 15  # Minuten
DEFAULT_PIHOLE_ENABLED: Final = False
DEFAULT_PIHOLE_HOST: Final = "https://192.168.9.252"
DEFAULT_PIHOLE_DOMAIN: Final = "fritz.box"

MIN_SCAN_INTERVAL: Final = 15
MAX_SCAN_INTERVAL: Final = 3600

# --- Attribute des Sammelsensors ----------------------------------------
ATTR_HOSTS: Final = "hosts"
ATTR_TOTAL: Final = "gesamt"
ATTR_ACTIVE: Final = "aktiv"
ATTR_INACTIVE: Final = "inaktiv"
ATTR_GUESTS: Final = "gastnetz"
ATTR_BLOCKED: Final = "gesperrt"
ATTR_UPDATES: Final = "updates_verfuegbar"
ATTR_STATIC: Final = "statische_ip"
ATTR_LAST_SCAN: Final = "letzte_abfrage"
ATTR_ADDRESS_SOURCE_SCAN: Final = "letzte_ip_typ_abfrage"
ATTR_ADDRESS_SOURCE_STATE: Final = "ip_typ_erfassung"
ATTR_PIHOLE_RECORDS: Final = "pihole_manuelle_eintraege"
ATTR_PIHOLE_ERROR: Final = "pihole_fehler"
ATTR_PIHOLE_ENABLED: Final = "pihole_aktiv"
ATTR_PIHOLE_ENTRIES: Final = "pihole_eintraege"

# --- Dienste -------------------------------------------------------------
SERVICE_SET_DEVICE_NAME: Final = "set_device_name"
SERVICE_WAKE_ON_LAN: Final = "wake_on_lan"
SERVICE_SET_COMMENT: Final = "set_device_comment"
SERVICE_ACKNOWLEDGE_DEVICE: Final = "acknowledge_device"
SERVICE_PIHOLE_ADD_RECORD: Final = "pihole_add_record"
SERVICE_PIHOLE_UPDATE_RECORD: Final = "pihole_update_record"
SERVICE_PIHOLE_DELETE_RECORD: Final = "pihole_delete_record"
SERVICE_PIHOLE_SYNC_ALL: Final = "pihole_sync_all"
SERVICE_CLEANUP_STALE_HOSTS: Final = "cleanup_stale_hosts"
SERVICE_REFRESH: Final = "refresh"

ATTR_MAC: Final = "mac"
ATTR_NAME: Final = "name"
ATTR_COMMENT: Final = "comment"
ATTR_IP: Final = "ip"
ATTR_DNS_NAMES: Final = "dns_names"
ATTR_OLD_RECORD: Final = "old_record"

# --- Dashboard-Karte -----------------------------------------------------
CARD_FILENAME: Final = "fritzsync-network-card.js"
URL_BASE: Final = f"/{DOMAIN}"
CARD_URL: Final = f"{URL_BASE}/{CARD_FILENAME}"
