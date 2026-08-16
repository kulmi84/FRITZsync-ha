# Changelog

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
