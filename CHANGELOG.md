# Changelog

## 1.5.0 – Lokaler Eventstream und direkte VELUX-Steuerung

Änderungen gegenüber dem letzten offiziellen Stable-Release **1.1.0** (interne Testbuilds nicht einzeln aufgeführt):

### Lokale KIX300-/KIG300-Verbindung
- HomeKit/HAP-Kopplung mit KIX300 und KIG300, einschließlich direkter Gateway-IP bei eingeschränkter mDNS-Erkennung über Subnetze.
- Lokaler Eventstream für verfügbare Sensor- und Positionswerte; automatische Erkennung und Überwachung des Listeners.
- Temperatur, Luftfeuchtigkeit und CO₂ werden bei lokaler Änderung ohne Warten auf das Cloud-Abrufintervall an Loxone übertragen, sofern ausgewählt.
- Positionsrückmeldungen während der Fahrt und bestätigte Endposition über Eventstream.

### Steuerung und Gerätezuordnung
- Direkte lokale Steuerung für AUF, ZU und Position (0–100), sofern das Gerät eine beschreibbare HAP-Characteristic besitzt.
- Automatischer Steuerweg: lokal zuerst, Cloud als Fallback; STOP und VELUX-Automatik weiterhin über Cloud.
- Automatisches, persistentes Multi-Aktor-Mapping für mehrere Fenster und Rollläden ohne feste AID-Reihenfolge.
- Konflikterkennung und Selbstkorrektur bereits gespeicherter falscher Gerätezuordnungen.
- Mehrdeutige lokale Gerätezuordnungen werden nicht blind direkt angesteuert.

### Loxone, Oberfläche und Stabilität
- Local-first für geeignete Sensor-/Positionswerte mit Cloud-Ergänzung und reduziertem Doppelversand bei „nur Änderungen“.
- Bestehende UDP-Namen, individuelle Wertauswahl und Heartbeat bleiben kompatibel.
- Neu gegliederte Einstellungen: VELUX Cloud inklusive signierter Gateway-Kopplung, lokale KIX/KIG-Verbindung, UDP-Rückmeldungen und UDP-Steuerung.
- Verbesserte Eventstream-Initialisierung, Watchdog/Neustart und Upgrade-Verhalten.
- Konfiguration, Tokens, Kopplungsdaten und gelernte Zuordnungen bleiben bei normalen Updates erhalten.

**Getestet:** KIX300 im Einzelaktor-Betrieb und KIG300 mit mehreren Fenstern/Rollläden durch Community-Test.

---

## 1.1.50 – Bereinigung und Installationshärtung
- Produktive HAP-Steuerung und Mapping-Logik nach erfolgreichem KIG300-Mehrfenster-Test bereinigt.
- Einmalige IPC-/Test-Diagnoselogzeilen entfernt; relevante Betriebs-, Mapping-, Eventstream- und UDP-Meldungen bleiben erhalten.
- Fehlgeschlagene Cloud-Fallbacks löschen einen offenen HAP-Lernauftrag sofort.
- Nicht mehr verwendete Eventstream-Diagnoseaktionen aus dem CGI-Backend entfernt; Pairing und Neuinitialisierung bleiben erhalten.
- Neuinstallation geprüft und Abhängigkeitsinstaller vor dem Aufruf explizit ausführbar gemacht.
- Upgradepfad geprüft: Konfiguration, Tokens, Logs und persistentes HAP-Gerätemapping bleiben erhalten; Listener starten mit neuem Code.
- Kritische HAP-Mapping-, Fallback-, Daemon- und Installationspfade mit wartbaren Kommentaren dokumentiert.

## 1.1.45
- Automatisches, ereignisbasiertes HAP-AID-Lernen für KIG300 mit mehreren VELUX-Aktoren.
- Persistente, konfliktgeschützte HAP-AID-zu-VELUX-Zuordnung ohne feste AID-Reihenfolge.
- Lokale HAP-Direktsteuerung pro gelerntem Aktor; Cloud-Fallback bleibt erhalten.
- Eventstream-Positionen werden nach gelerntem Mapping an den bestehenden UDP-Namen gesendet.
- Multi-AID Eventstream berücksichtigt nun auch den UDP-Modus „nur Änderungen“.
- KIX300-Einzelaktor-Verhalten bleibt unverändert.

## 1.1.44 – KIG300 HAP-Accessory-Diagnose
- Protokolliert beim HAP/Eventstream-Scan zusätzlich Identifikationsdaten der Accessories (z. B. Name, Hersteller, Modell, Seriennummer, Firmware), soweit vom Gateway bereitgestellt.
- Speichert die erkannten Identifikations-Characteristics zusätzlich in `event_accessory_metadata.json`.
- Keine automatische AID-Zuordnung und keine Freigabe der Direktsteuerung bei mehreren Aktoren: Sicherheitssperre bleibt bestehen.
- KIX300-Steuerung, Eventstream, Cloud-Fallback, UDP und VELUX-Automatik bleiben unverändert.

## 1.1.42 – KIG300 HAP-Pairing-Fix
- Behebt `NameError: name 'ev' is not defined` beim HomeKit/HAP-Pairing des KIG300.
- Eventstream-Konfiguration wird vor den KIG/HAP-Aktionen initialisiert.
- Der nicht mehr benötigte lokale HAP-Steuertest wurde aus den Einstellungen entfernt.
- Produktive HAP-Direktsteuerung, Eventstream, Cloud-Fallback, UDP und VELUX-Automatik bleiben unverändert.

## 1.1.41 – Direkter HAP-Steuerweg
- AUF, ZU und Position können produktiv über lokalen HAP/HomeKit-Weg gesteuert werden.
- Primärer Steuerweg wählbar: Direkt oder Cloud; jeweils mit automatischem Fallback.
- Steuerungsseite zeigt Primär- und Fallback-Weg sichtbar an.
- STOP und VELUX-Automatik bleiben unverändert auf dem Cloud-Weg.
- HAP-Direktsteuerung ist bis zur Gerätezuordnung bei mehreren Aktoren aus Sicherheitsgründen gesperrt.

## 1.1.40 - HAP Local Control Test
- Isolierter lokaler HAP-Schreibtest für `position.target` (0-100).
- Nutzt ausschließlich die vorhandene HAP-Kopplung; Cloud-/Signed-Steuerung bleibt unverändert.
- Characteristic wird dynamisch aus den Event-Fähigkeiten ermittelt und muss `pw` besitzen.
- Sicherheitsabbruch bei keiner oder mehreren passenden Target-Characteristics.
- Write-Ergebnis und anschließende Eventstream-Rückmeldung werden im Plugin-Log protokolliert.

# 1.1.38 - Eventstream Positions-UDP

- Lokale HAP-Fensterereignisse werden in den bereits bestehenden UDP-Positionswert integriert.
- Während einer Fahrt wird `position.target` sofort als Position an Loxone gesendet.
- Bei `position.state=2` bestätigt `position.current` den tatsächlich erreichten Endwert.
- Ist `position.target` nicht vorhanden/null, dient `position.current` als Fallback.
- Bestehende UDP-Auswahl und benutzerdefinierte UDP-Namen werden respektiert.
- Modus „Nur Änderungen“ berücksichtigt den gemeinsamen UDP-Cache, damit Eventstream und Cloud-Polling keine unnötigen Doppelwerte senden.
- Bei mehreren Fenster-Positionswerten wird nicht geraten; ohne eindeutige HAP-Gerätezuordnung erfolgt keine Event-UDP-Ausgabe.
- Cloud-Polling, Steuerung, Automatik und HAP-Pairing bleiben unverändert.

# 1.1.37 - HAP Eventstream Listener

- Event-Watchdog wird jetzt vor dem cron-Ende jede Minute ausgeführt.
- Event-Watchdog startet nach dem Speichern der Einstellungen sofort.
- HAP-Subscription und Listener-Status werden eindeutig protokolliert.
- Eventstream-Port wird gespeichert; Standard bei Neuinstallation ist 5001.
- Nach erfolgreichem Pairing zeigt das Setup-Code-Feld nur noch „Vorhanden – nichts ändern“; der Code selbst wird weiterhin nicht gespeichert.
- Noch keine UDP-Weiterleitung der HAP-Events.

# 1.1.36 - Event-Characteristics Diagnose sichtbar

- Event-Werte werden mit AID/IID, Characteristic, Typ, aktuellem Wert und HAP-Rechten in der Oberfläche angezeigt.
- Dieselben sieben Event-Characteristics werden beim Scan in das normale VELUX-Log geschrieben.
- Komplette Compact-Ausgabe wird zusätzlich als Diagnose unter event_accessories_compact.txt gespeichert.
- Pairing, Cloud-Worker, UDP, Steuerung und Abfrageintervall unverändert.

# 1.1.35 - Direct HAP Pairing für homekit_python 0.19.0

- Pairing-Resolver an die auf LoxBerry bestätigte homekit_python-Version 0.19.0 angepasst.
- Verwendet exakt `find_device_ip_and_port` aus `Controller.start_pairing()`.
- Direkter KIX/KIG-Endpunkt ersetzt nur die Bonjour-Auflösung; HAP Pair-Setup/Kryptografie bleibt unverändert in homekit_python.
- Keine Änderung an Cloud-Worker, UDP, Steuerung oder Abfrageintervall.

# 1.1.34 - Direct HAP Pairing

- KIX/KIG Pairing kann den bereits verifizierten direkten HAP-Endpunkt verwenden, wenn mDNS die Subnetz-/VLAN-Grenze nicht ueberquert.
- Kein Fallback auf fremde `_hap._tcp`-Geräte.
- Die echte Accessory Pairing ID wird weiterhin kryptografisch während HAP Pair-Setup vom Gateway gelernt; es wird keine Device-ID geraten.
- Bestehender Cloud-Worker, UDP und Abfrageintervall unverändert.

# Changelog

## 1.1.32 – Eventstream Pairing Guard
- Pairing-Pfad für den lokalen KIX/KIG-HAP-Eventstream vorbereitet.
- HomeKit-Setup-Code wird nur an den Pairing-Prozess übergeben und nicht in `config.json` gespeichert.
- Sicherheitsprüfung: Pairing ist nur zulässig, wenn der per mDNS erkannte HAP-Service exakt zur bekannten VELUX-Gateway-IP gehört; ein fremdes HomeKit-Gerät wird niemals verwendet.
- Der im direkten Diagnosepfad geprüfte HAP-Port wird beim Pairing zusätzlich gegengeprüft.
- Bei getrennten Subnetzen wird keine HAP-Device-ID erfunden: solange der `_hap._tcp`-Record des KIX/KIG den LoxBerry nicht erreicht, meldet die Oberfläche dies nachvollziehbar statt falsch zu koppeln.
- Cloud-Worker, 3-Minuten-Abfrage, VELUX-Steuerung, Automatik und bestehende UDP-Ausgabe unverändert.

## 1.1.31 – Direkte KIX-HAP-Diagnose

- Read-only Direktprüfung der bekannten KIX/KIG-IP bei durch VLAN/Subnetz blockiertem mDNS.
- Diagnose-Port ist variabel und wird nicht fest auf 5001 gesetzt.
- Der Test führt nur eine TCP-Verbindung und `GET /accessories` aus; kein Pairing, keine Steuerung, keine UDP-Ausgabe.
- Normale HAP-Erkennung bleibt mDNS/Zeroconf-basiert; Cloud-Worker und bestehendes Abfrageintervall bleiben unverändert.

## 1.1.30 – Eventstream Discovery robust
- HAP-Discovery liest `_hap._tcp.local.` direkt per Zeroconf statt nur die formatierte CLI-Ausgabe zu parsen.
- Bereits gekoppelte VELUX Gateway-IP wird zur eindeutigen Zuordnung verwendet.
- Eventstream-Port wird ausschließlich aus dem HAP/mDNS Service Record übernommen; kein Standardport wird geraten.
- Fallback auf `homekit.discover`, falls direkte Zeroconf-Erkennung nicht verfügbar ist.
- Eventstream bleibt rein diagnostisch; bestehende UDP-Ausgabe, Steuerung und Cloud-Abfrageintervall unverändert.

## 1.1.29 – KIX/KIG Eventstream Diagnose
- Lokaler HomeKit/HAP-Eventstream als optionaler, rein diagnostischer Parallelkanal.
- Keine Änderung an Cloud-Abfrageintervall, Steuerung oder UDP-Ausgabe.
- Gateway-Port wird per HAP/mDNS erkannt; kein Port fest codiert.
- Pairing-/Eventdaten update-sicher im Plugin-Konfigurations-/Datenbereich.

# Changelog

## 1.1.28 – KIG300 Signed-Payload-Abgleich
- Signierter Dachfenster-Payload an die Referenz-/App-Struktur angeglichen: `force=true` wird nicht mehr im signierten Modul mitgesendet.
- HMAC, Sign-Key-ID, Bridge, Target-Position, Timestamp/Nonce und `app_type=app_velux` bleiben unverändert.
- Keine Änderung an KIX300-Steuerpfad, Close/Stop, Pairing, Token, UDP oder VELUX-Automatik.

## 1.1.27
- Anzeige unter „UDP Messages“ verbessert: Der aktuelle Wert bleibt in der Spalte „Aktuell“ sichtbar.
- Die UDP-Message-Vorlage wird nun direkt Loxone-tauglich mit `=\v` angezeigt, z. B. `velux.module.dachfenster_bad.mode=\v`.
- Nur Anzeige/Kopiertext geändert; tatsächlicher UDP-Versand, Worker, API und Steuerung bleiben unverändert.

## 1.1.25 – Einheitliche Loxone-Anzeige für Automatikstatus

- `module.<gerät>.mode` wird jetzt nicht nur beim tatsächlichen UDP-Versand, sondern auch auf der Statusseite und unter „UDP Messages“ identisch als `0/1/2` dargestellt.
- Mapping: `0=algo_disabled`, `1=algo_available`, `2=algo_active`.
- Unter „UDP Messages“ zeigt die Vorschau nun das vollständige Telegramm inklusive aktuellem Wert, z. B. `velux.module.dachfenster_bad.mode=2`.
- Der originale VELUX-Textwert bleibt intern in `state.json` für Diagnose und zukünftige Kompatibilität erhalten.
- Keine Änderungen an KIG/KIX-Steuerpfad, Signing, Pairing, Token-Handling oder Automatik-Steuerbefehl.

## 1.1.24 – KIG/KIX und Loxone-Automatikstatus

- KIG-300-Support und zweistufige Gateway-/Signing-Kopplung in Dokumentation und Loxone-Hinweisen vollständig beschrieben; KIX-300-Unterstützung bleibt erhalten.
- VELUX-Gerätemodus wird für Loxone über den bestehenden UDP-Namen `module.<gerät>.mode` numerisch ausgegeben: `0=algo_disabled`, `1=algo_available`, `2=algo_active`.
- Der originale VELUX-Textmodus bleibt intern für Status und Diagnose erhalten; unbekannte zukünftige Modi werden nicht falsch umcodiert.
- Automatik-Status und Automatik-Steuerung klar getrennt: Wiederfreigabe weiterhin über `velux.cmd.velux_active.automation=\v` mit Wert `1`.
- Loxone-Beispiele und Export vereinheitlicht: `open`, `close`, `stop` und `position` verwenden `=\v`; für digitale Befehle gilt Wert `1`, für Position `0–100`.
- v1.1.23 Request-Kompatibilitätsanpassung bleibt enthalten: signierte Fensterbefehle senden zusätzlich `app_type=app_velux`.
- Keine weitere Änderung am KIG/KIX-Steuerpfad, Signing, Nonce/Timestamp, Rain-Override, Pairing oder Token-Handling.

## 1.1.22 – Token-Refresh-Puffer Test

- Access-Token wird bereits bei weniger als 30 Minuten Restlaufzeit erneuert.
- Gleiche 30-Minuten-Regel für Worker, Steuerung und Gateway-Kopplung.
- CONTROL AUTH DIAG bleibt vollständig aktiv, damit Token-Alter, Restlaufzeit und Refresh-Quelle weiter nachvollziehbar sind.
- Keine Änderungen an Signing, Nonce/Timestamp, Rain-Override, Gerätepfaden, UDP, Automatik oder Pairing-Ablauf.

## 1.1.21 - Auth-/Code-28-Diagnose

- Reiner Diagnose-Build auf Basis von 1.1.20.
- Protokolliert bei Steuerbefehlen ausschließlich nicht geheime OAuth-Zeitdaten (Token-Alter, Restlaufzeit und Herkunft aus Cache/Refresh/Login).
- Protokolliert für signierte Fensterbefehle sicheren Request-Kontext (Zeitpunkt, API-Pfad, App-Version, Home-/Geräte-/Gateway-ID).
- Access-Token, Refresh-Token, Signing-Key und Hash werden weiterhin nicht protokolliert.
- Keine Änderung an Signing, Timestamp/Nonce, Pairing, Steuerpfaden, UDP, Automatik oder KIX300-Verhalten.

## 1.1.20 – Zweistufige Gateway-Kopplung

- Gateway-/Signing-Kopplung in zwei bewusst getrennte Schritte aufgeteilt: zuerst Cloud-`retrieve_key`, danach Benutzeraktion am Gateway und lokaler Schlüsselabruf über TCP 25050.
- Die Oberfläche fordert nach erfolgreicher Vorbereitung ausdrücklich zum Drücken der Pairing-Taste am VELUX Gateway auf.
- Der lokale Schlüsselabruf startet erst über den separaten Button „Taste gedrückt – Schlüssel abrufen“.
- Eine vorbereitete Kopplung läuft nach 15 Minuten ab und muss dann neu gestartet werden.
- Vorhandene Signing Keys werden bei Vorbereitung, Timeout, Netzwerkfehler oder Cloud-Fehler nicht gelöscht oder überschrieben; gespeichert wird erst nach vollständig erfolgreichem lokalem Schlüsselaustausch.
- Kein automatisches Re-Pairing bei Code 28.
- Keine Änderung an Fenster-/KIX-Steuerpfad, HMAC, Timestamp/Nonce, UDP, Heartbeat oder VELUX-Automatik.

## 1.1.19 – Signatur: eindeutige Timestamp/Nonce-Paare

- Timestamp/Nonce-Vergabe für signierte VELUX-Fensterbefehle an die aktuelle Referenzlogik angepasst.
- Ein bereits verwendetes `(timestamp, nonce)`-Paar wird nicht erneut verwendet.
- Läuft die Uhr innerhalb derselben Sekunde bzw. nicht über den letzten Timestamp hinaus, wird der Nonce erhöht.
- Bei einem neueren Timestamp startet der Nonce wieder bei `0`.
- Der letzte Signaturstand wird prozessübergreifend im Plugin-Datenverzeichnis gespeichert, damit UDP-Listener und Web-Steuerung dieselbe Sequenz verwenden.
- Keine Änderung an Pairing, Schlüsselmaterial, UDP, Heartbeat, Automatik oder Geräteklassifizierung.
- KIX-300-Steuerpfad bleibt unverändert; die Anpassung betrifft nur die Signaturvergabe signierter Fensterbefehle.

## 1.1.18 – Signierter Fensterpfad: VELUX Regen-Override

- Signierte Dachfenster-Befehle senden wieder den VELUX-Regen-Override (`force=true`) im Modul-Payload.
- HMAC-Signatur, Timestamp und `nonce=0` für Einzelbefehle bleiben unverändert.
- Kein automatischer Retry bei API-Code 28 und keine Änderung an Pairing/Signierschlüsseln.
- KIX/KIG-Steuerpfad, Automatik, UDP, Heartbeat und Log-Cleanup aus 1.1.17 bleiben unverändert.

## 1.1.17 – Log-Cleanup und Größenbegrenzung

- Diagnose-RAW-Ausgaben aus dem normalen Dauerbetrieb entfernt.
- Gemeinsame, prozesssichere Logroutine für Worker, Scheduler, Steuerung und Gateway-Kopplung.
- `veluxactive.log` wird hart auf maximal 1.000.000 Byte begrenzt.
- Täglicher Log-Reset um 00:00 Uhr über den minütlichen LoxBerry-Cron.
- Keine Änderung am funktionierenden KIX/KIG-Steuer-, Signing-, Pairing-, UDP- oder Automatikpfad.

## 1.1.16 – Fenster/Rollladen-Steuerpfad getrennt

- Dachfenster und Rollläden werden bei der Steuerung nicht mehr pauschal gleich behandelt.
- Nur erkannte Dachfenster verwenden bei `open` den signierten KIG/KIX-Fensterpfad bzw. bei `position` den vorhandenen Code-9-Signatur-Fallback.
- Rollläden/Jalousien verwenden für `open` und `position` wieder den normalen Setstate-Pfad ohne Fenstersignatur.
- `velux_type`, `rain_position` und `secure_position` werden im normalisierten Gerätestatus erhalten, damit die Gerätetrennung stabil möglich ist.
- Der Code-6-Retry für `close` und `stop` bleibt unverändert.
- Keine spekulative Änderung an HMAC/Nonce, Pairing, Token, UDP, Heartbeat oder VELUX-Automatik.

## 1.1.15 – KIG300 Regression-Fix Auf/Position

- Stellt für `open` und `position` den in v1.1.13 verwendeten Steuer-/Fallback-Pfad wieder her.
- Behält den gezielten Code-6-Retry für `close` und `stop` unverändert bei.
- Keine Änderungen an Signierung/HMAC, Gateway-Pairing, Token, UDP, Heartbeat oder VELUX-Automatik.
- Keine persistenten Einstellungen werden überschrieben.

## 1.1.13 – Code-6 Stabilitäts-Retry
- Temporäre Gateway-Antwort `code 6` wird bei `close` und `stop` gezielt behandelt.
- Maximal zwei Wiederholungen mit gestaffelten Wartezeiten (5 s / 15 s).
- Andere Fehlercodes werden nicht automatisch wiederholt.
- Der funktionierende signierte OPEN-/POSITION-Pfad bleibt unverändert.
- Pairing, Token, UDP, Heartbeat und VELUX-Automatik bleiben unverändert.

## 1.1.12 – KIG 300 Open-Pfad

- `open` verwendet bei KIG-300-Fenstern jetzt direkt den bereits funktionierenden signierten Positionspfad mit `target_position=100`.
- Der vorherige normale `setstate`-Versuch für `open`, der Code 9 liefern konnte, wird übersprungen.
- `position`, `stop` und `close` bleiben funktional unverändert.
- Keine Änderungen an Pairing, Signierschlüssel, Token, Worker, UDP, Heartbeat oder VELUX-Automatik.

# Changelog

## 1.1.11 – KIG 300 Fenstersteuerung nach VELUX-App-Protokoll
- Signierte `open`-/`position`-Requests an `/syncapi/v1/setstate` an den dokumentierten VELUX-App-Request angeglichen.
- Entfernt `force=true` aus dem signierten Fenstermodul; Signatur, `nonce=0`, Timestamp und HMAC-Berechnung bleiben unverändert.
- Entfernt `app_type` aus dem signierten Positions-Request; `app_version`, Home-ID, Zeitzone, Bridge, Sign-Key-ID und Hash bleiben erhalten.
- `stop` verwendet jetzt den von der VELUX-App verwendeten Gateway-Befehl `stop_movements=all` statt `target_position=-1`.
- Der bei KIG 300 nachweislich funktionierende `close=0`-Pfad bleibt unverändert.
- Keine Änderung an Pairing/Sign-Key, Token-Handling, Worker, UDP, Heartbeat oder VELUX-Automatik.

## 1.1.10 – KIG/KIX Gateway- und Signaturdiagnose
- Persistiert für NXG-Gateways ausschließlich nicht-sensitive Diagnosezustände (`secure`, `busy`, `locked`, `locking`, `last_reset_type`, `calibrating`, `wifi_state`, `wifi_strength`) im normalisierten Status.
- `pairing` wird aus Sicherheitsgründen nicht gespeichert oder protokolliert; erfasst wird nur ein abstrahierter `pairing_state` (z. B. `present`, `empty`, `true`, `false`, `missing`).
- Die PRE-Diagnose vor signierten Fensterbefehlen zeigt diese Gateway-Zustände, damit erfolgreiche und mit Code 28 abgelehnte Öffnungsbefehle verglichen werden können.
- Keine Änderung an HMAC/Signatur, `nonce=0`, Pairing, Steuerbefehlen oder Retry-Verhalten.
- Abrufintervall: 3 Minuten ist der Standard für neue Konfigurationen; bestehende Einstellungen bleiben erhalten. Die Oberfläche warnt sichtbar vor Intervallen unter 3 Minuten.

## 1.1.9 – KIG 300 Gateway-Zustandsdiagnose
- Reiner Diagnosebuild; Steuerungs-, Pairing- und Signierlogik bleiben unverändert.
- Protokolliert vor einem signierten Öffnungs-/Positionsbefehl zusätzlich die bereits im letzten Status vorhandenen Gateway-Felder `pairing`, `secure`, `busy`, `locked`, `locking`, `last_reset_type`, `reachable` und `last_seen`.
- Kein zusätzlicher API-Aufruf und kein zusätzlicher Steuerbefehl.
- Sign-Key-Fingerprint-Diagnose aus 1.1.8, API-Lock, Schutz vor 49→1-Teilstatus und kein automatischer Retry bei Code 6/28 bleiben erhalten.
- Tokens, Gateway-Kopplung, UDP-Konfiguration, Heartbeat und VELUX-Automatik werden nicht verändert.

## 1.1.8 – KIG 300 Sign-Key-Konsistenzdiagnose
- Reiner Diagnosebuild auf Basis 1.1.7; Steuerungs-, Pairing- und Signierlogik bleiben unverändert.
- Protokolliert beim signierten Fensterbefehl einen gekürzten SHA-256-Fingerprint des vorhandenen `hash_sign_key`, dessen Länge sowie die zugehörige `sign_key_id` und Gateway-ID.
- Der geheime Signierschlüssel selbst, HMAC/Hash des Steuerbefehls, Tokens und Passwort werden nicht protokolliert.
- Keine zusätzlichen API-Aufrufe, keine Wiederholungsbefehle und kein automatisches Re-Pairing.
- KIX/KIG-Steuerpfad, API-Lock, Code-6/28-Schutz, 49→1-Statusschutz, UDP, Heartbeat und VELUX-Automatik bleiben unverändert.

## 1.1.7 – KIG 300 Signatur-Diagnose
- Reiner Diagnosebuild: Steuerungs-, Pairing- und Signierlogik bleiben unverändert.
- Protokolliert vor dem signierten Fensterbefehl den bereits bekannten Geräte-/Gateway-Zustand, ohne einen zusätzlichen API-Aufruf auszulösen.
- Erweitert die sicheren Signatur-Metadaten um `home_id`, App-Typ/-Version und `force`; geheime Signierschlüssel, HMAC/Hash sowie Tokens werden weiterhin nicht protokolliert.
- Erfolgreiche und abgelehnte signierte Requests können damit gezielter miteinander verglichen werden.
- Kein automatischer Retry bei Code 6/28, API-Lock und 49→1-Statusschutz bleiben unverändert.

## 1.1.6 – KIG 300 API-Zugriffsschutz
- Serialisiert VELUX-Cloudzugriffe zwischen Worker und Steuerung über einen gemeinsamen API-Lock.
- Ein Steuerbefehl wartet kurz, wenn gerade ein Statusabruf läuft; ein Scheduler-Lauf wird auf den nächsten Lauf verschoben, wenn gerade gesteuert wird.
- Verhindert damit parallele `homestatus`-/`setstate`-Zugriffe, die in den KIG-300-Diagnoselogs zeitlich zusammenfielen.
- Die bestehende Signatur (`nonce=0`, Timestamp/HMAC-Aufbau) bleibt bewusst unverändert, da genau dieser Signierpfad in früheren Logs bereits erfolgreich akzeptiert wurde.
- Schutz gegen unvollständige 49→1-Statusabrufe sowie kein automatischer Retry bei Code 6/28 bleiben erhalten.
- Pairing, Signierschlüssel, Tokens, UDP-Konfiguration, Heartbeat und VELUX-Automatik werden nicht verändert.

## 1.1.5 – KIG 300 Steuerungs-Schutz
- Entfernt auch den automatischen zweiten Versuch nach `code 6` bei `open`/`position`.
- Bei `code 6` wird der ursprüngliche Gateway-Fehler jetzt direkt zurückgegeben und kein identischer Folgebefehl gesendet.
- Der bestehende `code 9`-Fallback auf den signierten `setstate` bleibt unverändert.
- Der Schutz aus 1.1.4 gegen unvollständige Statusabrufe (z. B. 49 auf 1 Wert) bleibt vollständig erhalten.
- Kein automatischer Retry bei signiertem `code 28` bleibt ebenfalls erhalten.
- Pairing, Signierschlüssel, Tokens, UDP-Konfiguration, Heartbeat und VELUX-Automatik werden nicht verändert.

## 1.1.4 – KIG 300 Schutzbuild
- Entfernt den wirkungslosen automatischen zweiten Versuch nach signiertem `code 28`; dadurch wird das Gateway bei diesem Fehler nicht mit einem identischen Folgeversuch belastet.
- Erkennt einen plötzlichen massiven Einbruch gegenüber dem letzten vollständigen Status (z. B. 49 auf 1 Wert).
- Ein solcher unvollständiger Abruf überschreibt `state.json` nicht mehr. Die letzte vollständige Geräte-/Aktorbasis bleibt für WebUI und Steuerung erhalten.
- Ein verworfener Teilabruf zählt nicht als erfolgreicher Scheduler-Lauf; der nächste Cron-Lauf versucht den Abruf erneut.
- KIG-300-Diagnose für signierte Befehle und unvollständige Abrufe bleibt aktiv.
- Zugangsdaten, Tokens, Pairing-/Signierschlüssel, UDP-Konfiguration und VELUX-Automatik werden nicht verändert.

## 1.1.3 – KIG 300 Diagnosebuild
- Zusätzliche sichere Diagnose für signierte `open`-/`position`-Aufrufe.
- Pro signiertem Aufruf werden Zeitstempel, Nonce, Geräte-/Bridge-ID, Zielposition und Laufzeit protokolliert.
- Sign-Key-ID darf zur Zuordnung protokolliert werden; geheimer Signierschlüssel, Hash-Sign-Key, Access-/Refresh-Token und erzeugter HMAC werden ausdrücklich nicht geloggt.
- Code-28-Fehler enthalten die nicht geheimen Request-Metadaten zum direkten Vergleich mit erfolgreichen Aufrufen.
- Auffällig unvollständige Statusabrufe werden mit Geräte-/Werteanzahl und Rohstruktur-Zählwerten markiert.
- Steuerlogik und einmalige Retries aus 1.1.2 bleiben unverändert; keine zusätzlichen API-Anfragen.

## 1.1.2 – KIG 300 Testbuild
- Experimentelle, gezielt begrenzte Fehlerbehandlung für KIG-300-Steuerprobleme.
- Bei `code 6` während `open`/`position`: einmaliger Retry nach 3 Sekunden.
- Bei signiertem `code 28`: Signatur wird mit neuem Zeitstempel neu erzeugt und einmal nach 3 Sekunden wiederholt.
- Bestehender `code 9`-Fallback auf signierten `setstate` bleibt unverändert.
- Keine Wiederholungsschleifen; maximal ein zusätzlicher Versuch pro beobachtetem Fehlerpfad.
- `close`, `stop`, Automatik, Worker, UDP und Heartbeat bleiben unverändert.
- Zusätzliche Logeinträge `CONTROL KIG300 TEST` zur eindeutigen Auswertung.

## 1.1.1
- Heartbeat gegen kurze VELUX-Cloud-/API-Aussetzer robuster gemacht.
- Konfigurierbare Fehlertoleranz für aufeinanderfolgende temporäre Fehler (Standard: 3).
- Timeout-, Netzwerk-, HTTP-429- und HTTP-5xx-Fehler setzen den Heartbeat erst nach Erreichen der Schwelle auf 0.
- Erfolgreicher Cloud-Abruf setzt den Fehlerzähler sofort zurück.
- Nicht-temporäre Authentifizierungs-, Konfigurations- und API-Fehler setzen den Heartbeat weiterhin unmittelbar auf 0.
- Zusätzliche Heartbeat-Diagnose im Log und Statuszustand.

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

## 1.1.39
- KIX/KIG Eventstream aus dem Diagnose-/Teststatus in den normalen Pluginbetrieb überführt.
- Testbereich mit Gateway-Suche, HAP-Probe, Characteristic-Scan und Characteristic-Tabelle aus der normalen Oberfläche entfernt.
- Statusseite zeigt Eventstream-Zustand, HAP-Kopplung, Anzahl abonnierter Characteristics und letztes empfangenes Event.
- Eventstream-Einstellungen auf Aktivierung, HAP-Port und sichere Erstkopplung reduziert.
- Setup-Code wird weiterhin nicht gespeichert oder erneut angezeigt.
- Positions-UDP aus 1.1.38 unverändert: während Fahrt Target, nach Fahrt Current; Cloud-Abruf bleibt Fallback.
- Produktive HAP-Kopplung wieder vollständig in den Einstellungen verfügbar; nur reine Diagnoseaktionen bleiben ausgeblendet.
- Nach einer neuen HAP-Kopplung werden die eventfähigen Characteristics automatisch eingelesen und der Listener gestartet.
- Bei bestehender Kopplung kann der Eventstream ohne Setup-Code neu initialisiert werden; dabei werden Characteristics neu gelesen und der Listener neu gestartet.
