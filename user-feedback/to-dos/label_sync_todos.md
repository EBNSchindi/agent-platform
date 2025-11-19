# To-dos – Label- & Klassifikations-Synchronisation in Mailprogrammen

## Aktueller Stand (Ist-Zustand)

- **Gmail**
  - Ungelesene Mails werden mit `fetch_unread_emails_tool` abgerufen und enthalten u. a. `id`, `thread_id`, `subject`, `sender`, `snippet`, `body`, `labels` (Gmail-Label-IDs).
  - Der Classifier erzeugt für jede Mail ein `EmailClassification`-Objekt mit `category`, `confidence`, `suggested_label`, `should_reply`, `urgency`, `reasoning`.
  - Im Orchestrator (`EmailOrchestrator._process_single_email`):
    - Spam-Mails (`classification.category == "spam"`) werden mit `apply_label_tool(account_id, email_id, "Spam")` gelabelt und anschließend mit `archive_email_tool(...)` aus dem Posteingang entfernt.
    - Für alle Mails mit `classification.suggested_label` ruft der Orchestrator bei Gmail `apply_label_tool(...)` auf; dieses nutzt `GmailService.apply_label`, um das Label via Gmail API zu setzen (inkl. automatischer Label-Erstellung über `_get_or_create_label`).
    - Je nach Modus (MANUAL, DRAFT, AUTO_REPLY) werden zusätzlich Drafts erstellt oder Auto-Replies gesendet.
  - Klassifikationsdaten werden in `processed_emails` persistiert.

- **Ionos**
  - Ungelesene Mails werden via IMAP (`IonosService.fetch_unread_emails`) abgerufen.
  - Spam-Mails werden im Orchestrator mit `archive_ionos_email(email_id)` behandelt, was intern `apply_label(email_id, "Archive")` nutzt und die Mail in den Archiv-Ordner verschiebt.
  - `IonosService.apply_label(email_id, folder)` kann grundsätzlich genutzt werden, um Mails in andere IMAP-Ordner (als Label-Ersatz) zu kopieren, wird aktuell aber nur indirekt für das Archiv verwendet.

## To-dos – Technik & Implementierung

- **Gmail**
  - [ ] Mapping der Klassifikations-Kategorien zu sinnvollen Standard-Labels überprüfen und ggf. zentral konfigurieren (z. B. `spam → "Spam"`, `important → "Important"`, `normal → "Newsletters"/"Notifications"`, `auto_reply_candidate → "Auto-Reply"`).
  - [ ] Sicherstellen, dass `classification.suggested_label` immer mit diesem Mapping konsistent ist (entweder im Classifier oder in einer Zwischenschicht im Orchestrator).
  - [ ] Logging/Monitoring ergänzen, um Fehler in `apply_label_tool` bzw. `GmailService.apply_label` und der Label-Erstellung früh zu erkennen (z. B. ungültige Labelnamen).
  - [ ] Optional: Tests/Scripts ergänzen, die gezielt Mails mit verschiedenen `suggested_label`-Werten erzeugen und prüfen, ob die Labels in Gmail korrekt gesetzt werden.

- **Ionos**
  - [ ] Im Orchestrator auch für Ionos-Mails `classification.suggested_label` auswerten und nicht nur Spam behandeln:
    - z. B. Mapping von `suggested_label` auf IMAP-Ordner (`"Newsletters"`, `"Important"`, `"Work"`, etc.).
    - Aufruf von `IonosService.apply_label(email_id, folder)` mit dem gemappten Ordnernamen.
  - [ ] Konvention für Ordnernamen in Ionos definieren (z. B. existierende Ordner vs. automatische Ordner-Erstellung, falls unterstützt).
  - [ ] Fehlerhandling implementieren, falls ein Zielordner nicht existiert oder das Kopieren fehlschlägt (Fallback-Strategie, Logging).

- **Datenbank & Konsistenz**
  - [ ] Sicherstellen, dass nach erfolgreicher Label-/Ordner-Zuordnung in Gmail/Ionos der entsprechende `ProcessedEmail`-Eintrag aktualisiert wird (z. B. Speicherung des final verwendeten Label-/Ordnernamens in `extra_metadata`).
  - [ ] Optional: Backfill-Job, der bestehende `processed_emails`-Einträge mit ihren tatsächlichen Labels/Ordnern aus dem Mailkonto abgleicht und Diskrepanzen markiert.

## To-dos – User-Feedback & Lernen

- [ ] User-Aktionen im Mailprogramm (z. B. „Label geändert“, „Mail aus Spam zurückgeholt“, „Mail in Ordner X verschoben“) als `FeedbackEvent` erfassen, um daraus Sender-/Domain-Präferenzen (`SenderPreference`, `DomainPreference`) zu aktualisieren.
- [ ] Regeln definieren, wie solche Feedback-Events in künftige `suggested_label`-Entscheidungen einfließen (z. B. bevorzugte Ordner/Labels pro Absender/Domain).
- [ ] UI- oder Reporting-Mechanismen vorsehen, mit denen der Nutzer nachvollziehen kann, welche Labels/Kategorien das System warum gewählt hat, und Korrekturen besonders leicht geben kann.

