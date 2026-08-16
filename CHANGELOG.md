# Changelog

## 0.1.3

- Dashboard-Karte kann von Home Assistant mehrfach konfiguriert werden
- verhindert den Lovelace-Fehler beim erneuten Aufruf von `setConfig()`

## 0.1.2

- TLS- und FRITZ!Box-Client außerhalb des Home-Assistant-Event-Loops initialisieren
- kompatibel mit der Blocking-Call-Erkennung aktueller Home-Assistant-Versionen

## 0.1.1

- FRITZ!Box-Benutzer korrekt an `fritzconnection` übergeben
- verhindert den unspezifischen Fehler beim Einrichten der Integration

## 0.1.0

- erste eigenständige Version
- Mesh-Topologie mit Fallback nach Verbindungstyp
- Gerätenamen direkt in der FRITZ!Box ändern
- Internetzugang sperren und freigeben
- Wake-on-LAN
- Bestätigung vor allen schreibenden Aktionen
