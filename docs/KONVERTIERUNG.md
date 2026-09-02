# Konvertierung Moodle → LiaScript

Wie der Moodle-Kurs *Happy Kit V2* (Kurs-ID 33187, Moodle 4.5.13) in diesen
LiaScript-Kurs überführt wird, und was dabei bewusst verloren geht.

## Ablauf

```bash
# 1. Backup entpacken
mkdir -p /pfad/backup && tar xzf sicherung-moodle2-course-33187-*.mbz -C /pfad/backup

# 2. Abschnitt(e) konvertieren  ->  src/NN-*.md + media/ + downloads/
python tools/moodle2lia.py --backup /pfad/backup --section 3

# 3. Fragmente zu README.md zusammensetzen
python build.py
```

`README.md` ist erzeugt und wird nicht direkt bearbeitet. Redaktionelle
Änderungen gehören in die Fragmente unter `src/`.

Ein LiaScript-Kurs ist **genau eine Markdown-Datei**. Das `import:` im
Kopfbereich importiert Makros, keine Inhalte — deshalb der Build-Schritt.

## Was übernommen wird

| Moodle | LiaScript | Anmerkung |
|---|---|---|
| Abschnitt (`section`) | `##`-Kapitel | Name und Einleitungstext |
| `folder` | `###`-Werkzeug | Ordnername wird zum Werkzeugnamen |
| `folder`-Intro (HTML) | Markdown | Kurzbeschreibung, Badge-Zeile als Zitat |
| `hvp` H5P.Accordion | `<details>`-Blöcke | ein Block je Panel |
| Ordner-Inhalte | `downloads/` + Liste | Dateinamen werden slugifiziert |
| Bilder in Intros | `media/` | über den contenthash aufgelöst |

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
