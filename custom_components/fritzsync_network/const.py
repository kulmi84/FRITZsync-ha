"""Constants for FritzSync Network."""

DOMAIN = "fritzsync_network"
VERSION = "0.2.4"
PLATFORMS = ["sensor"]
CARD_FILENAME = "fritzsync-network-card.js"
URL_BASE = f"/{DOMAIN}"
CARD_URL = f"{URL_BASE}/{CARD_FILENAME}"

CONF_USE_TLS = "use_tls"
CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_HOST = "fritz.box"
DEFAULT_SCAN_INTERVAL = 60

SERVICE_RENAME = "rename_device"
SERVICE_SET_BLOCKED = "set_internet_blocked"
SERVICE_WAKE = "wake_device"

ATTR_ENTRY_ID = "entry_id"
ATTR_MAC = "mac"
ATTR_IP = "ip"
ATTR_NAME = "name"
ATTR_BLOCKED = "blocked"
