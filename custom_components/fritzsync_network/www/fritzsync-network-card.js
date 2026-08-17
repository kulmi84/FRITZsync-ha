/**
 * FRITZ!Sync - Homeassistant - Dashboard-Karte
 * Teil der Integration fritzsync_network (kulmi84).
 *
 * Bewusste Entwurfsentscheidungen:
 *
 * - Light DOM statt Shadow DOM. Im Shadow DOM loest <ha-icon> seine
 *   Icon-Definitionen unzuverlaessig auf, und ein zweiter Ladeweg der
 *   Moduldatei bricht dort still mit einer DOMException ab. Alle
 *   CSS-Klassen tragen deshalb das Praefix "fbn-", damit nichts in
 *   fremde Karten ausblutet.
 * - Skelett-Rendering: Werkzeugleiste und Tabellenkopf werden genau
 *   einmal gebaut, bei neuen Daten wird nur der <tbody> ersetzt. Damit
 *   verliert das Suchfeld bei jeder Aktualisierung des Sensors weder
 *   Fokus noch Inhalt und die Scrollposition bleibt stehen.
 * - Ein customElements.get()-Waechter verhindert, dass ein doppelt
 *   eingebundenes Modul beim zweiten define() abbricht.
 */

const FBN_VERSION = "1.10.19";

/* ------------------------------------------------------------------ */
/* Konfiguration                                                       */
/* ------------------------------------------------------------------ */

const CONFIG_DEFAULTS = {
  entity: "",
  title: "Netzwerkgeräte",

  // Spalten
  show_status: true,
  show_name: true,
  show_network: true,
  show_ip: true,
  show_mac: true,
  show_ptr1: true,
  show_ptr2: false,
  show_comment: true,
  show_connection: true,
  show_ha_name: true,
  show_ip_type: true,
  show_wan: true,
  show_update: true,
  show_speed: true,
  show_model: false,
  show_type: false,
  column_order: [],

  // Darstellung
  show_summary: true,
  show_search: true,
  show_filter: true,
  show_filter_all: true,
  show_filter_active: true,
  show_filter_inactive: true,
  show_filter_guest: true,
  show_filter_blocked: true,
  show_filter_update: true,
  show_filter_new: true,
  show_filter_manual: true,
  show_filter_networks: true,
  show_refresh: true,
  show_pihole_records: true,
  hide_inactive: false,
  compact: false,
  max_rows: 0,
  show_details_popup: true,
  open_device_on_click: true,
  show_scroll_arrows: true,
  sticky_name: true,
  ip_opens_web: true,
  ip_web_fallback: true,

  // Sortierung
  sort_by: "ip",
  sort_dir: "asc",

  // Farben (leer = Wert des aktiven Themes)
  color_header_bg: "",
  color_header_text: "",
  color_row_text: "",
  color_row_alt_bg: "",
  color_border: "",
  color_active: "",
  color_inactive: "",
  color_guest: "",
  color_blocked: "",
  color_update: "",
  color_static: "",
  color_accent: "",
};

/**
 * Spaltendefinition. "prio" steuert das Verhalten auf schmalen Karten:
 * 3 verschwindet zuerst, dann 2. Spalten mit prio 1 bleiben immer.
 */
const COLUMNS = [
  { key: "status", cfg: "show_status", label: "", short: "", prio: 1, sortable: true, align: "center" },
  { key: "name", cfg: "show_name", label: "FRITZ!Box-Name", prio: 1, sortable: true },
  { key: "network", cfg: "show_network", label: "Netz", prio: 2, sortable: true },
  { key: "mac", cfg: "show_mac", label: "MAC-Adresse", prio: 3, sortable: true },
  { key: "ptr2", cfg: "show_ptr2", label: "PTR 2", prio: 3, sortable: true },
  { key: "ip", cfg: "show_ip", label: "IP-Adresse", prio: 1, sortable: true },
  { key: "ptr1", cfg: "show_ptr1", label: "PTR 1", prio: 2, sortable: true },
  { key: "comment", cfg: "show_comment", label: "Kommentar", prio: 2, sortable: true },
  { key: "connection", cfg: "show_connection", label: "Verbindung", prio: 2, sortable: true },
  { key: "ha_name", cfg: "show_ha_name", label: "Home Assistant", prio: 2, sortable: true },
  { key: "ip_type", cfg: "show_ip_type", label: "IP-Typ", prio: 3, sortable: true },
  { key: "wan", cfg: "show_wan", label: "Internet", prio: 3, sortable: true, align: "center" },
  { key: "update", cfg: "show_update", label: "Update", prio: 3, sortable: true, align: "center" },
  { key: "speed", cfg: "show_speed", label: "Tempo", prio: 3, sortable: true, align: "right" },
  { key: "model", cfg: "show_model", label: "Modell", prio: 3, sortable: true },
  { key: "type", cfg: "show_type", label: "Gerätetyp", prio: 3, sortable: true },
];

const DEFAULT_COLUMN_WIDTHS = {
  status: 40, name: 220, network: 100, mac: 150, ptr1: 180, ptr2: 180,
  ip: 130, comment: 150, connection: 125, ha_name: 150, ip_type: 100,
  wan: 80, update: 80, speed: 95, model: 140, type: 120,
};

const FILTERS = [
  { key: "alle", cfg: "show_filter_all", label: "Alle", icon: "mdi:format-list-bulleted" },
  { key: "aktiv", cfg: "show_filter_active", label: "Aktiv", icon: "mdi:lan-connect" },
  { key: "inaktiv", cfg: "show_filter_inactive", label: "Inaktiv", icon: "mdi:lan-disconnect" },
  { key: "gast", cfg: "show_filter_guest", label: "Gast", icon: "mdi:account-question" },
  { key: "gesperrt", cfg: "show_filter_blocked", label: "Gesperrt", icon: "mdi:web-off" },
  { key: "update", cfg: "show_filter_update", label: "Update", icon: "mdi:package-down" },
  { key: "neu", cfg: "show_filter_new", label: "Neu", icon: "mdi:new-box" },
  { key: "manuell", cfg: "show_filter_manual", label: "Manuell", icon: "mdi:dns" },
];

/** Standardfarbe je Farbschluessel, wenn der Nutzer nichts gesetzt hat. */
const COLOR_FALLBACKS = {
  color_header_bg: "var(--table-row-alternative-background-color, var(--secondary-background-color))",
  color_header_text: "var(--secondary-text-color)",
  color_row_text: "var(--primary-text-color)",
  color_row_alt_bg: "transparent",
  color_border: "var(--divider-color)",
  color_active: "var(--success-color, #43a047)",
  color_inactive: "var(--disabled-text-color, #9e9e9e)",
  color_guest: "var(--warning-color, #ffa600)",
  color_blocked: "var(--error-color, #db4437)",
  color_update: "var(--info-color, #039be5)",
  color_static: "var(--primary-color)",
  color_accent: "var(--primary-color)",
};

const COLOR_EDITOR_FIELDS = [
  { key: "color_header_bg", label: "Kopfzeile Hintergrund" },
  { key: "color_header_text", label: "Kopfzeile Schrift" },
  { key: "color_row_text", label: "Zeilen Schrift" },
  { key: "color_row_alt_bg", label: "Jede zweite Zeile" },
  { key: "color_border", label: "Trennlinien" },
  { key: "color_active", label: "Aktiv" },
  { key: "color_inactive", label: "Inaktiv" },
  { key: "color_guest", label: "Gastnetz" },
  { key: "color_blocked", label: "Gesperrt" },
  { key: "color_update", label: "Update verfügbar" },
  { key: "color_static", label: "Statische IP" },
  { key: "color_accent", label: "Akzent (Sortierung, Filter)" },
];

/* ------------------------------------------------------------------ */
/* Hilfsfunktionen                                                     */
/* ------------------------------------------------------------------ */

/** Fuellt fehlende Schluessel mit den Standardwerten auf. */
function withDefaults(config) {
  return { ...CONFIG_DEFAULTS, ...(config || {}) };
}

function orderedColumns(config) {
  const known = new Map(COLUMNS.map((column) => [column.key, column]));
  const requested = Array.isArray(config.column_order) ? config.column_order : [];
  const keys = [...new Set(requested.filter((key) => known.has(key)))];
  for (const column of COLUMNS) if (!keys.includes(column.key)) keys.push(column.key);
  return keys.map((key) => known.get(key));
}

/**
 * Laesst nur Farbwerte durch, die sicher in eine CSS-Variable koennen.
 * Alles mit ; < > { } ( ) ausserhalb von rgb/hsl/var oder mit url()
 * wird verworfen - so kann ueber die Kartenkonfiguration kein fremdes
 * CSS eingeschleust werden.
 */
function sanitizeColor(value) {
  if (typeof value !== "string") return "";
  const text = value.trim();
  if (!text) return "";
  if (text.length > 120) return "";
  if (/[;<>{}\\]/.test(text)) return "";
  if (/url\s*\(|expression|@import|javascript:/i.test(text)) return "";
  if (/^#[0-9a-f]{3,8}$/i.test(text)) return text;
  if (/^[a-z][a-z0-9-]*$/i.test(text)) return text;
  if (/^(rgb|rgba|hsl|hsla|var|color-mix)\([^()]*(\([^()]*\))?[^()]*\)$/i.test(text)) {
    return text;
  }
  return "";
}

const HEX_COLOR_RE = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i;

/** Wandelt Kurzschreibweisen wie #abc in #aabbcc, sonst leer. */
function normalizeHex(value) {
  if (typeof value !== "string" || !HEX_COLOR_RE.test(value.trim())) return "";
  let hex = value.trim().toLowerCase();
  if (hex.length === 4) {
    hex = "#" + hex[1] + hex[1] + hex[2] + hex[2] + hex[3] + hex[3];
  }
  return hex;
}

/** Maskiert Text, der aus der FRITZ!Box stammt, vor der HTML-Ausgabe. */
function escapeHtml(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/**
 * Liefert auch innerhalb der verschachtelten Home-Assistant-Shadow-Roots
 * das wirklich fokussierte Element. document.activeElement endet dort
 * sonst bereits am aeusseren Host und erkennt unsere Eingabefelder nicht.
 */
function deepActiveElement() {
  let active = document.activeElement;
  while (active && active.shadowRoot && active.shadowRoot.activeElement) {
    active = active.shadowRoot.activeElement;
  }
  return active;
}

/** Sortierschluessel, der IPv4-Adressen numerisch ordnet. */
function ipSortKey(ip) {
  const parts = String(ip || "").split(".");
  if (parts.length !== 4) return Number.MAX_SAFE_INTEGER;
  let value = 0;
  for (const part of parts) {
    const octet = Number(part);
    if (!Number.isInteger(octet) || octet < 0 || octet > 255) {
      return Number.MAX_SAFE_INTEGER;
    }
    value = value * 256 + octet;
  }
  return value;
}

/** Prueft eine IPv4-Adresse gegen ein CIDR-Netz, auch ausserhalb von /24. */
function ipv4InCidr(ip, cidr) {
  const [network, prefixText] = String(cidr || "").split("/");
  const ipValue = ipSortKey(ip);
  const networkValue = ipSortKey(network);
  const prefix = Number(prefixText);
  if (ipValue === Number.MAX_SAFE_INTEGER || networkValue === Number.MAX_SAFE_INTEGER
      || !Number.isInteger(prefix) || prefix < 0 || prefix > 32) return false;
  const blockSize = 2 ** (32 - prefix);
  return Math.floor(ipValue / blockSize) === Math.floor(networkValue / blockSize);
}

/** "1000 Mbit/s" bzw. "—" bei unbekanntem Tempo. */
function formatSpeed(speed) {
  const value = Number(speed) || 0;
  if (value <= 0) return "—";
  if (value >= 1000 && value % 1000 === 0) return `${value / 1000} Gbit/s`;
  return `${value} Mbit/s`;
}

/** Restlaufzeit der DHCP-Zuweisung in lesbarer Form. */
function formatLease(seconds) {
  const value = Number(seconds);
  if (!Number.isFinite(value) || value <= 0) return "";
  if (value < 3600) return `noch ${Math.round(value / 60)} min`;
  if (value < 86400) return `noch ${Math.round(value / 3600)} h`;
  return `noch ${Math.round(value / 86400)} Tage`;
}

/** Icon je Verbindungsart. */
function connectionIcon(host) {
  if (!host.active) return "mdi:lan-disconnect";
  if (host.connection === "wlan") return "mdi:wifi";
  if (host.connection === "lan") return "mdi:ethernet";
  if (host.connection === "powerline") return "mdi:power-plug";
  return "mdi:help-network-outline";
}

/**
 * Ermittelt die Webadresse eines Geraets fuer den Klick auf die
 * IP-Adresse. Bevorzugt die von der FRITZ!Box gemeldete URL
 * (X_AVM-DE_URL), faellt sonst - falls erlaubt - auf http://<ip> zurueck.
 * Aus Sicherheitsgruenden werden ausschliesslich http/https zugelassen;
 * alles andere (z. B. ein manipuliertes javascript:-Schema) wird
 * verworfen.
 */
function webUrl(host, allowFallback) {
  const raw = String(host.url || "").trim();
  if (/^https?:\/\/\S+$/i.test(raw)) return raw;
  if (allowFallback && host.ip) {
    const ip = String(host.ip).trim();
    // Nur eine plausible IPv4/Hostadresse akzeptieren.
    if (/^[a-z0-9.:_-]+$/i.test(ip)) return `http://${ip}`;
  }
  return "";
}

/** Wert, nach dem eine bestimmte Spalte sortiert wird. */
function sortValue(host, key) {
  switch (key) {
    case "status":
      return host.active ? 0 : 1;
    case "name":
      return String(host.name || "").toLowerCase();
    case "ip":
      return ipSortKey(host.ip);
    case "mac":
      return String(host.mac || "");
    case "network":
    case "ptr1":
    case "ptr2":
    case "comment":
      return String(host[key] || "").toLowerCase();
    case "connection":
      return String(host.connection_label || "").toLowerCase();
    case "ha_name":
      // Geraete ohne Home-Assistant-Zuordnung ans Ende sortieren.
      return host.ha_name ? `0${String(host.ha_name).toLowerCase()}` : "1";
    case "ip_type":
      if (host.static_ip === true) return "0";
      if (host.static_ip === false) return "1";
      return "2";
    case "wan":
      return host.blocked ? 0 : 1;
    case "update":
      return host.update_available ? 0 : 1;
    case "speed":
      return Number(host.speed) || 0;
    case "model":
      return String(host.model || "").toLowerCase();
    case "type":
      return String(host.device_class_user || host.device_class || "").toLowerCase();
    default:
      return "";
  }
}

/* ------------------------------------------------------------------ */
/* Karte                                                               */
/* ------------------------------------------------------------------ */

class FritzSyncNetworkCard extends HTMLElement {
  constructor() {
    super();
    this._config = withDefaults({});
    this._hass = null;
    this._search = "";
    this._filter = "aktiv";
    // Netz und Status sind getrennte Filter. So kann z. B. innerhalb
    // des Gastnetzes zwischen "Aktiv" und "Alle" gewechselt werden.
    this._networkFilter = "";
    this._sortBy = "ip";
    this._sortDir = "asc";
    this._signature = "";
    this._built = false;
    this._resizeObserver = null;
    // Popup: der Overlay-Knoten haengt am document.body, nicht in der
    // Karte - so liegt er sicher ueber allem, unabhaengig von den
    // Stapelkontexten des Dashboards. Gemerkt wird die MAC-Adresse des
    // gerade gezeigten Geraets, um den Inhalt bei neuen Sensordaten
    // aktualisieren zu koennen.
    this._popup = null;
    this._popupMac = null;
    this._popupReturnFocus = null;
    this._onPopupKeydown = null;
    this._piholeEditing = "";
    this._piholeDraft = false;
    this._piholeEdits = {};
    this._piholeHiddenRecords = new Set();
    this._busyCount = 0;
    this._columnWidths = {};
  }

  /* -- Lovelace-Schnittstelle -------------------------------------- */

  setConfig(config) {
    if (!config || !config.entity) {
      throw new Error("Bitte den Sensor mit der Geräteliste auswählen (entity).");
    }
    this._config = withDefaults(config);
    try {
      this._columnWidths = JSON.parse(
        localStorage.getItem(`fritzsync-column-widths:${this._config.entity}`) || "{}"
      );
    } catch (_error) {
      this._columnWidths = {};
    }
    this._sortBy = this._config.sort_by;
    this._sortDir = this._config.sort_dir === "desc" ? "desc" : "asc";
    this._built = false;
    this._signature = "";
    this._closePopup();
    this.innerHTML = "";
    if (this._hass) this._update();
  }

  set hass(hass) {
    this._hass = hass;
    this._update();
  }

  getCardSize() {
    const rows = this._hosts().length;
    return Math.min(12, 3 + Math.ceil(rows / 3));
  }

  static getConfigElement() {
    return document.createElement("fritzsync-network-card-editor");
  }

  static getStubConfig(hass) {
    const entity = Object.keys(hass && hass.states ? hass.states : {}).find(
      (id) => id.startsWith("sensor.") && id.includes("gerate")
    );
    return { type: "custom:fritzsync-network-card", entity: entity || "" };
  }

  connectedCallback() {
    this._observeWidth();
  }

  disconnectedCallback() {
    if (this._resizeObserver) {
      this._resizeObserver.disconnect();
      this._resizeObserver = null;
    }
    // Ein offenes Popup nicht verwaist am body haengen lassen.
    this._closePopup();
  }

  /* -- Daten -------------------------------------------------------- */

  _stateObj() {
    if (!this._hass || !this._config.entity) return null;
    return this._hass.states[this._config.entity] || null;
  }

  _hosts() {
    const state = this._stateObj();
    if (!state || !state.attributes) return [];
    const hosts = state.attributes.hosts;
    return Array.isArray(hosts) ? hosts : [];
  }

  _manualPiholeHosts() {
    const state = this._stateObj();
    const attributes = (state && state.attributes) || {};
    if (!this._config.show_pihole_records || !attributes.pihole_aktiv) return [];
    const allEntries = Array.isArray(attributes.pihole_eintraege)
      ? attributes.pihole_eintraege : [];
    const currentRecords = new Set(allEntries.map((item) => item.record));
    for (const record of this._piholeHiddenRecords) {
      if (!currentRecords.has(record)) this._piholeHiddenRecords.delete(record);
    }
    const entries = allEntries.filter(
      (item) => !this._piholeHiddenRecords.has(item.record)
    );
    const networks = Array.from(new Map(
      this._hosts()
        .filter((host) => host.network && host.network !== "manuell")
        .map((host) => [host.network, host.zone || "Netz"])
    ).entries()).sort((left, right) => {
      const leftPrefix = Number(String(left[0]).split("/")[1]) || 0;
      const rightPrefix = Number(String(right[0]).split("/")[1]) || 0;
      return rightPrefix - leftPrefix;
    });
    return entries.filter((item) => !item.managed).map((item, index) => {
      const matched = networks.find(([network]) => ipv4InCidr(item.ip, network));
      const network = matched ? matched[0] : "manuell";
      const zone = matched ? matched[1] : "manuell";
      const guest = zone === "Gast" || zone === "Gast/anderes Netz";
      return {
      _pihole: true,
      _record: item.record,
      _pihole_index: index,
      name: item.names,
      ip: item.ip,
      network,
      zone,
      guest,
      active: false,
      mac: "",
      connection: "unbekannt",
      connection_label: "—",
      ptr1: "",
      ptr2: "",
      comment: "",
      ha_name: "",
      speed: 0,
      };
    });
  }

  _listHosts() {
    return [...this._hosts(), ...this._manualPiholeHosts()];
  }

  /** Erkennt, ob sich an den angezeigten Daten ueberhaupt etwas geaendert hat. */
  _computeSignature(hosts) {
    return hosts
      .map((host) =>
        [
          host.mac,
          host.ip,
          host.name,
          host.active ? 1 : 0,
          host.connection_label,
          host.network,
          host.ptr1,
          host.ptr2,
          host.comment,
          host.is_new ? 1 : 0,
          host.ha_name,
          host.static_ip,
          host.blocked ? 1 : 0,
          host.update_available ? 1 : 0,
          host.speed,
          host.stale_ip_duplicate ? 1 : 0,
        ].join("|")
      )
      .join("~");
  }

  _visibleColumns() {
    return orderedColumns(this._config).filter((column) => this._config[column.cfg]);
  }

  _columnStyle(column) {
    return `text-align:${column.align || "left"}`;
  }

  _renderColgroup() {
    const group = this.querySelector(".fbn-colgroup");
    if (!group) return;
    const columns = this._visibleColumns();
    const widths = columns.map((column) =>
      Number(this._columnWidths[column.key]) || DEFAULT_COLUMN_WIDTHS[column.key] || 100
    );
    const total = widths.reduce((sum, width) => sum + width, 0) || 1;
    group.innerHTML = columns.map((column, index) => {
      const percent = widths[index] / total * 100;
      return `<col class="fbn-coldef-${column.key}" style="width:${percent.toFixed(4)}%">`;
    }).join("");
  }

  _saveColumnWidths() {
    try {
      localStorage.setItem(
        `fritzsync-column-widths:${this._config.entity}`,
        JSON.stringify(this._columnWidths)
      );
    } catch (_error) {
      // Private Browsermodi koennen localStorage sperren; Ziehen wirkt dann
      // weiterhin bis zum naechsten Neuladen.
    }
  }

  _setBusy(busy) {
    this._busyCount = Math.max(0, this._busyCount + (busy ? 1 : -1));
    if (this._root) {
      this._root.classList.toggle("fbn-busy", this._busyCount > 0);
      this._root.setAttribute("aria-busy", this._busyCount > 0 ? "true" : "false");
    }
  }

  _stickyColumnsEnabled() {
    const keys = this._visibleColumns().map((column) => column.key);
    return this._config.sticky_name && keys[0] === "status" && keys[1] === "name";
  }

  _applyStatusFilter(hosts, filter) {
    switch (filter) {
      case "aktiv":
        return hosts.filter((host) => !host._pihole && host.active);
      case "inaktiv":
        return hosts.filter((host) => !host._pihole && !host.active);
      case "gast":
        return hosts.filter((host) => host.guest);
      case "gesperrt":
        return hosts.filter((host) => !host._pihole && host.blocked);
      case "update":
        return hosts.filter((host) => !host._pihole && host.update_available);
      case "neu":
        return hosts.filter((host) => !host._pihole && host.is_new);
      case "manuell":
        return hosts.filter((host) => host._pihole);
      default:
        return hosts;
    }
  }

  _filteredHosts() {
    const search = this._search.trim().toLowerCase();
    let hosts = this._listHosts();

    if (this._config.hide_inactive) {
      hosts = hosts.filter((host) => host._pihole || host.active);
    }

    hosts = this._applyStatusFilter(hosts, this._filter);

    if (this._networkFilter) {
      hosts = hosts.filter((host) => host.network === this._networkFilter);
    }

    if (search) {
      hosts = hosts.filter((host) =>
        [host.name, host.ip, host.mac, host.network, host.zone, host.ptr1, host.ptr2, host.comment, host.ha_name, host.model, host.host_name]
          .map((value) => String(value || "").toLowerCase())
          .some((value) => value.includes(search))
      );
    }

    const direction = this._sortDir === "desc" ? -1 : 1;
    const sorted = hosts.slice().sort((left, right) => {
      const a = sortValue(left, this._sortBy);
      const b = sortValue(right, this._sortBy);
      if (a < b) return -1 * direction;
      if (a > b) return 1 * direction;
      // Stabiler Zweitschluessel, damit die Reihenfolge nicht springt.
      return ipSortKey(left.ip) - ipSortKey(right.ip);
    });

    const limit = Number(this._config.max_rows) || 0;
    return limit > 0 ? sorted.slice(0, limit) : sorted;
  }

  /** Anzahl der Zeilen eines Filters in Kombination mit dem jeweils anderen Filter. */
  _filterCount(key) {
    let hosts = this._listHosts();
    if (this._config.hide_inactive) {
      hosts = hosts.filter((host) => host._pihole || host.active);
    }
    if (key.startsWith("network:")) {
      const network = key.slice("network:".length);
      hosts = this._applyStatusFilter(hosts, this._filter);
      return hosts.filter((host) => host.network === network).length;
    }
    hosts = this._applyStatusFilter(hosts, key);
    if (this._networkFilter) {
      hosts = hosts.filter((host) => host.network === this._networkFilter);
    }
    return hosts.length;
  }

  /* -- Aufbau ------------------------------------------------------- */

  _update() {
    if (!this._hass) return;
    if (!this._built) {
      this._build();
      this._built = true;
    }
    const hosts = this._listHosts();
    const signature = this._computeSignature(hosts);
    const changed = signature !== this._signature;
    this._signature = signature;
    if (changed) this._buildFilters();
    const piholeEnabled = !!((this._stateObj() || {}).attributes || {}).pihole_aktiv;
    this.querySelectorAll(".fbn-pihole-tool").forEach((button) => {
      button.hidden = !piholeEnabled;
    });
    this._renderSummary();
    this._renderBody();
    if (changed) this._renderHead();
    if (this._popup) this._refreshPopup();
  }

  _build() {
    const config = this._config;
    this.innerHTML = "";

    const card = document.createElement("ha-card");
    card.className = "fbn-card";
    if (config.title) card.setAttribute("header", config.title);
    card.innerHTML = `
      <style>${this._styles()}</style>
      <div class="fbn-root${config.compact ? " fbn-compact" : ""}${
      this._stickyColumnsEnabled() ? " fbn-sticky" : ""
    }">
        <div class="fbn-toolbar">
          <div class="fbn-filters"></div>
          <div class="fbn-tools">
            <button class="fbn-chip fbn-pihole-sync fbn-pihole-tool" type="button" hidden title="Alle FRITZ!Box-Geräte an Pi-hole übertragen">
              <ha-icon icon="mdi:sync"></ha-icon><span>Pi-hole abgleichen</span>
            </button>
            <button class="fbn-chip fbn-pihole-add fbn-pihole-tool" type="button" hidden title="Manuellen DNS-Eintrag hinzufügen">
              <ha-icon icon="mdi:plus"></ha-icon><span>DNS-Eintrag</span>
            </button>
            <button class="fbn-chip fbn-refresh" type="button" title="Geräteliste jetzt aktualisieren">
              <ha-icon icon="mdi:refresh"></ha-icon><span>Aktualisieren</span>
            </button>
            <button class="fbn-chip fbn-export" type="button" title="Aktuelle Ansicht als Excel-Datei exportieren">
              <ha-icon icon="mdi:microsoft-excel"></ha-icon>
              <span>Excel-Export</span>
            </button>
            <div class="fbn-searchwrap"></div>
          </div>
        </div>
        <div class="fbn-summary"></div>
        <div class="fbn-scrollwrap">
          <button class="fbn-arrow fbn-arrow-left" type="button" hidden
                  aria-label="Nach links blättern" tabindex="-1">
            <ha-icon icon="mdi:chevron-left"></ha-icon>
          </button>
          <div class="fbn-scroll">
            <table class="fbn-table">
              <colgroup class="fbn-colgroup"></colgroup>
              <thead><tr class="fbn-head"></tr></thead>
              <tbody class="fbn-body"></tbody>
            </table>
          </div>
          <button class="fbn-arrow fbn-arrow-right" type="button" hidden
                  aria-label="Nach rechts blättern" tabindex="-1">
            <ha-icon icon="mdi:chevron-right"></ha-icon>
          </button>
        </div>
        <div class="fbn-empty" hidden>Keine Geräte gefunden.</div>
      </div>
    `;
    this.appendChild(card);

    this._root = card.querySelector(".fbn-root");
    this._root.style.cssText = this._colorVars();

    this._buildFilters();
    this._buildRefresh();
    this._buildExport();
    this._buildSearch();
    this._buildHead();
    this._bindPihole();
    this._renderHead();
    this._observeWidth();
    this._bindScrollArrows(card.querySelector(".fbn-scrollwrap"));
  }

  _buildFilters() {
    const container = this.querySelector(".fbn-filters");
    if (!container) return;
    if (!this._config.show_filter) {
      container.hidden = true;
      return;
    }
    const networks = this._config.show_filter_networks ? Array.from(
      new Map(
        this._hosts()
          .filter((host) => host.network)
          .map((host) => [host.network, host.zone || "Netz"])
      ).entries()
    ).map(([network, zone]) => ({
      key: `network:${network}`,
      label: zone === "Gast/anderes Netz" ? "Gast" : zone,
      icon: zone === "Heimnetz" ? "mdi:lan" : "mdi:account-network",
    })) : [];
    const staticFilters = FILTERS.filter((filter) => this._config[filter.cfg]);
    this._availableFilters = [...staticFilters, ...networks];
    if (!staticFilters.some((filter) => filter.key === this._filter)) {
      this._filter = staticFilters.some((filter) => filter.key === "aktiv")
        ? "aktiv"
        : "alle";
    }
    if (!this._config.show_filter_networks) this._networkFilter = "";
    container.innerHTML = this._availableFilters.map((filter) => {
      const count = this._filterCount(filter.key);
      const newAlert = filter.key === "neu" && count > 0;
      return `
        <button class="fbn-chip${newAlert ? " fbn-chip-new-alert" : ""}" data-filter="${filter.key}" type="button"
                ${newAlert ? `title="${count} neue${count === 1 ? "s Gerät" : " Geräte"} bestätigen"` : ""}
                aria-pressed="${filter.key.startsWith("network:")
                  ? filter.key.slice("network:".length) === this._networkFilter
                  : filter.key === this._filter}">
          <ha-icon icon="${filter.icon}"></ha-icon><span>${escapeHtml(filter.label)} (${count})</span>
        </button>`;
    }).join("");
    if (!container.dataset.bound) {
      container.dataset.bound = "1";
      container.addEventListener("click", (event) => {
        const button = event.target.closest(".fbn-chip");
        if (!button) return;
        this._setFilter(button.dataset.filter);
      });
    }
  }

  _buildRefresh() {
    const button = this.querySelector(".fbn-refresh");
    if (!button) return;
    button.hidden = !this._config.show_refresh;
    button.addEventListener("click", async () => {
      if (!this._hass || button.disabled) return;
      button.disabled = true;
      button.querySelector("ha-icon").setAttribute("icon", "mdi:loading");
      try {
        await this._hass.callService("fritzsync_network", "refresh", {});
      } finally {
        button.disabled = false;
        button.querySelector("ha-icon").setAttribute("icon", "mdi:refresh");
      }
    });
  }

  /* -- Waagerechtes Blättern (Smartphone) --------------------------- */

  /**
   * Auf schmalen Karten passen nicht alle Spalten nebeneinander. Statt
   * Spalten zu verstecken, wird die Tabelle waagerecht scrollbar: per
   * Wischgeste (nativer Touch-Scroll) oder ueber die beiden Pfeile am
   * Rand. Der Gerätename bleibt dabei links stehen (siehe fbn-sticky).
   */
  _bindScrollArrows(wrapEl) {
    if (!wrapEl || wrapEl.dataset.arrowsBound) return;
    wrapEl.dataset.arrowsBound = "1";
    const scrollEl = wrapEl.querySelector(".fbn-scroll");
    const left = wrapEl.querySelector(".fbn-arrow-left");
    const right = wrapEl.querySelector(".fbn-arrow-right");
    if (!scrollEl) return;
    this._scrollEl = scrollEl;

    const step = () => Math.max(120, Math.round(scrollEl.clientWidth * 0.66));
    if (left) {
      left.addEventListener("click", () => {
        scrollEl.scrollBy({ left: -step(), behavior: "smooth" });
      });
    }
    if (right) {
      right.addEventListener("click", () => {
        scrollEl.scrollBy({ left: step(), behavior: "smooth" });
      });
    }
    scrollEl.addEventListener("scroll", () => this._updateArrows(), {
      passive: true,
    });
    this._updateArrows();
  }

  /**
   * Blendet die Pfeile passend zur Scrollposition ein oder aus: linker
   * Pfeil nur, wenn nach links scrollbar; rechter nur, wenn nach rechts.
   * Ist die Tabelle komplett sichtbar, bleiben beide verborgen.
   */
  _updateArrows() {
    const scrollEl = this._scrollEl;
    if (!scrollEl) return;
    const wrap = scrollEl.closest(".fbn-scrollwrap");
    if (!wrap) return;
    const left = wrap.querySelector(".fbn-arrow-left");
    const right = wrap.querySelector(".fbn-arrow-right");
    const arrowsOn = this._config.show_scroll_arrows;
    const maxScroll = scrollEl.scrollWidth - scrollEl.clientWidth;
    const pos = scrollEl.scrollLeft;
    // 2px Toleranz gegen Rundungsfehler.
    const canLeft = arrowsOn && pos > 2;
    const canRight = arrowsOn && pos < maxScroll - 2;
    if (left) {
      left.hidden = !canLeft;
      left.tabIndex = canLeft ? 0 : -1;
    }
    if (right) {
      right.hidden = !canRight;
      right.tabIndex = canRight ? 0 : -1;
    }
  }

  /** Setzt den aktiven Filter und aktualisiert Chips, Zusammenfassung, Liste. */
  _setFilter(key) {
    if (!(this._availableFilters || FILTERS).some((filter) => filter.key === key)) return;
    if (key.startsWith("network:")) {
      const network = key.slice("network:".length);
      this._networkFilter = this._networkFilter === network ? "" : network;
    } else {
      if (key === this._filter) return;
      this._filter = key;
    }
    this.querySelectorAll(".fbn-chip").forEach((chip) => {
      const chipKey = chip.dataset.filter;
      if (!chipKey) return;
      const pressed = chipKey.startsWith("network:")
        ? chipKey.slice("network:".length) === this._networkFilter
        : chipKey === this._filter;
      chip.setAttribute("aria-pressed", String(pressed));
    });
    this._renderSummary();
    this._renderBody();
  }

  _buildSearch() {
    const container = this.querySelector(".fbn-searchwrap");
    if (!container) return;
    if (!this._config.show_search) {
      container.hidden = true;
      return;
    }
    container.innerHTML = `
      <label class="fbn-search">
        <ha-icon icon="mdi:magnify"></ha-icon>
        <input type="search" placeholder="Name, IP oder MAC" aria-label="Geräte durchsuchen">
      </label>`;
    const input = container.querySelector("input");
    input.addEventListener("input", () => {
      this._search = input.value;
      this._renderSummary();
      this._renderBody();
    });
  }

  _buildExport() {
    const button = this.querySelector(".fbn-export");
    if (!button || button.dataset.bound) return;
    button.dataset.bound = "1";
    button.addEventListener("click", () => this._exportXlsx());
  }

  /** Exportiert exakt die sichtbaren Spalten und gefilterten Zeilen als XLSX. */
  _exportXlsx() {
    const hosts = this._filteredHosts();
    // Nicht nur die Kartenkonfiguration, sondern die wirklich gerenderte
    // Ansicht ist massgeblich. Damit fehlen im Editor deaktivierte und auf
    // der aktuellen Kartenbreite ausgeblendete Felder auch im Export.
    const renderedKeys = Array.from(this.querySelectorAll(".fbn-head .fbn-th"))
      .filter((cell) => window.getComputedStyle(cell).display !== "none")
      .map((cell) => cell.dataset.sort)
      .filter(Boolean);
    const visible = this._visibleColumns().filter(
      (column) => !renderedKeys.length || renderedKeys.includes(column.key)
    );
    if (!visible.length) {
      window.alert("Für den Excel-Export ist keine Spalte eingeblendet.");
      return;
    }
    const headers = visible.map((column) =>
      column.key === "status" ? "Status" : column.label
    );
    const networkLabel = (host) => {
      if (host._pihole) return "manuell";
      const guest = host.guest || host.zone === "Gast" || host.zone === "Gast/anderes Netz";
      if (guest) return host.connection === "wlan" ? "Gast WLAN" : "Gast LAN";
      return host.connection === "wlan" ? "WLAN" : "LAN";
    };
    const cellValue = (host, key) => {
      switch (key) {
        case "status": return host._pihole ? "Pi-hole" : host.active ? "aktiv" : "inaktiv";
        case "name": return host.name || "";
        case "network": return networkLabel(host);
        case "mac": return host.mac || "";
        case "ip": return host.ip || "";
        case "ptr1": return host.ptr1 || "";
        case "ptr2": return host.ptr2 || "";
        case "comment": return host.comment || "";
        case "connection": return host.connection_label || "";
        case "ha_name": return host.ha_name || "";
        case "ip_type": return host.static_ip === true ? "statisch" : host.static_ip === false ? "DHCP" : "";
        case "wan": return host.blocked ? "gesperrt" : "";
        case "update": return host.update_available ? "verfügbar" : "";
        case "speed": return formatSpeed(host.speed);
        case "model": return host.model || "";
        case "type": return host.device_class_user || host.device_class || "";
        default: return "";
      }
    };
    const rows = hosts.map((host) =>
      visible.map((column) => cellValue(host, column.key))
    );

    // XLSX ist ein ZIP-Container aus XML-Dateien. Die kleine lokale
    // Implementierung vermeidet externe Skripte/CDNs und funktioniert auch,
    // wenn Home Assistant keinen Internetzugang hat.
    const encoder = new TextEncoder();
    const xmlEscape = (value) => String(value ?? "")
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;")
      .replace(/'/g, "&apos;").replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g, "");
    const colName = (index) => {
      let value = index + 1;
      let name = "";
      while (value) {
        value -= 1;
        name = String.fromCharCode(65 + (value % 26)) + name;
        value = Math.floor(value / 26);
      }
      return name;
    };
    const sheetRows = [headers, ...(rows.length ? rows : [headers.map(() => "")])];
    const sheetXmlRows = sheetRows.map((row, rowIndex) => {
      const cells = row.map((value, colIndex) => {
        // inlineStr speichert alle Werte als Text und verhindert damit auch
        // Formel-Injection durch Gerätenamen, die mit =, +, - oder @ beginnen.
        const ref = `${colName(colIndex)}${rowIndex + 1}`;
        const style = rowIndex === 0 ? ' s="1"' : "";
        return `<c r="${ref}" t="inlineStr"${style}><is><t xml:space="preserve">${xmlEscape(value)}</t></is></c>`;
      }).join("");
      return `<row r="${rowIndex + 1}">${cells}</row>`;
    }).join("");
    const lastColumn = colName(headers.length - 1);
    const lastRow = sheetRows.length;
    const tableRef = `A1:${lastColumn}${lastRow}`;
    const fallbackWidths = { status: 9, name: 28, network: 14, mac: 20, ip: 16, ptr1: 28, ptr2: 28, comment: 24, connection: 18, ha_name: 24, ip_type: 14, wan: 14, update: 12, speed: 14, model: 22, type: 22 };
    const widths = visible.map((column) => this._columnWidths[column.key]
      ? Math.max(6, Math.round(this._columnWidths[column.key] / 7))
      : (fallbackWidths[column.key] || 16));
    const colWidths = widths.map((width, index) =>
      `<col min="${index + 1}" max="${index + 1}" width="${width}" customWidth="1"/>`
    ).join("");

    const files = {
      "[Content_Types].xml": `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>`,
      "_rels/.rels": `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>`,
      "xl/workbook.xml": `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Netzwerkgeräte" sheetId="1" r:id="rId1"/></sheets></workbook>`,
      "xl/_rels/workbook.xml.rels": `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>`,
      "xl/styles.xml": `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="11"/><name val="Calibri"/></font></fonts><fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF1F4E78"/><bgColor indexed="64"/></patternFill></fill></fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>`,
      "xl/worksheets/sheet1.xml": `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><dimension ref="${tableRef}"/><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><sheetFormatPr defaultRowHeight="15"/><cols>${colWidths}</cols><sheetData>${sheetXmlRows}</sheetData></worksheet>`,
    };

    const crcTable = new Uint32Array(256);
    for (let n = 0; n < 256; n += 1) {
      let c = n;
      for (let k = 0; k < 8; k += 1) c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
      crcTable[n] = c >>> 0;
    }
    const crc32 = (bytes) => {
      let crc = 0xFFFFFFFF;
      for (const byte of bytes) crc = crcTable[(crc ^ byte) & 0xFF] ^ (crc >>> 8);
      return (crc ^ 0xFFFFFFFF) >>> 0;
    };
    const u16 = (view, offset, value) => view.setUint16(offset, value, true);
    const u32 = (view, offset, value) => view.setUint32(offset, value >>> 0, true);
    const chunks = [];
    const central = [];
    let offset = 0;
    for (const [name, content] of Object.entries(files)) {
      const nameBytes = encoder.encode(name);
      const data = encoder.encode(content);
      const crc = crc32(data);
      const local = new Uint8Array(30 + nameBytes.length + data.length);
      const lv = new DataView(local.buffer);
      u32(lv, 0, 0x04034B50); u16(lv, 4, 20); u16(lv, 6, 0x0800);
      u16(lv, 8, 0); u16(lv, 10, 0); u16(lv, 12, 0x0021); u32(lv, 14, crc);
      u32(lv, 18, data.length); u32(lv, 22, data.length); u16(lv, 26, nameBytes.length); u16(lv, 28, 0);
      local.set(nameBytes, 30); local.set(data, 30 + nameBytes.length);
      chunks.push(local);

      const entry = new Uint8Array(46 + nameBytes.length);
      const ev = new DataView(entry.buffer);
      u32(ev, 0, 0x02014B50); u16(ev, 4, 20); u16(ev, 6, 20); u16(ev, 8, 0x0800);
      u16(ev, 10, 0); u16(ev, 12, 0); u16(ev, 14, 0x0021); u32(ev, 16, crc);
      u32(ev, 20, data.length); u32(ev, 24, data.length); u16(ev, 28, nameBytes.length);
      u16(ev, 30, 0); u16(ev, 32, 0); u16(ev, 34, 0); u16(ev, 36, 0); u32(ev, 38, 0); u32(ev, 42, offset);
      entry.set(nameBytes, 46); central.push(entry);
      offset += local.length;
    }
    const centralOffset = offset;
    const centralSize = central.reduce((sum, item) => sum + item.length, 0);
    const end = new Uint8Array(22);
    const endView = new DataView(end.buffer);
    u32(endView, 0, 0x06054B50); u16(endView, 4, 0); u16(endView, 6, 0);
    u16(endView, 8, central.length); u16(endView, 10, central.length);
    u32(endView, 12, centralSize); u32(endView, 16, centralOffset); u16(endView, 20, 0);

    const blob = new Blob([...chunks, ...central, end], {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `fritzsync-netzwerk-${new Date().toISOString().slice(0, 10)}.xlsx`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 0);
  }

  /**
   * Baut den Tabellenkopf genau einmal. Beim Sortieren wird danach nur
   * noch der Zustand der vorhandenen Zellen umgeschaltet - wuerde hier
   * innerHTML neu gesetzt, verloere ein gerade angeklicktes <th> mitten
   * im Klick seinen Platz im Dokument und der Tastaturfokus spraenge.
   */
  _buildHead() {
    const row = this.querySelector(".fbn-head");
    if (!row) return;
    this._renderColgroup();
    row.innerHTML = this._visibleColumns()
      .map((column) => {
        const label = column.key === "status" ? "Status" : column.label;
        return `
          <th class="fbn-th fbn-col-${column.key} fbn-prio-${column.prio}"
              data-sort="${column.key}" scope="col" tabindex="0" role="columnheader"
              style="${this._columnStyle(column)}"
              title="Nach ${escapeHtml(label)} sortieren">
            <span class="fbn-th-inner">
              <span class="fbn-th-label">${escapeHtml(column.label)}</span>
              <ha-icon class="fbn-sorticon" icon="mdi:arrow-up" hidden></ha-icon>
            </span>
            ${column.key === "status" ? "" : `<span class="fbn-resizer" data-resize="${column.key}" title="Spaltenbreite ziehen; Doppelklick setzt sie zurück"></span>`}
          </th>`;
      })
      .join("");

    const sort = (key) => {
      if (this._sortBy === key) {
        this._sortDir = this._sortDir === "asc" ? "desc" : "asc";
      } else {
        this._sortBy = key;
        this._sortDir = "asc";
      }
      this._renderHead();
      this._renderBody();
    };

    row.addEventListener("click", (event) => {
      if (event.target.closest(".fbn-resizer")) return;
      const header = event.target.closest("th[data-sort]");
      if (header) sort(header.dataset.sort);
    });
    row.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      const header = event.target.closest("th[data-sort]");
      if (!header) return;
      event.preventDefault();
      sort(header.dataset.sort);
    });

    row.querySelectorAll(".fbn-resizer").forEach((handle) => {
      handle.addEventListener("pointerdown", (event) => {
        event.preventDefault();
        event.stopPropagation();
        const key = handle.dataset.resize;
        const header = handle.closest("th");
        const headers = Array.from(row.querySelectorAll("th[data-sort]"));
        const index = headers.indexOf(header);
        const neighbourIndex = index < headers.length - 1 ? index + 1 : index - 1;
        const neighbour = headers[neighbourIndex];
        if (!neighbour) return;
        const neighbourKey = neighbour.dataset.sort;
        const startX = event.clientX;
        const startWidth = header.getBoundingClientRect().width;
        const neighbourStartWidth = neighbour.getBoundingClientRect().width;
        headers.forEach((item) => {
          this._columnWidths[item.dataset.sort] = item.getBoundingClientRect().width;
        });
        handle.classList.add("fbn-resizing");
        document.body.style.cursor = "col-resize";
        document.body.style.userSelect = "none";
        const move = (moveEvent) => {
          moveEvent.preventDefault();
          const delta = moveEvent.clientX - startX;
          const signedDelta = neighbourIndex > index ? delta : -delta;
          const width = Math.max(54, Math.round(startWidth + signedDelta));
          const appliedDelta = width - startWidth;
          const neighbourWidth = Math.max(54, Math.round(neighbourStartWidth - appliedDelta));
          const actualDelta = neighbourStartWidth - neighbourWidth;
          this._columnWidths[key] = Math.round(startWidth + actualDelta);
          this._columnWidths[neighbourKey] = neighbourWidth;
          this._renderColgroup();
          this._updateArrows();
        };
        const stop = () => {
          window.removeEventListener("pointermove", move, true);
          window.removeEventListener("pointerup", stop, true);
          window.removeEventListener("pointercancel", stop, true);
          handle.classList.remove("fbn-resizing");
          document.body.style.removeProperty("cursor");
          document.body.style.removeProperty("user-select");
          this._saveColumnWidths();
        };
        // Auf window lauschen: Home Assistant kann den Zeiger beim Ziehen aus
        // dem Header/Editor heraus bewegen; der Griff verliert ihn dann nicht.
        window.addEventListener("pointermove", move, true);
        window.addEventListener("pointerup", stop, true);
        window.addEventListener("pointercancel", stop, true);
      });
      handle.addEventListener("dblclick", (event) => {
        event.preventDefault();
        event.stopPropagation();
        delete this._columnWidths[handle.dataset.resize];
        this._saveColumnWidths();
        this._renderColgroup();
        this._renderBody();
      });
    });
  }

  /** Schaltet Markierung und Sortierpfeil auf die aktive Spalte um. */
  _renderHead() {
    const row = this.querySelector(".fbn-head");
    if (!row) return;
    if (!row.children.length) this._buildHead();

    row.querySelectorAll("th[data-sort]").forEach((header) => {
      const active = header.dataset.sort === this._sortBy;
      header.classList.toggle("fbn-sorted", active);
      header.setAttribute(
        "aria-sort",
        active ? (this._sortDir === "asc" ? "ascending" : "descending") : "none"
      );
      const icon = header.querySelector(".fbn-sorticon");
      if (!icon) return;
      icon.hidden = !active;
      if (active) {
        icon.setAttribute(
          "icon",
          this._sortDir === "asc" ? "mdi:arrow-up" : "mdi:arrow-down"
        );
      }
    });
  }

  _renderSummary() {
    const container = this.querySelector(".fbn-summary");
    if (!container) return;
    if (!this._config.show_summary) {
      container.hidden = true;
      return;
    }
    const state = this._stateObj();
    const attributes = (state && state.attributes) || {};
    const shown = this._filteredHosts().length;
    const parts = [
      `${attributes.gesamt || 0} Geräte`,
      `${attributes.aktiv || 0} aktiv`,
    ];
    if (attributes.updates_verfuegbar) {
      parts.push(`${attributes.updates_verfuegbar} mit Update`);
    }
    if (attributes.gesperrt) parts.push(`${attributes.gesperrt} gesperrt`);
    const manual = this._manualPiholeHosts().length;
    if (manual) parts.push(`${manual} manuell`);
    const filtered = shown !== (attributes.gesamt || 0) ? ` · ${shown} angezeigt` : "";
    container.textContent = parts.join(" · ") + filtered;
  }

  _renderBody(force = false) {
    const body = this.querySelector(".fbn-body");
    const empty = this.querySelector(".fbn-empty");
    if (!body) return;

    const state = this._stateObj();
    if (!state) {
      body.innerHTML = "";
      if (empty) {
        empty.hidden = false;
        empty.textContent = `Der Sensor ${this._config.entity} ist nicht verfügbar.`;
      }
      return;
    }

    const activeElement = deepActiveElement();
    if (!force && activeElement && body.contains(activeElement)) return;
    const hosts = this._filteredHosts();
    if (empty) {
      empty.hidden = hosts.length > 0;
      empty.textContent = "Keine Geräte gefunden.";
    }

    const columns = this._visibleColumns();
    const draft = this._piholeDraft
      ? this._renderPiholeRow(
          {record: "", names: "", ip: "", managed: false}, columns, true, true
        )
      : "";
    body.innerHTML = draft + hosts.map((host) => this._renderRow(host, columns)).join("");

    if (this._piholeDraft || this._piholeEditing) {
      requestAnimationFrame(() => {
        const selector = this._piholeDraft
          ? ".fbn-pihole-draft .fbn-pihole-names"
          : ".fbn-pihole-editing .fbn-pihole-names";
        const input = body.querySelector(selector);
        if (!input || !input.isConnected) return;
        input.focus();
        const end = input.value.length;
        input.setSelectionRange?.(end, end);
      });
    }

    if (!body.dataset.bound) {
      body.dataset.bound = "1";
      body.addEventListener("click", (event) => {
        const acknowledge = event.target.closest("[data-ack-mac]");
        if (acknowledge) {
          event.stopPropagation();
          this._acknowledgeDevice(acknowledge.dataset.ackMac, acknowledge);
          return;
        }
        // Klick auf den IP-Link oeffnet die Weboberflaeche, nicht das Popup.
        if (event.target.closest("a")) return;
        const row = event.target.closest("tr[data-mac]");
        if (row) this._activateRow(row.dataset.mac, row);
      });
      body.addEventListener("keydown", (event) => {
        if (event.key !== "Enter" && event.key !== " ") return;
        if (event.target.closest("[data-ack-mac]")) return;
        // Enter auf dem fokussierten IP-Link folgt dem Link.
        if (event.target.closest("a")) return;
        const row = event.target.closest("tr[data-mac]");
        if (!row) return;
        event.preventDefault();
        this._activateRow(row.dataset.mac, row);
      });
    }

    // Nach jedem Neuaufbau kann sich die Gesamtbreite geaendert haben.
    this._updateArrows();
  }

  _piholeRecords() {
    const state = this._stateObj();
    const value = state && state.attributes
      ? state.attributes.pihole_eintraege
      : [];
    return Array.isArray(value) ? value : [];
  }

  _renderPiholeRow(item, columns, draft = false, editing = draft) {
    const editKey = draft ? "__draft__" : item.record;
    if (editing && this._piholeEdits[editKey]) {
      item = { ...item, ...this._piholeEdits[editKey] };
    }
    const cells = columns.map((column) => {
      const tdClass = `fbn-td fbn-col-${column.key} fbn-prio-${column.prio}`;
      const style = this._columnStyle(column);
      if (column.key === "status") return `<td class="${tdClass}" style="${style}" data-pihole-column="status"><span class="fbn-dot fbn-dot-pihole" title="Manueller Pi-hole-DNS-Eintrag"></span></td>`;
      if (column.key === "name") return editing
        ? `<td class="${tdClass} fbn-pihole-namecell" style="${style}" data-pihole-column="name"><div class="fbn-namecell"><ha-icon class="fbn-rowicon fbn-pihole-icon" icon="mdi:pi-hole"></ha-icon><input class="fbn-pihole-names" value="${escapeHtml(item.names || "")}" placeholder="name.fritz.box" aria-label="DNS-Name oder Aliasnamen" spellcheck="false"></div><span class="fbn-pihole-rowbuttons"><button class="fbn-icon-btn fbn-pihole-save" type="button" title="Speichern"><ha-icon icon="mdi:content-save"></ha-icon></button>${draft ? "" : `<button class="fbn-icon-btn fbn-pihole-delete" type="button" title="Löschen"><ha-icon icon="mdi:delete"></ha-icon></button>`}<button class="fbn-icon-btn fbn-pihole-cancel" type="button" title="Abbrechen"><ha-icon icon="mdi:close"></ha-icon></button></span></td>`
        : `<td class="${tdClass}" style="${style}" data-pihole-column="name"><div class="fbn-namecell"><ha-icon class="fbn-rowicon fbn-pihole-icon" icon="mdi:pi-hole"></ha-icon><span class="fbn-name">${escapeHtml(item.names || "—")}</span></div></td>`;
      if (column.key === "ip") return editing
        ? `<td class="${tdClass}" style="${style}" data-pihole-column="ip"><input class="fbn-pihole-ip" value="${escapeHtml(item.ip || "")}" placeholder="192.168.9.x" aria-label="IP-Adresse" inputmode="decimal" spellcheck="false"></td>`
        : `<td class="${tdClass} fbn-mono" style="${style}" data-pihole-column="ip">${escapeHtml(item.ip || "—")}</td>`;
      if (column.key === "network") return `<td class="${tdClass}" style="${style}" data-pihole-column="network"><span class="fbn-badge ${item.managed ? "" : "fbn-badge-manual"}">${item.managed ? "Pi-hole" : "manuell"}</span></td>`;
      return `<td class="${tdClass} fbn-dim" style="${style}" data-pihole-column="${column.key}">—</td>`;
    }).join("");
    return `<tr class="fbn-pihole-row${draft ? " fbn-pihole-draft" : ""}${editing ? " fbn-pihole-editing" : ""}" data-record="${escapeHtml(item.record || "")}" data-ip="${escapeHtml(item.ip || "")}" data-names="${escapeHtml(item.names || "")}" data-managed="${item.managed ? "1" : "0"}"${editing ? "" : ' tabindex="0"'} title="Zum Bearbeiten anklicken">${cells}</tr>`;
  }

  _editPiholeRow(row) {
    if (!row || row.classList.contains("fbn-pihole-editing")) return;
    this._piholeEditing = row.dataset.record || "";
    this._piholeEdits[this._piholeEditing] = {
      names: row.dataset.names || "",
      ip: row.dataset.ip || "",
    };
    row.classList.add("fbn-pihole-editing");
    row.removeAttribute("tabindex");
    const nameCell = row.querySelector('[data-pihole-column="name"]');
    const ipCell = row.querySelector('[data-pihole-column="ip"]');
    if (!nameCell || !ipCell) return;
    nameCell.classList.add("fbn-pihole-namecell");
    nameCell.innerHTML = `<div class="fbn-namecell"><ha-icon class="fbn-rowicon fbn-pihole-icon" icon="mdi:pi-hole"></ha-icon><input class="fbn-pihole-names" value="${escapeHtml(row.dataset.names || "")}" aria-label="DNS-Name oder Aliasnamen" spellcheck="false"></div><span class="fbn-pihole-rowbuttons"><button class="fbn-icon-btn fbn-pihole-save" type="button" title="Speichern"><ha-icon icon="mdi:content-save"></ha-icon></button><button class="fbn-icon-btn fbn-pihole-delete" type="button" title="Löschen"><ha-icon icon="mdi:delete"></ha-icon></button><button class="fbn-icon-btn fbn-pihole-cancel" type="button" title="Abbrechen"><ha-icon icon="mdi:close"></ha-icon></button></span>`;
    ipCell.innerHTML = `<input class="fbn-pihole-ip" value="${escapeHtml(row.dataset.ip || "")}" aria-label="IP-Adresse" inputmode="decimal" spellcheck="false">`;
    requestAnimationFrame(() => {
      const input = row.querySelector(".fbn-pihole-names");
      if (input && input.isConnected) input.focus();
    });
  }

  _bindPihole() {
    const root = this.querySelector(".fbn-root");
    if (!root || root.dataset.piholeBound) return;
    root.dataset.piholeBound = "1";
    root.addEventListener("input", (event) => {
      if (!event.target.matches(".fbn-pihole-names, .fbn-pihole-ip")) return;
      const row = event.target.closest(".fbn-pihole-row");
      if (!row) return;
      const key = row.classList.contains("fbn-pihole-draft")
        ? "__draft__" : row.dataset.record;
      this._piholeEdits[key] = {
        names: row.querySelector(".fbn-pihole-names")?.value || "",
        ip: row.querySelector(".fbn-pihole-ip")?.value || "",
      };
    });
    root.addEventListener("keydown", (event) => {
      if (!event.target.matches(".fbn-pihole-names, .fbn-pihole-ip")) return;
      // Home Assistant verwendet Buchstaben als globale Tastenkürzel. Solange
      // ein DNS-Feld aktiv ist, dürfen diese Ereignisse die Karte nicht verlassen.
      event.stopPropagation();
      const row = event.target.closest(".fbn-pihole-row");
      if (!row) return;
      if (event.key === "Escape") {
        event.preventDefault();
        row.querySelector(".fbn-pihole-cancel")?.click();
      } else if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        row.querySelector(".fbn-pihole-save")?.click();
      }
    });
    root.addEventListener("click", async (event) => {
      const sync = event.target.closest(".fbn-pihole-sync");
      if (sync) {
        if (!window.confirm("Alle FRITZ!Box-Geräte mit IP-Adresse jetzt an Pi-hole übertragen?\n\nVorhandene lokale DNS-Zuordnungen derselben Geräte werden aktualisiert.")) return;
        sync.disabled = true;
        this._setBusy(true);
        try {
          await this._hass.callService("fritzsync_network", "pihole_sync_all", {});
        } catch (error) {
          window.alert(`Pi-hole-Gesamtabgleich fehlgeschlagen: ${error && error.message ? error.message : error}`);
        } finally {
          sync.disabled = false;
          this._setBusy(false);
        }
        return;
      }
      const add = event.target.closest(".fbn-pihole-add");
      if (add) {
        event.preventDefault();
        const body = this.querySelector(".fbn-body");
        if (!body) return;
        if (!this._config.show_name || !this._config.show_ip) {
          window.alert("Für einen neuen DNS-Eintrag müssen die Spalten FRITZ!Box-Name und IP-Adresse eingeblendet sein.");
          return;
        }
        const existing = body.querySelector(".fbn-pihole-draft");
        if (existing) {
          existing.scrollIntoView({ behavior: "smooth", block: "center" });
          existing.querySelector(".fbn-pihole-names")?.focus();
          return;
        }
        this._piholeDraft = true;
        this._piholeEdits.__draft__ = { names: "", ip: "" };
        this._renderBody();
        const row = body.querySelector(".fbn-pihole-draft");
        if (!row) return;
        row.scrollIntoView({ behavior: "smooth", block: "center" });
        requestAnimationFrame(() => {
          const input = row.querySelector(".fbn-pihole-names");
          if (input && input.isConnected) input.focus();
        });
        return;
      }
      const row = event.target.closest(".fbn-pihole-row");
      if (!row) return;
      if (event.target.closest(".fbn-pihole-cancel")) {
        const editKey = row.classList.contains("fbn-pihole-draft")
          ? "__draft__" : row.dataset.record;
        delete this._piholeEdits[editKey];
        this._piholeEditing = "";
        if (row.classList.contains("fbn-pihole-draft")) {
          this._piholeDraft = false;
          this._renderBody(true);
        } else {
          row.outerHTML = this._renderPiholeRow({
            record: row.dataset.record,
            ip: row.dataset.ip,
            names: row.dataset.names,
            managed: row.dataset.managed === "1",
          }, this._visibleColumns(), false);
        }
        return;
      }
      const remove = event.target.closest(".fbn-pihole-delete");
      const save = event.target.closest(".fbn-pihole-save");
      if (!remove && !save) {
        event.preventDefault();
        event.stopPropagation();
        this._editPiholeRow(row);
        return;
      }
      const ip = row.querySelector(".fbn-pihole-ip").value.trim();
      const names = row.querySelector(".fbn-pihole-names").value.trim();
      if (save && (!ip || !names)) {
        window.alert("Bitte DNS-Name und IP-Adresse vollständig eintragen.");
        (names ? row.querySelector(".fbn-pihole-ip") : row.querySelector(".fbn-pihole-names"))?.focus();
        return;
      }
      const oldRecord = row.dataset.record || "";
      const question = remove
        ? `Pi-hole-DNS-Eintrag wirklich löschen?\n\n${oldRecord}`
        : `${oldRecord ? "Pi-hole-DNS-Eintrag ändern" : "Pi-hole-DNS-Eintrag anlegen"}?\n\n${ip} ${names}`;
      if (!window.confirm(question)) return;
      const button = remove || save;
      button.disabled = true;
      this._setBusy(true);
      try {
        if (remove) {
          await this._hass.callService("fritzsync_network", "pihole_delete_record", {
            old_record: oldRecord,
          });
        } else if (oldRecord) {
          await this._hass.callService("fritzsync_network", "pihole_update_record", {
            old_record: oldRecord, ip, dns_names: names,
          });
        } else {
          await this._hass.callService("fritzsync_network", "pihole_add_record", {
            ip, dns_names: names,
          });
        }
        this._piholeEditing = "";
        this._piholeDraft = false;
        if (remove) this._piholeHiddenRecords.add(oldRecord);
        delete this._piholeEdits[oldRecord || "__draft__"];
        button.blur();
        // Der normale Fokus-Schutz darf einen bewusst abgeschlossenen
        // Schreibvorgang nicht blockieren. Der Service wartet bereits auf
        // den anschliessenden Coordinator-Refresh, daher liegt jetzt der
        // aktuelle Pi-hole-Stand vor.
        this._renderBody(true);
      } catch (error) {
        this._piholeEditing = oldRecord;
        window.alert(`Pi-hole-Änderung fehlgeschlagen: ${error && error.message ? error.message : error}`);
      } finally {
        button.disabled = false;
        this._setBusy(false);
      }
    });
  }

  /**
   * Reagiert auf Klick oder Tastendruck einer Zeile. Vorrang hat das
   * Detail-Popup (dort steht auch die MAC-Adresse, die in der schmalen
   * Tabelle ausgeblendet sein kann). Ist das Popup abgeschaltet, gilt
   * das bisherige Verhalten: sofort das Home-Assistant-Geraet oeffnen.
   */
  _activateRow(mac, rowEl) {
    if (this._config.show_details_popup) {
      const host = this._hosts().find((item) => item.mac === mac);
      if (host) this._openPopup(host, rowEl);
      return;
    }
    if (this._config.open_device_on_click) {
      const host = this._hosts().find((item) => item.mac === mac);
      if (host && host.ha_device_id) this._openDevice(host.ha_device_id);
    }
  }

  /** Ob ein Zeilenklick ueberhaupt etwas ausloest. */
  _rowInteractive(host) {
    if (this._config.show_details_popup) return true;
    return this._config.open_device_on_click && !!host.ha_device_id;
  }

  _renderRow(host, columns) {
    if (host._pihole) {
      return this._renderPiholeRow({
        record: host._record,
        names: host.name,
        ip: host.ip,
        managed: false,
      }, columns, false, this._piholeEditing === host._record);
    }
    const macAttr = ` data-mac="${escapeHtml(host.mac)}"`;
    const interactive = this._rowInteractive(host);
    const classes = ["fbn-tr"];
    if (!host.active) classes.push("fbn-inactive");
    if (host.is_new) classes.push("fbn-new");
    let extra = "";
    if (interactive) {
      classes.push("fbn-clickable");
      extra = ' tabindex="0" role="button"';
    }
    const cells = columns
      .map(
        (column) =>
          `<td class="fbn-td fbn-col-${column.key} fbn-prio-${column.prio}" style="text-align:${
            column.align || "left"
          }">${this._renderCell(host, column.key)}</td>`
      )
      .join("");
    return `<tr class="${classes.join(" ")}"${macAttr}${extra}>${cells}</tr>`;
  }

  _renderCell(host, key) {
    switch (key) {
      case "status":
        return `<span class="fbn-dot ${
          host.active ? "fbn-dot-on" : "fbn-dot-off"
        }" title="${host.active ? "Verbunden" : "Nicht verbunden"}"></span>`;

      case "name": {
        const badges = [];
        if (host.is_new) badges.push(`<button type="button" class="fbn-badge fbn-badge-new" data-ack-mac="${escapeHtml(host.mac)}" title="Neues Gerät als bekannt bestätigen"><ha-icon icon="mdi:check-circle-outline"></ha-icon>Neu bestätigen</button>`);
        if (host.vpn) badges.push('<span class="fbn-badge">VPN</span>');
        if (host.priority) badges.push('<span class="fbn-badge">Priorität</span>');
        return `
          <div class="fbn-namecell">
            <ha-icon class="fbn-rowicon" icon="${connectionIcon(host)}"></ha-icon>
            <span class="fbn-name">${escapeHtml(host.name)}</span>
            ${badges.join("")}
          </div>`;
      }

      case "ip": {
        const plain = `<span class="fbn-mono">${escapeHtml(host.ip || "—")}</span>`;
        if (!host.ip || !this._config.ip_opens_web) return plain;
        const url = webUrl(host, this._config.ip_web_fallback);
        if (!url) return plain;
        // Der Link oeffnet die Weboberflaeche in einem neuen Tab. Der
        // Klick darauf darf NICHT zusaetzlich das Zeilen-Popup oeffnen -
        // das faengt der Zeilen-Handler ueber "closest('a')" ab.
        return `<a class="fbn-iplink fbn-mono" href="${escapeHtml(url)}"
                   target="_blank" rel="noopener noreferrer"
                   title="Weboberfläche öffnen (${escapeHtml(url)})"
                   aria-label="Weboberfläche von ${escapeHtml(host.name)} öffnen"
                >${escapeHtml(host.ip)}<ha-icon class="fbn-iplink-icon" icon="mdi:open-in-new"></ha-icon></a>`;
      }

      case "mac":
        return `<span class="fbn-mono fbn-dim">${escapeHtml(host.mac || "—")}</span>`;

      case "network":
        if (host.guest || host.zone === "Gast" || host.zone === "Gast/anderes Netz") {
          return host.connection === "wlan"
            ? '<span class="fbn-badge fbn-badge-guest">Gast WLAN</span>'
            : '<span class="fbn-badge fbn-badge-guest">Gast LAN</span>';
        }
        return host.connection === "wlan"
          ? '<span class="fbn-badge">WLAN</span>'
          : '<span class="fbn-badge">LAN</span>';

      case "ptr1":
        return `<span class="fbn-mono fbn-dim">${escapeHtml(host.ptr1 || "—")}</span>`;

      case "ptr2":
        return `<span class="fbn-mono fbn-dim">${escapeHtml(host.ptr2 || "—")}</span>`;

      case "comment":
        return escapeHtml(host.comment || "—");

      case "connection":
        return escapeHtml(host.connection_label || "—");

      case "ha_name":
        return host.ha_name
          ? `<span class="fbn-ha">${escapeHtml(host.ha_name)}</span>`
          : '<span class="fbn-dim">—</span>';

      case "ip_type": {
        if (host.static_ip === true) {
          return '<span class="fbn-badge fbn-badge-static">statisch</span>';
        }
        if (host.static_ip === false) {
          const lease = formatLease(host.lease_time_remaining);
          return `<span class="fbn-dim">DHCP${
            lease ? ` <span class="fbn-lease">(${escapeHtml(lease)})</span>` : ""
          }</span>`;
        }
        return '<span class="fbn-dim" title="IP-Typ-Erfassung ist ausgeschaltet oder noch nicht gelaufen">—</span>';
      }

      case "wan":
        return host.blocked
          ? '<ha-icon class="fbn-icon-blocked" icon="mdi:web-off" title="Internetzugang gesperrt"></ha-icon>'
          : '<span class="fbn-dim">—</span>';

      case "update":
        return host.update_available
          ? '<ha-icon class="fbn-icon-update" icon="mdi:package-down" title="Firmware-Update verfügbar"></ha-icon>'
          : '<span class="fbn-dim">—</span>';

      case "speed":
        return `<span class="fbn-mono fbn-dim">${escapeHtml(formatSpeed(host.speed))}</span>`;

      case "model":
        return escapeHtml(host.model || "—");

      case "type":
        return escapeHtml(host.device_class_user || host.device_class || "—");

      default:
        return "";
    }
  }

  /** Oeffnet die Geraeteseite in Home Assistant. */
  _openDevice(deviceId) {
    if (!deviceId) return;
    const path = `/config/devices/device/${deviceId}`;
    history.pushState(null, "", path);
    window.dispatchEvent(new Event("location-changed"));
  }

  /* -- Detail-Popup ------------------------------------------------- */

  /**
   * Oeffnet das Detail-Popup fuer ein Geraet. Der Overlay-Knoten wird
   * bewusst an document.body gehaengt (nicht in die Karte), damit er
   * ueber allem liegt, egal in welchem Stapelkontext die Karte steckt.
   */
  _openPopup(host, returnFocusEl) {
    this._closePopup();
    this._popupMac = host.mac;
    this._popupReturnFocus = returnFocusEl || null;

    const overlay = document.createElement("div");
    overlay.className = "fbn-overlay";
    overlay.innerHTML = `
      <style>${this._popupStyles()}</style>
      <div class="fbn-modal" role="dialog" aria-modal="true"
           aria-label="Gerätedetails ${escapeHtml(host.name)}">
        <div class="fbn-modal-head">
          <ha-icon class="fbn-modal-icon" icon="${connectionIcon(host)}"></ha-icon>
          <div class="fbn-modal-titles">
            <div class="fbn-modal-title"></div>
            <div class="fbn-modal-sub"></div>
          </div>
          <button class="fbn-modal-close" type="button" aria-label="Schließen">
            <ha-icon icon="mdi:close"></ha-icon>
          </button>
        </div>
        <div class="fbn-modal-body"></div>
        <div class="fbn-modal-foot"></div>
      </div>`;
    document.body.appendChild(overlay);
    this._popup = overlay;

    // Schliessen ueber Klick auf den Hintergrund, aber nicht auf den
    // Dialog selbst.
    overlay.addEventListener("mousedown", (event) => {
      if (event.target === overlay) this._closePopup();
    });

    // Die dynamische Fusszeile wird bei Sensordaten aktualisiert. Darum
    // bereits beim Druecken schliessen: Ein Neuaufbau zwischen pointerdown
    // und click kann den urspruenglichen Button sonst austauschen.
    overlay.addEventListener("pointerdown", (event) => {
      if (!event.target.closest(".fbn-modal-close, .fbn-modal-close2")) return;
      event.preventDefault();
      event.stopPropagation();
      this._closePopup();
    });

    this._onPopupKeydown = (event) => {
      if (event.key === "Escape") {
        event.stopPropagation();
        this._closePopup();
      }
    };
    overlay.addEventListener("keydown", this._onPopupKeydown);

    overlay
      .querySelector(".fbn-modal-close")
      .addEventListener("click", () => this._closePopup());

    this._refreshPopup();

    const close = overlay.querySelector(".fbn-modal-close");
    if (close && close.focus) close.focus();
  }

  /** Baut den Inhalt des Popups aus den jeweils aktuellen Daten neu auf. */
  _refreshPopup() {
    if (!this._popup) return;
    const host =
      this._hosts().find((item) => item.mac === this._popupMac) || null;
    if (!host) {
      // Geraet ist aus der Liste verschwunden - Popup mit Hinweis lassen,
      // aber nicht abrupt schliessen.
      const body = this._popup.querySelector(".fbn-modal-body");
      if (body && !body.dataset.gone) {
        body.dataset.gone = "1";
        const note = document.createElement("div");
        note.className = "fbn-modal-note";
        note.textContent = "Dieses Gerät ist nicht mehr in der Liste.";
        body.prepend(note);
      }
      return;
    }

    const title = this._popup.querySelector(".fbn-modal-title");
    const sub = this._popup.querySelector(".fbn-modal-sub");
    title.textContent = host.name;
    sub.innerHTML = `
      <span class="fbn-dot ${host.active ? "fbn-dot-on" : "fbn-dot-off"}"></span>
      ${host.active ? "Verbunden" : "Nicht verbunden"} · ${escapeHtml(
      host.connection_label || "—"
    )}`;

    this._popup.querySelector(".fbn-modal-body").innerHTML =
      this._popupRows(host);
    this._popup.querySelector(".fbn-modal-foot").innerHTML =
      this._popupButtons(host);

    // Kopier-Knoepfe verkabeln.
    this._popup.querySelectorAll(".fbn-copy").forEach((button) => {
      button.addEventListener("click", () => this._copy(button.dataset.copy, button));
    });

    // Home Assistant oeffnen.
    const haButton = this._popup.querySelector(".fbn-act-ha");
    if (haButton) {
      haButton.addEventListener("click", () => {
        this._closePopup();
        this._openDevice(host.ha_device_id);
      });
    }

    // Wake-on-LAN.
    const wolButton = this._popup.querySelector(".fbn-act-wol");
    if (wolButton) {
      wolButton.addEventListener("click", () => this._wakeDevice(host, wolButton));
    }

    const renameButton = this._popup.querySelector(".fbn-act-rename");
    if (renameButton) {
      renameButton.addEventListener("click", () => this._renameDevice(host, renameButton));
    }
    const commentButton = this._popup.querySelector(".fbn-act-comment");
    if (commentButton) {
      commentButton.addEventListener("click", () => this._setComment(host, commentButton));
    }
    const acknowledgeButton = this._popup.querySelector(".fbn-act-acknowledge");
    if (acknowledgeButton) {
      acknowledgeButton.addEventListener("click", () =>
        this._acknowledgeDevice(host.mac, acknowledgeButton)
      );
    }

    // Schliessen in der Fusszeile.
    const footClose = this._popup.querySelector(".fbn-modal-close2");
    if (footClose) footClose.addEventListener("click", () => this._closePopup());
  }

  /** Definitionsliste aller Felder eines Geraets. */
  _popupRows(host) {
    const rows = [];
    const add = (label, value, options) => {
      const opts = options || {};
      const shown =
        value === null || value === undefined || value === "" ? "—" : value;
      const copy =
        opts.copy && shown !== "—"
          ? `<button class="fbn-copy" type="button" data-copy="${escapeHtml(
              opts.copy
            )}" aria-label="${escapeHtml(label)} kopieren"><ha-icon icon="mdi:content-copy"></ha-icon></button>`
          : "";
      rows.push(`
        <div class="fbn-drow">
          <div class="fbn-dt">${escapeHtml(label)}</div>
          <div class="fbn-dd${opts.mono ? " fbn-mono" : ""}">${shown}${copy}</div>
        </div>`);
    };

    add("Gerätename", escapeHtml(host.name));
    add("Netz", escapeHtml(host.zone || ""));
    add("Subnetz", escapeHtml(host.network || ""), { mono: true });
    add("IP-Adresse", escapeHtml(host.ip), { mono: true, copy: host.ip });
    add("MAC-Adresse", escapeHtml(host.mac), { mono: true, copy: host.mac });
    add("PTR 1", escapeHtml(host.ptr1 || ""), { mono: true, copy: host.ptr1 });
    add("PTR 2", escapeHtml(host.ptr2 || ""), { mono: true, copy: host.ptr2 });
    add("Kommentar", escapeHtml(host.comment || ""));
    add("Verbindung", escapeHtml(host.connection_label));
    add(
      "Status",
      host.active ? "Verbunden" : "Nicht verbunden"
    );

    let ipType = "—";
    if (host.static_ip === true) ipType = "statisch";
    else if (host.static_ip === false) {
      const lease = formatLease(host.lease_time_remaining);
      ipType = lease ? `DHCP (${escapeHtml(lease)})` : "DHCP";
    }
    add("IP-Typ", ipType);

    add("Tempo", host.active ? escapeHtml(formatSpeed(host.speed)) : "—");
    add("Internetzugang", host.blocked ? "gesperrt" : "erlaubt");
    if (host.filter_profile) add("Filterprofil", escapeHtml(host.filter_profile));
    add("Firmware-Update", host.update_available ? "verfügbar" : "keines");
    if (host.model) add("Modell", escapeHtml(host.model));
    add(
      "Gerätetyp",
      escapeHtml(host.device_class_user || host.device_class || "")
    );
    if (host.host_name && host.host_name !== host.name) {
      add("Hostname", escapeHtml(host.host_name));
    }

    const flags = [];
    if (host.guest) flags.push("Gastnetz");
    if (host.vpn) flags.push("VPN");
    if (host.priority) flags.push("Priorität");
    if (host.meshable) flags.push("Mesh-fähig");
    if (flags.length) add("Merkmale", escapeHtml(flags.join(", ")));

    add(
      "Home Assistant",
      host.ha_name ? escapeHtml(host.ha_name) : ""
    );

    return rows.join("");
  }

  /** Fusszeile des Popups mit den moeglichen Aktionen. */
  _popupButtons(host) {
    const buttons = [];
    const url = this._config.ip_opens_web
      ? webUrl(host, this._config.ip_web_fallback)
      : "";
    if (url) {
      buttons.push(
        `<a class="fbn-btn fbn-act-web" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer"><ha-icon icon="mdi:open-in-new"></ha-icon>Weboberfläche öffnen</a>`
      );
    }
    if (host.ha_device_id) {
      buttons.push(
        '<button class="fbn-btn fbn-act-ha" type="button"><ha-icon icon="mdi:open-in-new"></ha-icon>In Home Assistant öffnen</button>'
      );
    }
    // Aufwecken nur anbieten, wenn das Geraet gerade nicht verbunden ist
    // und Home Assistant fuer den Dienstaufruf bereitsteht.
    if (!host.active && this._hass) {
      buttons.push(
        '<button class="fbn-btn fbn-act-wol" type="button"><ha-icon icon="mdi:power"></ha-icon>Aufwecken (WoL)</button>'
      );
    }
    if (this._hass) {
      if (host.is_new) {
        buttons.push(
          '<button class="fbn-btn fbn-act-acknowledge" type="button"><ha-icon icon="mdi:check-circle-outline"></ha-icon>Als bekannt bestätigen</button>'
        );
      }
      buttons.push(
        '<button class="fbn-btn fbn-act-rename" type="button"><ha-icon icon="mdi:pencil"></ha-icon>Umbenennen</button>'
      );
      buttons.push(
        '<button class="fbn-btn fbn-act-comment" type="button"><ha-icon icon="mdi:comment-edit-outline"></ha-icon>Kommentar</button>'
      );
    }
    buttons.push(
      '<button class="fbn-btn fbn-btn-primary fbn-modal-close2" type="button">Schließen</button>'
    );
    return buttons.join("");
  }

  /** Kopiert einen Wert in die Zwischenablage, mit kurzer Rueckmeldung. */
  _copy(value, button) {
    const done = () => {
      const icon = button.querySelector("ha-icon");
      if (icon) icon.setAttribute("icon", "mdi:check");
      setTimeout(() => {
        if (icon) icon.setAttribute("icon", "mdi:content-copy");
      }, 1200);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(value).then(done).catch(() => {});
    }
  }

  /** Ruft den Wake-on-LAN-Dienst der Integration auf. */
  _wakeDevice(host, button) {
    if (!this._hass || !host.mac) return;
    button.disabled = true;
    const label = button;
    this._hass
      .callService("fritzsync_network", "wake_on_lan", { mac: host.mac })
      .then(() => {
        label.innerHTML = '<ha-icon icon="mdi:check"></ha-icon>Signal gesendet';
      })
      .catch(() => {
        label.disabled = false;
        label.innerHTML = '<ha-icon icon="mdi:alert"></ha-icon>Fehlgeschlagen';
      });
  }

  _renameDevice(host, button) {
    const name = prompt("Neuer Gerätename in der FRITZ!Box:", host.name || "");
    if (!name || name === host.name) return;
    if (!confirm(`„${host.name}“ wirklich in „${name}“ umbenennen?\n\nWenn Pi-hole in den Integrationseinstellungen aktiviert ist, wird auch der lokale DNS-Eintrag aktualisiert.`)) return;
    button.disabled = true;
    this._hass.callService("fritzsync_network", "set_device_name", { mac: host.mac, name })
      .then(() => { button.innerHTML = '<ha-icon icon="mdi:check"></ha-icon>Umbenannt'; })
      .catch(() => { button.disabled = false; button.innerHTML = '<ha-icon icon="mdi:alert"></ha-icon>Fehlgeschlagen'; });
  }

  _setComment(host, button) {
    const comment = prompt("Kommentar für dieses Gerät:", host.comment || "");
    if (comment === null || comment === host.comment) return;
    if (!confirm("Kommentar wirklich speichern?")) return;
    button.disabled = true;
    this._hass.callService("fritzsync_network", "set_device_comment", { mac: host.mac, comment })
      .then(() => { button.innerHTML = '<ha-icon icon="mdi:check"></ha-icon>Gespeichert'; })
      .catch(() => { button.disabled = false; button.innerHTML = '<ha-icon icon="mdi:alert"></ha-icon>Fehlgeschlagen'; });
  }

  _acknowledgeDevice(mac, button) {
    if (!this._hass || !mac) return;
    if (!confirm("Neues Gerät wirklich als bekannt bestätigen?")) return;
    button.disabled = true;
    this._hass.callService("fritzsync_network", "acknowledge_device", { mac })
      .then(() => {
        button.innerHTML = '<ha-icon icon="mdi:check"></ha-icon>Bestätigt';
        if (button.classList.contains("fbn-act-acknowledge")) {
          setTimeout(() => this._closePopup(), 500);
        }
      })
      .catch(() => {
        button.disabled = false;
        button.innerHTML = '<ha-icon icon="mdi:alert"></ha-icon>Fehlgeschlagen';
      });
  }

  /** Schliesst das Popup und raeumt Listener und Fokus auf. */
  _closePopup() {
    if (!this._popup) return;
    if (this._onPopupKeydown) {
      this._popup.removeEventListener("keydown", this._onPopupKeydown);
      this._onPopupKeydown = null;
    }
    if (this._popup.parentNode) this._popup.parentNode.removeChild(this._popup);
    this._popup = null;
    this._popupMac = null;
    const returnTo = this._popupReturnFocus;
    this._popupReturnFocus = null;
    if (returnTo && returnTo.focus && document.contains(returnTo)) {
      returnTo.focus();
    }
  }

  /* -- Breite ------------------------------------------------------- */

  /**
   * Aktualisiert die Blätter-Pfeile, wenn sich die Kartenbreite aendert.
   * Spalten werden bewusst NICHT mehr versteckt - auf schmalen Karten
   * wird die Tabelle stattdessen waagerecht scrollbar, damit auch die
   * hinteren Spalten (z. B. Home Assistant) erreichbar bleiben.
   */
  _observeWidth() {
    if (this._resizeObserver || typeof ResizeObserver === "undefined") return;
    if (!this._root) return;
    this._resizeObserver = new ResizeObserver(() => this._updateArrows());
    this._resizeObserver.observe(this._root);
  }

  /* -- Farben und CSS ----------------------------------------------- */

  /** Baut die Inline-CSS-Variablen aus den konfigurierten Farben. */
  _colorVars() {
    return Object.keys(COLOR_FALLBACKS)
      .map((key) => {
        const value = sanitizeColor(this._config[key]);
        const variable = `--fbn-${key.replace("color_", "").replace(/_/g, "-")}`;
        return `${variable}: ${value || COLOR_FALLBACKS[key]};`;
      })
      .join("");
  }

  _styles() {
    return `
      .fbn-root { padding: 0 0 8px; color: var(--fbn-row-text); }
      .fbn-toolbar {
        display: flex; flex-wrap: wrap; gap: 8px; align-items: center;
        justify-content: space-between; padding: 8px 16px 4px;
      }
      .fbn-filters { display: flex; flex-wrap: wrap; gap: 6px; }
      .fbn-tools { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-left: auto; }
      .fbn-export ha-icon { --mdc-icon-size: 17px; width: 17px; height: 17px; color: #43a047; }
      .fbn-chip {
        display: inline-flex; align-items: center; gap: 4px;
        border: 1px solid var(--fbn-border); border-radius: 16px;
        background: none; color: inherit; cursor: pointer;
        padding: 4px 10px; font: inherit; font-size: 0.85em; line-height: 1.4;
      }
      .fbn-chip ha-icon { --mdc-icon-size: 16px; width: 16px; height: 16px; }
      .fbn-chip[aria-pressed="true"] {
        border-color: var(--fbn-accent); color: var(--fbn-accent);
      }
      .fbn-chip.fbn-chip-new-alert {
        border-color: var(--warning-color, #ffb300);
        color: var(--warning-color, #ffb300);
        background: color-mix(in srgb, var(--warning-color, #ffb300) 18%, transparent);
      }
      .fbn-chip:focus-visible { outline: 2px solid var(--fbn-accent); outline-offset: 2px; }
      .fbn-busy, .fbn-busy * { cursor: progress !important; }
      .fbn-busy button:disabled ha-icon { animation: fbn-spin 850ms linear infinite; }
      @keyframes fbn-spin { to { transform: rotate(360deg); } }
      .fbn-search {
        display: inline-flex; align-items: center; gap: 6px;
        border: 1px solid var(--fbn-border); border-radius: 16px; padding: 3px 10px;
      }
      .fbn-search ha-icon { --mdc-icon-size: 18px; width: 18px; height: 18px; opacity: 0.7; }
      .fbn-search input {
        border: none; background: none; color: inherit; font: inherit;
        font-size: 0.9em; min-width: 120px; padding: 2px 0; outline: none;
      }
      .fbn-summary {
        padding: 2px 16px 8px; font-size: 0.82em; color: var(--fbn-header-text);
      }
      .fbn-card, .fbn-root, .fbn-scrollwrap, .fbn-scroll {
        min-width: 0; max-width: 100%; box-sizing: border-box;
      }
      .fbn-scrollwrap { position: relative; overflow: hidden; }
      .fbn-scroll { width: 100%; overflow-x: hidden; }
      .fbn-arrow {
        position: absolute; top: 0; bottom: 0; width: 34px; z-index: 5;
        border: none; cursor: pointer; display: flex; align-items: center;
        justify-content: center; color: var(--fbn-accent);
        background: linear-gradient(
          to var(--fbn-arrow-dir, right),
          var(--card-background-color, rgba(255,255,255,0.96)),
          rgba(0, 0, 0, 0)
        );
      }
      .fbn-arrow[hidden] { display: none; }
      .fbn-arrow ha-icon { --mdc-icon-size: 26px; width: 26px; height: 26px;
        background: var(--card-background-color, #fff); border-radius: 50%;
        box-shadow: 0 1px 4px rgba(0,0,0,0.25); }
      .fbn-arrow-left { left: 0; --fbn-arrow-dir: right; }
      .fbn-arrow-right { right: 0; --fbn-arrow-dir: left; }
      .fbn-arrow:focus-visible { outline: 2px solid var(--fbn-accent); outline-offset: -2px; }
      .fbn-table {
        width: 100%; min-width: 100%; border-collapse: collapse;
        table-layout: fixed; font-size: 0.92em;
      }
      .fbn-th {
        position: sticky; top: 0; z-index: 1;
        background: var(--fbn-header-bg); color: var(--fbn-header-text);
        font-weight: 500; font-size: 0.85em; white-space: nowrap;
        padding: 8px 12px; cursor: pointer; user-select: none;
        border-bottom: 1px solid var(--fbn-border); box-sizing: border-box;
        overflow: hidden; text-overflow: ellipsis;
      }
      .fbn-resizer {
        position: absolute; top: 0; right: -7px; bottom: 0; width: 15px;
        z-index: 6; cursor: col-resize; touch-action: none;
      }
      .fbn-resizer::after {
        content: ""; position: absolute; top: 18%; bottom: 18%; left: 7px;
        width: 2px; background: color-mix(in srgb, var(--fbn-border) 65%, transparent);
      }
      .fbn-resizer:hover::after, .fbn-resizer.fbn-resizing::after { background: var(--fbn-accent); }
      .fbn-th-inner { display: inline-flex; align-items: center; gap: 4px; }
      .fbn-th.fbn-sorted { color: var(--fbn-accent); }
      .fbn-sorticon { --mdc-icon-size: 14px; width: 14px; height: 14px; }
      .fbn-td {
        padding: 8px 12px; border-bottom: 1px solid var(--fbn-border);
        vertical-align: middle; overflow: hidden; text-overflow: ellipsis;
        box-sizing: border-box; min-width: 0; max-width: 0;
      }
      .fbn-col-connection { white-space: normal; overflow-wrap: anywhere; }
      .fbn-col-speed { white-space: nowrap; }
      .fbn-compact .fbn-td, .fbn-compact .fbn-th { padding: 4px 8px; }
      .fbn-tr:nth-child(even) { background: var(--fbn-row-alt-bg); }
      .fbn-tr.fbn-new { background: color-mix(in srgb, var(--warning-color, #ffb300) 20%, transparent); }
      .fbn-tr:last-child .fbn-td { border-bottom: none; }
      .fbn-inactive { opacity: 0.55; }
      .fbn-clickable { cursor: pointer; }
      /* Sticky: Status und Gerätename bleiben beim Blättern links stehen. */
      .fbn-sticky .fbn-col-status {
        position: sticky; left: 0; z-index: 2; box-sizing: border-box;
        width: 40px; min-width: 40px;
        background: var(--card-background-color, #fff);
      }
      .fbn-sticky .fbn-col-name {
        position: sticky; left: 40px; z-index: 2; box-sizing: border-box;
        background: var(--card-background-color, #fff);
      }
      .fbn-sticky .fbn-new .fbn-col-status,
      .fbn-sticky .fbn-new .fbn-col-name {
        background: color-mix(in srgb, var(--warning-color, #ffb300) 20%, var(--card-background-color, #fff));
      }
      .fbn-sticky .fbn-th.fbn-col-status,
      .fbn-sticky .fbn-th.fbn-col-name {
        z-index: 3; background: var(--fbn-header-bg);
      }
      .fbn-namecell { display: flex; align-items: center; gap: 6px; min-width: 0; }
      .fbn-rowicon { --mdc-icon-size: 18px; width: 18px; height: 18px; flex: 0 0 auto; }
      .fbn-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
        max-width: 40vw; }
      .fbn-mono { font-family: var(--code-font-family, monospace); font-size: 0.95em; }
      .fbn-iplink {
        color: var(--fbn-accent); text-decoration: none;
        display: inline-flex; align-items: center; gap: 3px;
      }
      .fbn-iplink:hover { text-decoration: underline; }
      .fbn-iplink-icon {
        --mdc-icon-size: 13px; width: 13px; height: 13px; opacity: 0;
        transition: opacity 120ms ease;
      }
      .fbn-iplink:hover .fbn-iplink-icon,
      .fbn-iplink:focus-visible .fbn-iplink-icon { opacity: 0.7; }
      .fbn-dim { color: var(--fbn-inactive); }
      .fbn-lease { font-size: 0.85em; }
      .fbn-dot {
        display: inline-block; width: 10px; height: 10px; border-radius: 50%;
      }
      .fbn-dot-on { background: var(--fbn-active); }
      .fbn-dot-off { background: var(--fbn-inactive); }
      .fbn-dot-pihole { background: var(--fbn-accent); box-shadow: 0 0 0 2px color-mix(in srgb, var(--fbn-accent) 20%, transparent); }
      .fbn-pihole-icon { color: var(--fbn-accent); }
      .fbn-badge {
        display: inline-block; border-radius: 4px; padding: 1px 6px;
        font-size: 0.72em; border: 1px solid var(--fbn-border); white-space: nowrap;
      }
      .fbn-badge-guest { color: var(--fbn-guest); border-color: var(--fbn-guest); }
      .fbn-badge-new { color: #5d4300; background: var(--warning-color, #ffb300); border-color: var(--warning-color, #ffb300); cursor: pointer; font: inherit; display: inline-flex; align-items: center; gap: 3px; }
      .fbn-badge-new ha-icon { --mdc-icon-size: 14px; width: 14px; height: 14px; }
      .fbn-badge-static { color: var(--fbn-static); border-color: var(--fbn-static); }
      .fbn-icon-blocked { color: var(--fbn-blocked); --mdc-icon-size: 18px; width: 18px; height: 18px; }
      .fbn-icon-update { color: var(--fbn-update); --mdc-icon-size: 18px; width: 18px; height: 18px; }
      .fbn-empty { padding: 16px; text-align: center; color: var(--fbn-inactive); }
      .fbn-pihole-heading td { padding: 5px 10px; background: var(--fbn-header-bg); }
      .fbn-pihole-heading td > div { display: flex; align-items: center; flex-wrap: wrap; gap: 6px 12px; }
      .fbn-pihole-heading td > div > span:first-child { display: inline-flex; align-items: center; gap: 6px; font-weight: 600; }
      .fbn-pihole-heading ha-icon { --mdc-icon-size: 17px; color: var(--fbn-accent); }
      .fbn-pihole-buttons { display: inline-flex; flex-wrap: wrap; gap: 6px; margin-left: auto; }
      .fbn-pihole-heading .fbn-btn { padding: 4px 8px; font-size: 0.78em; }
      .fbn-pihole-row { cursor: pointer; }
      .fbn-pihole-row:hover td { background: color-mix(in srgb, var(--fbn-accent) 5%, transparent); }
      .fbn-pihole-row td { padding-top: 2px; padding-bottom: 2px; height: 27px; }
      .fbn-pihole-row input {
        width: 100%; box-sizing: border-box; min-width: 70px;
        border: 1px solid var(--fbn-border); border-radius: 4px;
        padding: 3px 6px; background: transparent;
        color: var(--fbn-row-text); font: inherit; font-size: 0.86em; line-height: 1.25;
      }
      .fbn-pihole-row input:focus { outline: 2px solid var(--fbn-accent); outline-offset: 0; }
      .fbn-badge-manual { color: var(--warning-color, #ffb300); border-color: var(--warning-color, #ffb300); }
      .fbn-pihole-namecell { position: relative; }
      .fbn-pihole-namecell input { padding-right: 72px; }
      .fbn-pihole-rowbuttons { position: absolute; right: 7px; top: 50%; transform: translateY(-50%); display: inline-flex; gap: 2px; }
      .fbn-icon-btn {
        display: inline-flex; border: none; border-radius: 4px;
        background: var(--card-background-color); color: inherit; cursor: pointer; padding: 2px;
      }
      .fbn-icon-btn ha-icon { --mdc-icon-size: 15px; width: 15px; height: 15px; }
      .fbn-pihole-delete { color: var(--fbn-blocked); }
      .fbn-pihole-save { color: var(--fbn-accent); }
      .fbn-pihole-error { color: var(--error-color, #db4437); font-size: 0.8em; }
      .fbn-clickable:focus-visible { outline: 2px solid var(--fbn-accent); outline-offset: -2px; }
      .fbn-th:focus { outline: none; }
      .fbn-th:focus-visible { outline: 2px solid var(--fbn-accent); outline-offset: -2px; }
    `;
  }

  /**
   * Styles des Detail-Popups. Getrennt von _styles(), weil der Overlay-
   * Knoten am document.body haengt und dort sein eigenes <style> braucht.
   */
  _popupStyles() {
    return `
      .fbn-overlay {
        position: fixed; inset: 0; z-index: 9999;
        background: rgba(0, 0, 0, 0.45);
        display: flex; align-items: center; justify-content: center;
        padding: 16px;
      }
      .fbn-modal {
        background: var(--card-background-color, var(--ha-card-background, #fff));
        color: var(--primary-text-color, #212121);
        border-radius: var(--ha-card-border-radius, 12px);
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.35);
        width: min(460px, 100%); max-height: min(80vh, 640px);
        display: flex; flex-direction: column; overflow: hidden;
        font-family: var(--primary-font-family, inherit);
      }
      .fbn-modal-head {
        display: flex; align-items: center; gap: 12px;
        padding: 16px 16px 12px; border-bottom: 1px solid var(--divider-color, #e0e0e0);
      }
      .fbn-modal-icon { --mdc-icon-size: 26px; width: 26px; height: 26px; flex: 0 0 auto; }
      .fbn-modal-titles { flex: 1; min-width: 0; }
      .fbn-modal-title {
        font-size: 1.15em; font-weight: 500;
        overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
      }
      .fbn-modal-sub {
        font-size: 0.82em; color: var(--secondary-text-color, #727272);
        display: flex; align-items: center; gap: 6px; margin-top: 2px;
      }
      .fbn-modal-close {
        border: none; background: none; cursor: pointer; padding: 4px;
        color: var(--secondary-text-color, #727272); border-radius: 50%;
        display: inline-flex; flex: 0 0 auto;
      }
      .fbn-modal-close:hover { background: var(--divider-color, #e0e0e0); }
      .fbn-modal-body { padding: 8px 16px; overflow-y: auto; }
      .fbn-modal-note {
        background: var(--warning-color, #ffa600); color: #000;
        border-radius: 6px; padding: 6px 10px; margin: 8px 0; font-size: 0.85em;
      }
      .fbn-drow {
        display: flex; justify-content: space-between; gap: 16px;
        padding: 7px 0; border-bottom: 1px solid var(--divider-color, #ededed);
      }
      .fbn-drow:last-child { border-bottom: none; }
      .fbn-dt { color: var(--secondary-text-color, #727272); font-size: 0.9em; flex: 0 0 auto; }
      .fbn-dd {
        text-align: right; word-break: break-word;
        display: inline-flex; align-items: center; gap: 6px; justify-content: flex-end;
      }
      .fbn-dd.fbn-mono { font-family: var(--code-font-family, monospace); }
      .fbn-copy {
        border: none; background: none; cursor: pointer; padding: 2px;
        color: var(--secondary-text-color, #727272); display: inline-flex;
        border-radius: 4px;
      }
      .fbn-copy:hover { color: var(--primary-color, #03a9f4); }
      .fbn-copy ha-icon { --mdc-icon-size: 16px; width: 16px; height: 16px; }
      .fbn-modal-foot {
        display: flex; flex-wrap: wrap; gap: 8px; justify-content: flex-end;
        padding: 12px 16px 16px; border-top: 1px solid var(--divider-color, #e0e0e0);
      }
      .fbn-btn {
        display: inline-flex; align-items: center; gap: 6px;
        border: 1px solid var(--divider-color, #e0e0e0); border-radius: 8px;
        background: none; color: inherit; font: inherit; font-size: 0.9em;
        padding: 8px 14px; cursor: pointer;
      }
      .fbn-btn ha-icon { --mdc-icon-size: 18px; width: 18px; height: 18px; }
      a.fbn-btn { text-decoration: none; color: inherit; }
      .fbn-btn:hover { background: var(--divider-color, #f0f0f0); }
      .fbn-btn[disabled] { opacity: 0.6; cursor: default; }
      .fbn-btn-primary {
        border-color: var(--primary-color, #03a9f4); color: var(--primary-color, #03a9f4);
      }
      .fbn-dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; }
      .fbn-dot-on { background: var(--success-color, #43a047); }
      .fbn-dot-off { background: var(--disabled-text-color, #9e9e9e); }
    `;
  }
}

/* ------------------------------------------------------------------ */
/* Editor                                                              */
/* ------------------------------------------------------------------ */

const EDITOR_SCHEMA = [
  { name: "entity", required: true, selector: { entity: { domain: "sensor" } } },
  { name: "title", selector: { text: {} } },
  {
    type: "expandable",
    name: "spalten",
    title: "Spalten",
    flatten: true,
    icon: "mdi:table-column",
    schema: COLUMNS.map((column) => ({
      name: column.cfg,
      selector: { boolean: {} },
    })),
  },
  {
    type: "expandable",
    name: "darstellung",
    title: "Darstellung",
    flatten: true,
    icon: "mdi:tune",
    schema: [
      { name: "show_summary", selector: { boolean: {} } },
      { name: "show_search", selector: { boolean: {} } },
      { name: "show_filter", selector: { boolean: {} } },
      { name: "show_filter_all", selector: { boolean: {} } },
      { name: "show_filter_active", selector: { boolean: {} } },
      { name: "show_filter_inactive", selector: { boolean: {} } },
      { name: "show_filter_guest", selector: { boolean: {} } },
      { name: "show_filter_blocked", selector: { boolean: {} } },
      { name: "show_filter_update", selector: { boolean: {} } },
      { name: "show_filter_new", selector: { boolean: {} } },
      { name: "show_filter_manual", selector: { boolean: {} } },
      { name: "show_filter_networks", selector: { boolean: {} } },
      { name: "show_refresh", selector: { boolean: {} } },
      { name: "show_pihole_records", selector: { boolean: {} } },
      { name: "hide_inactive", selector: { boolean: {} } },
      { name: "compact", selector: { boolean: {} } },
      { name: "show_details_popup", selector: { boolean: {} } },
      { name: "open_device_on_click", selector: { boolean: {} } },
      { name: "show_scroll_arrows", selector: { boolean: {} } },
      { name: "sticky_name", selector: { boolean: {} } },
      { name: "ip_opens_web", selector: { boolean: {} } },
      { name: "ip_web_fallback", selector: { boolean: {} } },
      {
        name: "max_rows",
        selector: { number: { min: 0, max: 500, mode: "box" } },
      },
    ],
  },
  {
    type: "expandable",
    name: "sortierung",
    title: "Sortierung",
    flatten: true,
    icon: "mdi:sort",
    schema: [
      {
        name: "sort_by",
        selector: {
          select: {
            mode: "dropdown",
            options: COLUMNS.map((column) => ({
              value: column.key,
              label: column.key === "status" ? "Status" : column.label,
            })),
          },
        },
      },
      {
        name: "sort_dir",
        selector: {
          select: {
            mode: "dropdown",
            options: [
              { value: "asc", label: "Aufsteigend" },
              { value: "desc", label: "Absteigend" },
            ],
          },
        },
      },
    ],
  },
];

const EDITOR_LABELS = {
  entity: "Sensor mit der Geräteliste",
  title: "Titel",
  show_status: "Status",
  show_name: "Gerät",
  show_network: "Netz / Subnetz",
  show_ip: "IP-Adresse",
  show_mac: "MAC-Adresse",
  show_ptr1: "PTR 1",
  show_ptr2: "PTR 2",
  show_comment: "Kommentar",
  show_connection: "Verbindung",
  show_ha_name: "Home-Assistant-Gerätename",
  show_ip_type: "IP-Typ (DHCP oder statisch)",
  show_wan: "Internetzugang",
  show_update: "Firmware-Update",
  show_speed: "Tempo",
  show_model: "Modell",
  show_type: "Gerätetyp",
  show_summary: "Zusammenfassung anzeigen",
  show_search: "Suchfeld anzeigen",
  show_filter: "Filterleiste anzeigen",
  show_filter_all: "Filter „Alle“ anzeigen",
  show_filter_active: "Filter „Aktiv“ anzeigen",
  show_filter_inactive: "Filter „Inaktiv“ anzeigen",
  show_filter_guest: "Filter „Gast“ anzeigen",
  show_filter_blocked: "Filter „Gesperrt“ anzeigen",
  show_filter_update: "Filter „Update“ anzeigen",
  show_filter_new: "Filter „Neu“ anzeigen",
  show_filter_manual: "Filter „Manuell“ anzeigen",
  show_filter_networks: "Netzfilter „Heimnetz/Gast“ anzeigen",
  show_refresh: "Schaltfläche „Aktualisieren“ anzeigen",
  show_pihole_records: "Manuelle Pi-hole-DNS-Einträge anzeigen",
  hide_inactive: "Nicht verbundene Geräte ausblenden",
  compact: "Kompakte Zeilen",
  show_details_popup: "Klick öffnet ein Detail-Popup",
  open_device_on_click: "Klick öffnet das Home-Assistant-Gerät",
  show_scroll_arrows: "Blätter-Pfeile bei breiter Tabelle",
  sticky_name: "Gerätename beim Blättern festhalten",
  ip_opens_web: "Klick auf die IP öffnet die Weboberfläche",
  ip_web_fallback: "Notfalls http://IP verwenden",
  max_rows: "Höchstzahl Zeilen (0 = alle)",
  sort_by: "Sortieren nach",
  sort_dir: "Richtung",
};

const EDITOR_HELPERS = {
  show_network: "Unterscheidet LAN/WLAN sowie Gast LAN/Gast WLAN; Subnetze sind separat filterbar.",
  show_ptr1: "Erste PTR-Antwort der FRITZ!Box; kann den schreibgeschützten Namen der Erstverbindung enthalten.",
  show_ptr2: "Zweite PTR-Antwort, sofern die FRITZ!Box mehrere Namen meldet.",
  show_comment: "MAC-basierter Kommentar, lokal in Home Assistant gespeichert.",
  show_ip_type: "Braucht die eingeschaltete IP-Typ-Erfassung in den Einstellungen der Integration.",
  show_ha_name: "Zeigt den Gerätenamen aus Home Assistant, sofern das Gerät dort eine MAC-Adresse hinterlegt hat.",
  show_details_popup: "Zeigt beim Antippen alle Felder eines Geräts, auch die auf schmalen Karten ausgeblendeten wie die MAC-Adresse.",
  show_filter: "Schaltet die komplette Filterleiste ein oder aus. Die folgenden Schalter bestimmen die einzelnen Filter.",
  open_device_on_click: "Wirkt nur, wenn das Detail-Popup ausgeschaltet ist.",
  show_scroll_arrows: "Passen nicht alle Spalten nebeneinander (z. B. auf dem Smartphone), wird die Tabelle waagerecht scrollbar. Diese Pfeile blättern zusätzlich per Klick; wischen geht auch direkt.",
  sticky_name: "Beim waagerechten Blättern bleiben Statuspunkt und Gerätename links stehen.",
  ip_opens_web: "Öffnet die von der FRITZ!Box gemeldete Geräteseite in einem neuen Browser-Tab.",
  ip_web_fallback: "Meldet die FRITZ!Box keine Adresse, wird http://<IP> versucht. Kann bei Geräten ohne Weboberfläche ins Leere laufen.",
  max_rows: "Begrenzt die Tabelle, zum Beispiel für eine Übersichtskarte.",
};

class FritzSyncNetworkCardEditor extends HTMLElement {
  constructor() {
    super();
    this._config = withDefaults({});
    this._hass = null;
    this._rendered = false;
    this._focusedColorKey = null;
  }

  setConfig(config) {
    this._config = withDefaults(config);
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._form) this._form.hass = hass;
  }

  _fire(config) {
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config },
        bubbles: true,
        composed: true,
      })
    );
  }

  _render() {
    if (!this._rendered) {
      this.innerHTML = `
        <style>${this._styles()}</style>
        <div class="fbn-editor">
          <div class="fbn-form"></div>
          <details class="fbn-order-editor">
            <summary>
              <ha-icon icon="mdi:swap-vertical"></ha-icon>
              <span class="fbn-order-title">Spalten verschieben</span>
              <ha-icon class="fbn-order-chevron" icon="mdi:chevron-down"></ha-icon>
            </summary>
            <div class="fbn-order-help">Ziehen oder mit den Pfeilen verschieben. Ausgeblendete Spalten bleiben in der Reihenfolge erhalten.</div>
            <div class="fbn-order-rows"></div>
          </details>
          <details class="fbn-color-editor">
            <summary>
              <ha-icon icon="mdi:palette-outline"></ha-icon>
              <span class="fbn-color-title">Farben</span>
              <ha-icon class="fbn-color-chevron" icon="mdi:chevron-down"></ha-icon>
            </summary>
            <div class="fbn-color-body">
              <button type="button" class="fbn-reset"><ha-icon icon="mdi:restore"></ha-icon>Alle Farben zurücksetzen</button>
              <div class="fbn-color-rows"></div>
            </div>
          </details>
        </div>`;

      this._form = document.createElement("ha-form");
      this._form.schema = EDITOR_SCHEMA;
      this._form.computeLabel = (schema) =>
        EDITOR_LABELS[schema.name] || schema.title || schema.name;
      this._form.computeHelper = (schema) => EDITOR_HELPERS[schema.name] || "";
      this._form.addEventListener("value-changed", (event) => {
        event.stopPropagation();
        this._config = withDefaults({ ...this._config, ...event.detail.value });
        this._fire(this._config);
      });
      this.querySelector(".fbn-form").appendChild(this._form);

      this.querySelector(".fbn-reset").addEventListener("click", () => {
        // Der Fokusschutz wird hier bewusst uebergangen: ein Klick auf
        // "Zuruecksetzen" ist eine ausdrueckliche Nutzerentscheidung.
        this._focusedColorKey = null;
        const config = { ...this._config };
        for (const field of COLOR_EDITOR_FIELDS) config[field.key] = "";
        this._config = config;
        this._fire(config);
        this._renderColors();
      });

      this.querySelector(".fbn-order-rows").addEventListener("click", (event) => {
        const button = event.target.closest("button[data-move]");
        if (!button) return;
        this._moveColumn(button.dataset.key, button.dataset.move === "up" ? -1 : 1);
      });

      this._rendered = true;
    }

    if (this._hass) this._form.hass = this._hass;
    this._form.data = this._config;
    this._renderColumnOrder();
    this._renderColors();
  }

  _renderColumnOrder() {
    const container = this.querySelector(".fbn-order-rows");
    if (!container) return;
    const columns = orderedColumns(this._config);
    container.innerHTML = columns.map((column, index) => `
      <div class="fbn-order-row" draggable="true" data-key="${column.key}">
        <ha-icon class="fbn-order-drag" icon="mdi:drag-vertical"></ha-icon>
        <span>${escapeHtml(column.key === "status" ? "Status" : column.label)}</span>
        <span class="fbn-order-state">${this._config[column.cfg] ? "sichtbar" : "ausgeblendet"}</span>
        <button type="button" data-key="${column.key}" data-move="up" aria-label="Nach oben" ${index === 0 ? "disabled" : ""}><ha-icon icon="mdi:chevron-up"></ha-icon></button>
        <button type="button" data-key="${column.key}" data-move="down" aria-label="Nach unten" ${index === columns.length - 1 ? "disabled" : ""}><ha-icon icon="mdi:chevron-down"></ha-icon></button>
      </div>`).join("");
    let dragged = "";
    container.querySelectorAll(".fbn-order-row").forEach((row) => {
      row.addEventListener("dragstart", () => {
        dragged = row.dataset.key;
        row.classList.add("fbn-dragging");
      });
      row.addEventListener("dragend", () => {
        dragged = "";
        row.classList.remove("fbn-dragging");
      });
      row.addEventListener("dragover", (event) => event.preventDefault());
      row.addEventListener("drop", (event) => {
        event.preventDefault();
        const target = row.dataset.key;
        if (dragged && target && dragged !== target) this._moveColumnBefore(dragged, target);
      });
    });
  }

  _setColumnOrder(keys) {
    this._config = { ...this._config, column_order: keys };
    this._fire(this._config);
    this._renderColumnOrder();
  }

  _moveColumn(key, delta) {
    const keys = orderedColumns(this._config).map((column) => column.key);
    const from = keys.indexOf(key);
    const to = from + delta;
    if (from < 0 || to < 0 || to >= keys.length) return;
    [keys[from], keys[to]] = [keys[to], keys[from]];
    this._setColumnOrder(keys);
  }

  _moveColumnBefore(key, target) {
    const keys = orderedColumns(this._config).map((column) => column.key);
    const from = keys.indexOf(key);
    if (from < 0) return;
    keys.splice(from, 1);
    keys.splice(keys.indexOf(target), 0, key);
    this._setColumnOrder(keys);
  }

  _renderColors() {
    const container = this.querySelector(".fbn-color-rows");
    if (!container) return;

    container.innerHTML = COLOR_EDITOR_FIELDS.map((field) => {
      const raw = this._config[field.key] || "";
      const safe = sanitizeColor(raw);
      const effective = safe || COLOR_FALLBACKS[field.key];
      const hex = normalizeHex(safe) || "#888888";
      const note = safe
        ? `aktuell: ${escapeHtml(safe)}`
        : `aktuell: Standard des Themes (${escapeHtml(COLOR_FALLBACKS[field.key])})`;
      const invalid = raw && !safe ? '<span class="fbn-invalid">Wert nicht gültig</span>' : "";
      return `
        <div class="fbn-color-row" data-key="${field.key}">
          <div class="fbn-color-meta">
            <span class="fbn-color-label">${escapeHtml(field.label)}</span>
            <span class="fbn-color-note">${note}</span>
            ${invalid}
          </div>
          <div class="fbn-color-controls">
            <span class="fbn-color-preview" style="background:${effective}"></span>
            <input class="fbn-color-text" type="text" value="${escapeHtml(raw)}"
                   placeholder="z. B. #4caf50" aria-label="${escapeHtml(field.label)}">
            <input class="fbn-color-pick" type="color" value="${hex}"
                   aria-label="${escapeHtml(field.label)} grafisch wählen">
          </div>
        </div>`;
    }).join("");

    container.querySelectorAll(".fbn-color-row").forEach((row) => {
      const key = row.dataset.key;
      const text = row.querySelector(".fbn-color-text");
      const pick = row.querySelector(".fbn-color-pick");

      text.addEventListener("focus", () => {
        this._focusedColorKey = key;
      });
      text.addEventListener("blur", () => {
        if (this._focusedColorKey === key) this._focusedColorKey = null;
      });
      text.addEventListener("change", () => this._setColor(key, text.value));
      pick.addEventListener("change", () => this._setColor(key, pick.value));
    });

    // Fokus nach einem externen Neuzeichnen zurueckgeben.
    if (this._focusedColorKey) {
      const field = container.querySelector(
        `.fbn-color-row[data-key="${this._focusedColorKey}"] .fbn-color-text`
      );
      if (field) {
        const end = field.value.length;
        field.focus();
        field.setSelectionRange(end, end);
      }
    }
  }

  _setColor(key, value) {
    const config = { ...this._config, [key]: value || "" };
    this._config = config;
    this._fire(config);
    this._renderColors();
  }

  _styles() {
    return `
      .fbn-editor { display: flex; flex-direction: column; gap: 16px; }
      .fbn-order-editor, .fbn-color-editor {
        border: 1px solid var(--divider-color); border-radius: 6px; padding: 0;
      }
      .fbn-order-editor > summary, .fbn-color-editor > summary {
        display: flex; align-items: center; gap: 8px; cursor: pointer;
        padding: 12px 16px; font-size: 16px; font-weight: 400;
        list-style: none;
      }
      .fbn-order-editor > summary::-webkit-details-marker,
      .fbn-color-editor > summary::-webkit-details-marker { display: none; }
      .fbn-order-editor > summary::marker, .fbn-color-editor > summary::marker { content: ""; }
      .fbn-order-editor > summary ha-icon, .fbn-color-editor > summary ha-icon { --mdc-icon-size: 24px; width: 24px; height: 24px; }
      .fbn-order-title, .fbn-color-title { flex: 1; }
      .fbn-order-chevron, .fbn-color-chevron { transition: transform 180ms ease; }
      .fbn-order-editor[open] > summary .fbn-order-chevron,
      .fbn-color-editor[open] > summary .fbn-color-chevron { transform: rotate(180deg); }
      .fbn-order-help { padding: 0 16px 8px; font-size: 0.82em; color: var(--secondary-text-color); }
      .fbn-order-rows { padding: 0 16px 12px; }
      .fbn-order-row {
        display: grid; grid-template-columns: 24px minmax(120px, 1fr) auto 34px 34px;
        align-items: center; gap: 6px; min-height: 38px;
        border-bottom: 1px solid var(--divider-color); cursor: grab;
      }
      .fbn-order-row:last-child { border-bottom: none; }
      .fbn-order-row.fbn-dragging { opacity: 0.45; }
      .fbn-order-drag { color: var(--secondary-text-color); }
      .fbn-order-state { font-size: 0.75em; color: var(--secondary-text-color); }
      .fbn-order-row button {
        border: none; background: none; color: var(--primary-text-color); cursor: pointer;
        width: 34px; height: 34px; padding: 5px; border-radius: 50%;
      }
      .fbn-order-row button[disabled] { opacity: 0.25; cursor: default; }
      .fbn-order-row button ha-icon { --mdc-icon-size: 20px; width: 20px; height: 20px; }
      .fbn-color-body { padding: 0 16px 16px; }
      .fbn-reset {
        display: inline-flex; align-items: center; gap: 6px;
        border: 1px solid var(--divider-color); border-radius: 4px;
        background: none; color: var(--primary-color); font: inherit;
        font-size: 0.9em; padding: 6px 12px; cursor: pointer; margin-bottom: 12px;
      }
      .fbn-reset ha-icon { --mdc-icon-size: 18px; width: 18px; height: 18px; }
      .fbn-color-row {
        display: flex; align-items: center; justify-content: space-between;
        gap: 12px; padding: 8px 0; border-bottom: 1px solid var(--divider-color);
        flex-wrap: wrap;
      }
      .fbn-color-row:last-child { border-bottom: none; }
      .fbn-color-meta { display: flex; flex-direction: column; min-width: 140px; }
      .fbn-color-note { font-size: 0.75em; color: var(--secondary-text-color); }
      .fbn-invalid { font-size: 0.75em; color: var(--error-color); }
      .fbn-color-controls { display: flex; align-items: center; gap: 8px; }
      .fbn-color-preview {
        width: 22px; height: 22px; border-radius: 4px;
        border: 1px solid var(--divider-color); flex: 0 0 auto;
      }
      .fbn-color-text {
        width: 120px; padding: 4px 6px; font: inherit; font-size: 0.9em;
        border: 1px solid var(--divider-color); border-radius: 4px;
        background: none; color: var(--primary-text-color);
      }
      .fbn-color-pick {
        width: 34px; height: 28px; padding: 0; border: none; background: none;
        cursor: pointer;
      }
    `;
  }
}

/* ------------------------------------------------------------------ */
/* Registrierung                                                       */
/* ------------------------------------------------------------------ */

if (!customElements.get("fritzsync-network-card")) {
  customElements.define("fritzsync-network-card", FritzSyncNetworkCard);
}
if (!customElements.get("fritzsync-network-card-editor")) {
  customElements.define("fritzsync-network-card-editor", FritzSyncNetworkCardEditor);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "fritzsync-network-card")) {
  window.customCards.push({
    type: "fritzsync-network-card",
    name: "FRITZ!Sync - Homeassistant",
    description: "Sortierbare Tabelle aller Geräte im FRITZ!Box-Heimnetz.",
    preview: false,
    documentationURL: "https://github.com/kulmi84/FRITZsync-ha",
  });
}

console.info(
  `%c FRITZSYNC-NETWORK-CARD %c ${FBN_VERSION} `,
  "color:#fff;background:#1c6ea4;font-weight:700;",
  "color:#1c6ea4;background:#fff;font-weight:700;"
);
