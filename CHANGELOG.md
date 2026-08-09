# Changelog

## 0.5.5
- Kompakter Gateway-Kopplungsstatus auf der Statusseite
- Gateway-Kopplung unter Einstellungen
- Loxone-Hilfe pro Aktor
- UDP-Sende- und Empfangsport getrennt konfigurierbar
- Gateway-Signierung für Dachfensterpositionen
- UDP-Steuerung von Loxone
- Update-feste Konfiguration und Kopplungsdaten

## 0.5.1
- UDP-Empfangsdiagnose und korrigierte Loxone-Ausgangsbeispiele

## 0.4.1
- Automatische Installation/Prüfung von `cryptography`

## 0.4.0
- Gateway-Kopplung und signierte Positionssteuerung

## 0.3.x
- Direkte Websteuerung und UDP-Steuerlistener

## 0.2.x
- Konfigurierbare UDP-Messages, Regensensor und Temperaturkorrektur

## 0.1.x
- VELUX Login, Homes/Geräte/Werte und LoxBerry-Miniserver-Anbindung

## 0.5.6

- Abrufintervall/Scheduler korrigiert.
- Startzeit des letzten Abrufs wird als Referenz für den nächsten Lauf verwendet.
- Statusseite zeigt Abrufintervall und nächsten geplanten Lauf.
- Scheduler-Diagnose im Plugin-Log ergänzt.


## 0.5.9

- Scheduler für den regelmäßigen VELUX-Abruf grundlegend korrigiert.
- LoxBerry-Standard `cron/cron.01min` verwendet.
- Separater Scheduler mit Lock gegen parallele Läufe.
- Intervall wird vom Start eines erfolgreichen Laufs berechnet.
- Bei einem Fehler erfolgt beim nächsten Scheduler-Tick ein neuer Versuch.
- Anzeige des nächsten Laufs korrigiert.
