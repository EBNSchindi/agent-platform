# Digital Twin Platform – Vision & Strategische Ausrichtung

*Abgeleitet aus `docs/VISION.md` für das interne Projektmanagement.*

## 🎯 Kernziel
Entwicklung eines **lernenden, persönlichen Digital Twins**, der als aktiver Partner agiert, Informationen verarbeitet und proaktiv unterstützt.

**Leitprinzip:** Das System ist lebendig und wächst inkrementell. Arbeit **MIT** dem System, nicht dagegen.

---

## 📍 Roadmap & Phasen

### Phase 1: Foundation (Input & Analyse) – **AKTUELL**
Fokus auf E-Mail-Verarbeitung, Klassifikation und Journaling.
- [x] E-Mail Ingest (Gmail/IMAP)
- [x] Klassifikation (Rule → History → LLM)
- [ ] Event-Log System (Single Source of Truth)
- [ ] Extraktion (Tasks, Entscheidungen)
- [ ] Tagesjournal-Generierung

### Phase 2: Intelligence (Muster & Kontext) – **NEXT**
Verständnis von Beziehungen und Themen.
- [ ] Personen- & Beziehungsanalyse
- [ ] Themen-Erkennung (Recurring Topics)
- [ ] Mustererkennung über Zeit
- [ ] Wochenjournal

### Phase 3: Interaction (Dialog & Core) – **FUTURE**
Natürliche Interaktion und Selbstmodell.
- [ ] Chat-Interface ("Talk to your Twin")
- [ ] Reflexions-Unterstützung
- [ ] Knowledge Graph Visualisierung

---

## 🏗️ Architektur-Säulen

1.  **Input Hub:** Sammelt alle Daten (Aktuell: Nur E-Mail).
2.  **Analysis Engine:** Versteht Intent, Kontext und Priorität.
3.  **Memory System:**
    *   *Event-Log:* Unveränderliche Historie aller Aktionen (Append-Only).
    *   *Memory-Objects:* Aktueller Wissensstand (Tasks, People), abgeleitet aus Events.
4.  **Twin Core:** Das "Gehirn", das Präferenzen und Stil modelliert.
5.  **Twin Interface:** Die Schnittstelle zum Nutzer (aktuell Debug-Views).

---

## ⚖️ System-Prinzipien (Non-Negotiables)

*   **Event-First:** Jede Aktion erzeugt ein Event. Der State leitet sich daraus ab.
*   **Human-in-the-Loop (HITL):** Keine kritischen Entscheidungen ohne Review-Möglichkeit. Das System schlägt vor, der Nutzer entscheidet/korrigiert.
*   **Learning:** Jede Nutzer-Interaktion (Korrektur, Bestätigung) verbessert das Modell.
*   **Modularität:** Klare Trennung der Verantwortlichkeiten.
*   **Pragmatismus:** Kein Overengineering. MVP-Fokus in Phase 1.

---

## 📊 Erfolgsmetriken (Phase 1)
- >90% korrekte E-Mail-Klassifikation.
- Präzise Extraktion von Tasks & Entscheidungen.
- Tägliche, automatische Journal-Generierung.
- Etablierte Feedback-Loops für kontinuierliches Lernen.

