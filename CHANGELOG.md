# Changelog

## 1.1.0 – Stable

Großes Qualitäts-, Sicherheits-, Reboot- und WebUI-Update seit dem letzten offiziellen Stable-Release **1.0.0**.

### Oberfläche und Bedienung

- Weboberfläche umfassend aufgeräumt und vereinheitlicht.
- Responsive Darstellung für Desktop, Tablet und Smartphone.
- Statusseite mit besser strukturierten Homes, Geräten und aktuellen VELUX-Werten.
- Aktuelle Werte auf Smartphones als übersichtliche Karten dargestellt.
- Einstellungsseite in klare Bereiche für VELUX-Konto, Abruf/Plugin, UDP-Statuswerte, UDP-Steuerung und Gateway gegliedert.
- Erweiterte UDP-Einstellungen platzsparend zusammengefasst.
- UDP-Messages-Seite neu strukturiert und auf Desktop sowie Smartphone optimiert.
- Globale UDP-Statusanzeigen für Aktivierung, Heartbeat, Sendeart, Ziel, Port und Präfix.
- Funktionen „Alle aktivieren“ und „Alle deaktivieren“ für erkannte UDP-Werte.
- Einzelne UDP-Werte weiterhin frei aktivierbar und individuell benennbar.
- Buttons, Tabs und Navigation in Normal-, Hover-, Focus-, Active- und Disabled-Zuständen auf gute Lesbarkeit geprüft.
- Störende geerbte Text-/Box-Schatten, Filter und Browser-/LoxBerry-CSS-Effekte neutralisiert.
- Zentrale Versionsanzeige aus `plugin.cfg`; alter hardcodierter Versions-Fallback entfernt.

### Stabilität, Sicherheit und Reboot

- Worker-Lock aktiviert, damit Scheduler und manuelle Abrufe nicht parallel gegen die VELUX API laufen.
- UDP-Steuerbefehle werden nur von konfigurierten erlaubten Absendern akzeptiert.
- LoxBerry-Miniserver können als erlaubte Absender verwendet werden.
- Bestehende Absenderfreigaben bleiben bei temporären Fehlern der Miniserver-Abfrage erhalten.
- UDP-Listener veröffentlicht seine PID erst nach erfolgreichem Port-Bind.
- Restriktivere Behandlung von Laufzeitdateien.
- Listener-Watchdog und Neustartverhalten robuster gestaltet.
- Reboot-Robustheit verbessert: temporäre Netzwerk-, API- oder UDP-Probleme werden beim nächsten Scheduler-Lauf erneut versucht.
- Letzter erfolgreicher Lauf wird nur nach tatsächlich erfolgreicher Verarbeitung aktualisiert.
- Refresh-Token bleibt der bevorzugte Authentifizierungsweg.
- Login-/Credential-Fallback bleibt für Recovery erhalten; Zugangsdaten werden nicht unbeabsichtigt gelöscht.
- Fehlende Credential-Felder werden defensiv behandelt, um CGI-/HTTP-500-Fehler zu vermeiden.
- Update-Sicherheit für Zugangsdaten, Tokens, Home-/Gateway-Zuordnung, Kopplungsdaten, Miniserver, UDP-Auswahl, Intervalle, Pluginstatus und Listener-Konfiguration überprüft.

### UDP, Loxone und Logging

- Loxone-Export verwendet den tatsächlich konfigurierten UDP-Präfix.
- Individuell konfigurierte UDP-Namen und Auswahlen werden im Export korrekt berücksichtigt.
- Boolean-Werte werden konsistent als `1/0` behandelt.
- Erfolgreich gesendete UDP-Telegramme werden einzeln im Plugin-Log protokolliert, z. B. `UDP TX -> ... key=value`.
- Das Log zeigt auch, wenn UDP deaktiviert ist oder im Modus „nur Änderungen“ keine Telegramme zu senden sind.
- Empfangene Loxone-Steuerbefehle sowie erfolgreiche und fehlgeschlagene VELUX-Steuerungen bleiben nachvollziehbar protokolliert.
- Heartbeat und bestehende veröffentlichte UDP-Syntax bleiben kompatibel.

### VELUX-Funktionen

- Bestehende Home-, Raum- und Geräteerkennung erhalten.
- Gateway-Kopplung und signierte Steuerbefehle erhalten.
- Steuerung von AUF, STOP, ZU und Position weiterhin geräteabhängig unterstützt.
- VELUX-Automatik und Wiederaufnahme nach manueller Steuerung unverändert berücksichtigt.
- Textzustände wie `algo_active`, `algo_available` und `manual` bleiben für Loxone auswertbar.

### Release und Dokumentation

- README vollständig auf Version 1.1.0 aktualisiert.
- LoxWiki/DokuWiki-Dokumentation auf den aktuellen Funktionsstand gebracht.
- AutoUpdate-Metadaten für Stable und Pre-Release auf `v1.1.0` aktualisiert.
- GitHub-Release-Text, Tag-Angaben und Release-Artefakte für `v1.1.0` vorbereitet.
- GitHub-Workflow zur Prüfung und Veröffentlichung des Release-Artefakts enthalten.

## 1.0.0 – Stable

Erster finaler Stable-Release.

- Zentrale Versionsquelle über `plugin.cfg`
- UDP-Ausgabe ohne zusätzliches `=`
- VELUX ACTIVE Automatisierung über `mode=algo_available`
- Loxone UDP-Befehl `velux.cmd.velux_active.automation=1`
- UDP-Listener wird bei Updates sauber beendet und neu gestartet
- UDP-Sendeeinstellungen und UDP-Auswahl bleiben bei Updates erhalten
- Sicherung der `config.json`
- Plugin Aktiv/Inaktiv
- Gateway-Kopplung für signierte Steuerbefehle
- Stabiler Scheduler
- Logging und Diagnose
