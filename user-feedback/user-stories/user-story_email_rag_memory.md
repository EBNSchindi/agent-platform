# User Story – Vektordatenbank & RAG für persönliche E‑Mail-Erinnerung

## Beschreibung

Als vielbeschäftigter Wissensarbeiter möchte ich, dass mein E‑Mail-System eine Vektordatenbank mit Retrieval-Augmented Generation (RAG) über meine vergangenen, für mich relevanten Konversationen aufbaut und nutzt, damit der Agent bei Klassifizierung und Antwortentwürfen auf inhaltlich ähnliche frühere Fälle zugreifen, meinen Kontext besser verstehen und konsistentere, hochwertigere Vorschläge machen kann.

## Akzeptanzkriterien

- Relevante E‑Mails und Konversationen (z. B. wichtige Projekte, Entscheidungen, Zusagen/Absagen, Konfliktfälle) werden als strukturierte Einträge in einer Vektordatenbank gespeichert; dabei werden Threads sinnvoll gechunkt (z. B. nach thematischen Abschnitten oder Nachrichtenblöcken).
- Beim Klassifizieren einer neuen E‑Mail kann der Agent die Vektordatenbank abfragen und ähnliche frühere Konversationen finden; diese Ähnlichkeit fließt in den Importance-Score bzw. die Kategorie ein (z. B. „ähnlich zu früheren als wichtig markierten Mails“).
- Beim Erstellen eines Antwortentwurfs führt der Responder-Agent eine RAG-Abfrage durch und erhält die wichtigsten n (z. B. 3–5) relevanten früheren Nachrichten/Antworten, die als Kontext in die Prompting- bzw. Entscheidungslogik einfließen (z. B. Formulierungen, Argumentationslinien, Projektkontext).
- Der Agent kann sich in Formulierungen explizit auf frühere Kommunikation beziehen (z. B. „wie in unserer Mail vom … besprochen“), sofern diese Informationen im RAG-Kontext verfügbar und sinnvoll sind.
- Es gibt klare Filter- und Sicherheitsregeln, welche E‑Mails in die Vektordatenbank aufgenommen werden (z. B. keine hochsensiblen Inhalte, nur bestimmte Ordner/Labels) sowie Mechanismen zum Löschen/Anonymisieren von Einträgen auf Wunsch.
- Die Nutzung der Vektordatenbank verbessert die Qualität von Klassifikation und Antwortentwürfen messbar (z. B. weniger Korrekturen notwendig, höhere Übereinstimmung mit meinen tatsächlichen Entscheidungen), ohne dass die Antwortzeiten oder Systemkosten unvertretbar steigen.

## Aktualisierung & Maintenance

- Nach jedem relevanten Verarbeitungsschritt (z. B. Klassifizierung, Erstellen/Versenden einer wichtigen Antwort) werden neue, als relevant eingestufte Mails/Threads automatisch eingebettet und mit passenden Metadaten (z. B. `account_id`, `thread_id`, Labels, Importance-Score) in die Vektordatenbank aufgenommen.
- Änderungen an Mails (z. B. verschoben in „wichtig“, als „low priority“ markiert, umgelabelt) führen zu einer Aktualisierung der zugehörigen Einträge in der Vektordatenbank oder zur Versionierung (alte Version als veraltet gekennzeichnet).
- Ein periodischer Maintenance-Job (z. B. täglich oder wöchentlich über den Scheduler) prüft auf fehlende oder veraltete Embeddings, erzeugt diese bei Bedarf neu und entfernt oder archiviert alte, nicht mehr relevante Einträge entsprechend konfigurierbarer Aufbewahrungsregeln.
- Es gibt konfigurierbare Retention- und Privacy-Regeln, etwa „nur die letzten 12 Monate“ oder „nur Mails mit bestimmten Labels“, und das Löschen/Anonymisieren einer Mail führt auch zum Löschen/Anonymisieren der entsprechenden Vektordatenbank-Einträge.
- Feedback-getaggte Mails (z. B. explizit als „besonders wichtig“ markiert oder vom System aktiv nachgefragt) werden mit hoher Priorität in die Vektordatenbank aufgenommen, damit sie das zukünftige Verhalten des Systems stärker beeinflussen.

