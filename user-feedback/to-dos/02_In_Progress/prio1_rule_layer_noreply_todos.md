# To-do – Überarbeitung Rule Layer: Kontextbasierte Klassifizierung von `noreply@`-Mails

## 🎯 Ziel
`noreply@`-Mails sollen nicht pauschal als unwichtig (Newsletter/System) eingestuft werden. Wenn sie wichtige Keywords enthalten (z.B. "Rechnung", "Booking"), müssen sie hoch priorisiert werden.

## Status: 🟡 In Progress (Analyse abgeschlossen, Implementierung offen)

### Bereits vorhanden
- Grundlegende Erkennung von `noreply`-Adressen (`SYSTEM_SENDER_PATTERNS`).
- Absenkung der Confidence auf 0.50, damit LLM übernehmen kann.

### Was fehlt (Gap Analysis)
- **Keine Hochstufung:** Es fehlt die Logik, die bei `noreply` + "Rechnung" *direkt* `importance=0.85` setzt. Aktuell bleibt es bei "System Notification" (Low Importance).
- **Fehlende Keywords:** Liste `SYSTEM_KEYWORDS` ist unvollständig (z.B. "Buchung", "Ticket" fehlen).

## Betroffene Datei
- `agent_platform/classification/importance_rules.py`
  - Klasse `RuleLayer`
  - Methoden `_check_system_notification_patterns` und `classify`

## Konkrete To-dos (Technisch)

### 1. Keyword-Listen erweitern (`agent_platform/classification/importance_rules.py`)
- [ ] **Konstanten anpassen:**
  - Erweitern von `SYSTEM_KEYWORDS` um spezifische Transaktions-Begriffe:
    - `"invoice"`, `"rechnung"`, `"payment"`, `"zahlung"`, `"order"`, `"bestellung"`, `"booking"`, `"buchung"`, `"ticket"`, `"versand"`, `"shipping"`.
  - Ggf. Einführung einer neuen Liste `CRITICAL_TRANSACTION_KEYWORDS` für noch höhere Gewichtung.

### 2. Logik-Anpassung in `_check_system_notification_patterns`
- [ ] **Kombinations-Logik implementieren:**
  - Wenn `sender` matches `noreply@` **UND** `body/subject` contains `CRITICAL_TRANSACTION_KEYWORDS`:
    - Return `score` erhöhen (z.B. +3 statt +1).
    - Return `matches` mit explizitem Hinweis (z.B. `"critical_transaction:invoice"`).

### 3. Klassifizierungs-Logik in `classify` Methode
- [ ] **Priorisierung anpassen:**
  - Aktuell: `noreply` -> `importance=0.4`, `confidence=0.80`.
  - Neu: Wenn `system_score` hoch (durch Transaktions-Keywords):
    - Setze `importance=0.85`.
    - Setze `category="finance"` oder `"wichtig_todo"`.
    - Behalte hohe `confidence`.
  - Neu: Wenn `noreply` OHNE Keywords (reines System-Ping):
    - Setze `confidence=0.50` (Deckelung).
    - Damit kann der History-Layer oder LLM-Layer überschreiben.

### 4. Tests
- [ ] **Test-Cases erstellen (`tests/classification/test_importance_rules.py`):**
  - `noreply@amazon.de` + "Ihre Rechnung" -> Expect High Importance.
  - `noreply@slack.com` + "New login" -> Expect Medium/Low Importance.
  - `noreply@marketing.com` + "Newsletter" -> Expect Low Importance (via Newsletter Check).
