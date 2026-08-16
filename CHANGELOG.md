# Changelog

## 1.9.1

- belegte Pi-hole-API-Sitzungen nach jedem Zugriff korrekt abmelden
- nur manuelle Pi-hole-DNS-Zeilen direkt nach IP in die Geräteliste einsortieren
- zusätzlichen Filter `Manuell` ergänzen
- Bearbeitungsmodus bei API-Fehlern geöffnet lassen
- automatisch synchronisierte Pi-hole-Duplikate nicht mehr separat anzeigen

## 1.9.0

- alle Pi-hole-Einträge dauerhaft innerhalb der Haupttabelle anzeigen
- DNS-Name und IP exakt unter den entsprechenden FRITZ!Box-Spalten ausrichten
- Pi-hole-Zeilen kompakter darstellen
- manuelle Einträge in der Spalte `Netz` als `manuell` kennzeichnen
- alle vorhandenen FRITZ!Box-Geräte per bestätigtem Gesamtabgleich an Pi-hole übertragen

## 1.8.1

- Pi-hole-Adressen ohne Protokoll standardmäßig über HTTPS ansprechen
- selbstsignierte Zertifikate lokaler Pi-hole-Installationen unterstützen
- beim Geräte-Umbenennen den lokalen DNS-Eintrag derselben IP überschreiben

## 1.8.0

- manuelle Local-DNS-Einträge aus Pi-hole 6 in Home Assistant anzeigen
- Pi-hole-Einträge mit Bestätigung anlegen, bearbeiten und löschen
- eigener einklappbarer Pi-hole-Bereich im Stil von FRITZSync/Pi-hole Sync
- Pi-hole-Fehler beeinträchtigen die FRITZ!Box-Geräteliste nicht

## 1.7.0

- Anzeige in HACS und Home Assistant in `FRITZ!Sync - Homeassistant` umbenannt
- sichtbaren FRITZ!Box-Gerätenamen über den verifizierten FRITZ!OS-WebUI-Weg ändern
- dauerhafte IPv4-Zuweisung getrennt von `AddressSource=DHCP` erkennen
- optionalen Aktualisieren-Button zur Karte hinzugefügt

## 1.2.0

- `Aktiv` ist der Standardfilter
- zusätzliche Filterchips werden automatisch für jedes erkannte Subnetz erzeugt
- kompakte Netzangabe: `LAN` beziehungsweise `Gast (LAN/WLAN)`
- nach dem ersten Basisabgleich neu erkannte MAC-Adressen werden gelb markiert
- neue Geräte können über das `Neu`-Abzeichen dauerhaft bestätigt werden
- zusätzlicher Filter `Neu`

## 1.1.0

- Spalten `Netz`, `PTR 1`, `PTR 2` und `Kommentar` aus dem separaten FRITZSync-Projekt übernommen
- PTR-Namen werden direkt beim DNS-Server der FRITZ!Box abgefragt
- Kommentare werden MAC-basiert in Home Assistant gespeichert
- FRITZ!Box-Gerätename und Kommentar lassen sich im Detaildialog mit Bestätigung ändern

## 1.0.0

- vollständiger Neuaufbau auf Basis der stabilen Integration `fritzbox_netzwerk`
- automatische Registrierung der Dashboard-Karte als Lovelace-Modulressource
- sortierbare und filterbare Netzwerkgerätetabelle mit grafischem Editor
- Detaildialog, Home-Assistant-Gerätezuordnung und Wake-on-LAN
- Optionen für Abfrageintervall und DHCP-/statische-IP-Erfassung
- Domain, Kartenkennung und Dienste auf FritzSync umgestellt

Die frühere 0.x-Implementierung wurde ersetzt und wird nicht weitergeführt.
