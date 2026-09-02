# VELUX Active Connect

VELUX Active Connect verbindet VELUX ACTIVE / VELUX App Control mit LoxBerry und Loxone. Das Plugin erkennt Homes, Räume und Geräte, überträgt ausgewählte Statuswerte per UDP an Loxone und ermöglicht – abhängig vom Gerät – die Steuerung von Fenstern sowie die Wiederaufnahme der VELUX-Automatik.

## Aktuelle Version

**1.1.0 Stable**  
Minimum LoxBerry: **4.0.0**

## Funktionen

- VELUX ACTIVE Cloud-Anbindung
- Automatische Home-, Raum- und Geräteerkennung
- Gateway-Kopplung für signierte Steuerbefehle
- Token-Erneuerung über Refresh-Token mit nachvollziehbarem Login-Fallback
- Temperatur, Feuchtigkeit, CO₂, Helligkeit, Luftqualität und weitere von VELUX gemeldete Werte
- Regenstatus, sofern von VELUX bereitgestellt
- Frei wählbare UDP-Rückmeldungen für Loxone
- Wahlweise alle Werte oder nur Änderungen senden
- Boolean-Werte konsistent als `1/0`
- Heartbeat
- UDP-Steuerung Loxone → VELUX mit Prüfung erlaubter Absender
- Fenstersteuerung: AUF, STOP, ZU und Position, sofern unterstützt
- Wiederaufnahme der VELUX ACTIVE Automatik
- Plugin Aktiv/Inaktiv
- Scheduler → Worker mit Lock gegen parallele API-Läufe
- Dauerhafter UDP-Listener mit Watchdog/Restart
- Update-sichere Konfiguration, UDP-Auswahl und Gateway-Daten
- Zentrale Versionsanzeige aus `plugin.cfg`
- Loxone-Export mit konfiguriertem Präfix und individuellen UDP-Namen
- Lesbare, kontrastreiche Weboberfläche in allen Button-/Navigationszuständen
- GitHub AutoUpdate
- Logging und Diagnose

## Architektur

Periodische Abfragen laufen über:

```text
cron.01min -> Scheduler -> Intervallprüfung -> Worker -> VELUX API -> UDP an Loxone
```

Steuerbefehle laufen über:

```text
Loxone -> UDP -> Listener/Daemon -> Validierung/Absenderprüfung -> VELUX API
```

Die CGI-Seiten dienen ausschließlich der Oberfläche und interaktiven Aktionen; periodische Hintergrundlogik läuft nicht im CGI.

## Loxone UDP-Steuerung

```text
velux.cmd.dachfenster_bad.open=1
velux.cmd.dachfenster_bad.stop=1
velux.cmd.dachfenster_bad.close=1
velux.cmd.dachfenster_bad.position=50
velux.cmd.velux_active.automation=1
```

Die Automatisierung wird über `mode=algo_available` wieder freigegeben. Zustände wie `algo_active`, `algo_available` und `manual` werden als Textstatus behandelt und können in Loxone entsprechend ausgewertet werden.

UDP-Rückmeldungen werden als `key=value` übertragen, zum Beispiel:

```text
velux.module.velux_gateway.reachable=1
velux.room.bad.temperature=23.7
```

## Installation

Die Release-Datei `VELUX_Active_Connect_v1.1.0.zip` über die LoxBerry-Pluginverwaltung installieren. Danach VELUX-Zugangsdaten und Loxone-Miniserver konfigurieren, Daten abrufen, gewünschte UDP-Werte auswählen und – falls für Steuerbefehle erforderlich – das Gateway koppeln.

## Dokumentation

Die vollständige LoxWiki-/DokuWiki-Seite liegt unter:

```text
wiki/velux_active_connect.txt
```

## AutoUpdate

Stable und Pre-Release-Konfiguration zeigen für diesen offiziellen Stand auf GitHub Release `v1.1.0`.

## Repository

https://github.com/fuul1984/loxberry-plugin-velux-active-connect

## Lizenz / Community

Community-Projekt für LoxBerry. VELUX und Netatmo sind Marken ihrer jeweiligen Rechteinhaber. Dieses Projekt ist nicht mit VELUX oder Netatmo verbunden.
