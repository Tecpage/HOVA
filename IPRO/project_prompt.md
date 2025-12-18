
# Projekt Y / IPRO – Persistenter Arbeits‑Prompt (YAML‑SSOT)

Dieses Dokument ist die **verbindliche Referenz**, wie Projekt Y (Bereich IPRO) aufgebaut ist und wie wir damit arbeiten.
Es dient als „Prompt im Projekt“, falls Chat‑Kontext oder Wissen verloren geht.

---

## 1) Leitprinzipien

1. **Keine Datenbank**
   Projekt Y arbeitet im aktuellen Setup vollständig **datenbankfrei**.

2. **YAML ist Single Source of Truth (SSOT)**
   Fachliche Wahrheit liegt ausschließlich in YAML‑Dateien im Projektordner.

3. **Append‑Only für Zeitreihen / Bewegungsdaten**
   Zeitabhängige Daten (z. B. Sollstellungen) werden **nicht überschrieben**.
   Korrekturen erfolgen als **neuer Eintrag** (später ggf. `kind: correction`).

4. **Revisionssicherheit**
   - menschenlesbar
   - diff‑freundlich
   - Referenzen über stabile IDs
   - jede Änderung wird dokumentiert (`change_log`)

---

## 2) Ordnerstruktur (aktuell)

```
Y/IPRO/
├─ tenants.yaml           # Stammdaten: Verwaltung + externe Mieter + Kontakte + Adressen
├─ payments.yaml          # Sollstellungen (Rent Roll) – historisch + aktuell (append-only)
├─ technical_assets.yaml  # Technische Anlagen (Bestand + Wartung)
└─ project_prompt.md      # Dieses Dokument
```

---

## 3) tenants.yaml – Stammdaten

### Zweck
- Verwaltung (IPRO) als Organisation
- Externe Mieter (TEN‑IDs)
- Mieternummern (`tenant_no`)
- Ansprechpartner & E‑Mails (Mitteilungen/Rechnungen)
- Postanschriften (über YAML‑Anker)

### Struktur
- `organisations:` enthält mind. `ORG-0001` (IPRO)
- `address_templates:` enthält wiederverwendbare Adress‑Objekte als YAML‑Anker
- `tenants:` Liste der Mieter mit `id: TEN-XXXX`

### Regeln
- IDs sind stabil: `TEN-0001`, `TEN-0002`, …
- `managed_by` verweist auf `ORG-0001`
- E‑Mails:
  - `email_notifications` und `email_invoices` als YAML‑Listen (auch bei 1 Adresse)
- Adressen:
  - **keine Duplikate**: `address: *addr_…` referenziert Templates
- Änderungen:
  - jede fachliche Änderung erhält einen Eintrag in `change_log`

---

## 4) payments.yaml – Sollstellungen (Rent Roll)

### Zweck
- Abbildung der **monatlichen Sollstellungen** je Mieter (nicht Ist‑Zahlungen)
- historisch korrekt, prüfbar, append‑only

### Struktur
- `meta`, `validation`, `assistant_prompt_snapshot` am Dateikopf
- `payments:` enthält pro Mieter einen Record für `period` + `as_of`

### Regeln
- `kind` ist im aktuellen Zweig **rent_roll** (Ist‑Zahlungen werden **nicht** modelliert)
- `components` enthält:
  - Bausteine (BK/NK, Heizung, Lager/Keller, Parkplatz, Reinigung, Poststelle, Verwaltergeb., sonstige DL)
  - plus `base_rent_net` als **Rest**, damit gilt:
    `sum(components) == total_net`
- Referenzen:
  - `tenant_id` muss in `tenants.yaml` existieren
- Änderungen:
  - append‑only: keine bestehenden Records überschreiben
  - jede Änderung erhält einen Eintrag in `change_log`

### Wichtiger Hinweis (Soll vs. Verrechnung)
Manche Tabellen enthalten neben Sollwerten zusätzliche Spalten (z. B. Verrechnung/Abweichung/0‑Werte).
Diese gehören **nicht** in `payments.yaml`, solange wir nur **Soll (rent_roll)** führen.
Falls Verrechnungen/Abweichungen modelliert werden sollen, erfolgt das separat (z. B. später `kind: correction` oder eigenes File).

---

## 5) technical_assets.yaml – Technische Anlagen

### Zweck
- Anlagenbestand (HVAC/Kälte) als SSOT
- Wartungsstände (letzter Service / nächste Wartung)
- Optionale Zuordnung zu Mietern (assigned_tenant)

### Struktur
- `meta`, `validation`, `assistant_prompt_snapshot` am Dateikopf
- `assets:` Liste mit `id: TA-0001 …`

### Regeln
- IDs stabil: `TA-0001 …` (keine Wiederverwendung)
- Seriennummern sollten eindeutig sein; Duplikate markieren/prüfen
- Wartungsdaten Format: `YYYY-MM`
- `assigned_tenant` (falls gesetzt) muss in `tenants.yaml` existieren
- Änderungen:
  - `change_log` wird fortgeschrieben

---

## 6) Änderungsdokumentation (verbindlich)

Jede fachliche Änderung wird in der betroffenen YAML‑Datei dokumentiert:

```yaml
change_log:
  - ts: "YYYY-MM-DD"
    file: "<datei>.yaml"
    summary: "<kurze Beschreibung>"
    source: "<Quelle / Anlass>"
```

---

## 7) Rolle von ChatGPT im Projekt

ChatGPT ist:
- Struktur‑ und Konsistenzinstanz (IDs, Referenzen)
- Validator (Summen, Formate, Verknüpfungen)
- Normalisierer (Listen/Anker/Formatierung)
- Schreiber in Projektdateien (gezielte Patches)

ChatGPT ist **nicht**:
- eine Datenbank
- ein stiller Hintergrunddienst
- eine Blackbox (alle Änderungen sind im YAML sichtbar)

---

## 8) Arbeitsmodus (Minimalprozess)

1) Daten/Änderung im Chat liefern (Text, Tabellen, Listen)
2) ChatGPT normalisiert in YAML‑Struktur
3) Patch wird in die Datei geschrieben
4) `change_log` wird ergänzt
5) Validierung/Checks werden aktualisiert (falls relevant)

---

## 9) Projekt-Historie (was bisher umgesetzt wurde)

- Aufbau YAML-SSOT ohne Datenbank; Entscheidung: Trennung Stammdaten (tenants) vs. Sollstellungen (payments) vs. Technik (technical_assets).
- `tenants.yaml`: IPRO als `ORG-0001`; externe Mieter `TEN-0001…TEN-0061` angelegt; `tenant_no` ergänzt; Ansprechpartner + E-Mails (Mitteilungen/Rechnungen) ergänzt.
- `tenants.yaml`: Postanschriften ergänzt; Standardisierung über YAML-Anker (`address_templates`); jede Änderung im `change_log` dokumentiert.
- `payments.yaml`: `meta`/`validation`/`assistant_prompt_snapshot` ergänzt; Rent Roll Nov 2025 (`as_of: 2025-11-01`, `period: 2025-11`) vollständig übernommen; `base_rent_net` als Rest eingeführt zur Summenvalidierung.
- `payments.yaml`: Fix durchgeführt: fehlender `tenant_id` bei `PAY-2025-11-01-TEN-0054` ergänzt.
- `payments.yaml`: Klarstellung: Verrechnungs-/Abweichungsspalten aus Tabellen sind nicht Teil von `rent_roll`; Ist-Zahlungen werden in diesem Projektzweig nicht modelliert.
- `technical_assets.yaml`: Anlagenbestand Klima/Kälte vollständig (`TA-0001…TA-0015`) erfasst; Wartungsdaten (`2025-10`/`2026-10`) ergänzt; Validierungsregeln und Prompt-Snapshot ergänzt; Hinweis auf mögliche Seriennummern-Duplikate.

## 10) Versionierung & Wiederherstellung (wenn Chat-Kontext verloren geht)

1) **Git ist empfohlen**: Der Projektordner `Y/` wird als Git-Repository geführt; jede Änderung wird committet (Commit-Message = `change_log.summary`).
2) **`change_log` ist verpflichtend**: Jede YAML-Datei enthält `change_log` mit Datum, Zusammenfassung und Quelle.
3) **Dateien sind die Wahrheit**: Bei Verlust des Chat-Kontexts werden die Projektdateien (`tenants.yaml`, `payments.yaml`, `technical_assets.yaml`, `project_prompt.md`) als Ausgangspunkt genommen.
4) **Arbeitsmodus zur Rekonstruktion**:
   - Datei im Editor öffnen und im Chat teilen (oder relevante Ausschnitte)
   - ChatGPT validiert Referenzen/Summen und ergänzt Änderungen
5) **Revisionsregel**: Bewegungsdaten (`payments.yaml`) sind append-only; Korrekturen nur als neue Records.

**Wichtig:** ChatGPT hat ohne Öffnen/Teilen der Dateien keinen autonomen Zugriff auf lokale Dateien. Sobald die Dateien im Chat-Kontext angezeigt oder geteilt werden, kann ChatGPT anhand dieses Prompts und der YAML-Inhalte sofort wieder konsistent weiterarbeiten.
### Generierte Dateien
- `dashboard/index.html`
- `dashboard/app.js`
- `dashboard/data/*.json`

Diese Dateien werden **automatisch aus YAML erzeugt** und dürfen **nicht manuell geändert** werden.

**Dieser Prompt ist verbindlich für die weitere Arbeit an Projekt Y / IPRO.**