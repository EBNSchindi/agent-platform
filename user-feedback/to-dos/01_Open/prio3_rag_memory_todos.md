# To-dos – Vektordatenbank & RAG (Memory Extension)

## Ziel
Implementierung eines Langzeitgedächtnisses für den Agenten, um aus vergangenen Interaktionen zu lernen. E-Mails sollen als Vektoren gespeichert werden, um semantische Ähnlichkeiten zu finden.

## Technische Analyse & Architektur
- **Datenbank:** Erweiterung des Schemas oder Nutzung einer externen Vector-DB (z.B. ChromaDB, PGVector).
- **Service:** Neuer `VectorService` parallel zum `MemoryService`.
- **Integration:** Responder-Agent nutzt RAG-Kontext.

## Backend-Tasks

### Datenbank & Models
- [ ] **Schema-Design:** Entscheidung für Vektor-Storage (z.B. `pgvector` Extension für PostgreSQL oder separate Tabelle `email_embeddings`).
  - Entwurf Tabelle `email_embeddings`:
    - `email_id` (FK)
    - `vector` (Array/Binary)
    - `embedding_model` (String, z.B. "openai-text-embedding-3-small")
    - `chunk_index` (Int, falls Body gesplittet wird)
- [ ] **Model-Update:** `agent_platform/db/models.py` erweitern.

### Core Services
- [ ] **VectorService Implementierung:**
  - Erstellen von `agent_platform/memory/vector_service.py`.
  - Methoden: `add_email_embedding(email)`, `search_similar(query_text, limit=5)`.
  - Integration des Embedding-Providers (z.B. OpenAI Embeddings via `agent_platform/llm/providers.py`).
- [ ] **Backfill-Job:** Script erstellen (`scripts/operations/backfill_embeddings.py`), um existierende `ProcessedEmail`-Einträge nachträglich zu embedden.

### Agent Integration
- [ ] **Responder Erweiterung (`modules/email/agents/responder.py`):**
  - Vor dem Prompt-Aufbau: Suche nach ähnlichen *gesendeten* Antworten im Vector-Store.
  - Injektion der Top-3 ähnlichen Konversationen in den System-Prompt ("Here is how you answered similar emails in the past: ...").
- [ ] **Classifier Erweiterung (Optional):**
  - Nutzung ähnlicher klassifizierter Mails zur Verbesserung der `confidence` bei unsicheren Fällen.

## Infrastruktur & Maintenance
- [ ] **Automatisierung:** Trigger definieren (z.B. "Nach Senden einer Antwort" -> "Embedding erstellen").
- [ ] **Cleanup:** Veraltete Embeddings löschen (Retention Policy).

