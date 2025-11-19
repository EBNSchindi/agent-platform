# User Story – Sichtbare Label- & Klassifikations-Synchronisation

## Beschreibung

Als Nutzer der E‑Mail-Agenten-Plattform möchte ich, dass die vom System berechneten Klassifikationen (z. B. Spam, Wichtig, Newsletter) zuverlässig als Labels bzw. Ordner in meinen Mailprogrammen (Gmail und Ionos) sichtbar werden und mit der internen Klassifikationslogik konsistent bleiben, damit ich die Entscheidungen des Systems direkt in meinem gewohnten Postfach nachvollziehen und bei Bedarf korrigieren kann.

## Akzeptanzkriterien

- Für Gmail werden Klassifikations-Ergebnisse aus dem `EmailClassification`-Modell (`category`, `suggested_label`) über den Orchestrator in echte Gmail-Labels übersetzt:
  - Der Orchestrator ruft bei Spam `apply_label_tool(account_id, email_id, "Spam")` und anschließend `archive_email_tool(...)` auf, sodass die Mail nicht mehr im primären Posteingang erscheint.
  - Für alle anderen Klassifikationen mit `suggested_label` ruft der Orchestrator `apply_label_tool(...)` auf, das über `GmailService.apply_label` und die Gmail API (`users.messages.modify`) das passende Label setzt.
  - Falls ein Label noch nicht existiert, wird es über `_get_or_create_label` automatisch angelegt und danach verwendet.
- Für Ionos werden Klassifikationen mindestens auf Spam-Ebene sichtbar:
  - Spam-Mails werden über `archive_ionos_email(email_id)` in den `Archive`-Ordner verschoben (IMAP-Äquivalent von Label „Archive“/„Spam“ je nach Konfiguration).
  - Die vorhandene `apply_label(email_id, folder)`-Funktion von `IonosService` kann genutzt werden, um weitere Klassifikationen (z. B. „Newsletters“, „Important“) als IMAP-Ordner abzubilden.
- Alle Klassifikations-Ergebnisse werden zusätzlich in der Datenbank-Tabelle `processed_emails` gespeichert (`agent_platform/db/models.py`), inklusive:
  - `category`, `confidence`, `suggested_label`, `should_reply`, `urgency`
  - sowie erweiterte Felder wie `importance_score`, `classification_confidence`, `rule_layer_hint`, `history_layer_hint`.
- Für jede verarbeitete Mail ist die sichtbare Darstellung im Mailprogramm (Label/Ordner) konsistent mit dem gespeicherten Klassifikationsdatensatz in `processed_emails`, sodass interne Auswertungen und die sichtbare Oberfläche zusammenpassen.
- Benutzer können anhand der Labels/Ordner im Mailprogramm nachvollziehen, wie das System eine Mail eingeordnet hat, und ihre manuellen Änderungen werden später als Feedback (über `FeedbackEvent` & verwandte Tabellen) genutzt, um das Klassifikationsverhalten zu verbessern.

