# REQ-001: Standardisierte E-Mail-Speicherung

**Status:** Proposed
**Priorität:** High
**Erstellt:** 2025-11-20
**Kategorie:** Architecture / Data Storage

---

## Zusammenfassung

Alle eingehenden E-Mails sollen unabhängig von ihrer Klassifizierung (wichtig, unwichtig, spam) im gleichen Format mit vollem Inhalt (`storage_level='full'`) in der Datenbank gespeichert werden.

---

## Anforderung (User Story)

**Als** Digital Twin Email Platform
**möchte ich** alle E-Mails vollständig speichern (body_text, body_html, summary, metadata)
**damit** das System aus allen E-Mails lernen kann und keine Datenlücken bei der Analyse entstehen.

---

## Hintergrund & Motivation

### Aktuelle Situation

Die `ProcessedEmail`-Tabelle unterstützt drei Storage-Level:
- `full`: Vollständiger Inhalt (body_text + body_html + summary + metadata)
- `summary`: Nur LLM-generierte Zusammenfassung (2-3 Sätze) + metadata
- `minimal`: Nur Metadaten (subject, sender, timestamps, etc.)

**Problem:** Unterschiedliche Storage-Level führen zu:
- Inkonsistenter Datenhaltung
- Datenlücken bei der Analyse
- Eingeschränktem Machine Learning (fehlende Trainingsdaten)
- Komplexität beim Abrufen (if/else-Bedingungen)
- Erschwerte Debugging-Möglichkeiten

### Begründung (Speicher-Analyse)

Eine detaillierte Speicher-Simulation (siehe `scripts/analysis/storage_simulation.py`) zeigt:

| E-Mails/Tag | 1 Jahr | 3 Jahre | 8 Jahre |
|-------------|--------|---------|---------|
| 10          | 0.24 GB | 0.72 GB | 1.91 GB |
| 50          | 1.20 GB | 3.59 GB | 9.57 GB |
| 100         | 2.39 GB | 7.18 GB | 19.13 GB |

**Fazit:** Speicherplatz ist selbst bei maximaler Retention (FULL) vernachlässigbar.

### Vorteile der Standardisierung

✅ **Digital Twin Architektur**
- Vollständige Daten für Machine Learning (auch von "unwichtigen" E-Mails)
- Lernfähigkeit: System kann aus Fehlklassifikationen lernen
- Pattern-Erkennung über alle Kategorien hinweg

✅ **Event-First Prinzip**
- Konsistent mit immutable Events (alle Aktionen vollständig nachvollziehbar)
- Keine "Datenlöcher" beim Debugging

✅ **Feedback-Loop**
- Wenn User-Feedback zeigt, dass eine "unwichtige" E-Mail wichtig war → voller Kontext vorhanden
- Historische Analysen ohne Einschränkungen

✅ **Architektonische Einfachheit**
- Keine Bedingungen beim Speichern/Abrufen
- Vereinfachte Queries
- Einheitliche Datenstruktur

✅ **Thread-Handling**
- Eine "unwichtige" E-Mail kann Teil eines wichtigen Threads sein
- Vollständiger Thread-Kontext immer verfügbar

✅ **Compliance & Audit**
- Vollständige E-Mail-Historie
- Rechtssichere Archivierung
- Compliance mit DSGVO (Speicherdauer konfigurierbar)

---

## Akzeptanzkriterien

### AC1: Standard Storage Level
- [ ] Alle neuen E-Mails werden mit `storage_level='full'` gespeichert
- [ ] `ProcessedEmail.storage_level` default ist `'full'`
- [ ] `body_text` und `body_html` werden immer befüllt (wenn im Original vorhanden)

### AC2: Keine kategoriebasierte Unterscheidung
- [ ] Wichtige E-Mails → `storage_level='full'`
- [ ] Unwichtige E-Mails → `storage_level='full'`
- [ ] Spam → `storage_level='full'`
- [ ] Kategorie hat **keinen Einfluss** auf Storage-Level

### AC3: Vollständige Daten
- [ ] `body_text`: Immer gespeichert (Plain-Text-Inhalt)
- [ ] `body_html`: Immer gespeichert (wenn vorhanden)
- [ ] `summary`: Immer generiert und gespeichert (LLM-Zusammenfassung)
- [ ] Alle Metadaten: subject, sender, timestamps, classification, etc.

### AC4: Attachments
- [ ] `has_attachments`, `attachment_count` immer befüllt
- [ ] `attachments_metadata` enthält Liste aller Attachments
- [ ] Attachment-Dateien werden gemäß Attachment-Policy gespeichert
- [ ] Verknüpfung zu `attachments`-Tabelle funktioniert

### AC5: Thread-Handling
- [ ] `thread_id`, `thread_position`, `is_thread_start` werden befüllt
- [ ] `thread_summary` wird generiert (LLM-basiert)
- [ ] Alle E-Mails eines Threads haben vollständigen Inhalt

### AC6: Bestehende E-Mails
- [ ] Migration für bestehende E-Mails mit `storage_level != 'full'` vorhanden
- [ ] Migration-Script dokumentiert in `docs/migrations/`
- [ ] Rollback-Strategie definiert

### AC7: Dokumentation
- [ ] `CLAUDE.md` aktualisiert mit Storage-Strategie
- [ ] Speicher-Simulation referenziert (`scripts/analysis/storage_simulation.py`)
- [ ] Beispiel-Code für E-Mail-Speicherung dokumentiert

### AC8: Testing
- [ ] Unit Tests: E-Mails werden mit `storage_level='full'` gespeichert
- [ ] Integration Tests: Vollständige Daten abrufbar
- [ ] Edge Cases: Leere Bodies, nur HTML, nur Text

---

## Technische Spezifikation

### Datenbankschema (bereits vorhanden in `agent_platform/db/models.py`)

```python
class ProcessedEmail(Base):
    __tablename__ = "processed_emails"

    # Storage strategy
    storage_level = Column(String(20), nullable=False, default='full', index=True)
    # ✅ Default ist bereits 'full' (models.py:219)

    # Content storage (immer befüllen bei storage_level='full')
    summary = Column(Text, nullable=True)           # LLM-Zusammenfassung
    body_text = Column(Text, nullable=True)         # Plain-Text
    body_html = Column(Text, nullable=True)         # HTML (wenn vorhanden)

    # Thread handling (immer befüllen)
    thread_id = Column(String(200), nullable=True, index=True)
    thread_summary = Column(Text, nullable=True)
    thread_position = Column(Integer, nullable=True)
    is_thread_start = Column(Boolean, default=False)

    # Attachment metadata (immer befüllen)
    has_attachments = Column(Boolean, default=False, index=True)
    attachment_count = Column(Integer, default=0)
    attachments_metadata = Column(JSON, default={})
```

### Code-Änderungen

**1. E-Mail-Speicherung (Orchestrator/Processor)**

```python
# In agent_platform/orchestration/classification_orchestrator.py
# Oder in neuem email_processor.py

async def save_email_to_db(email_data: dict, classification_result: dict):
    """
    Save email with FULL storage level (always).
    """
    with get_db() as db:
        processed_email = ProcessedEmail(
            account_id=email_data['account_id'],
            email_id=email_data['email_id'],
            message_id=email_data.get('message_id'),
            subject=email_data.get('subject'),
            sender=email_data.get('sender'),
            received_at=email_data.get('received_at'),

            # Classification results
            category=classification_result['category'],
            confidence=classification_result['confidence'],
            importance_score=classification_result.get('importance_score'),
            classification_confidence=classification_result['confidence'],

            # ✅ ALWAYS 'full'
            storage_level='full',

            # ✅ ALWAYS store full content
            body_text=email_data.get('body_text'),
            body_html=email_data.get('body_html'),
            summary=await generate_summary(email_data),  # LLM-generated

            # ✅ ALWAYS store thread info
            thread_id=email_data.get('thread_id'),
            thread_summary=await generate_thread_summary(email_data),
            thread_position=email_data.get('thread_position'),
            is_thread_start=email_data.get('is_thread_start', False),

            # ✅ ALWAYS store attachment metadata
            has_attachments=len(email_data.get('attachments', [])) > 0,
            attachment_count=len(email_data.get('attachments', [])),
            attachments_metadata=email_data.get('attachments', []),
        )

        db.add(processed_email)
        # Commit happens on context exit
```

**2. Keine kategorie-basierte Logik**

```python
# ❌ REMOVE (wenn vorhanden):
if category == 'spam':
    storage_level = 'minimal'
elif category in ['unwichtig', 'normal']:
    storage_level = 'summary'
else:
    storage_level = 'full'

# ✅ REPLACE WITH:
storage_level = 'full'  # Always
```

---

## Optionale Erweiterung (Future Phase)

### Zeitbasierte Degradation (Optional, nicht jetzt)

Falls später Speicherplatz gespart werden soll:

```python
# Background Job: Degrade old unimportant emails
async def degrade_old_emails():
    """
    Run monthly: Degrade old emails based on age + importance.

    Rules:
    - 0-90 days: ALL → 'full' (no change)
    - 91-365 days: unwichtig → 'summary'
    - 365+ days: unwichtig → 'minimal', medium → 'summary'
    """
    with get_db() as db:
        # Example: Degrade emails older than 365 days
        cutoff_date = datetime.utcnow() - timedelta(days=365)

        # Unwichtig + old → minimal
        db.query(ProcessedEmail).filter(
            ProcessedEmail.received_at < cutoff_date,
            ProcessedEmail.category == 'unwichtig',
            ProcessedEmail.storage_level == 'full'
        ).update({
            'storage_level': 'minimal',
            'body_text': None,
            'body_html': None,
            # Keep: summary, metadata
        })
```

**Wichtig:** Dies ist **NICHT** Teil dieser Anforderung. Erst später implementieren, wenn wirklich nötig.

---

## Migration Plan

### Phase 1: Code-Änderungen
1. Sicherstellen, dass alle neuen E-Mails mit `storage_level='full'` gespeichert werden
2. LLM-Summary-Generierung für alle E-Mails aktivieren
3. Thread-Summary-Generierung implementieren

### Phase 2: Bestehende Daten (Optional)
Wenn bereits E-Mails mit `storage_level != 'full'` existieren:

```python
# Migration Script: Upgrade existing emails to 'full'
# ACHTUNG: Nur möglich, wenn Original-E-Mails noch abrufbar sind!

async def migrate_to_full_storage():
    """
    Upgrade existing emails to storage_level='full'.
    Requires access to original emails via Gmail/IMAP API.
    """
    with get_db() as db:
        emails_to_upgrade = db.query(ProcessedEmail).filter(
            ProcessedEmail.storage_level != 'full'
        ).all()

        for email in emails_to_upgrade:
            # Fetch original email from Gmail/IMAP
            original = await fetch_original_email(email.account_id, email.email_id)

            # Update with full content
            email.storage_level = 'full'
            email.body_text = original.get('body_text')
            email.body_html = original.get('body_html')
            email.summary = await generate_summary(original)

        # Commit happens on exit
```

**Wichtig:** Migration nur ausführen, wenn Original-E-Mails noch verfügbar sind!

### Phase 3: Testing
1. Unit Tests: Alle neuen E-Mails haben `storage_level='full'`
2. Integration Tests: Vollständige Daten abrufbar
3. Performance Tests: Query-Performance mit größeren Datenmengen

### Phase 4: Dokumentation
1. `CLAUDE.md` aktualisieren
2. `docs/STORAGE_STRATEGY.md` erstellen
3. Speicher-Simulation referenzieren

---

## Risiken & Mitigationen

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| Speicherplatz wird knapp | Niedrig | Mittel | Monitoring einrichten; Optional: Degradation-Job vorbereiten |
| Performance-Probleme bei Queries | Niedrig | Mittel | Indices optimieren (`storage_level`, `received_at`, `category`) |
| Migration schlägt fehl | Mittel | Niedrig | Migration ist optional; System funktioniert auch ohne |
| DSGVO-Konflikt (zu lange Speicherung) | Niedrig | Hoch | Retention-Policy definieren (z.B. Auto-Delete nach 10 Jahren) |

---

## Alternativen (verworfen)

### Alternative 1: Kategorie-basierte Speicherung
**Beschreibung:** Wichtige E-Mails → full, unwichtige → summary/minimal
**Verworfen weil:**
- Widerspricht Digital Twin Prinzip (lernt nur von wichtigen E-Mails)
- Datenlücken bei Feedback-Loop
- Komplexität ohne signifikanten Speichervorteil

### Alternative 2: Zeitbasierte Speicherung (initial)
**Beschreibung:** Von Anfang an mit Degradation starten
**Verworfen weil:**
- Premature Optimization
- Speicher ist kein Problem (< 10 GB für 3 Jahre)
- Kann später hinzugefügt werden

### Alternative 3: Externe Speicherung (S3, etc.)
**Beschreibung:** E-Mail-Bodies in S3, nur Metadaten in DB
**Verworfen weil:**
- Overengineering für die Datenmenge
- Zusätzliche Komplexität (API-Calls, Netzwerk-Latency)
- Kostet mehr als lokaler Speicher

---

## Erfolgsmetriken

Nach Implementierung sollten folgende Metriken erfüllt sein:

1. **100% der neuen E-Mails** haben `storage_level='full'`
2. **100% der neuen E-Mails** haben `body_text` UND/ODER `body_html` befüllt
3. **100% der neuen E-Mails** haben `summary` generiert
4. **Speicherverbrauch** entspricht Projektion (~2-8 GB für 3 Jahre)
5. **Query-Performance** bleibt unter 100ms für typische Abfragen
6. **Keine Fehler** bei Abruf von E-Mail-Inhalten (wegen fehlender Daten)

---

## Anhänge

- [Storage Simulation Script](../../scripts/analysis/storage_simulation.py)
- [Database Models](../../agent_platform/db/models.py)
- [CLAUDE.md](../../CLAUDE.md)

---

## Genehmigung & Sign-Off

- [ ] **Product Owner:** _____________________
- [ ] **Tech Lead:** _____________________
- [ ] **Entwickler:** _____________________

**Genehmigt am:** _____________________
