# Changelog

## 0.9.0

- Release-Kandidat vor 1.0.0
- Zentrale Versionsquelle: `plugin.cfg`; WebUI und User-Agent lesen die Version automatisch
- UDP-Ausgabe korrigiert: LoxBerry `msudp_send()` erhält echte Key/Value-Paare, kein zusätzliches `=` mehr
- VELUX ACTIVE Automatisierung per `velux.cmd.velux_active.automation=1` mit `mode=algo_available`
- UDP-Listener wird bei Updates sauber beendet und mit aktuellem Code neu gestartet
- UDP-Sendeeinstellungen und Wertauswahl bleiben bei Updates erhalten
- Plugin Aktiv/Inaktiv, Gateway-Kopplung, Scheduler und Diagnose aus dem getesteten 0.5.12-Stand übernommen

## 0.5.12
- UDP-Messages-Speicherfehler korrigiert: Speichern der Wertauswahl verändert keine allgemeinen UDP-Einstellungen mehr
- `udp_enabled`, Heartbeat, Auto-New, Miniserver, Ports, Präfix und Sendemodus bleiben beim Speichern der UDP-Auswahl unverändert
- zusätzliche Sicherheitskopie von `config.json` im Upgrade-Pfad
- UDP-Listener-Update korrigiert: laufender Listener wird vor Updates beendet und danach mit neuem Code gestartet
- veraltete `control_listener.pid` wird bei Updates nicht mehr wiederverwendet
- behebt den Fall „Web-Befehl funktioniert, UDP-Befehl verwendet noch alten Code“

- VELUX ACTIVE Automatisierung wieder aktivieren
- Automatik setzt Fenster auf `mode=algo_available`
- `manual` = Automatik aus
- `algo_available` / `algo_active` = Automatik aktiv
- Web-Button „Automatisierung aktivieren“
- Loxone UDP: `velux.cmd.velux_active.automation=1`
- `automation` als gültiger Web-/CLI-Steuerbefehl
- fehlerhafte `scenario=home`-Umsetzung entfernt
- bestehende Fenstersteuerung, Plugin Aktiv/Inaktiv und Scheduler bleiben erhalten
- empfohlenes Abrufintervall: 3 Minuten
