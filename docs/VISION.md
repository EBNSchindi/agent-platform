# Digital Twin Plattform - Vision & Big Picture

**Ein lernendes, persönliches System zur Verarbeitung, Analyse und Unterstützung**

---

## 🎯 Projektziel

Ich baue ein langfristiges System, das einen **persönlichen Digital Twin** entwickelt.

Der Digital Twin soll:
- ✅ Eingehende Informationen verarbeiten
- ✅ Mich, meine Prioritäten und meine Arbeitsweise immer besser verstehen
- ✅ Muster in meinen Entscheidungen, meiner Kommunikation und meinem Verhalten erkennen
- ✅ Ein wachsendes Gedächtnis entwickeln
- ✅ Mich bei Aufgaben, Reflexion und Organisation unterstützen
- ✅ Über eine Oberfläche mit mir interagieren können

**Das System soll nicht statisch, sondern lebendig, lernend und inkrementell wachsend sein.**

Ich arbeite **MIT** dem System, nicht nur "gegen" oder "über" das System.

---

## 🏗️ Die 5 zentralen Systemmodule

Der Digital Twin besteht langfristig aus **fünf logisch getrennten, aber miteinander verknüpften Modulen**:

### 1. Input Hub
**Die Eingangsschicht, die alle Datenkanäle sammelt.**

**Langfristige Kanäle:**
- E-Mail
- Sprache (Voice Notes)
- Notizen (Markdown, Notion, etc.)
- Kalender
- Messenger (WhatsApp, Telegram, etc.)
- Dokumente (PDFs, Word, etc.)
- Screenshots
- Browser History
- Git Commits

**Aktuell in Phase 1:**
- ✅ **Nur E-Mails** (Gmail + IMAP/Ionos)

---

### 2. Analysis Engine
**Alle Analysefunktionen und Agents.**

**Langfristige Funktionen:**
- Themen-Erkennung
- Intent-Erkennung (Was will der Sender?)
- Task-Extraktion
- Personen-Analyse (Beziehungen, Kommunikationsstil)
- Entscheidungs-Erkennung
- Muster-Erkennung (über Zeit)
- Prioritäts-Ableitung

**Aktuell in Phase 1:**
- ✅ **E-Mail-Klassifikation** (Rule → History → LLM)
- 🔄 **Zusammenfassung** (in Planung)
- 🔄 **Extraktion** (Tasks, Decisions, Questions - in Planung)

---

### 3. Memory System
**Das Gedächtnis des Digital Twins, bestehend aus zwei Schichten:**

#### 🔹 Event-Log (History Layer)
Alle Aktionen werden als **Events** gespeichert:
- `EMAIL_ANALYZED`
- `TASK_EXTRACTED`
- `USER_FEEDBACK`
- `DECISION_MADE`
- `JOURNAL_GENERATED`

**Prinzipien:**
- Events sind **unveränderlich** (Append-Only)
- Vollständige **historische Nachvollziehbarkeit**
- Basis für Learning & Feedback

#### 🔹 Memory-Objects (Knowledge Layer)
Abgeleitete Wissensobjekte:
- `Tasks` (offene Aufgaben)
- `Decisions` (zu treffende Entscheidungen)
- `Questions` (offene Fragen)
- `JournalEntries` (Tagesjournale)
- `People` (Personen & Beziehungen)
- `Topics` (erkannte Themen)
- `Patterns` (Verhaltens-Muster)

**Prinzipien:**
- Memory Objects bilden den **aktuellen Wissensstand**
- Werden **aus Events abgeleitet**
- Können **korrigiert/aktualisiert** werden
- Korrekturen erzeugen **neue Events**

**Aktuell in Phase 1:**
- ✅ `ProcessedEmail` (Email-Verarbeitungsstatus)
- ✅ `SenderPreference` (Sender-Verhalten mit EMA Learning)
- ✅ `DomainPreference` (Domain-Verhalten)
- 🔄 `Event` (Event-Log System - in Planung)
- 🔄 `Task`, `Decision`, `Question`, `JournalEntry` (in Planung)

---

### 4. Twin Core
**Das funktionale Selbstmodell des Digital Twins.**

**Langfristige Fähigkeiten:**
- Kommunikationsstil adaptieren (formal ↔ casual)
- Priorisierungen erkennen (was ist mir wichtig?)
- Entscheidungen vorbereiten (nicht treffen!)
- Muster ableiten (Gewohnheiten, Präferenzen)
- Dialog führen (natürliche Konversation)
- Aufgaben ableiten (aus Kontext)
- Empfehlungen geben (basierend auf Verhalten)
- Reflexion unterstützen (Journaling, Review)

**Aktuell in Phase 1:**
- ❌ **Noch NICHT implementiert**
- ✅ **Vorbereitet** durch Events + Memory
- ✅ **Erste Ansätze** in EMA Learning (SenderPreference)

---

### 5. Twin Interface
**Die spätere Oberfläche zur Interaktion mit dem Twin.**

**Langfristige Features:**
- Chat mit dem Twin (natürliche Konversation)
- Tages-/Wochenjournale (automatisch generiert)
- Agenten-Status (was läuft gerade?)
- Memory-/Knowledge-Graph (Visualisierung)
- Twin-Growth-Log (wie entwickelt sich der Twin?)
- Feedback-Interface (Korrekturen, Bestätigungen)
- Task/Decision/Question Management
- Pattern-Insights (erkannte Muster zeigen)

**Aktuell in Phase 1:**
- ❌ **Noch kein volles UI**
- ✅ **Einfache Debug-Sichten** (Logs, Database)
- 🔄 **Tagesjournal-Export** (Markdown - in Planung)

---

## 🤝 Human-in-the-Loop (HITL) - Systemgrundsatz

**Das System arbeitet kollaborativ mit mir.**

Ich bin nicht passiver Nutzer, sondern **aktiver Partner** des Twins.

### Die HITL-Regeln

#### 1. Keine endgültigen Entscheidungen ohne Möglichkeit des Eingriffs
- Das System darf in **klaren, risikoarmen Fällen** selbstständig handeln
  (z.B. Klassifikationen, Gruppierungen, Aufgabenableitungen)
- Ich muss diese Aktionen **nachvollziehen** können
- Ich kann jederzeit **korrigieren**

#### 2. Das System lernt aus meiner Interaktion
- **Bestätigungen** stärken das Modell
- **Korrekturen** erzeugen Lernevents
- **Feedback** fließt in das Twin Core ein

#### 3. Alle wichtigen autonomen Aktionen werden kommuniziert
- Ich bleibe jederzeit **im Bilde**, was das System tut
- Transparenz über alle automatischen Entscheidungen
- Review-Mechanismen für kritische Aktionen

**HITL ist ein fortlaufender Prozess, kein optionales Feature.**

---

## 📍 Aktueller Entwicklungsstand - Phase 1 (MVP)

**Wir starten nicht mit dem Twin.**
**Wir starten mit E-Mail Intake + Analyse + Tagesjournal.**

Alles andere (Twin Core, UI, Graph, weitere Quellen) kommt später.

### Phase-1-Ziele

✅ **Bereits implementiert:**
- E-Mails einlesen (Gmail + IMAP/Ionos)
- E-Mail-Klassifikation (3-Layer: Rule → History → LLM)
- Sender/Domain-Präferenzen mit EMA Learning (α=0.15)
- Review System (Daily Digest, Feedback Tracking)
- Scheduled Jobs (APScheduler)

🔄 **In Planung für Phase 1:**
- Event-Log System (alle Aktionen als Events)
- E-Mail-Analyse erweitern:
  - Zusammenfassung
  - Task-Extraktion
  - Decision-Extraktion
  - Question-Extraktion
- Memory-Objects erstellen (Tasks, Decisions, Questions, JournalEntries)
- Tagesjournal generieren (aus Events + Memory-Objects)
- HITL vorbereiten (Feedback-Interface, Korrekturen)

### Nicht Teil von Phase 1

❌ Keine echte UI (nur Debug-Views)
❌ Kein volles Twin Core (nur Vorbereitung)
❌ Keine Musteranalyse (kommt Phase 2+)
❌ Keine KI-Persönlichkeit (kommt Phase 3+)
❌ Kein Knowledge Graph (kommt Phase 3+)
❌ Keine Automationen außerhalb klarer Fälle
❌ Keine weiteren Input-Kanäle (nur E-Mail)

---

## 🗺️ Langfristige Roadmap

### Phase 1: E-Mail Intake + Analyse + Tagesjournal (AKTUELL)
- ✅ E-Mail-Klassifikation
- 🔄 Event-Log System
- 🔄 Task/Decision/Question-Extraktion
- 🔄 Tagesjournal-Generierung
- 🔄 HITL Feedback-Loops

**Dauer:** 2-3 Monate
**Status:** In Entwicklung (Week 1 abgeschlossen)

---

### Phase 2: Musteranalyse + Personen + Themen
- Personen-Analyse (Beziehungen, Kommunikationsstil)
- Themen-Erkennung (wiederkehrende Topics)
- Muster-Erkennung (Gewohnheiten über Zeit)
- Erweiterte Memory-Objects (People, Topics, Patterns)
- Wochenjournal (Zusammenfassung der Woche)

**Dauer:** 2-3 Monate
**Start:** Nach Phase 1 MVP

---

### Phase 3: Twin Core + Dialog + Reflexion
- Twin Core Grundlagen (Präferenz-Modell)
- Chat-Interface (natürliche Konversation)
- Reflexions-Unterstützung (Journaling, Review)
- Empfehlungen (basierend auf Mustern)
- Knowledge Graph (Visualisierung)

**Dauer:** 3-4 Monate
**Start:** Nach Phase 2

---

### Phase 4: Multi-Input + Automationen
- Weitere Input-Kanäle (Kalender, Notizen, Sprache)
- Cross-Channel-Analysen (E-Mail + Kalender + Notizen)
- Intelligente Automationen (mit HITL)
- Proaktive Vorschläge

**Dauer:** 4-6 Monate
**Start:** Nach Phase 3

---

### Phase 5: Twin Maturity + Full Interface
- Volles Twin-UI (Chat, Graph, Insights)
- Adaptive Kommunikation
- Langfristige Lernmodelle
- Twin-Growth-Tracking
- Export/Backup/Portabilität

**Dauer:** 6+ Monate
**Start:** Nach Phase 4

---

## 🎯 Systemgrundsätze

### 1. Event-First Architecture
**Alle Aktionen → Events**
- Vollständige Historie
- Nachvollziehbarkeit
- Learning-Basis

### 2. Memory-Objects sind abgeleitet
**Keine Überschreibung der Historie**
- Events sind unveränderlich
- Memory-Objects können korrigiert werden
- Korrekturen erzeugen neue Events

### 3. Human-in-the-Loop ist Pflicht
**Kollaboratives System**
- Keine autonomen Entscheidungen ohne Review-Möglichkeit
- Feedback fließt zurück ins System
- Transparenz über alle Aktionen

### 4. Modulare Architektur
**Logische Trennung, lose Kopplung**
- Jedes Modul hat klare Verantwortung
- Module kommunizieren über Events
- Einfach erweiterbar

### 5. Pragmatisches MVP-Denken
**Kein Overengineering**
- Phase-für-Phase Entwicklung
- Nur implementieren, was jetzt gebraucht wird
- Architektur so wählen, dass Erweiterung möglich ist

### 6. Lernendes System
**Continuous Improvement**
- System wird mit jeder Interaktion besser
- Feedback-Loops in allen Modulen
- Metriken für Growth-Tracking

---

## 📊 Erfolgs-Metriken

### Phase 1
- [ ] 90%+ der E-Mails werden korrekt klassifiziert
- [ ] Tasks/Decisions/Questions werden präzise extrahiert
- [ ] Tagesjournal wird täglich generiert
- [ ] HITL-Feedback wird erfasst und verarbeitet
- [ ] System läuft stabil im Produktionsbetrieb

### Langfristig (Phase 2-5)
- [ ] Twin erkennt 80%+ meiner Prioritäten korrekt
- [ ] Muster-Erkennung identifiziert wiederkehrende Verhalten
- [ ] Dialog mit Twin fühlt sich natürlich an
- [ ] System spart mir 10+ Stunden/Woche
- [ ] Twin "versteht" meine Arbeitsweise

---

## 🤖 Anforderungen an Coding Assistants

Coding Assistants (wie Claude Code) sollen:

✅ **Nur innerhalb der aktuellen Phase entwickeln**
(Auch wenn das Big Picture größer ist.)

✅ **Modular entwickeln**
Input-Modul, Analyse-Modul, Event-Modul, Memory-Modul, Journal-Modul.

✅ **Event-first entwickeln**
Alle Aktionen → Events.

✅ **Memory-Objects nur als abgeleitete Strukturen verwenden**
Kein Überschreiben der Historie.

✅ **Human-in-the-loop berücksichtigen**
Analysen sind Vorschläge, später einfach zu korrigieren, Feedback-Einbindung vorbereiten.

✅ **Keine Overengineering-Strukturen aufbauen**
Pragmatisch, MVP-tauglich.

✅ **Architektur so wählen, dass Phase 2 und 3 darauf aufbauen können**
Aber jetzt noch nicht umsetzen.

---

**Built with:**
- Python 3.10+
- OpenAI Agents SDK
- SQLAlchemy + SQLite
- Pydantic (Structured Outputs)
- APScheduler

**Powered by:**
- Vision & Incremental Growth
- Human-in-the-Loop Collaboration
- Event-First Architecture
