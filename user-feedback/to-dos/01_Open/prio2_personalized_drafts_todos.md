# To-dos – Personalisierte E-Mail-Entwürfe (Style Learning)

## Ziel
Der Agent soll den persönlichen Schreibstil des Nutzers (Tone of Voice, Begrüßungen, Struktur) lernen und automatisch anwenden. Dies geschieht durch Vergleich von *Entwurf* vs. *tatsächlich gesendeter Mail*.

## Technische Analyse
- **Datenquelle:** `ProcessedEmail` Tabelle enthält bereits `draft_generated` und kann mit gesendeten Mails verknüpft werden.
- **Speicherort:** `SenderPreference` oder eine neue Tabelle `UserStyleProfile`.

## Backend-Tasks

### Style-Analyse Pipeline
- [ ] **Diff-Analyzer:**
  - Implementierung einer Logik (`agent_platform/learning/style_analyzer.py`), die Unterschiede zwischen `generated_draft` und `final_sent_email` erkennt.
  - Extraktion von Merkmalen:
    - Formale vs. informelle Anrede.
    - Länge der Sätze.
    - Nutzung von Emojis.
    - Signatur-Variationen.
- [ ] **Feedback-Loop Integration:**
  - Trigger: Wenn eine Mail gesendet wird (`GmailService.send_email` oder via Webhook), prüfen ob es dazu einen Draft gab.
  - Wenn ja -> Style-Update anstoßen.

### Datenmodell
- [ ] **Erweiterung `SenderPreference`:**
  - Hinzufügen von Feldern für sender-spezifischen Stil (z.B. `preferred_tone`: "formal", "brief", "friendly").
- [ ] **Globales Style-Profil:**
  - Neue Config oder Tabelle für globale Präferenzen (z.B. "Nutzer duzt meistens Vornamen", "Nutzer nutzt nie 'Sehr geehrte'").

### Agent Integration
- [ ] **Prompt-Engineering (`modules/email/agents/responder.py`):**
  - `format_email_for_response` erweitern:
    - Laden des Style-Profils für den spezifischen Absender.
    - Injektion in den System-Instruction Block ("Style Note: You usually reply to this person informally.").

## Testing & Validierung
- [ ] **Test-Suite:** Vergleich von generierten Antworten vor und nach dem Training mit einer Test-Historie.

