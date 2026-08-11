# Changelog

## 1.0.0

Erster finaler Stable-Release.

- Zentrale Versionsquelle über `plugin.cfg`
- Version nur noch im oberen VELUX-Balken
- UDP-Ausgabe korrigiert: kein zusätzliches `=` mehr
- VELUX ACTIVE Automatisierung über `mode=algo_available`
- Loxone UDP-Befehl `velux.cmd.velux_active.automation=1`
- UDP-Listener wird bei Updates sauber beendet und neu gestartet
- UDP-Sendeeinstellungen und UDP-Auswahl bleiben bei Updates erhalten
- Zusätzliche Sicherung der `config.json`
- Plugin Aktiv/Inaktiv
- Gateway-Kopplung für signierte Steuerbefehle
- Stabiler Scheduler
- Logging und Diagnose verbessert
