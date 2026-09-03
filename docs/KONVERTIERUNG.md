# Konvertierung Moodle → LiaScript

Wie der Moodle-Kurs *Happy Kit V2* (Kurs-ID 33187, Moodle 4.5.13) in diesen
LiaScript-Kurs überführt wird, und was dabei bewusst verloren geht.

## Ablauf

```bash
# 1. Backup entpacken
mkdir -p /pfad/backup && tar xzf sicherung-moodle2-course-33187-*.mbz -C /pfad/backup

# 2. Abschnitte konvertieren  ->  src/1N-*.md + media/ + downloads/
python tools/moodle2lia.py --backup /pfad/backup \
    --section 0 --section 2 --section 3 --section 4 \
    --section 5 --section 6 --section 7 --section 8

# 3. Fragmente zu README.md zusammensetzen
python build.py
```

`README.md` ist erzeugt und wird nicht direkt bearbeitet. Redaktionelle
Änderungen gehören in die Fragmente unter `src/`.

Ein LiaScript-Kurs ist **genau eine Markdown-Datei**. Das `import:` im
Kopfbereich importiert Makros, keine Inhalte — deshalb der Build-Schritt.

## Dateinamen in src/

| Datei | Herkunft |
|---|---|
| `00-head.md` | **handgepflegt** — LiaScript-Kopf, Titel, PERMA-Tabelle |
| `1N-*.md` | **generiert** — je Kursabschnitt, N = Moodle-Abschnittsnummer |

Der Offset 10 ist Absicht: so belegt der handgepflegte Kopf `00-` allein und
ein Aufräum-Glob über die generierten Abschnitte kann ihn nicht miterwischen.
Vor einem Neulauf also `rm src/1*.md`, niemals `rm src/0*.md`.

## Übertragene Abschnitte

| Nr | Abschnitt | Werkzeuge |
|---:|---|---:|
| 0 | Herzlich Willkommen | — |
| 2 | Testimonials | Slider |
| 3 | P — Positive Emotions | 2 |
| 4 | E — Engagement | 2 |
| 5 | R — Relationships | 4 |
| 6 | M — Meaning | 2 |
| 7 | A — Accomplishment | 3 |
| 8 | Check-in Tools | 6 |

**Nicht übertragen:**

- **Abschnitt 1 „Let's Get Started!"** — enthält nur ein Inhaltsverzeichnis
  als Kachelnavigation. LiaScript erzeugt seine Navigation selbst; die
  Kacheln wären doppelt und würden ins Leere zeigen.
- **Abschnitt 9 „Admin-Abschnitt"** — im Moodle-Kurs auf *versteckt* gesetzt.
  Enthält Vorlagen, Codeschnipsel, Foren und interne Materialien. Gehört
  nicht in eine OER-Veröffentlichung.

## Was übernommen wird

| Moodle | LiaScript | Anmerkung |
|---|---|---|
| Abschnitt (`section`) | `##`-Kapitel | Name und Einleitungstext |
| `folder` | `###`-Werkzeug | Ordnername wird zum Werkzeugnamen |
| `folder`-Intro (HTML) | Markdown | Kurzbeschreibung, Badge-Zeile als Zitat |
| `hvp` H5P.Accordion | `<details>`-Blöcke | ein Block je Panel |
| `hvp` H5P.ImageSlider | untereinander gesetzte Bilder | Testimonials |
| `page` | `###`-Unterabschnitt | „Weitere Check-in-Fragen" |
| `<video>` im Abschnittstext | `!?[](…)` | LiaScript-Videosyntax |
| Ordner-Inhalte | `downloads/` + Liste | Dateinamen werden slugifiziert |
| Bilder in Intros | `media/` | über den contenthash aufgelöst |

Die Zuordnung Ordner → Accordion läuft über `match_keys()`, das mehrere
Titelvarianten probiert (voller Name, Teil vor und hinter dem Doppelpunkt).
Nötig, weil beide Schreibweisen vorkommen: bei *„Belbin-Test: Finde deine
Teamrolle"* steht der Werkzeugname **vor** dem Doppelpunkt, bei
*„Check-in: Self-Monitoring"* **dahinter**. `display_titles()` kürzt einen
Titel deshalb nur, solange er dadurch eindeutig bleibt.

Die 16 Accordions des Kurses enthalten ausschließlich Text in 3–4 Panels
(`Schritt-für-Schritt Anleitung`, `Tipps & Best Practice`, `Warum und wie das
wirkt`, `Literatur für Neugierige`) — keine Quizze, keine interaktiven
Übungen. Deshalb lassen sie sich verlustfrei als `<details>` abbilden, was
sowohl LiaScript als auch GitHub nativ rendert.

## Was NICHT übernommen wird

| Aktivität | Anzahl | Grund |
|---|---|---|
| `choice` (Lehrenden-Rating) | 14 | serverseitige Datenerhebung |
| `feedback` (Lehrenden-Feedback) | 15 | serverseitige Datenerhebung |
| `forum` | 2 | serverseitige Interaktion |
| `data` (Literaturdatenbank) | 1 | serverseitige Interaktion |
| `label` „Zurück zur Hauptseite" | 6 | Moodle-Navigationsartefakt |

**Der Kern des Problems:** LiaScript rendert vollständig clientseitig. Quiz-
und Umfragezustände liegen im Browser, nicht auf einem Server. SCORM 1.2
verliert sie beim Neuladen, SCORM 2004 hält sie nur innerhalb eines LMS.
Eine zentrale Auswertung der Lehrenden-Ratings ist damit nicht möglich.

Das ist vertretbar, weil diese Instrumente **interne Evaluationswerkzeuge**
sind und nicht zum Lernmaterial gehören. Sie bleiben im `.mbz` erhalten, das
parallel auf twillo veröffentlicht wird. Wer sie in der statischen Fassung
braucht, müsste auf ein externes Umfragewerkzeug verlinken.

## Bekannte offene Punkte

- **Interne Moodle-Links.** Einzelne Anleitungen verlinken hart auf
  `elearning.hs-ruhrwest.de/mod/folder/view.php?id=…`. Diese URLs sind
  ausserhalb der HRW nicht erreichbar. Der Konverter warnt darüber; die
  Links müssen redaktionell ersetzt werden.
- **Wooclap-Abhängigkeit.** Mehrere Werkzeuge setzen Wooclap-Vorlagen im
  HRW-Mandanten voraus. Für eine OER-Nachnutzung braucht es entweder eine
  öffentliche Vorlage oder eine werkzeugneutrale Beschreibung.
- **Grosse Dateien.** Siehe `GROSSE-DATEIEN.md`.
- **Lizenzen.** Siehe `../LICENSE` — die Rechteklärung ist Voraussetzung
  für jede Veröffentlichung.
