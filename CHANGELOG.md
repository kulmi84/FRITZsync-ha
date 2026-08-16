# Changelog

## 1.10.11

- Fußleisten-Schaltfläche `Schließen` bereits beim Drücken ausführen, bevor ein Sensorupdate sie ersetzen kann
- erfolgreich gelöschte Pi-hole-DNS-Zeilen sofort aus der Kartenansicht ausblenden
- optimistische Ausblendung automatisch aufheben, sobald der neue Pi-hole-Sensorstand eingetroffen ist

## 1.10.10

- nativen Fortschritts-Mauszeiger während Pi-hole-Speichern, Löschen und Gesamtabgleich anzeigen
- Symbol der laufenden Schaltfläche bis zum abgeschlossenen Coordinator-Abgleich drehen
- anonymisierte Screenshot-Galerie in die GitHub-Dokumentation aufnehmen

## 1.10.9

- Tabellenkörper nach erfolgreichem Pi-hole-Speichern oder -Löschen bewusst neu aufbauen
- Fokus-Schutz nur bei laufender Eingabe anwenden, nicht nach abgeschlossener Aktion
- neuen DNS-Entwurf auch beim Abbrechen sofort aus der Tabelle entfernen

## 1.10.8

- aktives DNS-Eingabefeld auch durch verschachtelte Home-Assistant-Shadow-Roots erkennen
- Tabellenzeile während der Texteingabe nicht mehr durch Sensoraktualisierungen neu aufbauen
- dadurch verhindern, dass Home Assistants globale Suche nach dem ersten Buchstaben übernimmt

## 1.10.7

- bearbeitete Pi-hole-Zeile nicht länger selbst fokussierbar machen
- laufende DNS-Eingaben im Kartenstatus puffern und bei Sensoraktualisierungen wiederherstellen
- Namensfeld nach einem unvermeidbaren Neuaufbau erneut fokussieren und Cursor ans Textende setzen

## 1.10.6

- Fokus nach dem Öffnen einer manuellen Pi-hole-DNS-Zeile zuverlässig im Namensfeld halten
- globale Home-Assistant-Tastenkürzel während der DNS-Eingabe unterdrücken
- DNS-Eintrag mit Enter speichern und mit Escape abbrechen, ohne aus der Zeile zu springen

## 1.10.5

- Zeilenumbruch in der Spalte `Verbindung` wieder zulassen, damit sie schmal eingestellt werden kann
- Geschwindigkeitswerte weiterhin einzeilig darstellen

## 1.10.4

- gespeicherte Pixelbreiten proportional auf die verfügbare Kartenbreite einpassen
- beim Ziehen einer Spaltengrenze die Nachbarspalte gegensinnig verändern
- Gesamtbreite der Tabelle konstant halten und horizontalen Scrollbalken entfernen

## 1.10.3

- Tabelle standardmäßig auf die verfügbare Kartenbreite einpassen
- erst dann horizontal scrollen, wenn manuell gesetzte Spaltenbreiten zusammen wirklich breiter als die Karte sind
- Spaltenbreiten zentral über ein `colgroup` statt widersprüchlich an jeder einzelnen Zelle setzen
- Überlappen langer PTR-, Namens- oder Kommentarwerte mit Nachbarspalten verhindern

## 1.10.2

- XLSX-Paket mit gültigem ZIP-Datum und vollständiger Arbeitsblatt-Dimension erzeugen
- nicht benötigten Excel-Autofilter entfernen, da bereits exakt die aktuelle Kartenansicht exportiert wird
- beim Export nur die in der gerenderten Kartenansicht tatsächlich sichtbaren Felder übernehmen
- Spaltenbreiten mit größeren sichtbaren Ziehgriffen und globalen Pointer-Events zuverlässig ändern
- manuelle Spaltenbreiten weiterhin pro Karte im Browser speichern
- den Entwurf eines neuen Pi-hole-DNS-Eintrags auch bei Sensoraktualisierungen geöffnet halten
- vor der DNS-Neuanlage verständlich auf notwendige Namens- und IP-Spalten hinweisen
- beim Aktualisieren-Button PTR 1/2 und IP-Typ unabhängig vom langsamen Intervall neu abfragen
- PTR 1/2 nach einer Geräteumbenennung sofort neu ermitteln
- bei Router-Datensätzen die private LAN-Adresse gegenüber einer verschachtelten öffentlichen WAN-Adresse bevorzugen
- dadurch irrtümliche Netzfilter wie `Gast: 185.22.44.0/24` verhindern

## 1.10.1

- wie in FRITZSync 7.9.3/7.9.4 die WebUI-`netDev`-Liste als Masterquelle für MAC, IPv4 und sichtbaren Namen verwenden
- TR-064 nur noch für Zusatzfelder derselben exakten MAC-Adresse verwenden
- historische und provisorische `PC-<MAC>`-Einträge ohne IPv4 nicht mehr anzeigen oder mit Einzelabfragen weiterverarbeiten
- bei nicht verfügbarer WebUI sicher auf TR-064 zurückfallen und auch dort inaktive `PC-<MAC>`-Karteileichen herausfiltern

## 1.10.0

- Spaltenbreiten direkt am Tabellenkopf per Ziehen verändern und browserbezogen speichern
- Spaltenbreite per Doppelklick auf den Ziehgriff zurücksetzen
- Excel-Reparaturmeldung durch Entfernen des fehlerhaften OOXML-Tabellenparts beheben
- beim Excel-Export ausschließlich sichtbare Spalten in ihrer aktuellen Reihenfolge exportieren
- beim Excel-Export ausschließlich aktuell gefilterte und gesuchte Zeilen exportieren
- `DNS-Eintrag` als sofort sichtbare Eingabezeile am Tabellenanfang öffnen
- DNS-Entwurf mit Enter speichern, Escape abbrechen und unvollständige Eingaben verständlich melden

## 1.9.4

- manuelle Pi-hole-Einträge anhand ihrer IPv4-Adresse einem erkannten CIDR-Netz zuordnen
- Pi-hole-Einträge in den Filtern `Heimnetz` und `Gast` mit anzeigen
- sichtbare Netzkennzeichnung der manuellen Einträge weiterhin als `manuell` belassen
- Verbindung und Geschwindigkeit ohne Zeilenumbruch darstellen
- redundantes `Gast`-Abzeichen hinter dem Gerätenamen entfernen

## 1.9.3

- manuelle Pi-hole-Zeilen mit blauem Statuspunkt und Pi-hole-Symbol anzeigen
- Pi-hole-Zellen mit denselben Spaltenklassen, Abständen und Sticky-Regeln wie Gerätezeilen ausrichten
- Symbol und Ausrichtung auch während der Bearbeitung beibehalten
- Schaltfläche `Dubletten bereinigen` aus der Karten-Werkzeugleiste entfernen

## 1.9.2

- fehlerhafte Mehrfacheinträge derselben IP zuverlässig erkennen
- aktive Geräte und echte Gerätenamen gegenüber inaktiven `PC-IP`-Platzhaltern bevorzugen
- veraltete FRITZ!Box-Einträge mit Vorschau, erneuter Sicherheitsprüfung und Bestätigung löschen
- erkannte Dubletten vom Pi-hole-Gesamtabgleich ausschließen

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
