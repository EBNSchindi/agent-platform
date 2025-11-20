# To-do – Überarbeitung Rule Layer: Kontextbasierte Klassifizierung von `noreply@`-Mails

## 🎯 Übergeordnete User Story – Balance zwischen Regeln, Historie & KI

Als E‑Mail-System-Nutzer möchte ich, dass die Wichtigkeit meiner E‑Mails vor allem durch Mustererkennung und mein eigenes Nutzungsverhalten (Historie, Feedback, Training) bestimmt wird – und starre Regeln nur die klaren Extremfälle (z. B. offensichtlicher Spam, eindeutige Newsletter) abfangen –, damit wichtige Mails nicht fälschlicherweise von zu aggressiven Heuristiken ausgefiltert werden, das System mit der Zeit immer besser zu meinen Gewohnheiten passt und ich anfangs bei Bedarf durch ein LLM bei jeder E‑Mail unterstützt werde.

**Schwerpunkte:**
- Regel-Layer liefert vor allem schnelle Hinweise und klare „Hard Cases“, aber dominiert nicht die Entscheidung (wenige wirklich hohe Confidences).
- History-/Feedback-Layer (Sender-/Domain-Präferenzen, FeedbackEvents) ist der Hauptträger der Intelligenz: das System lernt aus meinen tatsächlichen Aktionen (Antworten, Archivieren, Löschen, Label-Änderungen).
- Whitelists/Blacklists für ausgewählte Absender/Domains erlauben bewusst gesetzte harte Overrides („immer wichtig“ / „immer Low Priority“), aber nur an wenigen, klaren Stellen.
- In der Anfangsphase kann jede E‑Mail zusätzlich durch den LLM-Layer laufen (oder zumindest alles, was nicht klarer Spam/Newsletter ist), um gute Startdaten zu sammeln; mit steigender Datenbasis übernimmt der History-Layer mehr und der LLM wird selektiver genutzt.

Diese User Story bildet den Rahmen für die spezifische Verbesserung von `noreply@`-Mails unten.

## 🎯 Konkrete User Story – `noreply@`-Mails

Als Email-System-Nutzer möchte ich, dass `noreply@`-Emails basierend auf ihrem Inhalt korrekt klassifiziert werden, damit wichtige Rechnungen, Bestellbestätigungen und Verträge nicht als unwichtig (Importance 0.4) eingestuft werden.

## Aktuelles Problem

- Aktuell: `noreply@` → Importance ≈ 0.4, Confidence ≈ 0.80 (pauschale Einstufung als „eher unwichtig“ / Newsletter/Systemmail).
- Realität: Ein signifikanter Teil dieser Mails ist wichtig (ca. 40 %), z. B.:
  - `noreply@amazon.de` – „Rechnung“ → sollte Importance ~0.85 sein, ist aktuell 0.4.
  - `noreply@booking.com` – „Hotelbuchung“ → sollte Importance ~0.70 sein, ist aktuell 0.4.
  - `noreply@shop.com` – „Newsletter“ → Importance 0.4 ist ok, aber Confidence ist zu hoch.
- Konsequenz: Wichtige System-/Transaktionsmails laufen Gefahr, im Low-Priority-Bereich zu landen.

## Lösungsansätze

1. **Kontextbasierte Regeln**
   - Kombination aus Absender (`noreply@…`) und inhaltlichen Keywords:
   - Beispiele:
     - `noreply@*` + „rechnung“ / „invoice“ → Importance 0.85, hohe Confidence.
     - `noreply@*` + „bestellung“, „order confirmation“, „booking“, „hotelbuchung“ → Importance ≥ 0.80.

2. **Reduktion der Confidence für unsichere Fälle**
   - Generell: `noreply@` ohne starke inhaltliche Schlüsselwörter → niedrige Confidence (z. B. 0.40–0.50), damit History-/LLM-Layer entscheiden können.
   - Newsletter-Fälle (`unsubscribe`, „Newsletter“-Keywords) → Importance niedrig (≤ 0.20), aber keine künstlich hohe Confidence.

3. **Kombinierter Ansatz**
   - Klare positive Signale (Rechnung/Bestellung/Buchung) → hoher Importance-Score + hohe Confidence.
   - Unklare/neutral wirkende `noreply@` → mittlere/niedrige Confidence, sodass nachgelagerte Layer mehr Gewicht haben.

## Akzeptanzkriterien

- [ ] `noreply@` + Rechnung/Invoice → Importance ≥ 0.80.
- [ ] `noreply@` + Bestellung/Order/Booking/Hotelbuchung → Importance ≥ 0.80.
- [ ] `noreply@` + Newsletter/Marketing → Importance ≤ 0.20.
- [ ] `noreply@` ohne klaren Kontext → Confidence ≤ 0.50 (damit andere Layer entscheiden).
- [ ] Tests mit realen Email-Beispielen (mind. 10–20 Mails) zeigen, dass:
  - wichtige Transaktionsmails nicht mehr in „low priority“ verschwinden,
  - klassische Newsletter weiterhin niedrig priorisiert werden.

## Betroffene Dateien

- `agent_platform/classification/importance_rules.py:100–150`
  - `SYSTEM_SENDER_PATTERNS`, `SYSTEM_KEYWORDS` – hier werden aktuell `noreply@` und Keywords wie „invoice“, „rechnung“, „order confirmation“ erfasst.
- `agent_platform/classification/importance_rules.py:380–430`
  - `_check_system_notification_patterns` – kombiniert Sender-Patterns mit Keywords und liefert einen Score für System-/Transaktionsmails.

## Konkrete To-dos

- [ ] Analyse: Bestehendes Verhalten der `NEWSLETTER_SENDER_PATTERNS` und `SYSTEM_SENDER_PATTERNS` für `noreply@` vollständig nachvollziehen (inkl. Interaktion mit Newsletter-Regeln).
- [ ] Anpassung: `SYSTEM_KEYWORDS` ggf. erweitern/gewichten (z. B. stärkere Gewichtung für „invoice“, „rechnung“, „order confirmation“, „booking“, „reservation“).
- [ ] Regel-Logik: In `_check_system_notification_patterns` zusätzliche Gewichtung einführen, wenn sowohl `noreply@` als Senderpattern als auch starke Transaktions-Keywords vorkommen (→ höherer `system_score` → höhere Importance).
- [ ] Confidence-Steuerung: Für `noreply@` ohne starke Keywords ein explizites Confidence-Capping implementieren (z. B. Max-Confidence 0.50) und diese Fälle deutlich als „unsicher“ markieren, damit History/LLM-Layer übernehmen.
- [ ] Tests: Unit- oder Integrationstests für typische `noreply@`-Szenarien hinzufügen (Rechnung, Bestellung, Buchung, Newsletter, neutrale Systemmail) und gegen obige Akzeptanzkriterien prüfen.

## Story Points

- **Schätzung:** 5 Story Points (Medium) – betrifft zentrale Rule-Layer-Logik und erfordert saubere Tests mit realitätsnahen Beispielen.
