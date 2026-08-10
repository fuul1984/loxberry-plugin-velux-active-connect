# VELUX Active Connect v0.5.5

Basis ist unverändert v0.5.4.

Einzige funktionale Änderung:
- Auf der Statusseite wird die Gateway-Kopplung kompakt im gleichen Stil wie der Verbindungsstatus angezeigt:
  - Status: Verbunden
  - Gateway Kopplung: Gekoppelt

Alle Einstellungen, UDP Messages, Gateway-Kopplung, Steuerung und Diagnose bleiben wie in v0.5.4.


## v0.5.6

- Scheduler-Intervall korrigiert
- Intervall wird ab Start des letzten Abrufs berechnet, nicht ab dessen Ende
- verhindert zusätzliche Verzögerung durch Abrufdauer + 1-Minuten-Cron
- Status zeigt Abrufintervall und nächsten geplanten Lauf
- Scheduler schreibt Start und nächsten Lauf ins Log


## v0.5.7

- Scheduler-Aufruf über eigenen `bin/cronjob.sh`
- LoxBerry `cron.01min` verwendet einen Symlink auf diesen Entry Point
- Cron-Umgebung erhält explizit Config-, Data- und Log-Pfade
- `scheduler_tick.json` wird jede Minute aktualisiert
- Status zeigt „Scheduler letzter Tick“
- damit klar erkennbar: Cron läuft / Cron läuft nicht / Intervall noch nicht fällig


## v0.5.8

Scheduler auf das bewährte Somfy-TaHoma-Prinzip umgestellt:

- standardmässige LoxBerry-Datei `cron/cron.01min`
- separater `velux_scheduler.py`
- non-blocking Lock gegen parallele Scheduler-Läufe
- Intervallprüfung ausserhalb des eigentlichen VELUX-Workers
- erfolgreicher Zeitstempel wird erst nach vollständig erfolgreichem Worker-Lauf gesetzt
- bei Fehler wird kein Erfolgszeitstempel geschrieben; der nächste Minuten-Cron versucht erneut
- UDP-Control-Listener wird bei jedem Cron-Tick weiterhin überwacht


## v0.5.9

- Scheduler-Zeitbasis korrigiert
- Erfolgszeitpunkt wird erst nach erfolgreichem Worker-Lauf gespeichert
- gespeichert wird jedoch der START des erfolgreichen Laufs
- dadurch bleibt ein 1-Minuten-Intervall tatsächlich 1 Minute und wird nicht durch die API-Laufzeit auf 2 Minuten verlängert
- nächster geplanter Lauf wird im Log mit konkretem Zeitpunkt ausgegeben


## v0.5.10

- Statusseite: Schalter **Plugin aktiv / inaktiv**
- Inaktiv deaktiviert automatische Abrufe und den UDP-Steuerungslistener
- Einstellungen, Daten und Gateway-Kopplung bleiben erhalten
- Erweiterte Diagnose für `open` und `position`
- Diagnose protokolliert Home-ID, Device-ID, Bridge-ID, Gateway-ID und Kopplungsstatus
- normaler und signierter setstate-Pfad werden getrennt protokolliert
- keine Tokens, Passwörter oder privaten Schlüssel werden geloggt
- Hauptlog wird bei einer Neuinstallation geleert
- bei einem Update bleibt das bestehende Log erhalten
- Scheduler-Fix aus v0.5.9 bleibt unverändert
- kein 5-Sekunden-Warte-Workaround


## v0.5.12

- VELUX ACTIVE Automatisierung wieder aktivieren
- signierter Gateway-Befehl `scenario=home`
- Web-Button auf der Steuerungsseite
- Loxone UDP: `velux.cmd.velux_active.automation=1`
- benötigt erfolgreiche Gateway-Kopplung


### v0.5.12 Hotfix
- `automation` in `control_cli.py` als gültiger Web-Steuerbefehl freigegeben
- widersprüchliche Fehlermeldung mit altem `control_state` korrigiert


## v0.5.12

- Korrektur VELUX ACTIVE Automatisierung
- `scenario=home` entfernt: dieser Befehl betrifft Departure/Away Mode, nicht die Fensterautomatik
- Automatik aktivieren setzt Fenster nun unsigned auf `mode=algo_available`
- `manual` = Automatik aus
- `algo_available` / `algo_active` = Automatik aktiv
- Loxone UDP bleibt: `velux.cmd.velux_active.automation=1`


## v0.5.12 – korrigierter Stand

Die VELUX ACTIVE Automatisierung wird über den Fenstermodus wieder aktiviert:

```text
mode=algo_available
```

Loxone UDP:

```text
velux.cmd.velux_active.automation=1
```

`scenario=home` wird dafür nicht mehr verwendet.


### v0.5.12 UDP-Listener-Korrektur

- UDP-Listener wird bei Updates jetzt explizit neu gestartet.
- Alte PID-Dateien werden nicht übernommen.
- Damit verwendet UDP nach einem Plugin-Update garantiert den neuen `control_listener.py`.
