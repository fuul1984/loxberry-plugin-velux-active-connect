# VELUX Active Connect for LoxBerry

VELUX Active Connect verbindet **VELUX ACTIVE / VELUX App Control** mit LoxBerry und Loxone. Das Plugin liest Geräte- und Raumwerte über die VELUX-Cloud, sendet ausgewählte Werte per UDP an Loxone und kann Fenster/Rollläden über Web und Loxone steuern. Für signierte Dachfenster-Positionen unterstützt das Plugin die einmalige lokale Gateway-Kopplung.

## Funktionen

- VELUX Cloud Login mit Token-Refresh
- Homes, Räume und Geräte automatisch erkennen
- Temperatur, Feuchte, CO₂, Helligkeit, Luftqualität und weitere gemeldete Werte
- Regensignal des Gateways, sofern von VELUX gemeldet
- UDP-Ausgabe an einen in LoxBerry konfigurierten Miniserver
- Alle Werte senden oder nur geänderte Werte senden
- Heartbeat an Loxone
- Jede UDP-Message einzeln aktivierbar und umbenennbar
- Steuerung per Web und Loxone UDP: AUF, STOP, ZU, Position 0–100 %
- Gateway-Kopplung für signierte Dachfensterpositionen
- Konfiguration, Token und Kopplung bleiben bei Updates erhalten
- LoxBerry AutoUpdate vorbereitet und aktiviert

## Installation

Die aktuelle Release-ZIP aus **Releases** herunterladen und in LoxBerry unter **Plugin-Verwaltung → Plugin installieren** hochladen.

Nach der Installation unter **Einstellungen** VELUX E-Mail/Passwort, Miniserver, UDP-Sendeport und optional die Loxone-Steuerung konfigurieren.

## Loxone Steuerung

Beispiel für einen virtuellen UDP-Ausgang:

```text
/dev/udp/<LOXBERRY-IP>/7001
```

`Verbindung nach Senden schließen` aktivieren.

```text
velux.cmd.dachfenster_bad.open=1
velux.cmd.dachfenster_bad.stop=1
velux.cmd.dachfenster_bad.close=1
velux.cmd.dachfenster_bad.position=<v>
```

Die konkreten Befehle werden im Plugin bei jedem Aktor unter **Steuerung → Loxone Beispiel anzeigen** dargestellt. IP, Port, Präfix und Geräte-Key kommen aus der aktuellen Konfiguration.

## Gateway-Kopplung

Freie Positionen von Dachfenstern können signierte Befehle benötigen. Unter **Einstellungen → VELUX Gateway Kopplung** kann das Gateway einmalig gekoppelt werden. Der LoxBerry muss das Gateway im lokalen Netz über TCP-Port `25050` erreichen. Die Signierschlüssel werden lokal in der Plugin-Konfiguration gespeichert und bei Updates erhalten.

## Logging

Unter **Log** werden Cloud-Abrufe, gelesene Werte, UDP-Status, empfangene Loxone-Befehle, Steuerungsresultate und Kopplungsfehler angezeigt. Zugangsdaten oder Tokens werden nicht im Klartext protokolliert.

## AutoUpdate

Stable: `https://raw.githubusercontent.com/fuul1984/loxberry-plugin-velux-active-connect/main/release.cfg`  
Prerelease: `https://raw.githubusercontent.com/fuul1984/loxberry-plugin-velux-active-connect/main/prerelease.cfg`

## Entwicklung

Repository: https://github.com/fuul1984/loxberry-plugin-velux-active-connect

### Release erstellen

1. Version in `plugin.cfg`, `release.cfg` und `prerelease.cfg` anpassen.
2. Changelog aktualisieren.
3. Commit und Tag erstellen, z. B. `v0.5.5`.
4. Tag pushen.
5. GitHub Actions prüft das Plugin, baut die LoxBerry-ZIP und legt das GitHub Release an.

## Lizenz / Danksagung

Dieses Projekt steht unter der MIT-Lizenz. Die VELUX-Protokoll- und Signing-Implementierung wurde unter anderem anhand des MIT-lizenzierten Projekts `Niek/ha-velux-active` und des pyatmo-Verhaltens nachvollzogen. Siehe `THIRD_PARTY_NOTICES.md`.
