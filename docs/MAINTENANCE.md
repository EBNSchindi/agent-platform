# Dokumentations-Wartung & Update-Prozess

**Version:** 1.0.0
**Letzte Aktualisierung:** 2025-11-20
**Verantwortlich:** Daniel Schindler + Claude (AI-Assistant)

---

## 📖 Übersicht

Dieses Dokument beschreibt, wie die drei zentralen Projekt-Dokumente aktuell gehalten werden:

1. **PROJECT_SCOPE.md** - Living Document (häufige Updates)
2. **CLAUDE.md** - Semi-Static (Updates bei Pattern-Änderungen)
3. **docs/VISION.md** - Static (seltene Updates)

---

## 🎯 Dokumenten-Rollen & Verantwortlichkeiten

### PROJECT_SCOPE.md (Root-Level)

**Zweck**: Aktueller Status & Quick Reference für neue Entwickler

**Zielgruppe**:
- Neue Entwickler (Onboarding)
- Stakeholder (Status-Check)
- Team Members (Was funktioniert gerade?)

**Update-Frequenz**: Nach jedem Meilenstein (z.B. nach Complete-Step)

**Verantwortlich**:
- Claude (AI-Assistant) aktualisiert automatisch
- Daniel Schindler (Review & Approve)

**Inhalt**:
- ✅ Executive Summary
- ✅ Aktueller Status (Was ist fertig? Was ist in Arbeit?)
- ✅ Architektur-Übersicht
- ✅ Quick Start Guide
- ✅ Code-Statistik
- ✅ Roadmap
- ✅ Versions-Historie

---

### CLAUDE.md (Root-Level)

**Zweck**: Technische Patterns & Architektur-Prinzipien für AI-Assistenten

**Zielgruppe**:
- Claude Code (Primary User)
- Andere AI-Tools (Copilot, Cursor, etc.)
- Fortgeschrittene Entwickler (Pattern Reference)

**Update-Frequenz**: Bei Pattern-Änderungen oder Breaking Changes

**Verantwortlich**:
- Claude (AI-Assistant) schlägt Updates vor
- Daniel Schindler (Review & Approve)

**Inhalt**:
- ✅ OpenAI Agents SDK Patterns
- ✅ Code-Konventionen
- ✅ Development Commands
- ✅ Common Pitfalls
- ✅ Database Access Patterns
- ✅ Async Execution Patterns

**Update-Trigger**:
- ✅ Neue OpenAI Agents SDK Patterns entdeckt
- ✅ Neue Code-Konvention etabliert
- ✅ Breaking Change in Architektur
- ✅ Neuer häufiger Fallstrick identifiziert
- ✅ Neue Development Commands hinzugefügt

---

### docs/VISION.md (Docs-Folder)

**Zweck**: Big Picture & Langfristige Roadmap (2-Jahres-Plan)

**Zielgruppe**:
- Stakeholder (Strategische Planung)
- Architekten (System Design)
- Investor/Partner (Falls relevant)

**Update-Frequenz**: Selten - nur bei strategischen Änderungen

**Verantwortlich**:
- Daniel Schindler (Owner)
- Claude (AI-Assistant) kann Vorschläge machen

**Inhalt**:
- ✅ Digital Twin Konzept
- ✅ 5-Module-Architektur
- ✅ Event-First Architecture
- ✅ Human-in-the-Loop (HITL) Prinzipien
- ✅ Phase 1-5 Roadmap
- ✅ System-Grundsätze

**Update-Trigger**:
- ⚠️ Vision ändert sich fundamental
- ⚠️ Neue Module geplant
- ⚠️ Phase-Roadmap wird angepasst
- ⚠️ Architektur-Grundsätze ändern sich

---

## 🔄 Update-Prozess (Schritt-für-Schritt)

### Nach jedem Meilenstein (z.B. Complete-Step)

#### Step 1: COMPLETE-Dokument erstellen

**Wann**: Nachdem ein Feature/Step vollständig implementiert ist

**Location**: `docs/phases/PHASE_X_STEP_Y_COMPLETE.md`

**Template**:
```markdown
# Phase X - Step Y: [Feature Name] ✅ COMPLETE

**Status**: ✅ Completed
**Date**: YYYY-MM-DD
**Duration**: X hours/days

## Overview
[Was wurde gebaut?]

## What Was Built
[Detaillierte Beschreibung]

## Technical Challenges & Solutions
[Probleme und Lösungen]

## Test Results
[Test-Ergebnisse]

## Files Created/Modified
[Liste der Dateien]

## Next Steps
[Was kommt als Nächstes?]
```

**Beispiel**: `docs/phases/PHASE_1_STEP_1_COMPLETE.md` (Event-Log System)

---

#### Step 2: PROJECT_SCOPE.md aktualisieren

**Automatisch von Claude nach jedem COMPLETE-Dokument**

**Zu aktualisierende Sektionen**:

1. **Header (Zeile 4-5)**:
   ```markdown
   **Status:** Phase 1 in Entwicklung (Event-Log System ✅ Complete)
   **Letztes Update:** 2025-11-20
   ```

2. **Aktueller Status (Zeile 52-111)**:
   - ✅ Neue Features zu "Was ist fertig" hinzufügen
   - 🚧 "In Arbeit" Sektion aktualisieren
   - Link zum COMPLETE-Dokument hinzufügen

3. **Code-Statistik (Zeile 200-229)**:
   ```markdown
   📁 agent_platform/
      ├── [module]/      ~X Zeilen (Description)
      TOTAL: ~X Zeilen Production Code

   📁 tests/
      TEST COVERAGE: X/X Tests passing (100%) ✅
   ```

4. **Roadmap (Zeile 233-246)**:
   - ✅ Completed Steps markieren
   - 🚧 Current Step aktualisieren
   - Status-Prozent aktualisieren

5. **Definition of Done (Zeile 267-278)**:
   - ✅ Erfüllte Kriterien markieren
   - Progress-Prozent aktualisieren

6. **Versions-Historie (Zeile 306-312)**:
   ```markdown
   | Version | Datum | Meilenstein |
   |---------|-------|-------------|
   | X.Y.Z | 2025-MM-DD | [Feature] Complete |
   ```

**Versioning-Schema**:
- **Major (X.0.0)**: Neue Phase komplett
- **Minor (1.X.0)**: Neuer Step innerhalb Phase
- **Patch (1.0.X)**: Bugfixes, kleine Verbesserungen

**Beispiel**:
- `2.0.0`: Event-Log System Complete (großes neues Feature)
- `2.1.0`: Email Extraction Complete (nächster Step)
- `2.1.1`: Bugfix in Event-Log System

---

#### Step 3: CLAUDE.md prüfen & ggf. aktualisieren

**Prüfung**: Hat sich etwas an Patterns/Architektur geändert?

**Checkliste**:
- [ ] Neue Development Commands hinzugefügt?
- [ ] Neue Code-Konventionen etabliert?
- [ ] Neuer Common Pitfall entdeckt?
- [ ] Breaking Change in Architektur?
- [ ] Neue Database Access Patterns?
- [ ] Neue Async Execution Patterns?

**Wenn JA → CLAUDE.md aktualisieren**:

**Zu aktualisierende Sektionen**:

1. **Common Development Commands**:
   ```markdown
   ### Testing [New Module]

   ```bash
   # Test [feature]
   python tests/[module]/test_[feature].py
   ```
   ```

2. **Critical Implementation Details**:
   ```markdown
   ### [New Pattern Name]

   [Description]

   ```python
   # Example code
   ```
   ```

3. **Common Pitfalls**:
   ```markdown
   X. **[New Pitfall]**: [Description]
   ```

**Wenn NEIN → Überspringen**

---

#### Step 4: docs/VISION.md prüfen

**Prüfung**: Hat sich die langfristige Vision geändert?

**Checkliste**:
- [ ] Neue Module in Roadmap?
- [ ] Phase-Timing angepasst?
- [ ] Architektur-Grundsätze geändert?
- [ ] Neue System-Grundsätze?

**Normalerweise**: KEINE Änderung nötig (Vision ist stabil)

**Nur bei strategischen Änderungen** → Vision aktualisieren

---

## 📋 Checkliste für Updates

### Nach jedem Complete-Step

```markdown
- [ ] COMPLETE-Dokument erstellt (docs/phases/PHASE_X_STEP_Y_COMPLETE.md)
- [ ] PROJECT_SCOPE.md aktualisiert:
  - [ ] Status & Letzte Aktualisierung
  - [ ] "Was ist fertig" Sektion
  - [ ] Code-Statistik
  - [ ] Roadmap & Progress
  - [ ] Definition of Done
  - [ ] Versions-Historie
- [ ] CLAUDE.md geprüft & ggf. aktualisiert
- [ ] VISION.md geprüft (normalerweise keine Änderung)
- [ ] Pull Request erstellt mit allen Änderungen
- [ ] Commit-Message folgt Schema (siehe unten)
```

---

## 🎯 Commit-Message Schema

### Format

```
Docs: [Type] - [Short Description]

[Detailed Description]

Updated Files:
- PROJECT_SCOPE.md (Status, Code Stats, Roadmap)
- docs/phases/PHASE_X_STEP_Y_COMPLETE.md (New)
- [optional] CLAUDE.md (Patterns/Commands)

Progress: [X/Y Steps Complete] ([Percentage]%)
```

### Types

- **Milestone**: Großer Meilenstein (z.B. Phase Complete, Step Complete)
- **Update**: Regelmäßiges Update (Status, Stats)
- **Pattern**: Neue Patterns/Conventions in CLAUDE.md
- **Vision**: Vision/Roadmap Änderung

### Beispiele

```
Docs: Milestone - Event-Log System Complete (Phase 1 Step 1)

Completed Event-Log System as foundation for Digital Twin Platform.
All events now logged as immutable records with comprehensive test coverage.

Updated Files:
- PROJECT_SCOPE.md (Status: 2/5 Steps Complete, Code Stats, Version 2.0.0)
- docs/phases/PHASE_1_STEP_1_COMPLETE.md (New - Full documentation)

Progress: 2/5 Steps Complete (40%)
Test Coverage: 10/10 Tests Passing (100%)
```

```
Docs: Update - Code Stats & Progress after Email Extraction

Updated PROJECT_SCOPE.md with latest code statistics and progress metrics.

Updated Files:
- PROJECT_SCOPE.md (Code Stats, Progress: 3/5 Steps)

Progress: 3/5 Steps Complete (60%)
```

```
Docs: Pattern - New Event-Logging Pattern in CLAUDE.md

Added Event-Log integration pattern to CLAUDE.md for all future feature development.

Updated Files:
- CLAUDE.md (New section: Event-Logging Pattern)
- PROJECT_SCOPE.md (Minor update to reference CLAUDE.md)
```

---

## 🔍 Review-Prozess

### Self-Review Checkliste (vor PR)

```markdown
- [ ] Alle Links funktionieren (PROJECT_SCOPE → VISION, CLAUDE, COMPLETE docs)
- [ ] Versions-Historie ist korrekt
- [ ] Datums-Angaben sind aktuell
- [ ] Code-Statistik ist korrekt (Zeilen-Count, Test-Count)
- [ ] Status-Checkboxen sind konsistent (✅/🚧/❌)
- [ ] Prozent-Angaben sind korrekt berechnet
- [ ] Keine Tippfehler in wichtigen Sektionen
- [ ] Markdown-Formatierung ist korrekt
```

### Cross-Reference Check

```markdown
- [ ] PROJECT_SCOPE.md verweist auf VISION.md
- [ ] PROJECT_SCOPE.md verweist auf CLAUDE.md
- [ ] PROJECT_SCOPE.md verweist auf COMPLETE-Dokumente
- [ ] COMPLETE-Dokument verweist auf PROJECT_SCOPE.md
- [ ] Keine toten Links
```

---

## 🤖 Automatisierungs-Potenzial (Future)

### Aktuell: Manuelle Updates von Claude

Claude führt Updates nach jedem Meilenstein durch (siehe Prozess oben).

### Zukünftig: Automatisierung

**Mögliche Automatisierungen**:

1. **Code-Statistik**:
   ```bash
   # Script: scripts/update_code_stats.py
   # Zählt automatisch Zeilen, Tests, etc.
   # Aktualisiert PROJECT_SCOPE.md
   ```

2. **Test Coverage**:
   ```bash
   # Script: scripts/update_test_coverage.py
   # Läuft alle Tests
   # Aktualisiert PROJECT_SCOPE.md mit Ergebnissen
   ```

3. **Version Bumping**:
   ```bash
   # Script: scripts/bump_version.py [major|minor|patch]
   # Aktualisiert Version in PROJECT_SCOPE.md
   # Erstellt Git-Tag
   ```

4. **COMPLETE-Dokument Template**:
   ```bash
   # Script: scripts/create_complete_doc.py [phase] [step] [name]
   # Erstellt COMPLETE-Dokument aus Template
   # Füllt automatisch Datum, Phase, Step
   ```

**Noch nicht implementiert** - aber gute Kandidaten für Automation!

---

## 📊 Qualitäts-Metriken

### Dokumentations-Qualität

**Metriken**:
- ✅ Alle Links funktionieren
- ✅ Datums-Angaben < 7 Tage alt (bei aktiver Entwicklung)
- ✅ Code-Statistik stimmt mit tatsächlichem Code überein
- ✅ Test-Coverage-Angaben sind korrekt
- ✅ Keine Tippfehler in Headlines

**Ziel**: 100% Korrektheit bei jedem Update

### Update-Frequenz

**Ziel-Frequenz**:
- **PROJECT_SCOPE.md**: Nach jedem Meilenstein (~1x pro Woche bei aktiver Entwicklung)
- **CLAUDE.md**: Bei Pattern-Änderungen (~1x pro Monat)
- **VISION.md**: Bei strategischen Änderungen (~1x pro Quartal)

---

## 🔗 Quick Links

- **PROJECT_SCOPE.md**: [../PROJECT_SCOPE.md](../PROJECT_SCOPE.md)
- **CLAUDE.md**: [../CLAUDE.md](../CLAUDE.md)
- **VISION.md**: [VISION.md](VISION.md)
- **Phase Documentation**: [phases/](phases/)

---

## 📝 Change Log (dieses Dokument)

| Version | Datum | Änderung |
|---------|-------|----------|
| 1.0.0 | 2025-11-20 | Initial Version - Dokumentations-Wartungs-Prozess definiert |

---

**Nächstes Review**: Nach Phase 1 Complete
**Verantwortlich**: Daniel Schindler + Claude
