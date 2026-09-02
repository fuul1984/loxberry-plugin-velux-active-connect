# VELUX Active Connect v1.1.0 – Stable

Version 1.1.0 ist das große Qualitäts-, Sicherheits-, Reboot- und WebUI-Update seit dem letzten offiziellen Stable-Release **v1.0.0**.

## Highlights

- vollständig überarbeitete responsive Weboberfläche für Desktop und Smartphone
- aufgeräumte Einstellungen und neu strukturierte UDP-Messages-Seite
- verbesserte Statusdarstellung für Homes, Geräte und aktuelle VELUX-Werte
- vollständiges UDP-TX-Logging mit Ziel, Port und `key=value`
- echter Worker-Lock gegen parallele API-Läufe
- Prüfung erlaubter UDP-Absender für Loxone-Steuerbefehle
- robusterer Listener/Watchdog und verbessertes Verhalten nach LoxBerry-Reboots
- Refresh-Token-/Credential-Recovery gehärtet
- korrigierter Loxone-Export mit konfiguriertem Präfix und individuellen UDP-Namen
- zentrale Versionsanzeige ohne hardcodierte Fallback-Version
- bestehende VELUX-Steuerung und Wiederaufnahme der VELUX-Automatik erhalten
- LoxWiki, README, Changelog und AutoUpdate-Metadaten aktualisiert

## Kompatibilität

- Minimum LoxBerry: **4.0.0**
- bestehende veröffentlichte UDP-Namen bleiben kompatibel
- bestehende Konfiguration, Tokens, Gateway-/Home-Zuordnung, UDP-Auswahl, Miniserver- und Listener-Einstellungen bleiben bei Updates erhalten

## Installation / Update

Release-Artefakt:

`VELUX_Active_Connect_v1.1.0.zip`

Das ZIP kann über die LoxBerry-Pluginverwaltung installiert bzw. als Update eingespielt werden.

## GitHub

**Tag:** `v1.1.0`  
**Release-Titel:** `VELUX Active Connect v1.1.0 – Stable`  
**Release-Typ:** Stable / kein Pre-Release

Die vollständigen Änderungen gegenüber v1.0.0 stehen in `CHANGELOG.md`.
