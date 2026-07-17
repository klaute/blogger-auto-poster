# Richtlinien für automatisch erzeugte Projektartikel

## Zweck dieser Datei

Diese Richtlinien gelten für Codex bei der Analyse lokaler Projekte und bei der Erzeugung von Markdown-Dateien für den Blog.

Diese Datei beschreibt Inhalt, Stil und redaktionelle Grenzen der Artikel. Der technische Workflow mit Queue-Modell, Frontmatter-Verarbeitung, Blogger-Upload und Skripten ist im [README.md](README.md) dokumentiert.

Das ursprüngliche Ziel des Workflows bleibt erhalten:

> Aus vorhandenen Projekten, Quelltexten, Konfigurationen, Schaltplänen, README-Dateien und ergänzendem Projektkontext werden automatisch strukturierte technische Dokumentationen erzeugt.

Die erzeugten Texte dürfen sich gut lesen, sollen aber in erster Linie **belastbare Projektdokumentationen** sein.

Sie sind keine frei erzählten Rückblicke, keine Marketingtexte und keine künstlich ausgeschmückten Bloggeschichten.

---

# 1. Grundprinzip

Jeder Artikel beantwortet möglichst klar:

1. Was ist das Projekt?
2. Welches konkrete Problem löst es?
3. Warum wurde es entwickelt?
4. Warum wurde es selbst gebaut, obwohl es grundsätzlich Alternativen gab?
5. Wie ist es technisch aufgebaut?
6. Welche Hardware und Software werden verwendet?
7. Wie wird es gebaut, installiert, konfiguriert oder verwendet?
8. Welche Einschränkungen und Stolpersteine gibt es?
9. Welcher historische oder aktuelle Projektstand ist für Leser relevant?

Der Schwerpunkt liegt auf technischer Nachvollziehbarkeit.

Eine persönliche Einordnung ist erlaubt, wenn sie aus vorhandenen Quellen oder ausdrücklich bereitgestelltem Kontext hervorgeht. Sie darf nicht erfunden werden.

---

# 2. Verbindliche Regeln

## 2.1 Nichts erfinden

Codex darf keine Fakten ergänzen, die nicht aus mindestens einer der folgenden Quellen ableitbar sind:

- Quelltext
- README oder andere Dokumentation
- Konfigurationsdateien
- Commit-Historie
- Schaltpläne
- PCB-Dateien
- Kommentare im Projekt
- Skripte
- Dateinamen und Projektstruktur
- vom Autor bereitgestellte Zusatzinformationen

Nicht zulässig sind erfundene:

- Motive
- Probleme
- Ergebnisse
- Messwerte
- Zeiträume
- Entscheidungen
- Emotionen
- Nutzerzahlen
- Einsparungen
- Leistungsdaten
- Hardwarevarianten
- Projektziele

Wenn etwas nicht sicher feststellbar ist, muss es als unsicher gekennzeichnet oder weggelassen werden.

Beispiele:

> Aus den Projektdateien lässt sich ableiten, dass ...

> Vermutlich war vorgesehen, dass ...

> Der genaue Einsatzzweck ist im Repository nicht dokumentiert.

Keine Unsicherheit darf als Tatsache formuliert werden.

---

## 2.2 Dokumentation vor Erzählung

Der Artikel darf einen lesbaren Einstieg haben, aber er darf nicht zu einer nachträglich erfundenen Heldengeschichte werden.

Bevorzugt:

> USB2SerialMux verbindet über einen ATmega32U4 und zwei Multiplexer bis zu acht serielle Zielgeräte mit einem USB-Anschluss.

Nicht bevorzugt:

> Eines Tages war der Kabelsalat so groß, dass eine radikale Lösung her musste.

Der zweite Satz wäre nur zulässig, wenn diese Aussage ausdrücklich aus dem Projektkontext stammt.

---

## 2.3 Keine künstliche berufliche Selbstdarstellung

Die Artikel dürfen indirekt zeigen, wie der Autor arbeitet. Sie dürfen aber nicht absichtlich für Recruiter oder zur persönlichen Positionierung geschrieben werden.

Zu vermeiden sind Sätze wie:

- Das zeigt meine Stärke als Systemarchitekt.
- Dieses Projekt beweist meine Fähigkeit zur technischen Führung.
- Hier zeigt sich mein ganzheitlicher Engineering-Ansatz.
- Die Lösung demonstriert meine ausgeprägte Problemlösungskompetenz.

Die technische Arbeit soll für sich selbst sprechen.

---

## 2.4 Keine Marketing- oder KI-Sprache

Nicht verwenden:

- innovativ
- revolutionär
- leistungsstark
- zukunftssicher
- nahtlos
- ganzheitlich
- beeindruckend
- einzigartig
- State of the Art
- robuste Lösung

Solche Begriffe sind nur zulässig, wenn sie technisch konkret begründet und notwendig sind.

Ebenfalls vermeiden:

- Zusammenfassend lässt sich sagen
- In der heutigen digitalen Welt
- Dieses spannende Projekt
- Die Möglichkeiten sind nahezu unbegrenzt
- Ein weiterer wichtiger Aspekt
- Es ist erwähnenswert, dass
- Nicht nur ..., sondern auch ...

Der Stil soll natürlich und sachlich wirken.

---

## 2.5 Technische Genauigkeit

Alle technischen Aussagen müssen mit den Projektdateien übereinstimmen.

Besonders prüfen:

- Bauteilbezeichnungen
- Mikrocontroller
- Betriebssysteme
- Schnittstellen
- Pinbelegung
- Protokolle
- Baudraten
- Ports
- Dateipfade
- Build-Kommandos
- Abhängigkeiten
- Container-Images
- Gerätebezeichnungen
- Versionsangaben
- Lizenzinformationen

Bei Widersprüchen zwischen Dateien:

1. Widerspruch nicht still auflösen.
2. Die wahrscheinlich aktuelle Quelle bestimmen.
3. Unsicherheit im Artikel oder in einem Abschnitt „Offene Punkte“ kenntlich machen.

---

# 3. Artikeltypen

Codex soll vor dem Schreiben bestimmen, welcher Artikeltyp vorliegt.

## 3.1 Technische Projektdokumentation

Standardfall.

Geeignet für:

- Softwareprojekte
- Embedded-Projekte
- Hardware
- Platinen
- Automatisierungen
- Smart-Home-Komponenten
- Werkzeuge
- Integrationen
- Reparaturen
- Skripte

Schwerpunkt:

- Problem
- Architektur
- Umsetzung
- Betrieb
- Grenzen
- Projektstand

---

## 3.2 Erfahrungsbericht

Nur verwenden, wenn ausreichend persönlicher Kontext vorhanden ist.

Geeignet für:

- alte Blogentwürfe
- längere Projektrückblicke
- Lernprozesse
- Modellbau
- Reparaturberichte
- Entscheidungen zwischen mehreren Ansätzen

Ein Erfahrungsbericht darf persönlicher sein, muss aber weiterhin auf vorhandenen Inhalten beruhen.

---

## 3.3 Anleitung

Nur erzeugen, wenn das Projekt tatsächlich reproduzierbar dokumentiert ist.

Eine Anleitung benötigt:

- vollständige Voraussetzungen
- nachvollziehbare Schritte
- aktuelle Kommandos
- bekannte Abhängigkeiten
- überprüfbare Konfiguration

Wenn diese Informationen fehlen, keine scheinbar vollständige Anleitung erzeugen.

Stattdessen eine Projektdokumentation schreiben.

---

# 4. Empfohlene Struktur einer Projektdokumentation

Nicht jeder Artikel benötigt jede Überschrift. Die Struktur soll an das Projekt angepasst werden.

```markdown
---
title: "Projektname: kurze verständliche Beschreibung"
labels:
  - Projekt
  - ...
status: review
auto_labels: false
---

# Projektname

Kurze Einordnung in zwei bis vier Absätzen.

## Ausgangslage

Welches Problem oder welcher Bedarf ist dokumentiert?

## Ziel

Was sollte das Projekt erreichen?

## Warum Eigenbau?

Warum wurde eine eigene Lösung gebaut, obwohl es grundsätzlich andere Wege gegeben hätte?

## Aufbau

Wie ist das System technisch strukturiert?

## Hardware

Welche Hardware wird verwendet?

## Software

Welche Software, Bibliotheken, Dienste und Protokolle werden verwendet?

## Funktionsweise

Wie arbeiten die Komponenten zusammen?

## Build und Installation

Nur wenn aus den Dateien zuverlässig ableitbar.

## Konfiguration

Nur relevante Einstellungen beschreiben. Keine Secrets übernehmen.

## Verwendung

Konkrete und überprüfbare Beispiele.

## Stolpersteine

Bekannte Fehler, Einschränkungen und Besonderheiten.

## Projektstand

Nur wenn für Leser relevant: Was ist vorhanden, funktionsfähig, offen, veraltet oder nicht mehr in Verwendung?

## Fazit

Kurze sachliche Einordnung des Projekts.
```

---

# 5. Einstieg eines Artikels

Der Einstieg soll das Projekt sofort verständlich machen.

Er soll in der Regel enthalten:

- Projektname
- Zweck
- konkreter Einsatzbereich
- wichtigste technische Einordnung

Beispiel:

> USB2SerialMux ist eine kleine Hardware- und Firmwarelösung, mit der bis zu acht serielle Zielgeräte über einen einzigen USB-Anschluss erreichbar werden. Ein ATmega32U4 stellt zwei USB-CDC-Schnittstellen bereit und schaltet die UART-Leitungen über zwei Multiplexer auf den ausgewählten Kanal.

Nicht mit allgemeinen Aussagen beginnen.

Schlecht:

> Serielle Schnittstellen spielen in der Embedded-Entwicklung eine wichtige Rolle.

Das ist korrekt, aber austauschbar und unnötig allgemein.

---

# 6. Persönlicher Kontext

Persönlicher Kontext ist willkommen, wenn er vorhanden ist.

Beispiele:

- Warum das Projekt begonnen wurde
- Welches konkrete Problem im eigenen Aufbau bestand
- Warum eine bestehende Lösung nicht gepasst hat
- Warum der Autor sich für einen Eigenbau entschieden hat, obwohl andere Lösungen möglich waren
- Welche Entscheidung sich später als richtig oder falsch erwiesen hat
- Warum das Projekt nicht weitergeführt wurde

Dabei gilt:

- maximal so persönlich wie die Quelle
- keine erfundenen Motive
- keine psychologische Interpretation
- keine nachträgliche Karriereerzählung

Bevorzugt:

> Der konkrete Anlass war ein Orange-Pi-Cluster mit mehreren seriellen Konsolen.

Nicht zulässig ohne Quelle:

> Mich reizte schon immer die Herausforderung, komplexe Systeme auf elegante Weise zu vereinfachen.

---

# 7. Technische Tiefe

Die Artikel sollen genug technische Tiefe haben, um für technisch interessierte Leser nützlich zu sein.

Gleichzeitig sollen sie keine ungefilterte README-Kopie sein.

## Aufnehmen

- Architektur
- relevante Komponenten
- Datenfluss
- wichtige Schnittstellen
- typische Kommandos
- Besonderheiten
- zentrale Designentscheidungen
- bekannte Grenzen

## Kürzen oder weglassen

- jede einzelne Datei des Repositories
- vollständige API-Aufzählungen
- triviale Hilfsfunktionen
- interne Commit-Hashes
- irrelevante Build-Ausgaben
- alte Remotes
- private Infrastruktur
- unkommentierte Konfigurationsblöcke
- Details ohne Bedeutung für das Verständnis

Ein Commit-Hash gehört nur in den Artikel, wenn er für eine konkrete Version oder Fehleranalyse relevant ist.

---

# 8. Umgang mit veralteten Projekten

Alte Projekte dürfen dokumentiert werden.

Codex muss den historischen Kontext jedoch klar kennzeichnen.

Beispiele:

> Das Projekt stammt aus dem Jahr 2016 und verwendet die damals aktuelle LUFA-Version.

> Die beschriebenen X.Org- und Framebuffer-Einstellungen entsprechen dem damaligen Armbian-Stand und sind nicht als aktuelle Installationsanleitung gedacht.

Nicht so tun, als sei ein altes Projekt weiterhin aktuell gepflegt.

Mögliche Statusangaben:

- historisches Projekt
- abgeschlossen
- nicht mehr in Verwendung
- durch eine andere Lösung ersetzt
- weiterhin in Betrieb
- experimenteller Stand
- unvollständig
- nur lokal vorhanden

---

# 9. Umgang mit Projektentwicklung und Nachfolgelösungen

Wenn ein Projekt später ersetzt oder erweitert wurde, darf dies beschrieben werden.

Dabei sachlich bleiben.

Beispiel:

> Das lokale TFT-Display wurde später nicht weiterverwendet, weil der Umfang der verfügbaren Messwerte dafür zu groß geworden war. PowerMgr speichert die Daten inzwischen in InfluxDB und visualisiert sie über mehrere Grafana-Dashboards.

Nicht künstlich zur Architekturlektion aufblasen.

Nicht:

> Dies zeigt, dass gute Architektur bedeutet, Lösungen konsequent an wachsende Anforderungen anzupassen.

Eine solche Einordnung ist nur zulässig, wenn der Autor sie ausdrücklich wünscht.

---

# 10. Frontmatter

Jede Datei benötigt vollständiges YAML-Frontmatter.

Technisch verarbeitet der Auto-Poster laut README nur `title` und `labels` als Pflichtfelder. Die folgenden zusätzlichen Felder sind Codex-Konventionen für neu erzeugte oder grundlegend überarbeitete Artikel.

Standard:

```yaml
---
title: "Titel"
labels:
  - Projekt
  - KI generiert
status: review
auto_labels: false
---
```

## Status

- `review`: Standard für automatisch erzeugte Artikel
- `ready`: nur setzen, wenn dies ausdrücklich angefordert wird
- `ignore`: nicht veröffentlichen

Codex soll automatisch erzeugte Texte grundsätzlich mit `status: review` anlegen.

## Labels

Nur passende Labels verwenden.

Mögliche Kategorien:

- Projekt
- DIY
- Software
- Hardware
- Embedded
- Linux
- Python
- C
- C++
- Docker
- Smart Home
- Energie
- PV
- Aquarium
- Amateurfunk
- 3D-Druck
- Modellbau
- Tabletop
- Reparatur
- Automatisierung
- KI generiert

Keine unnötigen Synonyme als separate Labels ergänzen.

Beispiel:

Nicht gleichzeitig:

- Embedded
- Embedded Systems
- Embedded Linux
- Mikrocontroller

wenn nur eines oder zwei davon tatsächlich relevant sind.

---

# 11. Sprache und Orthografie

Alle Artikel werden in korrektem Deutsch geschrieben.

Verbindlich:

- echte Umlaute verwenden: ä, ö, ü
- ß verwenden, wo orthografisch korrekt
- keine Umschriften wie `ae`, `oe`, `ue`
- keine unnötigen englischen Begriffe
- etablierte technische Fachbegriffe dürfen englisch bleiben
- kurze, vollständige Sätze
- keine übermäßigen Gedankenstriche
- keine künstlich dramatischen Ein-Satz-Absätze

Beispiel:

Schlecht:

> Ein USB-Kabel. Acht Kanäle. Kein Chaos mehr.

Besser:

> Über ein USB-Kabel konnte jeweils einer von acht seriellen Kanälen ausgewählt werden.

---

# 12. Formatierung

## Überschriften

- genau eine H1-Überschrift
- logische H2-Struktur
- H3 nur bei tatsächlichem Bedarf
- keine Überschrift für jeden einzelnen Absatz

## Listen

Listen nur verwenden, wenn sie die Lesbarkeit verbessern.

Geeignet für:

- Hardware
- unterstützte Funktionen
- bekannte Einschränkungen
- Voraussetzungen
- Dashboard-Namen

Nicht jeden Fließtext in Bulletpoints zerlegen.

## Code

Nur überprüfbare Kommandos und Ausschnitte aufnehmen.

Codeblöcke immer mit Sprachkennung versehen:

```sh
python tools/muxctrl.py -d /dev/ttyACM0 -l 3 -m
```

Keine erfundenen Kommandos ergänzen.

---

# 13. Bilder, Videos und Links

Vorhandene Medienpositionen sollen als klare Platzhalter erhalten bleiben.

Beispiele:

```markdown
<!-- Bild: fertige Platine von oben -->
```

```markdown
<!-- Video: Demonstration der Kanalauswahl -->
```

Nicht einfach „(Bild)“ oder „(Video)“ schreiben, wenn sich der Inhalt genauer benennen lässt.

Links nur verwenden, wenn eine öffentliche und belastbare URL vorhanden ist.

GitHub-Links und öffentliche Okoyono-Gitea-Links dürfen veröffentlicht werden.

Keine NAS-, privaten Netzwerk-, Dateisystem- oder nicht öffentlichen Repository-Links veröffentlichen.

Wenn keine öffentliche Quelle vorhanden ist, genügt:

> Das Projekt liegt derzeit nur in meinem lokalen Archiv vor.

Dieser Hinweis ist nur nötig, wenn die Verfügbarkeit für den Artikel relevant ist.

---

# 14. Sicherheitsregeln

Niemals übernehmen:

- Passwörter
- Tokens
- API-Schlüssel
- private Schlüssel
- Cookies
- OAuth-Credentials
- interne Hostnamen
- private IP-Adressen
- WLAN-Zugangsdaten
- personenbezogene Daten
- interne Firmeninformationen
- nicht öffentliche Repository-URLs

Beispielkonfigurationen müssen neutralisiert werden.

Statt:

```yaml
host: 192.168.1.42
token: abc123
```

verwenden:

```yaml
host: <HOSTNAME_ODER_IP>
token: <TOKEN>
```

---

# 15. Qualitätssicherung vor dem Speichern

Vor dem Erzeugen einer Markdown-Datei muss Codex prüfen:

## Inhalt

- Ist der Zweck des Projekts verständlich?
- Ist das konkrete Problem belegt?
- Stimmen Hardware und Software mit den Quellen überein?
- Sind Unsicherheiten sichtbar?
- Wurde nichts erfunden?
- Ist der aktuelle oder historische Status korrekt?
- Gibt es einen belegten Abschnitt dazu, warum das Projekt entstand und warum ein Eigenbau gewählt wurde?

## Stil

- Ist der Text eine Projektdokumentation und keine Werbegeschichte?
- Klingt der Text sachlich und natürlich?
- Gibt es unnötige KI-Floskeln?
- Ist der Einstieg konkret?
- Sind Abschnitte sinnvoll strukturiert?
- Gibt es Wiederholungen?

## Veröffentlichung

- Sind Secrets entfernt?
- Sind interne Links entfernt und nur erlaubte öffentliche GitHub-/Okoyono-Gitea-Links gesetzt?
- Ist `status: review` gesetzt?
- Sind passende Labels vorhanden?
- Sind Umlaute korrekt?
- Sind Bild- und Videopositionen gekennzeichnet?

---

# 16. Vorgehen bei fehlendem Kontext

Wenn der technische Zweck nicht eindeutig aus den Dateien hervorgeht, soll Codex nicht raten.

Stattdessen soll in einer separaten Liste oder im Review-Kommentar eine konkrete Frage formuliert werden.

Beispiele:

- Wofür wurde dieses Projekt ursprünglich eingesetzt?
- Ist das System noch in Betrieb?
- Welche Hardwareversion wurde tatsächlich aufgebaut?
- Wurde das Projekt erfolgreich getestet?
- Gibt es Bilder der fertigen Platine?
- Ist das Repository öffentlich verfügbar?
- Wurde die ursprüngliche Lösung später ersetzt?

Nach Beantwortung dürfen die Informationen in den Artikel übernommen werden.

---

# 17. Abgrenzung zu redaktionellen Artikeln

Neben automatisch erzeugten Projektdokumentationen kann es gesonderte redaktionelle Artikel geben.

Beispiele:

- Warum Modellbau für mich ein Ausgleich zum Beruf ist
- Der Weg ist wichtiger als Perfektion
- Rückblick auf ein über Jahre gewachsenes System

Diese Texte folgen anderen Regeln und müssen ausdrücklich als redaktioneller Artikel beauftragt werden.

Codex darf eine technische Projektdokumentation nicht selbstständig in einen persönlichen Essay umwandeln.

Standardmäßig gilt immer:

> Projekt analysieren, technisch einordnen und nachvollziehbar dokumentieren.

---

# 18. Kurzfassung für Codex

Bei jedem Projekt:

1. Quellen analysieren.
2. Projektzweck und Problem bestimmen.
3. Unsicherheiten markieren.
4. Technische Struktur erklären.
5. Relevante Nutzung dokumentieren.
6. Grenzen und Projektstand nennen.
7. Keine Fakten oder Motive erfinden.
8. Keine Marketing- oder Recruiter-Sprache verwenden.
9. Markdown mit Frontmatter erzeugen.
10. `status: review` setzen.
