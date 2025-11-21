# To-dos – Label- & Klassifikations-Synchronisation in Mailprogrammen

## Aktueller Stand (Ist-Zustand)

- **Gmail**
  - Ungelesene Mails werden mit `fetch_unread_emails_tool` (`modules/email/tools/gmail_tools.py`) abgerufen.
  - Der Classifier erzeugt ein `EmailClassification`-Objekt (`agent_platform/classification/models.py`).
  - Im Orchestrator (`agent_platform/orchestration/classification_orchestrator.py`):
    - Spam (`category == "spam"`) -> `apply_label_tool(..., "Spam")` -> `archive_email_tool`.
    - Andere -> `apply_label_tool` nutzt `GmailService.apply_label`, was `users.messages.modify` aufruft.
  - Daten landen in `processed_emails` (`agent_platform/db/models.py`).

- **Ionos**
  - `IonosService.fetch_unread_emails` wird genutzt.
  - `archive_ionos_email` verschiebt in Archiv.
  - `apply_label` in `IonosService` (`modules/email/tools/ionos_tools.py`) kopiert/verschiebt in Ordner (Label-Ersatz).

## To-dos – Technik & Implementierung

- **Gmail Integration**
  - [ ] **Mapping-Konfiguration:**
    - Definieren einer zentralen Config (`agent_platform/core/config.py`) für Category-to-Label Mapping.
    - Beispiel: `{"wichtig_todo": "Action Required", "finance": "Rechnungen", "newsletter": "Newsletters"}`.
  - [ ] **Orchestrator Update (`agent_platform/orchestration/classification_orchestrator.py`):**
    - Sicherstellen, dass `classification.suggested_label` basierend auf der Config gesetzt wird.
    - Aufruf von `apply_label_tool` für alle validen Kategorien, nicht nur manuell.
  - [ ] **Service-Erweiterung (`modules/email/tools/gmail_tools.py`):**
    - Prüfen, ob `_get_or_create_label` Nested Labels (z.B. "AI/Wichtig") unterstützt.

- **Ionos Integration**
  - [ ] **Orchestrator Erweiterung:**
    - Implementierung analog zu Gmail: Wenn Ionos-Account -> `IonosService.apply_label(email_id, folder_name)` aufrufen.
  - [ ] **Folder-Check:**
    - Sicherstellen, dass Zielordner existieren oder Fallback (z.B. "INBOX") genutzt wird.

- **Datenbank & Konsistenz**
  - [ ] **Metadaten-Update:**
    - In `ProcessedEmail` (`agent_platform/db/models.py`) das tatsächlich gesetzte Label im Feld `gmail_labels_applied` oder `extra_metadata` speichern.

## To-dos – User-Feedback & Lernen

- [ ] **Feedback-Loop:**
  - `FeedbackEvent` (`agent_platform/db/models.py`) nutzen, um manuelle Label-Änderungen zu tracken.
  - API-Endpunkt für Webhook/Polling von Label-Änderungen (falls technisch via Gmail API History möglich).
