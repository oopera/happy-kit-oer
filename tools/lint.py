#!/usr/bin/env python3
"""
Prueft den generierten Kurs (README.md) auf die Fehler, die bei der
Konvertierung aus Moodle-HTML typischerweise entstehen.

    python tools/lint.py

Exit-Code 1, wenn Fehler gefunden wurden; Warnungen allein sind nicht fatal.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "README.md"

errors: list[str] = []
warnings: list[str] = []


def check(md: str) -> None:
    lines = md.split("\n")

    # -- Auszeichnung: ** muss paarweise auftreten (pro Absatz betrachtet)
    for block in re.split(r"\n\s*\n", md):
        if block.lstrip().startswith(("<details", "</details", "<!--")):
            continue
        if block.count("**") % 2:
            errors.append(f"unpaarige Fettung: {block.strip()[:70]}…")

    # -- leere / uebersprungene Ueberschriften
    prev = 0
    for i, l in enumerate(lines, 1):
        m = re.match(r"^(#{1,6})(\s*)(.*)$", l)
        if not m:
            continue
        lvl, text = len(m.group(1)), m.group(3).strip()
        if not text:
            errors.append(f"Zeile {i}: leere Ueberschrift")
        if prev and lvl > prev + 1:
            warnings.append(f"Zeile {i}: Ebene springt von h{prev} auf h{lvl} ({text[:40]})")
        prev = lvl

    # -- Reste aus dem Moodle-Backup
    for pat, msg in ((r"\$@\w+\*?\d*@\$", "nicht aufgeloester Moodle-Platzhalter"),
                     (r"@@PLUGINFILE@@", "nicht aufgeloester PLUGINFILE-Verweis"),
                     (r"<!--EMBED:", "verwaister Embed-Marker"),
                     (r"utm_\w+=", "Tracking-Parameter im Link"),
                     (r"Zurück zur (Haupt|Übersicht)", "Moodle-Navigationsrest"),
                     (r"Rating und Feedback", "Rating-Absatz nicht entfernt")):
        for m in re.finditer(pat, md):
            errors.append(f"{msg}: …{md[max(0,m.start()-30):m.end()+20]}…".replace("\n", " "))

    # -- <details> ausbalanciert
    o, c = md.count("<details>"), md.count("</details>")
    if o != c:
        errors.append(f"<details> unbalanciert: {o} geoeffnet, {c} geschlossen")

    # -- lokale Verweise existieren
    for m in re.finditer(r"\[([^\]]*)\]\(([^)]+)\)", md):
        url = m.group(2)
        if url.startswith(("http://", "https://", "#", "mailto:")):
            continue
        if not (ROOT / url).exists():
            errors.append(f"Datei fehlt: {url}")

    # -- Anker der Werkzeugliste zeigen auf existierende Ueberschriften
    anchors = {re.sub(r"[^a-z0-9]+", "-",
                      re.sub(r"^#{1,6}\s*", "", l).lower()
                      .replace("ä", "a").replace("ö", "o")
                      .replace("ü", "u").replace("ß", "ss")).strip("-")
               for l in lines if l.startswith("#")}
    for m in re.finditer(r"\]\(#([a-z0-9-]+)\)", md):
        if m.group(1) not in anchors and m.group(1) != "top":
            warnings.append(f"Anker zeigt ins Leere: #{m.group(1)}")

    # -- Links, die ausserhalb der HRW nicht funktionieren
    for u in sorted(set(re.findall(r"https?://elearning\.hs-ruhrwest\.de[^\s)]*", md))):
        warnings.append(f"interner Moodle-Link (ausserhalb der HRW tot): {u}")


def main() -> None:
    if not DOC.exists():
        sys.exit("README.md fehlt -- erst `python build.py` ausfuehren")
    check(DOC.read_text(encoding="utf-8"))

    for w in dict.fromkeys(warnings):
        print("WARNUNG:", w)
    for e in dict.fromkeys(errors):
        print("FEHLER :", e)

    n_e, n_w = len(set(errors)), len(set(warnings))
    print(f"\n{n_e} Fehler, {n_w} Warnungen")
    sys.exit(1 if n_e else 0)


if __name__ == "__main__":
    main()
