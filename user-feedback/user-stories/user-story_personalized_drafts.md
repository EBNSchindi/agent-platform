# User Story – Personalisierte E‑Mail‑Entwürfe mit Lernschleife

## Beschreibung

Als vielbeschäftigter Wissensarbeiter möchte ich, dass automatisch erzeugte E‑Mail‑Entwürfe im Draft-Ordner meine persönliche Schreibweise sowie die bisherige Kommunikation mit dem jeweiligen Kontakt berücksichtigen und das System aus meinen Änderungen am Entwurf gegenüber dem Vorschlag lernt, damit Antworten natürlicher, konsistenter und für mich mit möglichst wenig Nachbearbeitung verschickbar sind.

## Akzeptanzkriterien

- Bei der Erstellung eines Drafts analysiert das System meine bisher versendeten E‑Mails, um meinen allgemeinen Stil (Duzen/Siezen, Formalitätsgrad, typische Begrüßungs- und Schlussformeln, Signatur, Tonfall) zu erfassen und als Stilprofil zu verwenden.
- Zusätzlich werden – sofern vorhanden – die letzten Konversationen mit genau diesem Kontakt (Absender/Empfänger-Kombination) herangezogen, damit der Entwurf den bisherigen Ton und die Beziehung (formell/locker, Sprache, typische Themen) widerspiegelt.
- Der Responder-Agent erzeugt auf Basis des Stilprofils und der kontakt-spezifischen Historie einen Entwurf, der klar als Systemvorschlag gekennzeichnet ist (z. B. im Metadaten-Log oder in der UI).
- Für jede Antwort wird ein Paar gespeichert: ursprüngliche eingehende Mail, System-Draft, tatsächlich versendete Mail (nach meinen Änderungen).
- Das System analysiert regelmäßig die Unterschiede zwischen System-Draft und gesendeter Mail (z. B. angepasste Höflichkeit, hinzugefügter Kontext, geänderte Begrüßung) und aktualisiert daraus sowohl mein globales Stilprofil als auch kontakt-spezifische Präferenzen.
- Im Laufe der Zeit reduziert sich der manuelle Korrekturaufwand messbar (z. B. gemessen an durchschnittlicher Edit-Distanz oder Bearbeitungszeit), weil die Entwürfe immer besser zu meinem persönlichen Stil passen.

