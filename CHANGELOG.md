# Changelog

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
