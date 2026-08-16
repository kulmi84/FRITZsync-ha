const ICONS = {
  router: "mdi:router-network", lan: "mdi:ethernet", wlan: "mdi:wifi",
  guest: "mdi:account-group", powerline: "mdi:power-plug", other: "mdi:devices",
};

class FritzSyncNetworkCard extends HTMLElement {
  setConfig(config) {
    this.config = { title: "Netzwerk", show_offline: true, ...config };
    this.selected = null;
    this.filter = "all";
    this.query = "";
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    this.render();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this.config.entity) {
      this.config.entity = Object.keys(hass.states).find((entityId) => {
        const state = hass.states[entityId];
        return entityId.startsWith("sensor.") &&
          Array.isArray(state?.attributes?.hosts) &&
          Boolean(state?.attributes?.entry_id);
      });
    }
    this.render();
  }

  getCardSize() { return 8; }

  static getConfigElement() { return document.createElement("fritzsync-network-card-editor"); }
  static getStubConfig(hass, entities) {
    const entity = entities.find((id) => id.startsWith("sensor.") && id.includes("fritzsync"));
    return { entity, title: "Mein Netzwerk", show_offline: true };
  }

  _escape(value) {
    return String(value ?? "").replace(/[&<>'"]/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char]));
  }

  _filtered(hosts) {
    const needle = this.query.toLowerCase();
    return hosts.filter((host) => {
      if (!this.config.show_offline && !host.active) return false;
      if (this.filter === "active" && !host.active) return false;
      if (this.filter === "offline" && host.active) return false;
      if (this.filter === "blocked" && !host.blocked) return false;
      if (this.filter === "guest" && !host.guest) return false;
      return !needle || [host.name, host.ip, host.mac, host.model].some((v) => String(v || "").toLowerCase().includes(needle));
    });
  }

  _node(host) {
    const speed = host.speed ? `<span>${host.speed >= 1000 ? `${(host.speed/1000).toFixed(1)} Gbit/s` : `${host.speed} Mbit/s`}</span>` : "";
    return `<button class="device ${host.active ? "online" : "offline"} ${host.blocked ? "blocked" : ""}" data-device="${this._escape(host.id)}">
      <span class="status"></span><ha-icon icon="${ICONS[host.connection] || ICONS.other}"></ha-icon>
      <span class="label"><strong>${this._escape(host.name)}</strong><small>${this._escape(host.ip || "Keine IP")}</small></span>
      ${speed}${host.blocked ? '<ha-icon class="lock" icon="mdi:lock"></ha-icon>' : ""}
    </button>`;
  }

  _group(title, kind, hosts) {
    if (!hosts.length) return "";
    return `<section class="branch"><div class="branch-title"><ha-icon icon="${ICONS[kind] || ICONS.router}"></ha-icon><span>${this._escape(title)}</span><b>${hosts.length}</b></div><div class="line"></div><div class="devices">${hosts.map((host) => this._node(host)).join("")}</div></section>`;
  }

  _content(state) {
    const attrs = state.attributes || {};
    const hosts = this._filtered(attrs.hosts || []);
    const meshNodes = attrs.mesh_nodes || [];
    const groups = [];
    const assigned = new Set();
    for (const node of meshNodes) {
      const children = hosts.filter((host) => host.mesh_parent === node.id);
      if (!children.length) continue;
      children.forEach((host) => assigned.add(host.id));
      groups.push(this._group(node.name, "router", children));
    }
    const remaining = hosts.filter((host) => !assigned.has(host.id));
    const labels = { lan: "LAN", wlan: "WLAN", guest: "Gastnetz", powerline: "Powerline", other: "Weitere Geräte" };
    for (const kind of ["lan", "wlan", "guest", "powerline", "other"]) {
      groups.push(this._group(labels[kind], kind, remaining.filter((host) => host.connection === kind)));
    }
    return groups.join("") || '<div class="empty">Keine passenden Geräte</div>';
  }

  render() {
    if (!this._hass || !this.config || !this.shadowRoot) return;
    const state = this._hass.states[this.config.entity];
    if (!state) {
      const target = this.config.entity
        ? `Entität ${this._escape(this.config.entity)} nicht gefunden`
        : "Kein FritzSync-Network-Sensor gefunden. Bitte zuerst die Integration einrichten.";
      this.shadowRoot.innerHTML = `<style>${this._styles()}</style><ha-card><div class="empty">${target}</div></ha-card>`;
      return;
    }
    const attrs = state.attributes || {};
    this.shadowRoot.innerHTML = `<style>${this._styles()}</style><ha-card>
      <header><div><h2>${this._escape(this.config.title)}</h2><p>${attrs.active || 0} aktiv · ${attrs.total || 0} bekannt · ${attrs.blocked || 0} gesperrt</p></div><ha-icon icon="mdi:router-wireless"></ha-icon></header>
      <div class="tools"><input type="search" placeholder="Gerät suchen …" value="${this._escape(this.query)}"><div class="filters">${[["all","Alle"],["active","Aktiv"],["offline","Offline"],["blocked","Gesperrt"],["guest","Gast"]].map(([value,label]) => `<button data-filter="${value}" class="${this.filter === value ? "selected" : ""}">${label}</button>`).join("")}</div></div>
      <main><div class="root"><ha-icon icon="mdi:router-network"></ha-icon><div><strong>FRITZ!Box</strong><small>Internet &amp; Mesh Master</small></div></div><div class="trunk"></div>${this._content(state)}</main>
      <dialog></dialog>
    </ha-card>`;
    this.shadowRoot.querySelector("input").addEventListener("input", (event) => { this.query = event.target.value; this.render(); });
    this.shadowRoot.querySelectorAll("[data-filter]").forEach((button) => button.addEventListener("click", () => { this.filter = button.dataset.filter; this.render(); }));
    this.shadowRoot.querySelectorAll("[data-device]").forEach((button) => button.addEventListener("click", () => this._open(button.dataset.device, attrs.hosts || [], attrs.entry_id)));
  }

  _open(id, hosts, entryId) {
    const host = hosts.find((item) => item.id === id);
    if (!host) return;
    const dialog = this.shadowRoot.querySelector("dialog");
    dialog.innerHTML = `<form method="dialog"><button class="close" value="cancel"><ha-icon icon="mdi:close"></ha-icon></button><div class="hero"><span class="big-status ${host.active ? "online" : ""}"></span><div><h3>${this._escape(host.name)}</h3><p>${host.active ? "Verbunden" : "Offline"} · ${this._escape(host.connection.toUpperCase())}</p></div></div>
      <dl><dt>IP-Adresse</dt><dd>${this._escape(host.ip || "—")}</dd><dt>MAC-Adresse</dt><dd>${this._escape(host.mac || "—")}</dd><dt>Modell</dt><dd>${this._escape(host.model || "—")}</dd><dt>Tempo</dt><dd>${host.speed ? `${host.speed} Mbit/s` : "—"}</dd><dt>Internet</dt><dd>${host.blocked ? "Gesperrt" : "Freigegeben"}</dd></dl>
      <div class="actions"><button type="button" data-action="rename"><ha-icon icon="mdi:pencil"></ha-icon> Umbenennen</button><button type="button" data-action="block" ${!host.ip ? "disabled" : ""}><ha-icon icon="${host.blocked ? "mdi:lock-open" : "mdi:lock"}"></ha-icon> ${host.blocked ? "Freigeben" : "Sperren"}</button><button type="button" data-action="wake" ${!host.mac ? "disabled" : ""}><ha-icon icon="mdi:power"></ha-icon> Aufwecken</button></div><div class="feedback"></div></form>`;
    dialog.querySelector('[data-action="rename"]').onclick = async () => {
      const name = prompt("Neuer Gerätename in der FRITZ!Box:", host.name);
      if (!name || name === host.name) return;
      await this._confirmCall(dialog, `„${host.name}“ wirklich in „${name}“ umbenennen?`, "rename_device", { entry_id: entryId, mac: host.mac, name });
    };
    dialog.querySelector('[data-action="block"]').onclick = () => this._confirmCall(dialog, `Internetzugang für „${host.name}“ wirklich ${host.blocked ? "freigeben" : "sperren"}?`, "set_internet_blocked", { entry_id: entryId, ip: host.ip, blocked: !host.blocked });
    dialog.querySelector('[data-action="wake"]').onclick = () => this._confirmCall(dialog, `Wake-on-LAN wirklich an „${host.name}“ senden?`, "wake_device", { entry_id: entryId, mac: host.mac });
    dialog.showModal();
  }

  async _confirmCall(dialog, question, service, data) {
    if (!confirm(question)) return;
    const feedback = dialog.querySelector(".feedback");
    feedback.textContent = "Wird ausgeführt …";
    try {
      await this._hass.callService("fritzsync_network", service, data);
      feedback.textContent = "Erfolgreich ausgeführt.";
      setTimeout(() => { dialog.close(); }, 650);
    } catch (error) {
      feedback.textContent = `Fehler: ${error.message || error}`;
    }
  }

  _styles() { return `
    :host{--accent:var(--primary-color,#e20074);display:block} ha-card{overflow:hidden;font-family:var(--paper-font-body1_-_font-family,system-ui);background:linear-gradient(145deg,var(--ha-card-background,var(--card-background-color,#fff)),color-mix(in srgb,var(--accent) 5%,var(--card-background-color,#fff)))}
    header{display:flex;justify-content:space-between;align-items:center;padding:22px 24px 10px}header h2{margin:0;font-size:22px}header p{margin:5px 0 0;color:var(--secondary-text-color)}header>ha-icon{--mdc-icon-size:38px;color:var(--accent)}
    .tools{padding:10px 24px 16px}.tools input{box-sizing:border-box;width:100%;padding:11px 14px;border:1px solid var(--divider-color);border-radius:12px;background:var(--card-background-color);color:var(--primary-text-color);font:inherit}.filters{display:flex;gap:7px;overflow:auto;margin-top:10px}.filters button{border:0;border-radius:16px;padding:7px 12px;background:var(--secondary-background-color);color:var(--primary-text-color)}.filters .selected{background:var(--accent);color:white}
    main{padding:4px 24px 24px}.root{display:flex;align-items:center;gap:12px;width:max-content;margin:auto;padding:12px 18px;border-radius:16px;background:var(--accent);color:white;box-shadow:0 6px 18px color-mix(in srgb,var(--accent) 30%,transparent)}.root small,.label small{display:block;opacity:.72;margin-top:2px}.trunk{height:28px;width:2px;background:var(--divider-color);margin:auto}.branch{position:relative;margin:0 0 18px 20px}.branch:before{content:"";position:absolute;left:-20px;top:-1px;bottom:-19px;width:2px;background:var(--divider-color)}.branch:last-child:before{bottom:calc(100% - 22px)}.branch-title{display:flex;align-items:center;gap:9px;padding:9px 12px;border-radius:12px;background:var(--secondary-background-color)}.branch-title:before{content:"";position:absolute;left:-20px;width:20px;height:2px;background:var(--divider-color)}.branch-title b{margin-left:auto;font-size:12px;background:var(--card-background-color);padding:3px 7px;border-radius:10px}.devices{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:8px;margin:9px 0 0 20px}.device{position:relative;display:flex;align-items:center;gap:9px;border:1px solid var(--divider-color);border-radius:12px;padding:10px;background:var(--card-background-color);color:var(--primary-text-color);text-align:left;cursor:pointer}.device:hover{border-color:var(--accent);transform:translateY(-1px)}.device .label{min-width:0;flex:1}.device strong{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.device>span:not(.status):not(.label){font-size:11px;color:var(--secondary-text-color)}.status,.big-status{width:9px;height:9px;border-radius:50%;background:#9aa0a6;flex:none}.online .status,.big-status.online{background:#25a55f;box-shadow:0 0 0 3px color-mix(in srgb,#25a55f 18%,transparent)}.blocked{border-color:#dc3545}.lock{color:#dc3545;--mdc-icon-size:17px}.empty{padding:32px;text-align:center;color:var(--secondary-text-color)}
    dialog{width:min(430px,calc(100vw - 40px));box-sizing:border-box;border:0;border-radius:20px;padding:22px;background:var(--card-background-color);color:var(--primary-text-color);box-shadow:0 18px 55px #0007}dialog::backdrop{background:#0008}.close{float:right;border:0;background:transparent;color:inherit}.hero{display:flex;align-items:center;gap:13px}.hero h3{margin:0;font-size:21px}.hero p{margin:4px 0;color:var(--secondary-text-color)}dl{display:grid;grid-template-columns:110px 1fr;gap:8px;margin:22px 0}dt{color:var(--secondary-text-color)}dd{margin:0;overflow-wrap:anywhere}.actions{display:grid;gap:8px}.actions button{display:flex;align-items:center;justify-content:center;gap:8px;padding:10px;border:0;border-radius:10px;background:var(--secondary-background-color);color:var(--primary-text-color);font:inherit}.actions button:not(:disabled):hover{background:color-mix(in srgb,var(--accent) 15%,var(--secondary-background-color))}.feedback{min-height:20px;margin-top:12px;color:var(--secondary-text-color);text-align:center;font-size:13px}
    @media(max-width:600px){header,.tools,main{padding-left:14px;padding-right:14px}.devices{grid-template-columns:1fr;margin-left:12px}.branch{margin-left:12px}.branch:before{left:-12px}.branch-title:before{left:-12px;width:12px}}
  `; }
}

class FritzSyncNetworkCardEditor extends HTMLElement {
  setConfig(config) { this.config = config; this.render(); }
  set hass(hass) { this._hass = hass; this.render(); }
  render() {
    if (!this.config) return;
    const entities = this._hass ? Object.keys(this._hass.states).filter((id) => id.startsWith("sensor.") && id.includes("fritzsync")) : [];
    this.innerHTML = `<style>label{display:block;margin:12px 0}input,select{display:block;width:100%;box-sizing:border-box;padding:9px;margin-top:4px}</style><label>Entität<select name="entity">${entities.map((id) => `<option ${id===this.config.entity?"selected":""}>${id}</option>`).join("")}</select></label><label>Titel<input name="title" value="${this.config.title || "Mein Netzwerk"}"></label><label><input style="display:inline;width:auto" type="checkbox" name="show_offline" ${this.config.show_offline !== false ? "checked" : ""}> Offline-Geräte anzeigen</label>`;
    this.querySelectorAll("input,select").forEach((field) => field.onchange = () => {
      const config = { ...this.config, [field.name]: field.type === "checkbox" ? field.checked : field.value };
      this.dispatchEvent(new CustomEvent("config-changed", { detail: { config }, bubbles: true, composed: true }));
    });
  }
}

customElements.define("fritzsync-network-card", FritzSyncNetworkCard);
customElements.define("fritzsync-network-card-editor", FritzSyncNetworkCardEditor);
window.customCards = window.customCards || [];
window.customCards.push({ type: "fritzsync-network-card", name: "FritzSync Network Topology", description: "Interaktive FRITZ!Box-Netzwerktopologie" });
