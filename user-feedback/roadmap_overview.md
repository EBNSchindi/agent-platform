# Roadmap & Übersicht: User Feedback Integration

Diese Übersicht priorisiert die User-Stories und To-Dos für die nächste Entwicklungsphase der Agent Platform.

## 1. Quick Wins (Sofortige Umsetzung)
Diese Aufgaben haben geringe Komplexität, aber hohen Nutzen für die Zuverlässigkeit.

- **Rule Layer Optimierung (`noreply` Fix)**
  - *Ziel:* Wichtige Rechnungen/Bestellungen nicht mehr als "Low Priority" verlieren.
  - *Aufwand:* Gering (Anpassung `importance_rules.py`).
  - *Status:* 🟡 In Progress (Prio 1)
  - *Link:* [`to-dos/02_In_Progress/prio1_rule_layer_noreply_todos.md`](to-dos/02_In_Progress/prio1_rule_layer_noreply_todos.md)

- **Label-Synchronisation (Gmail/Ionos)**
  - *Ziel:* Sichtbarkeit der KI-Entscheidungen im Mail-Client.
  - *Aufwand:* Mittel (Config & Orchestrator-Logic).
  - *Status:* 🔴 Open (Prio 1)
  - *Link:* [`to-dos/01_Open/prio1_label_sync_todos.md`](to-dos/01_Open/prio1_label_sync_todos.md)

## 2. Core Features (Mittelfristig)
Diese Features erweitern die Kernfunktionalität und Usability.

- **"Tinder für E-Mails" (Training UI)**
  - *Ziel:* Schnelles Feedback sammeln, um das System zu verbessern.
  - *Aufwand:* Mittel (Neue API-Endpunkte + UI).
  - *Status:* 🔴 Open (Prio 2)
  - *Link:* [`to-dos/01_Open/prio2_tinder_training_todos.md`](to-dos/01_Open/prio2_tinder_training_todos.md)

- **Personalisierte Entwürfe (Style Learning)**
  - *Ziel:* Reduktion der manuellen Editierzeit bei Drafts.
  - *Aufwand:* Hoch (Analyse-Pipeline & Prompt-Engineering).
  - *Status:* 🔴 Open (Prio 2)
  - *Link:* [`to-dos/01_Open/prio2_personalized_drafts_todos.md`](to-dos/01_Open/prio2_personalized_drafts_todos.md)

## 3. Advanced Intelligence (Langfristig)
Tiefgreifende KI-Erweiterungen.

- **RAG & Vektordatenbank (Memory)**
  - *Ziel:* System lernt Kontext aus der gesamten Historie.
  - *Aufwand:* Hoch (Neue Infrastruktur, Embeddings).
  - *Status:* 🔴 Open (Prio 3)
  - *Link:* [`to-dos/01_Open/prio3_rag_memory_todos.md`](to-dos/01_Open/prio3_rag_memory_todos.md)

## Legende
- 🔴 Open
- 🟡 In Progress
- 🟢 Done

## Abhängigkeiten
1. `Label-Sync` sollte vor `Tinder-Training` kommen, da Labels eine Feedback-Form im Client sind.
2. `RAG` ist unabhängig, aber hilfreich für `Personalisierte Entwürfe`.
