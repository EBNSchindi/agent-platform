# To-dos – „Tinder für Emails“: Interaktives Trainings-UI

## Ziel

Ein UI- und Backend-Feature schaffen, mit dem der Nutzer in kurzer Zeit viele reale Emails manuell einordnen kann („swipen“), während das System die System-Vorhersage anzeigt und strukturiertes Feedback für Rule-, History- und LLM-Layer sammelt.

## Backend-To-dos

- [ ] **API-Endpunkt:** Endpoint bereitstellen, der ein Batch von Trainings-Kandidaten liefert:
  - Filter: bevorzugt Emails mit mittlerer/niedriger Confidence oder mit hoher Diskrepanz zwischen Rule-/History-/LLM-Layer.
  - Daten: `email_id`, `account_id`, Absender, Domain, Betreff, Snippet/Body-Ausschnitt, aktuelle Klassifikation (Kategorie, Importance, Confidence, Layer).
- [ ] **Feedback-Endpunkt:** Endpoint für das Speichern der Nutzerentscheidung:
  - Input: `email_id`, gewählte Kategorie/Wichtigkeit, optional Kommentar, UI-Aktion (z. B. „swipe_left/right“).
  - Speichern als `FeedbackEvent` inkl. ursprünglicher System-Klassifikation und Metadaten.
- [ ] **Sampling-Logik:** Logik für sinnvolle Auswahl von Trainingsmails:
  - Fokus auf „unsichere“ Fälle (Confidence im Bereich 0.4–0.85).
  - Mischung verschiedener Sender/Domains und Kategorien.
  - Optional: Limit pro Session und pro Tag.
- [ ] **Integration History-Layer:** Sicherstellen, dass neue `FeedbackEvent`-Einträge zeitnah in `SenderPreference`/`DomainPreference` einfließen (z. B. über periodischen Job oder direkte Aktualisierung).

## Frontend-/UI-To-dos

- [ ] **„Swipe“-UI entwerfen:** Einfache, fokussierte Oberfläche:
  - Ein E‑Mail-Snippet im Mittelpunkt.
  - Klar erkennbare Buttons/Shortcuts für die Ziel-Kategorien (Wichtig, Nice to know, Newsletter, Spam, etc.).
  - Anzeige der System-Vorhersage als Hinweis („Systemvorschlag“), ohne die eigene Entscheidung zu erzwingen.
- [ ] **Session-Handling:** Trainingssession mit fester Länge (z. B. 20 Mails) und Fortschrittsanzeige („12/20“).
- [ ] **Feedback am Ende:** Kurze Zusammenfassung der Session (Anzahl gelabelter Mails, geschätzter Nutzen für das System).

## Lernlogik & Konfiguration

- [ ] **Weighting:** Definieren, wie stark diese expliziten Trainingslabels die bestehenden Präferenzen beeinflussen (z. B. höheres Gewicht als passive Beobachtungen aus dem normalen Mail-Workflow).
- [ ] **Konfigurierbarkeit:** Möglichkeit, Trainingsmodus ein-/auszuschalten und ggf. die Intensität zu wählen (z. B. „20 Mails pro Tag“).
- [ ] **Sicherheit/Privacy:** Klarstellen, welche Inhalte im Trainings-UI angezeigt werden dürfen (z. B. keine hochsensiblen Mails, optional Maskierung bestimmter Daten).

