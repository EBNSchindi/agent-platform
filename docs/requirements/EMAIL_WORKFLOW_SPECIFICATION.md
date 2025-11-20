# E-Mail Workflow & Datenhaltung - Spezifikation

**Version:** 1.0.0
**Datum:** 2025-11-20
**Status:** Finalisiert - Ready for Implementation
**Autor:** Daniel Schindler

---

## 📋 Executive Summary

Der Digital Twin verarbeitet E-Mails mit **gestaffelter Datenhaltung** nach Relevanz, organisiert Gmail automatisch und bietet ein interaktives Web-GUI für Review, Feedback und Journal.

**Kernprinzip:** "Intelligente Datenhaltung nach Relevanz"

```
Relevant  (wichtig, action_required)     → Vollständige Daten (Body + Summary + Attachments)
Mittel    (nice_to_know)                 → Zusammenfassung
Irrelevant (newsletter, spam, unwichtig) → Nur Metadaten
```

---

## 🎯 Funktionale Anforderungen

### 1. Datenhaltungs-Strategie

#### 1.1 Storage Level Definition

**Kategorie 1: Relevante E-Mails (storage_level = 'full')**
- **Kategorien:** `wichtig`, `action_required`
- **Speichern:**
  - ✅ Vollständiger E-Mail-Body (Text + HTML)
  - ✅ LLM-generierte Zusammenfassung (2-3 Sätze)
  - ✅ Metadaten (Sender, Subject, Received_At, Email_ID)
  - ✅ Klassifikation (Category, Importance, Confidence)
  - ✅ Extrahierte Memory-Objects (Tasks, Decisions, Questions)
  - ✅ Events (EMAIL_RECEIVED, EMAIL_CLASSIFIED, EMAIL_ANALYZED, TASK_EXTRACTED, etc.)
  - ✅ Anhänge (siehe Abschnitt 3)

**Kategorie 2: Informative E-Mails (storage_level = 'summary')**
- **Kategorien:** `nice_to_know`
- **Speichern:**
  - ✅ LLM-generierte Zusammenfassung (1-2 Sätze)
  - ✅ Metadaten
  - ✅ Klassifikation
  - ❌ KEIN Body (Link zur Gmail-Mail bleibt)
  - ❌ KEINE Anhänge (nur Metadaten: Dateiname, Größe)

**Kategorie 3: Unwichtige E-Mails (storage_level = 'minimal')**
- **Kategorien:** `newsletter`, `spam`, `unwichtig`
- **Speichern:**
  - ✅ Metadaten (minimal: Sender, Subject, Received_At, Category)
  - ✅ Klassifikation (Confidence)
  - ❌ KEIN Body
  - ❌ KEINE Zusammenfassung
  - ❌ KEINE Extractions

#### 1.2 Storage Level Logic

```python
def determine_storage_level(category: str, confidence: float) -> str:
    """
    Bestimme Storage Level basierend auf Kategorie

    Returns:
        'full'    - Volle Daten (Body + Summary + Attachments + Extractions)
        'summary' - Zusammenfassung only
        'minimal' - Nur Metadaten
    """
    if category in ['wichtig', 'action_required']:
        return 'full'
    elif category in ['nice_to_know']:
        return 'summary'
    else:  # newsletter, spam, unwichtig
        return 'minimal'
```

---

### 2. Gmail-Automation

#### 2.1 Label-Strategie

**Confidence-basierte Automation:**
- **High Confidence (≥ 0.90):** Automatisches Labeln + Optional Archive
- **Medium Confidence (0.65-0.90):** Review Queue
- **Low Confidence (< 0.65):** Review Queue + Manual Flag

**Label-Mapping:**
```python
LABEL_MAP = {
    'wichtig': '🔴 Wichtig',
    'action_required': '⚡ Action Required',
    'nice_to_know': '📘 Nice to Know',
    'newsletter': '📰 Newsletter',
    'spam': '🗑️ Spam',
    'unwichtig': '📭 Unwichtig'
}
```

#### 2.2 Auto-Archive Logic

```python
def should_auto_archive(category: str, confidence: float) -> bool:
    """
    Auto-archive für unwichtige E-Mails bei High Confidence
    """
    return (
        category in ['newsletter', 'spam', 'unwichtig'] and
        confidence >= 0.90
    )
```

**Verhalten:**
- `newsletter`, `spam`, `unwichtig` + High Confidence → Archivieren (aus Inbox entfernen)
- `wichtig`, `action_required` → In Inbox behalten
- `nice_to_know` → In Inbox behalten (optional: User-konfigurierbar)

#### 2.3 Read/Unread Management

- `wichtig`, `action_required` → Als **ungelesen** lassen
- Alle anderen → Als **gelesen** markieren

---

### 3. Anhang-Handling

#### 3.1 Priorisierung

**E-Mails mit Anhängen haben höheren Stellenwert:**
- Confidence-Boost: +0.05 bis +0.10 (wenn Anhang relevant erscheint)
- Nie automatisch als `spam` klassifizieren, wenn Anhang vorhanden

#### 3.2 Speicherung

**Verzeichnisstruktur:**
```
attachments/
├── gmail_1/
│   ├── msg_abc123/
│   │   ├── invoice_q4.pdf
│   │   └── budget_report.xlsx
│   └── msg_def456/
│       └── presentation.pptx
├── gmail_2/
│   └── msg_xyz789/
│       └── contract.pdf
└── ionos/
    └── msg_uvw012/
        └── image.jpg
```

**Datei-Pfad:** `attachments/{account_id}/{email_id}/{original_filename}`

**Speicher-Regeln:**
- **storage_level = 'full':** Alle Anhänge herunterladen
- **storage_level = 'summary':** Nur Metadaten speichern (Dateiname, Größe, MIME-Type)
- **storage_level = 'minimal':** Keine Anhänge

**Unterstützte Formate:**
- Dokumente: PDF, DOCX, XLSX, PPTX, TXT
- Bilder: JPG, PNG, GIF, SVG
- Archive: ZIP, RAR (Metadaten only, kein Extract)
- Andere: Als Binary speichern

**Größenlimit:**
- Max. 25MB pro Anhang
- Größere Anhänge: Nur Metadaten + Warning im Journal

#### 3.3 Anhang-Analyse (Optional, keine Priorität)

**Phase 2+ Features:**
- PDF: Text-Extraktion
- DOCX: Text-Extraktion
- Bilder: OCR (Texterkennung)
- XLSX: Tabellen-Struktur-Erkennung

**Aktuell:** Nur Download & Speicherung

---

### 4. Thread-Handling

#### 4.1 Thread-Kontext-Erstellung

**Bei E-Mail in Thread:**
1. Thread-History abrufen (letzte 10 E-Mails max.)
2. Bei mehr als 10: Relevante E-Mails auswählen (LLM-basiert)
3. Thread-Zusammenfassung erstellen
4. Aktuelle E-Mail in Kontext setzen

**Thread-Zusammenfassung Format:**
```markdown
## Thread-Kontext
**Thread-ID:** thread_abc123
**Teilnehmer:** Daniel, Boss, Team (3 Personen)
**E-Mails:** 7 (über 3 Tage)

**Zusammenfassung:**
Diskussion über Q4 Budget-Erhöhung. Boss hat Bedenken bezüglich
Marketing-Budget (+15%), Team argumentiert mit ROI-Prognosen.
Aktuell: Boss bittet um finale Zahlen bis Freitag.

**Aktuelle E-Mail:**
Boss fragt nach detaillierter Budget-Aufschlüsselung für Marketing.
```

#### 4.2 Thread-Relevanz-Auswahl

**Bei > 10 E-Mails im Thread:**
- LLM entscheidet, welche E-Mails relevant für Kontext
- Kriterien:
  - Enthält Entscheidungen?
  - Enthält wichtige Informationen?
  - Ändert Kontext signifikant?
- Rest: Nur in Metadaten verlinkt

---

### 5. Review Queue (Web-GUI)

#### 5.1 Trigger

E-Mails landen in Review Queue wenn:
- **Medium Confidence:** 0.65 ≤ confidence < 0.90
- **Low Confidence:** confidence < 0.65
- **Disagreement:** Layers klassifizieren unterschiedlich (Ensemble)

#### 5.2 Interface-Anforderungen

**Review Queue Dashboard:**
```
┌─────────────────────────────────────────────────┐
│ Review Queue - 7 E-Mails warten auf Review      │
├─────────────────────────────────────────────────┤
│                                                  │
│ [1] team@company.com                            │
│     Subject: "Team Update Q4"                   │
│     Received: 20.11.2025 14:32                  │
│                                                  │
│     Zusammenfassung:                            │
│     Team-Update über Q4-Fortschritt, keine      │
│     direkten Action Items, aber relevante Infos │
│                                                  │
│     Vorschlag: nice_to_know (Confidence: 75%)   │
│     Grund: History Layer sagt "nice_to_know",   │
│            LLM Layer sagt "wichtig"             │
│                                                  │
│     [✅ Approve] [✏️ Change to: wichtig ▼]      │
│     [🔗 Open in Gmail] [⏭️ Skip]                │
│                                                  │
├─────────────────────────────────────────────────┤
│ [2] ...                                         │
└─────────────────────────────────────────────────┘
```

**Pflicht-Elemente:**
- ✅ Absender (prominent)
- ✅ Betreff
- ✅ Timestamp
- ✅ Zusammenfassung (1-3 Sätze)
- ✅ Vorgeschlagene Kategorie + Confidence
- ✅ Grund für Review (Layer-Disagreement, Low Confidence, etc.)
- ✅ Action-Buttons
  - Approve (akzeptiert Vorschlag)
  - Change (Dropdown: andere Kategorie)
  - Open in Gmail (Link)
  - Skip (später entscheiden)

#### 5.3 Feedback-Loop

**Bei User-Action:**
1. **Feedback Event erstellen:**
   ```python
   log_event(
       event_type=EventType.USER_CORRECTION,
       account_id=account_id,
       email_id=email_id,
       payload={
           'original_category': 'nice_to_know',
           'corrected_category': 'wichtig',
           'original_confidence': 0.75,
           'correction_reason': 'user_review_queue'
       }
   )
   ```

2. **Sender-Präferenz aktualisieren (EMA Learning):**
   ```python
   # Adjust sender preference based on correction
   feedback_tracker.track_correction(
       email_id=email_id,
       sender_email=sender,
       corrected_category='wichtig',
       corrected_importance=0.85
   )
   ```

3. **ProcessedEmail aktualisieren:**
   ```python
   processed_email.category = 'wichtig'
   processed_email.classification_confidence = 1.0  # User override
   processed_email.user_corrected = True
   ```

4. **Gmail-Label aktualisieren:**
   ```python
   gmail_service.apply_label(email_id, '🔴 Wichtig')
   ```

---

### 6. History Scan (Rückwirkende Verarbeitung)

#### 6.1 Konfigurierbare Intervalle

**User kann wählen:**
- Letzte X Tage/Wochen/Monate
- Spezifischer Zeitraum (von-bis)
- Bestimmte Labels/Ordner

**Beispiele:**
```python
# Letzte 3 Monate
scan_history(account_id='gmail_1', days=90)

# Spezifischer Zeitraum
scan_history(
    account_id='gmail_1',
    start_date='2024-01-01',
    end_date='2024-03-31'
)

# Nur INBOX (keine Archive)
scan_history(account_id='gmail_1', labels=['INBOX'], days=180)
```

#### 6.2 History Scan Workflow

**Schritte:**
1. **Fetch E-Mails** (Gmail API, gestaffelt nach Zeitraum)
2. **Klassifizieren** (Batch-Processing, parallel)
3. **Storage Level bestimmen**
4. **Conditional:**
   - storage_level='full': Body speichern + Summarize + Extract
   - storage_level='summary': Summarize only
   - storage_level='minimal': Metadaten only
5. **Gmail-Labels setzen** (bei High Confidence)
6. **Archivieren** (bei unwichtig + High Confidence)
7. **Statistik generieren**

**Output:**
```
History Scan Complete - gmail_1 (01.01.2024 - 31.03.2024)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total E-Mails: 1,247
Classified: 1,247 (100%)

By Category:
  🔴 Wichtig:          87 (7.0%)
  ⚡ Action Required:  45 (3.6%)
  📘 Nice to Know:    312 (25.0%)
  📰 Newsletter:      678 (54.4%)
  🗑️ Spam/Unwichtig: 125 (10.0%)

Storage Levels:
  Full:    132 (10.6%) - 245 MB
  Summary: 312 (25.0%) - 12 MB
  Minimal: 803 (64.4%) - 3 MB

Gmail Actions:
  Labels Set:    1,189 (95.3%)
  Archived:        803 (64.4%)
  Review Queue:     58 (4.7%)

Processing Time: 18m 32s
```

---

### 7. Journal (Web-GUI)

#### 7.1 Format & Inhalt

**Journal-Typ:** Tagesjournal (Daily)

**Anzeige-Zeiten:**
- **Abends (20:00 Uhr):** Heutiges Journal generieren & anzeigen
- **Morgens (08:00 Uhr):** Gestriges Journal anzeigen

**Struktur:**

```markdown
# Tagesjournal - 20. November 2025

## 🤖 Agent-Aktivitäten

### E-Mail Modul
- **Verarbeitet:** 45 E-Mails
  - 32 auto-klassifiziert (High Confidence)
  - 13 zur Review (Medium/Low Confidence)
- **Labels gesetzt:** 32
  - 🔴 Wichtig: 6
  - ⚡ Action Required: 4
  - 📘 Nice to Know: 8
  - 📰 Newsletter: 14
- **Archiviert:** 14 (Newsletter)
- **Extrahiert:**
  - 8 Tasks
  - 3 Decisions
  - 5 Questions

### Weitere Module
_(Platzhalter für zukünftige Module: Calendar, Finance, etc.)_

---

## 🔴 Wichtige E-Mails (6)

### 1. [Boss - Q4 Budget Review](link_to_email)
**Von:** boss@company.com
**Zeit:** 14:32
**Thread:** 7 E-Mails über 3 Tage

**Zusammenfassung:**
Boss requests Q4 budget review with detailed marketing breakdown.
Deadline: Friday. Previous thread discussed budget concerns and ROI.

**Extrahiert:**
- 📋 **Task:** Review Q4 budget and prepare marketing breakdown
  - Priority: High
  - Deadline: 2025-11-25 (Friday)
  - Assignee: Me
  - [View Task](link_to_task)

**Anhänge:**
- 📄 budget_q4_draft.xlsx (1.2 MB)

---

### 2. [Client - Project Timeline Adjustment](link_to_email)
**Von:** client@project.com
**Zeit:** 16:15

**Zusammenfassung:**
Client asks about timeline flexibility for Phase 2 due to
internal delays. Suggests meeting next week to discuss.

**Extrahiert:**
- ❓ **Question:** Timeline flexibility for Phase 2?
  - Type: Decision
  - Urgency: Medium
  - [Answer](link_to_question)
- 📋 **Task:** Schedule meeting with client for timeline discussion
  - Priority: Medium
  - [View Task](link_to_task)

---

_(Weitere wichtige E-Mails...)_

---

## ⚡ Action Required (4)

_(Ähnliches Format wie oben)_

---

## 📘 Nice to Know (8)

_(Kompaktere Darstellung, nur Zusammenfassungen)_

1. **Team** - Q4 Progress Update | [Read](link)
2. **Marketing** - Campaign Results | [Read](link)
...

---

## 🔔 Review Queue (13)

**Diese E-Mails benötigen deine Entscheidung:**

1. **team@company.com** - "Team Update Q4"
   - Vorschlag: nice_to_know (75%)
   - [Review](link_to_review_queue)

_(Weitere Review-Items...)_

---

## 📊 Statistiken

### E-Mail-Verteilung
- Wichtig: 6 (13.3%)
- Action Required: 4 (8.9%)
- Nice to Know: 8 (17.8%)
- Newsletter: 14 (31.1%)
- Archiviert: 13 (28.9%)

### Top Absender
1. boss@company.com (4 E-Mails)
2. team@company.com (3 E-Mails)
3. client@project.com (2 E-Mails)

### Offene Items
- 📋 Tasks: 12 offen (8 neu heute)
- ❓ Questions: 7 offen (5 neu heute)
- ⚖️ Decisions: 3 offen (3 neu heute)
```

#### 7.2 Interaktive Elemente

**Pflicht-Features:**
- ✅ Links zu E-Mails (öffnet Gmail)
- ✅ Links zu Tasks (öffnet Task-Detail-View)
- ✅ Links zu Questions/Decisions
- ✅ Link zur Review Queue
- ✅ Zusammenklappbare Sections
- ✅ Filter (z.B. "Nur wichtige anzeigen")

#### 7.3 Erweiterte Journal-Komponenten (Zukunft)

**E-Mails sind nur eine Komponente des Journals:**
- 📧 E-Mail-Modul (aktuell)
- 📅 Calendar-Modul (Phase 3+)
- 💰 Finance-Modul (Phase 4+)
- 📝 Notes-Modul (Phase 4+)
- 🧠 Twin-Insights (Phase 5+)

**Weitere Veredelung folgt in späteren Phasen.**

---

## 🔧 Technische Anforderungen

### 1. Multi-Account Support

**Strategie:** Einheitlich über alle Accounts

**Accounts:**
- gmail_1 (persönlich)
- gmail_2 (business)
- gmail_3 (?)
- ionos

**Konfiguration:**
```python
# Gleiche Rules, gleiche Storage-Strategie für alle Accounts
for account in ['gmail_1', 'gmail_2', 'gmail_3', 'ionos']:
    apply_storage_strategy(account, strategy='unified')
    apply_classification_config(account, config=default_config)
    apply_label_strategy(account, label_map=LABEL_MAP)
```

### 2. Processing Mode

**Erwartetes Volumen:** 10-30 E-Mails/Tag (maximal 30-100/Tag)

**Modus A: Real-time (Bevorzugt)**
```python
# Sofortige Verarbeitung bei Empfang
on_email_received(email):
    classify(email)
    determine_storage_level(email)
    conditional_summarize(email)
    conditional_extract(email)
    apply_labels(email)
    log_events(email)
```

**Modus B: Batch (Fallback bei > 30 E-Mails/Tag)**
```python
# Scheduled Batches alle 30 Minuten
@scheduler.scheduled_job('interval', minutes=30)
def process_email_batch():
    new_emails = fetch_new_emails()
    asyncio.gather(*[classify(email) for email in new_emails])
    # ... rest of pipeline
```

### 3. Database Schema

**Neue Felder in `ProcessedEmail`:**
```python
class ProcessedEmail(Base):
    __tablename__ = "processed_emails"

    # ... bestehende Felder ...

    # NEU: Datenhaltungs-Strategie
    storage_level = Column(String(20), nullable=False, default="minimal")
    # Values: 'full', 'summary', 'minimal'

    # NEU: Zusammenfassung (für 'full' und 'summary')
    summary = Column(Text, nullable=True)

    # NEU: Vollständiger Body (nur bei 'full')
    body_text = Column(Text, nullable=True)
    body_html = Column(Text, nullable=True)

    # NEU: Thread-Kontext
    thread_id = Column(String(200), nullable=True, index=True)
    thread_summary = Column(Text, nullable=True)
    thread_position = Column(Integer, nullable=True)  # Position im Thread

    # NEU: Anhänge
    has_attachments = Column(Boolean, default=False)
    attachment_count = Column(Integer, default=0)
    attachments_metadata = Column(JSON, nullable=True)
    # Format: [{"filename": "...", "size": ..., "mime_type": "...", "stored": true/false}]

    # NEU: User Corrections
    user_corrected = Column(Boolean, default=False)
    user_corrected_at = Column(DateTime, nullable=True)
    original_category = Column(String(100), nullable=True)  # Vor Correction
```

**Neue Tabelle: `Attachments`**
```python
class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True)
    attachment_id = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))

    # E-Mail Reference
    email_id = Column(String(200), nullable=False, index=True)
    processed_email_id = Column(Integer, ForeignKey("processed_emails.id"), nullable=True)
    account_id = Column(String(100), nullable=False, index=True)

    # File Info
    original_filename = Column(String(500), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    mime_type = Column(String(200), nullable=False)

    # Storage
    stored_path = Column(String(1000), nullable=True)  # attachments/{account}/{email}/{file}
    storage_status = Column(String(50), default="pending")
    # Values: 'pending', 'stored', 'failed', 'skipped_too_large'

    # Metadata
    downloaded_at = Column(DateTime, nullable=True)
    file_hash = Column(String(64), nullable=True)  # SHA-256 for deduplication

    # Analysis (Phase 2+)
    extracted_text = Column(Text, nullable=True)
    analysis_metadata = Column(JSON, nullable=True)
```

### 4. Web-GUI Technology Stack

**Bereits definiert in Week 8 (HITL Interface):**
- Framework: (zu bestimmen - Flask, FastAPI, oder React)
- Features:
  - Review Queue Dashboard
  - Journal Display
  - Task/Decision/Question Management
  - Feedback Interface

### 5. Security & Privacy

**Verschlüsselung:** Unverschlüsselt (Standard SQLite)
- Grund: System läuft lokal beim User
- Keine Cloud-Synchronisation
- Daten verlassen Computer nicht

**Zugriffskontrolle:**
- Web-GUI: Localhost only (127.0.0.1)
- Optional: Basic Auth für zusätzliche Sicherheit

---

## 🚫 Explizit NICHT Teil dieser Spezifikation

### Phase 2+ Features (nicht jetzt):
- ❌ Anhang-Analyse (PDF-Text-Extraktion, OCR, etc.)
- ❌ Embeddings für semantische Suche (Vector DB)
- ❌ Cross-Email-Analytics
- ❌ Proaktive Vorschläge
- ❌ RAG (Retrieval Augmented Generation)
- ❌ Conversation-Tracking über mehrere Threads
- ❌ Weitere Input-Kanäle (Calendar, Notizen, etc.)

### Bewusste Scope-Limitation:
- Gmail Spam-Ordner wird ignoriert (nicht scannen)
- Keine automatischen E-Mail-Replies (nur Drafts in Zukunft)
- Keine E-Mail-Löschungen (nur Archive)
- Keine OAuth-Token-Rotation (manuell)

---

## ✅ Acceptance Criteria

### Functional Requirements:
- [ ] E-Mails werden nach Importance gestuft gespeichert
- [ ] Gmail-Labels werden bei High Confidence automatisch gesetzt
- [ ] Unwichtige E-Mails werden archiviert
- [ ] Anhänge werden heruntergeladen und in Verzeichnisstruktur gespeichert
- [ ] Thread-Kontext wird erstellt (max. 10 E-Mails)
- [ ] Review Queue zeigt Medium/Low Confidence E-Mails
- [ ] User kann Klassifikationen korrigieren (Feedback-Loop)
- [ ] History Scan funktioniert mit konfigurierbaren Intervallen
- [ ] Tagesjournal wird täglich generiert (abends + morgens)
- [ ] Journal zeigt Agent-Aktivitäten + wichtige E-Mails

### Non-Functional Requirements:
- [ ] Processing-Zeit: < 3s pro E-Mail (Real-time Mode)
- [ ] Batch-Processing: < 30s für 30 E-Mails
- [ ] History Scan: < 5 min für 1000 E-Mails
- [ ] Web-GUI reagiert in < 500ms
- [ ] Datenbank-Queries: < 100ms
- [ ] Storage: < 500MB für 1000 E-Mails (mit Anhängen)

### Quality Requirements:
- [ ] Classification Accuracy: > 85% nach 2 Wochen Learning
- [ ] Storage Level Accuracy: > 95%
- [ ] Thread-Summary Quality: > 80% User-Zufriedenheit
- [ ] Review Queue Precision: < 15% False Positives
- [ ] System Uptime: > 99% (ohne geplante Wartung)

---

## 📊 Success Metrics

### Week 8 (Implementation Phase):
- [ ] DB Migration erfolgreich (neue Felder)
- [ ] Storage Level Logic implementiert
- [ ] Anhang-Download funktioniert
- [ ] Thread-Kontext-Erstellung funktioniert
- [ ] Review Queue im Web-GUI sichtbar
- [ ] Feedback-Loop funktioniert

### Week 9 (Testing & Validation):
- [ ] 100 E-Mails testweise verarbeitet
- [ ] 10 History-Scans durchgeführt
- [ ] 20 User-Corrections getestet
- [ ] 5 Tagesjournale generiert
- [ ] Alle Acceptance Criteria erfüllt

### Phase 1 Complete (MVP):
- [ ] System läuft produktiv für 2 Wochen
- [ ] > 500 E-Mails erfolgreich verarbeitet
- [ ] Classification Accuracy > 85%
- [ ] User verwendet Review Queue regelmäßig
- [ ] Daily Journal wird gelesen und genutzt

---

## 🗺️ Implementation Roadmap

### Step 1: Database & Storage (2-3 Tage)
1. ProcessedEmail Model erweitern (storage_level, summary, body_text, thread_*)
2. Attachment Model erstellen
3. Migration erstellen & ausführen
4. determine_storage_level() Logic implementieren

### Step 2: Summarization & Extraction (2-3 Tage)
1. Summarization Service implementieren (LLM-basiert)
2. Classification Orchestrator erweitern (Conditional Summarize)
3. Conditional Body Storage
4. Conditional Extraction (nur bei 'full')

### Step 3: Anhang-Handling (2-3 Tage)
1. Verzeichnisstruktur erstellen (attachments/{account}/{email}/)
2. Download-Logic implementieren
3. Attachment Model speichern
4. Größenlimit-Checks

### Step 4: Thread-Handling (2-3 Tage)
1. Thread-History abrufen (Gmail API)
2. Thread-Zusammenfassung erstellen (LLM)
3. Thread-Kontext in DB speichern
4. Aktuelle E-Mail in Kontext setzen

### Step 5: Gmail-Automation (1-2 Tage)
1. apply_label() Integration in Pipeline
2. should_auto_archive() Logic
3. should_auto_read() Logic
4. History-Scan erweitern (rückwirkend labeln)

### Step 6: Review Queue (3-4 Tage)
1. Review Queue Routing (Medium/Low Confidence)
2. Web-GUI: Review Dashboard
3. Feedback-Buttons (Approve/Change/Skip)
4. Feedback-Loop (Events + Sender-Präferenz Update)

### Step 7: Journal (2-3 Tage)
1. Journal-Generator Agent erweitern (Agent-Aktivitäten)
2. Journal-Format implementieren (Markdown + Interaktiv)
3. Web-GUI: Journal-Display
4. Scheduled Generation (abends 20:00, morgens 08:00)

### Step 8: Testing & Validation (3-5 Tage)
1. Integration Tests (alle Storage Levels)
2. E2E Tests (Real Gmail Accounts)
3. History Scan Tests (verschiedene Intervalle)
4. Review Queue Tests
5. Performance Tests (Batch-Processing)

**Total Estimated Time:** 15-25 Tage (3-5 Wochen)

---

## 🔗 Referenzen

- **Projektdokumentation:** `/docs/VISION.md`
- **Aktuelle Architektur:** `/CLAUDE.md`
- **Phase 1 Scope:** `/docs/phases/PHASE_1_SCOPE.md`
- **Event-Log System:** `/docs/phases/PHASE_1_STEP_1_COMPLETE.md`
- **Extraction System:** `/docs/phases/PHASE_1_STEP_2_COMPLETE.md`
- **Ensemble Classifier:** `/docs/phases/PHASE_2_ENSEMBLE_SYSTEM.md`

---

**Status:** ✅ Ready for Implementation
**Next Step:** Assign to Coding Assistant
**Target Completion:** Week 8-9 (Ende November 2025)
