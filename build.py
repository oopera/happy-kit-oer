#!/usr/bin/env python3
"""
Setzt die Fragmente aus src/ zu README.md zusammen.

Ein LiaScript-Kurs ist genau eine Markdown-Datei -- `import:` im Kopf importiert
Makros, keine Inhalte. Deshalb wird der Kurs aus nummerierten Fragmenten
gebaut, damit die einzelnen Abschnitte getrennt bearbeitbar und in git
sinnvoll diffbar bleiben.

    python build.py            # baut README.md
    python build.py --check    # prueft nur, ob README.md aktuell ist
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
OUT = ROOT / "README.md"

BANNER = ("<!-- Diese Datei wird von build.py erzeugt. "
          "Nicht direkt bearbeiten -- stattdessen die Fragmente in src/. -->\n")


def render() -> str:
    parts = [p.read_text(encoding="utf-8").rstrip()
             for p in sorted(SRC.glob("*.md"))]
    if not parts:
        sys.exit("src/ enthaelt keine Fragmente")
    return BANNER + "\n" + "\n\n".join(parts) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="nur pruefen, nichts schreiben")
    args = ap.parse_args()

    new = render()
    if args.check:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != new:
            sys.exit("README.md ist nicht aktuell -- bitte `python build.py` ausfuehren")
        print("README.md ist aktuell")
        return

    OUT.write_text(new, encoding="utf-8")
    n = len(list(SRC.glob("*.md")))
    print(f"README.md geschrieben ({n} Fragmente, {len(new.splitlines())} Zeilen)")


if __name__ == "__main__":
    main()
