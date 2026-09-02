# Grosse Dateien

Der Konverter übernimmt standardmässig keine Dateien über **10 MB**
(`--max-file-mb`). Im Gesamtkurs betrifft das:

| Datei | Grösse | Abschnitt |
|---|---:|---|
| `Happy-Kit-Anleitungen_Untertitel.mp4` | 57,9 MB | Willkommen |
| `Happy Kit_Positive Prompts_Foliensatz.pptx` | 33,8 MB | P |
| `Happy Kit_Positive Prompts_Foliensatz_engl.pptx` | 33,8 MB | P |
| `2_Happy Kit_Monatsaushänge.pdf` | 17,8 MB | Admin |
| `infobox-fur-lehrende-7691 (1).h5p` | 12,8 MB | Admin |

Der gesamte Kurs bringt 370,8 MB mit — zu viel für ein normales
Git-Repository, und `git-lfs` ist auf diesem Rechner nicht installiert.

## Empfohlenes Vorgehen

**1. Video auf das TIB AV-Portal.** ORCA.nrw sieht für Videos ohnehin das
TIB AV-Portal vor, nicht den Upload über twillo. Das nimmt allein 57,9 MB
aus dem Repository und bringt zusätzlich einen zitierfähigen DOI.

**2. Die beiden Foliensätze verkleinern.** Je 33,8 MB für einen
PowerPoint-Foliensatz deutet auf unkomprimierte Bilder hin. In PowerPoint:
*Datei → Informationen → Medien komprimieren*, bzw. *Bilder komprimieren*
mit 150 dpi. Erfahrungsgemäss bleiben davon wenige MB übrig.

**3. Bilder im Kurs prüfen.** 146 PNG-Dateien belegen zusammen 111,4 MB —
im Schnitt 780 KB pro Bild. Das sind mit hoher Wahrscheinlichkeit
unkomprimierte Screenshots. Eine verlustfreie Optimierung (`oxipng`,
`pngquant`) oder die Umwandlung nach WebP dürfte den Kurs mehr als
halbieren.

**4. Erst danach über LFS nachdenken.** Wenn nach Schritt 1–3 immer noch
einzelne grosse Dateien übrig sind, ist `git-lfs` die richtige Antwort —
vorher lohnt sich der Aufwand nicht.

## Übergangslösung

Bis dahin verweist der generierte Kurs für diese Dateien auf diese Seite,
statt einen toten Link zu erzeugen. Die betroffenen Downloads sind in
`.gitignore` ausgenommen.
