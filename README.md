# FritzSync Network

Eigenständige Home-Assistant-Custom-Integration für eine interaktive FRITZ!Box-
Netzwerktopologie. Geräte werden soweit möglich ihren echten Mesh-Knoten zugeordnet;
falls die FRITZ!Box keinen Pfad liefert, greift die Karte auf LAN, WLAN oder Gastnetz
zurück.

## Funktionen

- lokale Abfrage über die offizielle TR-064-Schnittstelle
- grafische Topologie mit Suche und Filtern
- Detailansicht mit IP, MAC, Verbindung, Modell, Tempo und Internetstatus
- Gerätename direkt in der FRITZ!Box ändern
- Internetzugang eines Geräts sperren oder freigeben
- Wake-on-LAN-Paket senden
- Bestätigungsdialog vor jeder schreibenden Aktion
- vollständige Einrichtung über die Home-Assistant-Oberfläche

## Voraussetzungen

- Home Assistant 2025.1 oder neuer
- FRITZ!Box mit aktiviertem **Zugriff für Anwendungen (TR-064)**
- FRITZ!Box-Benutzer mit dem Recht **FRITZ!Box Einstellungen**

## Installation über HACS

1. Dieses Repository in HACS als benutzerdefiniertes Repository der Kategorie
   **Integration** hinzufügen.
2. **FritzSync Network** installieren.
3. Home Assistant neu starten.
4. Unter **Einstellungen → Geräte & Dienste → Integration hinzufügen** nach
   `FritzSync Network` suchen.
5. Anschließend im Dashboard die Karte `FritzSync Network Topology` hinzufügen.

## Dashboard-YAML

```yaml
type: custom:fritzsync-network-card
entity: sensor.fritz_box_fritzsync_network
title: Mein Netzwerk
show_offline: true
```

Die Karte wird beim Laden der Integration automatisch als Lovelace-Ressource
registriert.

## Aktionen und Grenzen

- **Umbenennen** nutzt `X_AVM-DE_SetHostNameByMACAddress`.
- **Sperren/Freigeben** nutzt `DisallowWANAccessByIP` des offiziellen
  `X_AVM-DE_HostFilter1`-Dienstes. Ein Gerät benötigt dafür eine IPv4-Adresse.
- **Wake-on-LAN** wird von Home Assistant als lokales Magic Packet gesendet.
- FRITZ!OS- und Powerline-Geräte dürfen laut FRITZ!-Schnittstelle nicht gesperrt
  werden. Die Integration gibt die Fehlermeldung der FRITZ!Box verständlich weiter.
- Mesh-Daten sind modell- und FRITZ!OS-abhängig. Fehlen sie, bleibt die Ansicht
  vollständig nutzbar und gruppiert nach Verbindungstyp.

## Entwicklung

```bash
python -m unittest discover -s tests
```

## Lizenz

MIT
