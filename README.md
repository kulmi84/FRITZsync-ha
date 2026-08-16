# FRITZ!Sync - Homeassistant

Lokale Home-Assistant-Integration für FRITZ!Box-Netzwerkgeräte, Pi-hole-DNS und eine
konfigurierbare Dashboard-Tabelle. Geräte lassen sich durchsuchen, filtern, umbenennen,
aufwecken, bestätigen und als aktuelle Ansicht nach Excel exportieren.

![Version](https://img.shields.io/badge/Version-1.10.2-blue)
![HACS](https://img.shields.io/badge/HACS-Custom-orange)
![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2025.1%2B-41BDF5)
![FRITZ!OS](https://img.shields.io/badge/FRITZ!OS-8.x-E2001A)
![Pi--hole](https://img.shields.io/badge/Pi--hole-6.x-96060C)

---

## Inhalt

- [Was die Integration kann](#was-die-integration-kann)
- [Voraussetzungen](#voraussetzungen)
- [Installation](#installation)
- [Einrichtung](#einrichtung)
- [Einstellungen](#einstellungen)
- [Sensoren](#sensoren)
- [Dashboard-Karte](#dashboard-karte)
  - [Spalten](#spalten)
  - [Sortieren, filtern, suchen](#sortieren-filtern-suchen)
  - [Wischen und Blättern auf dem Smartphone](#wischen-und-blättern-auf-dem-smartphone)
  - [IP-Adresse öffnet die Weboberfläche](#ip-adresse-öffnet-die-weboberfläche)
  - [Excel-Export](#excel-export)
  - [Detail-Popup](#detail-popup)
  - [Farben](#farben)
  - [Beispiel-YAML](#beispiel-yaml)
- [Dienste](#dienste)
- [Fehlerbehebung](#fehlerbehebung)
- [Bekannte Einschränkungen](#bekannte-einschränkungen)
- [Entwicklung und Tests](#entwicklung-und-tests)
- [Versionshistorie](#versionshistorie)

---

## Was die Integration kann

- FRITZ!Box- und manuelle Pi-hole-DNS-Einträge als **gemeinsame, nach IP sortierbare Tabelle**
- WebUI-`netDev` als Masterquelle für MAC, IPv4 und sichtbaren Namen; bereinigter
  TR-064-Fallback ohne historische `PC-<MAC>`-Karteileichen
- **Sortierung, Suche und kombinierbare Filter** für Status, neue Geräte, manuelle
  DNS-Einträge, Heimnetz und Gastnetz
- frei wählbare und verschiebbare Spalten; Breiten direkt am Tabellenkopf ziehen und
  browserbezogen speichern
- Unterscheidung zwischen **LAN, WLAN, Gast LAN und Gast WLAN**
- **PTR 1/PTR 2**, Kommentare, IP-Typ, Verbindung, Tempo und Home-Assistant-Zuordnung
- neue Geräte gelb markieren und per bestätigtem Klick als bekannt übernehmen
- sichtbaren Gerätenamen nach Bestätigung direkt in der FRITZ!Box ändern
- optional beim Umbenennen den passenden lokalen Pi-hole-DNS-Eintrag aktualisieren
- manuelle Pi-hole-DNS-Einträge anzeigen, anlegen, bearbeiten und löschen
- bestätigter Gesamtabgleich aller geeigneten FRITZ!Box-Geräte mit Pi-hole
- **echter XLSX-Export** der aktuell sichtbaren Spalten und gefilterten Zeilen
- Aktualisieren lädt Geräteliste, PTR 1/2 und IP-Typ vollständig neu
- **Detail-Popup** bei Klick auf eine Zeile: zeigt alle Felder eines Geräts – auch die
  außerhalb des sichtbaren Bereichs liegenden –, mit Kopier-Knöpfen, Wake-on-LAN,
  Umbenennen, Kommentar und Sprung zum Home-Assistant-Gerät
- **Wischen und Blättern** auf dem Smartphone: alle Spalten per Wischen oder Pfeilen
  erreichbar, Gerätename bleibt dabei stehen
- **Klick auf die IP-Adresse** öffnet die Weboberfläche des Geräts im Browser
- Vollständig über die Oberfläche konfigurierbar, inklusive **frei wählbarer Farben**
- Zwei zusätzliche Zähler-Sensoren für Automatisierungen

Die Karte wird von der Integration mitgeliefert und automatisch als Lovelace-Ressource
eingetragen. Es ist keine separate Installation der Karte nötig.

---

## Voraussetzungen

- Home Assistant 2025.1 oder neuer
- Eine FRITZ!Box mit aktiviertem **„Zugriff für Anwendungen zulassen"**
  (Heimnetz → Netzwerk → Netzwerkeinstellungen)
- Ein FRITZ!Box-Benutzer mit der Berechtigung **„FRITZ!Box Einstellungen"**

Geräteidentität, IPv4-Adresse und sichtbarer Name stammen aus derselben WebUI-`netDev`-
Zeile. TR-064 ergänzt nur Eigenschaften derselben exakten MAC-Adresse. So gelangen
historische `PC-<MAC>`-Karteileichen und veraltete IP-/MAC-Zuordnungen nicht in die
Geräteliste. Bei nicht verfügbarer WebUI bleibt ein bereinigter TR-064-Fallback aktiv.

---

## Installation

### Über HACS (empfohlen)

1. In HACS → Integrationen → Menü oben rechts → **Benutzerdefinierte Repositories**
2. `https://github.com/kulmi84/FRITZsync-ha` als Kategorie *Integration*
   hinzufügen
3. „FRITZ!Sync - Homeassistant" installieren
4. Home Assistant neu starten

### Manuell

Den Ordner `custom_components/fritzsync_network` in das `config`-Verzeichnis von Home
Assistant kopieren und neu starten.

---

## Einrichtung

Einstellungen → Geräte & Dienste → **Integration hinzufügen** → „FRITZ!Sync - Homeassistant".

| Feld | Bedeutung |
| --- | --- |
| Adresse | Hostname oder IP-Adresse, üblicherweise `fritz.box` |
| Benutzername | FRITZ!Box-Benutzer mit der Berechtigung „FRITZ!Box Einstellungen" |
| Kennwort | Das zugehörige Kennwort |
| Verschlüsselt verbinden | HTTPS statt HTTP zur FRITZ!Box |

Die Zugangsdaten werden beim Anlegen sofort geprüft: erreichbar, Anmeldung gültig und
Hosts-Dienst nutzbar. Schlägt eines davon fehl, nennt der Dialog die konkrete Ursache,
statt später still keine Daten zu liefern.

---

## Einstellungen

Über *Konfigurieren* an der eingerichteten Integration:

| Einstellung | Standard | Bedeutung |
| --- | --- | --- |
| Abfrageintervall | 60 s | Wie oft die Geräteliste geholt wird (15–3600 s) |
| IP-Typ erfassen | an | Ob DHCP/statisch ermittelt wird |
| Intervall der IP-Typ-Abfrage | 15 min | Takt der IP-Typ-Erfassung |
| Pi-hole synchronisieren | aus | Lokale DNS-Einträge anzeigen und Schreibaktionen aktivieren |
| Pi-hole-Adresse | z. B. `http://pi.hole` | Adresse einer Pi-hole-6-Installation |
| Pi-hole-Kennwort | – | Nur serverseitig im Home-Assistant-Konfigurationseintrag gespeichert |
| Lokale DNS-Domain | `fritz.box` | Domain für automatisch erzeugte Gerätenamen |

**Warum zwei Intervalle?** Die komplette Geräteliste kommt mit einem einzigen Aufruf von
der FRITZ!Box. Die Angabe, ob eine IP-Adresse fest zugewiesen ist, steht dort aber nicht
drin – AVM liefert sie nur einzeln je Gerät. Bei 60 Geräten wären das 60 zusätzliche
Aufrufe pro Durchlauf. Da sich dieser Wert praktisch nie ändert, läuft er in einem
eigenen, langsamen Takt. Wer die Spalte nicht braucht, schaltet die Erfassung ab und
spart die Aufrufe vollständig.

---

## Sensoren

| Sensor | Zustand | Zweck |
| --- | --- | --- |
| `sensor.<name>_gerate` | Anzahl verbundener Geräte | Trägt die komplette Geräteliste im Attribut `hosts`; Datenquelle der Karte |
| `sensor.<name>_gerate_mit_update` | Anzahl | Automatisierung „neue Firmware verfügbar" |
| `sensor.<name>_gesperrte_gerate` | Anzahl | Überwachung der Kindersicherung |

Das Attribut `hosts` ist per `_unrecorded_attributes` vom Recorder ausgenommen. Ohne das
schriebe Home Assistant die vollständige Geräteliste bei jeder Änderung in die Datenbank –
bei 60 Geräten rund 15–20 kB pro Eintrag.

Weitere Attribute am Hauptsensor: `gesamt`, `aktiv`, `inaktiv`, `gastnetz`, `gesperrt`,
`updates_verfuegbar`, `statische_ip`, `letzte_abfrage`, `letzte_ip_typ_abfrage`,
`pihole_manuelle_eintraege` und `pihole_fehler`.

---

## Dashboard-Karte

Karte hinzufügen → **FRITZ!Sync - Homeassistant** → Sensor auswählen. Alles Weitere lässt sich im
grafischen Editor einstellen.

### Spalten

| Spalte | Standard | Quelle |
| --- | --- | --- |
| Status | an | `Active` – farbiger Punkt |
| FRITZ!Box-Name | an | Name aus der FRITZ!Box, samt Abzeichen für Gast, VPN und Priorität |
| Netz | an | Kompakt als `LAN`, `WLAN`, `Gast LAN` oder `Gast WLAN`; Subnetze stehen als Filterchips bereit |
| IP-Adresse | an | `IPAddress` |
| MAC-Adresse | an | `MACAddress` |
| PTR 1 | an | Erste PTR-Antwort des DNS-Servers der FRITZ!Box |
| PTR 2 | aus | Zweite PTR-Antwort, sofern vorhanden |
| Kommentar | an | Lokal in Home Assistant gespeicherter, MAC-basierter Kommentar |
| Verbindung | an | `InterfaceType` + Portnummer, z. B. „LAN 2" oder „WLAN (Gast)" |
| Home Assistant | an | Gerätename aus der Geräteregistrierung |
| IP-Typ | an | DHCP oder statisch, mit Lease-Restzeit |
| Internet | an | Internetzugang gesperrt (Kindersicherung) |
| Update | an | Firmware-Update für das Gerät verfügbar |
| Tempo | an | `X_AVM-DE_Speed` in Mbit/s bzw. Gbit/s |
| Modell | aus | Nur AVM-Geräte melden hier etwas |
| Gerätetyp | aus | Automatisch erkannte bzw. vom Nutzer gesetzte Geräteklasse |

Passen auf einer schmalen Karte – etwa in einer schmalen Dashboard-Spalte oder auf dem
Telefon – nicht alle Spalten nebeneinander, wird die Tabelle waagerecht scrollbar. So
bleiben auch die hinteren Spalten wie *Home Assistant* erreichbar. Näheres unter
[Wischen und Blättern auf dem Smartphone](#wischen-und-blättern-auf-dem-smartphone).

### Sortieren, filtern, suchen

Klick oder Enter auf eine Spaltenüberschrift sortiert nach dieser Spalte, ein zweiter Klick
dreht die Richtung. IP-Adressen werden dabei numerisch sortiert, `192.168.178.9` steht also
korrekt vor `192.168.178.10`. Startsortierung und -richtung lassen sich im Editor
festlegen.

Suchfeld und Filterleiste arbeiten zusammen: „Aktiv" plus Suchbegriff zeigt nur verbundene
Geräte, auf die der Begriff passt. Beide Bedienelemente behalten ihren Inhalt, wenn der
Sensor im Hintergrund neue Daten liefert.

Die Filterchips lassen sich im Karteneditor einzeln ein- oder ausblenden. Statusfilter
und Netzfilter sind kombinierbar, beispielsweise `Aktiv` zusammen mit dem Gastnetz.
Neue Geräte besitzen einen eigenen Filter und bleiben markiert, bis sie bestätigt wurden.

Spalten werden im Editor per Ziehen oder mit Hoch-/Runter-Schaltflächen angeordnet.
Die Breite lässt sich direkt am rechten Rand eines Tabellenkopfs ziehen; ein Doppelklick
setzt sie zurück. Die Breiten werden je Karte im Browser gespeichert.

### Pi-hole-DNS-Einträge

Ist die Pi-hole-Synchronisierung aktiviert, werden ausschließlich eigene lokale
Pi-hole-DNS-Einträge direkt zwischen die FRITZ!Box-Geräte einsortiert. Damit greift die
normale IP-Sortierung über beide Datenquellen hinweg. DNS-Namen stehen unter
`FRITZ!Box-Name`, Adressen unter `IP-Adresse`; in der Spalte `Netz` steht `manuell`.
Automatisch synchronisierte Pi-hole-Duplikate erscheinen nicht zusätzlich. Der Filter
`Manuell` zeigt auf Wunsch nur diese DNS-Zeilen. Ein Klick auf eine solche Zeile blendet
die Eingabefelder und Aktionen ein; bei einem API-Fehler bleibt sie geöffnet.

Der Button **„Alle Geräte an Pi-hole übertragen“** legt auch für bereits bekannte und
derzeit nicht verbundene FRITZ!Box-Geräte mit gespeicherter IP-Adresse einen lokalen
DNS-Eintrag an beziehungsweise aktualisiert dessen bisherige Zuordnung. Vor dem
Gesamtabgleich wird eine Bestätigung verlangt.

Eine Zeile besteht aus einer gültigen IPv4- oder IPv6-Adresse und mindestens einem
vollständigen DNS-Namen. Mehrere Aliasnamen werden durch Leerzeichen getrennt. Vor jedem
Schreib- oder Löschvorgang zeigt die Karte eine Bestätigung. Die Zugangsdaten bleiben im
Home-Assistant-Konfigurationseintrag und werden niemals an den Browser übertragen.

### Wischen und Blättern auf dem Smartphone

Passen nicht alle Spalten nebeneinander, wird die Tabelle waagerecht scrollbar. Auf dem
Telefon lässt sich einfach mit dem Finger nach links und rechts wischen, um die hinteren
Spalten (MAC-Adresse, Home Assistant, IP-Typ, Tempo …) einzusehen. Zusätzlich erscheinen
am linken und rechten Rand **Pfeile**, die sich auch anklicken lassen – jeder Klick blättert
etwa eine halbe Kartenbreite weiter. Die Pfeile erscheinen nur, wenn in ihre Richtung noch
etwas verborgen ist.

Statuspunkt und Gerätename bleiben beim Blättern links stehen, damit immer klar ist, zu
welchem Gerät die Werte gehören. Beides ist im Editor abschaltbar: *Blätter-Pfeile bei
breiter Tabelle* und *Gerätename beim Blättern festhalten*.

### IP-Adresse öffnet die Weboberfläche

Ein Klick auf die IP-Adresse öffnet die Weboberfläche des Geräts in einem neuen
Browser-Tab. Bevorzugt wird die Adresse, die die FRITZ!Box selbst zum Gerät meldet;
ist keine hinterlegt, wird `http://<IP>` versucht (abschaltbar über *Notfalls http://IP
verwenden*). Aus Sicherheitsgründen werden ausschließlich `http`- und `https`-Adressen
geöffnet. Der Klick auf die IP öffnet nicht zusätzlich das Detail-Popup; das steht über den
Rest der Zeile weiter zur Verfügung. Im Popup selbst gibt es dafür den Knopf *Weboberfläche
öffnen*.

Geräte ohne eigene Weboberfläche (viele IoT-Geräte, Sensoren) beantworten `http://<IP>`
nicht – dann zeigt der Browser einen Fehler. Wer das vermeiden möchte, schaltet den
Fallback ab; dann sind nur Geräte verlinkt, für die die FRITZ!Box tatsächlich eine Adresse
meldet.

### Excel-Export

**Excel-Export** erzeugt eine echte `.xlsx`-Arbeitsmappe. Exportiert werden genau die
aktuell angezeigten Zeilen nach Filter, Suche, Sortierung und Zeilenlimit. Ebenso werden
nur die in der aktuellen Kartenansicht tatsächlich sichtbaren Spalten in ihrer gewählten
Reihenfolge übernommen. Die Kopfzeile bleibt fixiert und die manuell gesetzten
Spaltenbreiten fließen in die Arbeitsmappe ein.

Alle Zellen werden als Text geschrieben. Dadurch interpretiert Excel Gerätenamen, die mit
`=`, `+`, `-` oder `@` beginnen, nicht als Formeln. Die Datei wird vollständig lokal im
Browser erzeugt; es werden keine Netzwerkdaten an einen externen Exportdienst übertragen.

### Detail-Popup

Ein Klick oder Enter auf eine Zeile öffnet ein Popup mit **allen** Angaben zum Gerät – auch
den Feldern, die auf einer schmalen Karte gerade aus dem sichtbaren Bereich gescrollt sind.
IP- und MAC-Adresse lassen sich dort mit einem Knopf in die Zwischenablage kopieren.

Je nach Gerät bietet das Popup zusätzlich:

- **In Home Assistant öffnen** – springt zur Geräteseite, sofern das Gerät in Home
  Assistant über seine MAC-Adresse bekannt ist
- **Aufwecken (WoL)** – sendet ein Wake-on-LAN-Signal, wird nur bei nicht verbundenen
  Geräten angezeigt

Das Popup ist der Standard. Wer stattdessen wie bisher direkt zur Home-Assistant-Geräteseite
springen möchte, schaltet im Editor *Klick öffnet ein Detail-Popup* ab; dann greift wieder
*Klick öffnet das Home-Assistant-Gerät*.

### Farben

Alle zwölf Farben lassen sich im Abschnitt *Farben* des Editors setzen – wahlweise per
Texteingabe (Hex, `rgb()`, `hsl()`, CSS-Farbname oder `var(--…)`) oder über die grafische
Farbauswahl. Zu jeder Farbe zeigt der Editor, welcher Wert aktuell greift. Ein Klick auf
*Alle Farben zurücksetzen* leert alle zwölf Werte in einem Zug.

Leer bedeutet: die Karte folgt dem aktiven Theme. Gesetzte Farben sind normale
Lovelace-Kartenkonfiguration und werden von Home Assistants eigener Dashboard-Speicherung
verwaltet – diese Integration hat dafür keinen eigenen Speicher.

### Beispiel-YAML

```yaml
type: custom:fritzsync-network-card
entity: sensor.fritz_box_5690_pro_netzwerk_gerate
title: Heimnetz

# Spalten
show_status: true
show_name: true
show_ip: true
show_mac: true
show_connection: true
show_ha_name: true
show_ip_type: true
show_wan: true
show_update: true
show_speed: true
show_model: false
show_type: false

# Darstellung
show_summary: true
show_search: true
show_filter: true
hide_inactive: false
compact: false
show_details_popup: true
open_device_on_click: true
show_scroll_arrows: true
sticky_name: true
ip_opens_web: true
ip_web_fallback: true
max_rows: 0

# Sortierung
sort_by: ip
sort_dir: asc

# Farben (leer = Theme)
color_active: "#43a047"
color_blocked: "#db4437"
```

---

## Dienste

### `fritzsync_network.set_device_name`

Benennt ein Netzwerkgerät in der FRITZ!Box um.

```yaml
action: fritzsync_network.set_device_name
data:
  mac: "3C:A6:F6:00:11:22"
  name: "Drucker Arbeitszimmer"
```

### `fritzsync_network.wake_on_lan`

Sendet ein Wake-on-LAN-Signal.

```yaml
action: fritzsync_network.wake_on_lan
data:
  mac: "3C:A6:F6:00:11:22"
```

### Weitere Dienste

| Dienst | Funktion |
| --- | --- |
| `fritzsync_network.set_device_comment` | MAC-basierten Kommentar speichern oder entfernen |
| `fritzsync_network.acknowledge_device` | Ein neues Gerät dauerhaft als bekannt bestätigen |
| `fritzsync_network.pihole_add_record` | Manuellen lokalen DNS-Eintrag anlegen |
| `fritzsync_network.pihole_update_record` | Vorhandenen manuellen DNS-Eintrag ersetzen |
| `fritzsync_network.pihole_delete_record` | Manuellen DNS-Eintrag löschen |
| `fritzsync_network.pihole_sync_all` | Geeignete FRITZ!Box-Geräte mit Pi-hole abgleichen |
| `fritzsync_network.refresh` | Geräteliste, PTR 1/2 und IP-Typ sofort vollständig aktualisieren |

Alle schreibenden Aktionen der Dashboard-Karte verlangen vorher eine Bestätigung.

---

## Fehlerbehebung

**Die Einrichtung meldet „Das Konto hat keinen Zugriff auf die FRITZ!Box-Einstellungen".**
In der FRITZ!Box unter System → FRITZ!Box-Benutzer beim verwendeten Konto die Berechtigung
*FRITZ!Box Einstellungen* setzen. Ein reiner Benutzer ohne diese Berechtigung kann die
Geräteliste nicht abrufen.

**Die Einrichtung meldet, der Dienst „Hosts" fehle.**
Unter Heimnetz → Netzwerk → Netzwerkeinstellungen die Option *Zugriff für Anwendungen
zulassen* aktivieren. Ohne sie ist die TR-064-Schnittstelle komplett abgeschaltet.

**Die Spalte „IP-Typ" zeigt überall nur „—".**
Entweder ist die IP-Typ-Erfassung in den Einstellungen der Integration ausgeschaltet, oder
sie ist seit dem Start noch nicht gelaufen. Die Karte zeigt bewusst „—" statt „DHCP"
anzunehmen – die Geräteliste selbst enthält diese Angabe nicht.

**Die Spalte „Home Assistant" bleibt leer.**
Zugeordnet wird ausschließlich über die MAC-Adresse in der Geräteregistrierung. Viele
Integrationen hinterlegen dort keine MAC. Prüfbar unter Einstellungen → Geräte & Dienste →
Gerät: steht dort keine MAC-Adresse, kann keine Zuordnung stattfinden.

**Die Karte erscheint nicht oder zeigt „Custom element doesn't exist".**
Läuft das Dashboard im YAML-Modus, kann die Integration die Ressource nicht selbst
eintragen; das Protokoll nennt dann die einzutragende URL. Andernfalls hilft ein harter
Neuladen des Browsers, in der Companion App das Leeren des App-Zwischenspeichers.

---

## Bekannte Einschränkungen

- **Statische IP-Adressen lassen sich nicht ändern.** Die TR-064-Schnittstelle von AVM
  kennt dafür keine Aktion. Schreibbar sind dort nur Gerätename, Anzeigename,
  Wake-on-LAN, Echtzeitpriorität und Geräteklasse. Ein Setzen der IP-Adresse wäre nur über
  die Weboberfläche der FRITZ!Box möglich – undokumentiert und bei jedem FRITZ!OS-Update
  potenziell defekt. Das ist bewusst nicht Teil dieser Version.
- **Kein Mesh.** WLAN-Band, Signalstärke und der Repeater, an dem ein Gerät hängt, stehen
  in einer eigenen Schnittstelle (`X_AVM-DE_GetMeshListPath`) und sind noch nicht
  ausgewertet.
- **Nur eine FRITZ!Box je Dienstaufruf.** Sind mehrere Boxen eingerichtet, wirken
  `set_device_name` und `wake_on_lan` auf die zuerst geladene.
- Die Zuordnung zu Home-Assistant-Geräten erfolgt ausschließlich über die MAC-Adresse.
  Es wird bewusst nicht über Namensähnlichkeit geraten.

---

## Entwicklung und Tests

Die reine Datenaufbereitung in `hosts.py`, `fritzbox_web.py` und `pihole.py` lässt
sich ohne laufende Home-Assistant-Instanz testen:

```bash
python -m unittest discover -s tests -v
node --check custom_components/fritzsync_network/www/fritzsync-network-card.js
python -m compileall -q custom_components/fritzsync_network
```

Der aktuelle Stand umfasst Tests für Hostnormalisierung, WebUI-/TR-064-Zusammenführung,
private Router-IP-Auswahl, Pi-hole-v6-DNS-Einträge und Sitzungsfreigabe. Der XLSX-Export
wird zusätzlich gegen ZIP-Integrität sowie mit OpenPyXL und LibreOffice geprüft.

---

## Versionshistorie

Alle Änderungen einschließlich Fehlerkorrekturen stehen im [Changelog](CHANGELOG.md).
Die aktuell installierte Version wird in HACS und in den Geräteinformationen der
Integration angezeigt.

---

## Lizenz

MIT
