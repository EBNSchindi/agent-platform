# User Story – „Tinder für Emails“: Interaktives Training der Klassifizierung

## Beschreibung

Als Nutzer der E‑Mail-Agenten-Plattform möchte ich eine schnelle, spielerische Oberfläche („Tinder für Emails“), in der mir echte, vom System vorklassifizierte Mails nacheinander angezeigt werden und ich mit einfachen Aktionen (z. B. Swipe/Buttons) festlegen kann, wie ich diese Mail einordnen würde, damit das System direkt aus meinen Entscheidungen lernen kann und die Wichtigkeits- und Kategorien-Vorhersagen immer besser zu meinem persönlichen Empfinden passen.

## Akzeptanzkriterien

- Die Oberfläche zeigt mir jeweils eine einzelne reale E‑Mail (oder ein repräsentatives Snippet) an, inklusive:
  - Betreff, Absender, Datum, kurzer Auszug aus dem Body.
  - Aktuelle System-Vorhersage (Kategorie, Importance, Confidence) als Vorschlag („System denkt: nice_to_know, 0.35, Confidence 0.78“).
- Ich kann mit sehr wenigen, klaren Aktionen antworten, z. B.:
  - „Wichtig / Action Required“
  - „Nice to know / Low Priority“
  - „Newsletter / Marketing“
  - „Spam“
  - Optional: „Überspringen“ / „Weiß nicht“.
- Jede meiner Entscheidungen erzeugt einen strukturierten Feedback-Eintrag (z. B. `FeedbackEvent`), der festhält:
  - Originale System-Klassifikation (Kategorie, Importance, Confidence, Layer).
  - Meine gewählte Kategorie / Wichtigkeit.
  - Timestamps und Basis-Kontext (Absender, Domain, Betreff).
- Das System nutzt diese Feedback-Daten, um:
  - Sender-/Domain-Präferenzen (`SenderPreference`, `DomainPreference`) zu aktualisieren.
  - Rule- und History-Layer mittelfristig zu kalibrieren (z. B. geänderte Prioritäten für bestimmte Pattern).
  - LLM-Prompts/Parameter ggf. anzupassen (z. B. Sensitivität für bestimmte Inhalte).
- Es gibt einen einfachen „Trainingsmodus“, in dem mir ein begrenztes Sample an Emails (z. B. 20–50 pro Session) präsentiert wird, idealerweise eine Mischung aus:
  - Fällen, bei denen sich Rules/History/LLM uneins sind (mittlere Confidence).
  - Repräsentativen Alltagsmails (Transaktionen, Newsletter, persönliche Kommunikation).
- Am Ende einer Session erhalte ich eine kurze Rückmeldung (z. B. „Du hast heute 30 Mails gelabelt – Danke! Diese Daten verbessern vor allem Layer 2 (Historie).“).

