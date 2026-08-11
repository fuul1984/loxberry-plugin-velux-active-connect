# VELUX Active Connect

VELUX Active Connect verbindet VELUX ACTIVE / App Control mit LoxBerry und Loxone.

## Version

Aktueller stabiler Stand: **1.0.0**

## Funktionen

- VELUX ACTIVE Cloud-Anbindung
- Homes, Räume und Geräte automatisch erkennen
- Temperatur, Feuchtigkeit, CO₂, Helligkeit und weitere Werte
- Regenstatus, sofern von VELUX gemeldet
- Frei wählbare UDP-Rückmeldungen für Loxone
- Alle Werte oder nur Änderungen senden
- Heartbeat
- Fenstersteuerung: AUF, STOP, ZU und Position
- Gateway-Kopplung für signierte Steuerbefehle
- VELUX ACTIVE Automatisierung wieder aktivieren
- Plugin Aktiv/Inaktiv auf der Statusseite
- Konfigurierbarer Scheduler
- Update-sichere Einstellungen und UDP-Auswahl
- GitHub AutoUpdate
- Logging und Diagnose

## Loxone UDP-Steuerung

```text
velux.cmd.dachfenster_bad.open=1
velux.cmd.dachfenster_bad.stop=1
velux.cmd.dachfenster_bad.close=1
velux.cmd.dachfenster_bad.position=50
velux.cmd.velux_active.automation=1
```

Die Automatisierung wird über `mode=algo_available` wieder freigegeben.

UDP-Rückmeldungen werden sauber als `key=value` übertragen, z. B.:

```text
velux.module.velux_gateway.reachable=1
```

Die Plugin-Version wird zentral aus `plugin.cfg` gelesen.
