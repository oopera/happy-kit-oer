#!/usr/bin/env python3
"""
Moodle-Backup (.mbz, entpackt)  ->  LiaScript-Markdown.

Liest einen entpackten Moodle-2-Backup-Ordner und erzeugt pro Kursabschnitt
ein Markdown-Fragment in src/ sowie die referenzierten Dateien in media/
und downloads/.

    python tools/moodle2lia.py --backup /pfad/zum/entpackten/backup --section 3

Die Fragmente werden anschliessend von build.py zu README.md zusammengesetzt.

Was bewusst NICHT uebernommen wird:
  * choice-  und feedback-Aktivitaeten (Lehrenden-Ratings) -- serverseitige
    Datenerhebung, die eine statische LiaScript-Seite nicht leisten kann.
  * forum, data -- dito.
  * "Zurueck zur Hauptseite"-Labels -- reine Moodle-Navigationsartefakte.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import unicodedata
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

NULL = "$@NULL@$"

# Aktivitaetstypen, die in der OER-Fassung entfallen (mit Begruendung fuer den Report)
SKIP_MODULES = {
    "choice": "Lehrenden-Rating (serverseitige Datenerhebung)",
    "feedback": "Lehrenden-Feedback (serverseitige Datenerhebung)",
    "forum": "Forum (serverseitige Interaktion)",
    "data": "Datenbank (serverseitige Interaktion)",
}


# --------------------------------------------------------------------------- utils
def slugify(name: str) -> str:
    """Dateiname -> repo-tauglicher Name, Umlaute aufgeloest, Endung erhalten."""
    stem, dot, ext = name.rpartition(".")
    if not dot:
        stem, ext = name, ""
    stem = (stem.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
                .replace("Ä", "Ae").replace("Ö", "Oe").replace("Ü", "Ue")
                .replace("ß", "ss"))
    stem = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode()
    stem = re.sub(r"[^A-Za-z0-9]+", "-", stem).strip("-").lower()
    stem = re.sub(r"-{2,}", "-", stem)
    return f"{stem}.{ext.lower()}" if ext else stem


def text_of(el, tag, default=""):
    v = el.findtext(tag)
    return default if v is None or v == NULL else v.strip()


# ------------------------------------------------------------------ HTML -> Markdown
class Html2Md(HTMLParser):
    """Konverter fuer die HTML-Teilmenge, die Moodle in intro-Feldern erzeugt."""

    SKIP = {"script", "style"}
    INLINE_WRAP = {"strong": "**", "b": "**", "em": "*", "i": "*", "code": "`"}

    def __init__(self, resolve_link=None, resolve_img=None):
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.resolve_link = resolve_link or (lambda u: u)
        self.resolve_img = resolve_img or (lambda u: u)
        self._skip_depth = 0
        self._list_stack: list[dict] = []
        self._href: list[str] = []
        self._link_text: list[list[str]] = []
        self._pending_block = False
        # Verschachtelte Auszeichnung zaehlen: Moodle schachtelt <strong> gern
        # ineinander und um Links herum, doppelte ** ergeben kaputtes Markdown.
        self._wrap_depth: dict[str, int] = {}

    # -- helpers
    def _emit(self, s):
        if self._skip_depth:
            return
        if self._link_text:
            self._link_text[-1].append(s)
        else:
            self.out.append(s)

    def _block(self):
        """Absatztrenner, ohne Leerzeilen zu haeufen."""
        if self.out and not "".join(self.out[-3:]).endswith("\n\n"):
            self.out.append("\n\n")

    # -- tags
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in self.SKIP:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return

        if tag in self.INLINE_WRAP:
            mark = self.INLINE_WRAP[tag]
            if self._wrap_depth.get(mark, 0) == 0:
                self._emit(mark)
            self._wrap_depth[mark] = self._wrap_depth.get(mark, 0) + 1
        elif tag == "br":
            self._emit("  \n")
        elif tag in ("p", "div"):
            self._block()
        elif re.fullmatch(r"h[1-6]", tag):
            self._block()
            # Kurs = #, Abschnitt = ##, Werkzeug = ###  ->  Inhalts-
            # ueberschriften beginnen bei ####, damit die LiaScript-
            # Navigation nicht zerfaellt.
            level = max(4, min(6, int(tag[1])))
            self._emit("#" * level + " ")
        elif tag in ("ul", "ol"):
            self._block()
            self._list_stack.append({"type": tag, "n": 0})
        elif tag == "li":
            if not self._list_stack:
                self._list_stack.append({"type": "ul", "n": 0})
            lvl = self._list_stack[-1]
            lvl["n"] += 1
            indent = "  " * (len(self._list_stack) - 1)
            marker = "- " if lvl["type"] == "ul" else f"{lvl['n']}. "
            self._emit("\n" + indent + marker)
        elif tag == "a":
            self._href.append(self.resolve_link(a.get("href", "")))
            self._link_text.append([])
        elif tag == "img":
            src = self.resolve_img(a.get("src", ""))
            alt = (a.get("alt") or "").replace("]", "")
            if src:
                self._emit(f"![{alt}]({src})")
        elif tag == "iframe":
            # Moodle-Einbettung (H5P) -- als Marker, wird spaeter ersetzt
            self._block()
            self._emit(f"<!--EMBED:{a.get('src','')}-->")

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return

        if tag in self.INLINE_WRAP:
            mark = self.INLINE_WRAP[tag]
            self._wrap_depth[mark] = max(0, self._wrap_depth.get(mark, 0) - 1)
            if self._wrap_depth[mark] == 0:
                self._emit(mark)
        elif tag in ("p", "div") or re.fullmatch(r"h[1-6]", tag):
            self._block()
        elif tag in ("ul", "ol"):
            if self._list_stack:
                self._list_stack.pop()
            self._block()
        elif tag == "a" and self._href:
            href = self._href.pop()
            label = "".join(self._link_text.pop()).strip()
            if not label:
                return
            if href and not href.startswith("#DROP"):
                self._emit(f"[{label}]({href})")
            else:
                self._emit(label)

    def handle_data(self, data):
        if self._skip_depth:
            return
        if not data.strip():
            # Whitespace nur erhalten, wenn er Woerter trennt
            if data and not data.isspace() or " " in data:
                self._emit(" " if data.strip() != data else "")
            return
        txt = re.sub(r"\s+", " ", data)
        self._emit(txt)

    def result(self) -> str:
        s = "".join(self.out)
        s = re.sub(r"[ \t]+\n", "\n", s)
        s = re.sub(r"\n{3,}", "\n\n", s)
        s = re.sub(r"\*\*\s+\*\*", " ", s)          # leere Fettungen
        s = re.sub(r"[ \t]{2,}", " ", s)
        return s.strip()


# --------------------------------------------------------------------------- backup
class Backup:
    def __init__(self, root: Path):
        self.root = root
        self.sections: dict[str, dict] = {}
        self.by_ctx: dict[str, dict] = {}
        self.by_module: dict[str, dict] = {}
        self.files: dict[tuple, dict] = {}
        self._load_sections()
        self._load_activities()
        self._load_files()

    def _load_sections(self):
        for p in self.root.glob("sections/section_*/section.xml"):
            r = ET.parse(p).getroot()
            self.sections[r.get("id")] = {
                "id": r.get("id"),
                "number": int(text_of(r, "number", "0")),
                "name": text_of(r, "name") or "(ohne Titel)",
                "summary": r.findtext("summary") or "",
                "visible": text_of(r, "visible", "1"),
            }

    def _load_activities(self):
        info = ET.parse(self.root / "moodle_backup.xml").getroot().find("information")
        meta = {}
        for a in info.findall(".//contents/activities/activity"):
            meta[a.findtext("moduleid")] = {
                "title": a.findtext("title") or "",
                "sectionid": a.findtext("sectionid"),
                "directory": a.findtext("directory"),
            }
        for mid, m in meta.items():
            d = self.root / m["directory"]
            modname = d.name.rsplit("_", 1)[0]
            f = d / f"{modname}.xml"
            if not f.exists():
                continue
            r = ET.parse(f).getroot()
            act = {
                "moduleid": mid,
                "contextid": r.get("contextid"),
                "modulename": modname,
                "title": m["title"],
                "sectionid": m["sectionid"],
                "dir": d,
                "root": r,
            }
            self.by_ctx[act["contextid"]] = act
            self.by_module[mid] = act

    def _load_files(self):
        for f in ET.parse(self.root / "files.xml").getroot().findall("file"):
            fn = text_of(f, "filename")
            if fn in (".", ""):
                continue
            key = (text_of(f, "contextid"), text_of(f, "filearea"), fn)
            self.files[key] = {
                "hash": text_of(f, "contenthash"),
                "size": int(text_of(f, "filesize", "0")),
                "component": text_of(f, "component"),
                "filearea": text_of(f, "filearea"),
                "filename": fn,
                "contextid": text_of(f, "contextid"),
                "license": text_of(f, "license", "(leer)"),
                "author": text_of(f, "author", "(leer)"),
            }

    def files_in(self, contextid: str, filearea: str | None = None):
        return [v for (c, a, _), v in sorted(self.files.items())
                if c == contextid and (filearea is None or a == filearea)]

    def content_path(self, contenthash: str) -> Path:
        return self.root / "files" / contenthash[:2] / contenthash


# --------------------------------------------------------------------------- convert
class Converter:
    PLACEHOLDER = re.compile(r"\$@(\w+)\*([\d]+)@\$")
    HRW_FILE = re.compile(
        r"https?://elearning\.hs-ruhrwest\.de/pluginfile\.php/(\d+)/(\w+)/(\w+)/\d+/([^\"'\s>]+)")

    def __init__(self, backup: Backup, out: Path, size_limit_mb: float = 10.0):
        self.b = backup
        self.out = out
        self.size_limit = size_limit_mb * 1024 * 1024
        self.copied: dict[str, str] = {}      # hash -> repo-relativer Pfad
        self.oversized: list[dict] = []
        self.dropped: list[tuple[str, str]] = []
        self.warnings: list[str] = []

    # ---------------------------------------------------------------- Dateien
    def _copy(self, meta: dict, kind: str) -> str | None:
        """Datei aus dem Content-Store ins Repo kopieren, Pfad zurueckgeben."""
        h = meta["hash"]
        if h in self.copied:
            return self.copied[h]
        src = self.b.content_path(h)
        if not src.exists():
            self.warnings.append(f"Inhalt fehlt im Backup: {meta['filename']}")
            return None
        if meta["size"] > self.size_limit:
            self.oversized.append(meta)
            self.copied[h] = None
            return None
        sub = "media" if kind == "media" else "downloads"
        dest_name = slugify(meta["filename"])
        dest = self.out / sub / dest_name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            shutil.copy2(src, dest)
        rel = f"{sub}/{dest_name}"
        self.copied[h] = rel
        return rel

    def _find_file(self, ctx: str, filename: str):
        for (c, _a, fn), v in self.b.files.items():
            if c == ctx and fn == filename:
                return v
        return None

    # ------------------------------------------------------------ Link-Aufloesung
    def _resolve(self, url: str) -> str:
        if not url:
            return ""

        # @@PLUGINFILE@@/name.svg  -> media/
        if url.startswith("@@PLUGINFILE@@/"):
            return "#DROP"      # ohne Kontext nicht aufloesbar; Aufrufer setzt Kontext

        # Harte HRW-Moodle-URLs auf Dateien -> downloads/
        m = self.HRW_FILE.search(url)
        if m:
            ctx, _comp, _area, fname = m.groups()
            from urllib.parse import unquote
            fname = unquote(fname)
            meta = self._find_file(ctx, fname)
            if meta:
                p = self._copy(meta, "download")
                if p:
                    return p
            self.warnings.append(f"HRW-Link nicht aufloesbar: {fname}")
            return "#DROP"

        # Moodle-Backup-Platzhalter
        m = self.PLACEHOLDER.search(url)
        if m:
            kind, ident = m.group(1), m.group(2)
            if kind in ("CHOICEVIEWBYID", "FEEDBACKVIEWBYID"):
                return "#DROP"                       # Rating/Feedback entfaellt
            if kind == "COURSESECTIONBYID":
                return "#top"
            if kind == "FOLDERVIEWBYID":
                act = self.b.by_module.get(ident)
                return "#" + anchor(act["title"]) if act else "#top"
            if kind == "HVPEMBEDBYID":
                return f"#DROP"
            if kind == "PLUGINFILEBYCONTEXT":
                return "#DROP"
            return "#DROP"

        return url

    def _img_resolver(self, ctx: str):
        def r(url: str) -> str:
            from urllib.parse import unquote
            if url.startswith("@@PLUGINFILE@@/"):
                fname = unquote(url.split("/", 1)[1])
                meta = self._find_file(ctx, fname)
                if meta:
                    return self._copy(meta, "media") or ""
                return ""
            m = self.PLACEHOLDER.search(url)
            if m and m.group(1) == "PLUGINFILEBYCONTEXT":
                fctx = m.group(2)
                fname = unquote(url.rsplit("/", 1)[-1])
                meta = self._find_file(fctx, fname)
                if meta:
                    return self._copy(meta, "media") or ""
                return ""
            return self._resolve(url)
        return r

    def html(self, raw: str, ctx: str) -> str:
        if not raw:
            return ""
        p = Html2Md(resolve_link=self._resolve, resolve_img=self._img_resolver(ctx))
        p.feed(raw)
        md = p.result()
        # verwaiste Embed-Marker entfernen (H5P wird separat eingesetzt)
        md = re.sub(r"<!--EMBED:[^>]*-->", "", md)
        md = md_cleanup(md)
        # Interne Moodle-Links funktionieren ausserhalb der HRW nicht.
        for hit in INTERNAL_MOODLE.findall(md):
            self.warnings.append(f"interner Moodle-Link bleibt bestehen: {hit}")
        return md.strip()

    # ------------------------------------------------------------------- H5P
    def accordion(self, act: dict) -> str:
        h = act["root"].find(".//hvp")
        data = json.loads(h.findtext("json_content") or "{}")
        ctx = act["contextid"]
        parts = []
        for panel in data.get("panels", []):
            title = self.html(panel.get("title", ""), ctx) or "Details"
            title = title.replace("\n", " ").strip()
            body = self.html(
                panel.get("content", {}).get("params", {}).get("text", ""), ctx)
            body = re.sub(r"^#+\s*", "", body)     # Ueberschrift im Panel unnoetig
            parts.append(
                "<details>\n"
                f"<summary><b>{title}</b></summary>\n\n{body}\n\n</details>")
        return "\n\n".join(parts)

    # --------------------------------------------------------------- Abschnitt
    def section(self, sectionid: str) -> str:
        sec = self.b.sections[sectionid]
        acts = [a for a in self.b.by_ctx.values() if a["sectionid"] == sectionid]
        acts.sort(key=lambda a: int(a["moduleid"]))

        # Reihenfolge aus moodle_backup.xml beibehalten
        order = {}
        info = ET.parse(self.b.root / "moodle_backup.xml").getroot().find("information")
        for i, a in enumerate(info.findall(".//contents/activities/activity")):
            order[a.findtext("moduleid")] = i
        acts.sort(key=lambda a: order.get(a["moduleid"], 0))

        # Werkzeuge = folder-Aktivitaeten; zugehoeriges Accordion per Titel matchen
        folders = [a for a in acts if a["modulename"] == "folder"]
        accordions = {norm(a["title"].replace("Accordeon:", "")): a
                      for a in acts if a["modulename"] == "hvp"}

        for a in acts:
            if a["modulename"] in SKIP_MODULES:
                self.dropped.append((a["title"], SKIP_MODULES[a["modulename"]]))
            elif a["modulename"] == "label" and a["title"].startswith("Zurück zur"):
                self.dropped.append((a["title"], "Moodle-Navigationsartefakt"))

        lines = [f"## {sec['name']}", ""]

        intro = strip_headings(self.html(sec["summary"], ""))
        intro = "\n".join(l for l in intro.split("\n")
                          if "Zurück zur" not in l and l.strip() != "[](#top)")
        intro = md_cleanup(intro)
        if intro:
            lines += [intro, ""]

        if folders:
            lines += ["In diesem Abschnitt findest du folgende Werkzeuge:", ""]
            for f in folders:
                lines.append(f"- [{tool_title(f['title'])}](#{anchor(tool_title(f['title']))})")
            lines.append("")

        for f in folders:
            lines += self.tool(f, accordions)

        return "\n".join(lines)

    def tool(self, folder: dict, accordions: dict) -> list[str]:
        ctx = folder["contextid"]
        title = tool_title(folder["title"])
        raw_intro = folder["root"].findtext(".//intro") or ""

        md = self.html(raw_intro, ctx)
        # Navigationszeilen "Zurueck zur Uebersicht" entfernen
        md = "\n".join(l for l in md.split("\n")
                       if "Zurück zur Übersicht" not in l)
        # Rating-/Feedback-Absatz entfernen. Die zugehoerigen choice-/feedback-
        # Aktivitaeten entfallen (siehe SKIP_MODULES), der Absatz wuerde sonst
        # mit toten Verweisen stehenbleiben.
        before = md
        md = re.sub(r"^#{3,}\s*\**Rating und Feedback\**\s*$.*?(?=^#{3,}\s|\Z)",
                    "", md, flags=re.S | re.M)
        if md == before and "Rating und Feedback" in before:
            self.warnings.append(f"Rating-Absatz in '{title}' nicht entfernt")

        # Badge-Zeile (⏰ … — 👤 …) herausloesen und als Blockquote setzen
        badges = ""
        m = re.search(r"^(#{3,}\s*)?(⏰[^\n]+)$", md, flags=re.M)
        if m:
            badges = m.group(2).strip()
            md = md.replace(m.group(0), "").strip()

        out = ["", f"### {title}", ""]
        if badges:
            out += [f"> {badges}", ""]
        if md:
            out += [md, ""]

        acc = accordions.get(norm(title))
        if acc:
            out += [self.accordion(acc), ""]

        # Materialien
        mats = [f for f in self.b.files_in(ctx, "content")]
        if mats:
            out += ["#### Material zum Download", ""]
            for meta in sorted(mats, key=lambda m: m["filename"]):
                p = self._copy(meta, "download")
                mb = meta["size"] / 1024 / 1024
                if p:
                    out.append(f"- [{meta['filename']}]({p}) — {mb:.1f} MB")
                else:
                    out.append(
                        f"- {meta['filename']} — {mb:.1f} MB "
                        f"*(zu gross fuer das Repository, siehe docs/GROSSE-DATEIEN.md)*")
            out.append("")
        return out


TRACKING = re.compile(r"[?&]utm_[a-z]+=[^)&\s]*")
INTERNAL_MOODLE = re.compile(r"https?://elearning\.hs-ruhrwest\.de/(?!pluginfile)[^)\s]*")


def md_cleanup(s: str) -> str:
    """Repariert die typischen Defekte, die aus Moodles TinyMCE-HTML entstehen."""
    # **fett ** / ** fett**  -> Leerzeichen aus der Auszeichnung herausziehen,
    # sonst rendert Markdown die Sterne als Literale.
    s = re.sub(r"\*\*(\s*)(.+?)(\s*)\*\*",
               lambda m: f"{m.group(1)}**{m.group(2)}**{m.group(3)}", s, flags=re.S)
    # **[**Text**](url)**  -> [**Text**](url)
    s = re.sub(r"\*\*\[\*\*(.+?)\*\*\]\((.*?)\)\*\*", r"[**\1**](\2)", s)
    # leere Ueberschriften (kamen aus <h3></h3>-Huellen)
    s = re.sub(r"^#{1,6}\s*$", "", s, flags=re.M)
    # Auszeichnung in Ueberschriften ist redundant
    s = re.sub(r"^(#{1,6}\s*)\*\*(.+?)\*\*\s*$", r"\1\2", s, flags=re.M)
    # Rueckwaerts-Links auf den Seitenanfang -> reiner Text
    s = re.sub(r"\[([^\]]*)\]\(#top\)", r"\1", s)
    # Tracking-Parameter aus Literaturlinks entfernen
    s = TRACKING.sub("", s)
    s = re.sub(r"\*\*\s*\*\*", "", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def tool_title(name: str) -> str:
    """Ordnernamen wie 'Anleitung Positive Prompts' auf den Werkzeugnamen kuerzen."""
    n = re.sub(r"^Anleitung\s+", "", name.strip())
    return re.sub(r":\s.*$", "", n)          # "Belbin-Test: Finde ..." -> "Belbin-Test"


def strip_headings(s: str) -> str:
    """Ueberschriften zu Fliesstext machen (fuer Abschnitts-Intros)."""
    return re.sub(r"^#{1,6}\s*", "", s, flags=re.M)


def norm(s: str) -> str:
    s = re.sub(r"^(anleitung|workbook)\s+", "", s.strip(), flags=re.I)
    return re.sub(r"\W+", "", s.lower())


def anchor(title: str) -> str:
    a = title.lower()
    for x, y in (("ä", "a"), ("ö", "o"), ("ü", "u"), ("ß", "ss")):
        a = a.replace(x, y)
    return re.sub(r"[^a-z0-9]+", "-", a).strip("-")


# ----------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backup", required=True, type=Path)
    ap.add_argument("--out", default=Path(__file__).resolve().parent.parent, type=Path)
    ap.add_argument("--section", type=int, action="append", required=True,
                    help="Abschnittsnummer (mehrfach moeglich)")
    ap.add_argument("--max-file-mb", type=float, default=10.0)
    args = ap.parse_args()

    b = Backup(args.backup)
    c = Converter(b, args.out, args.max_file_mb)

    for num in args.section:
        sid = next((s["id"] for s in b.sections.values() if s["number"] == num), None)
        if sid is None:
            raise SystemExit(f"Abschnitt {num} nicht gefunden")
        md = c.section(sid)
        name = f"{num:02d}-{anchor(b.sections[sid]['name'])}.md"
        dest = args.out / "src" / name
        dest.write_text(md + "\n", encoding="utf-8")
        print(f"geschrieben: src/{name}  ({len(md.splitlines())} Zeilen)")

    print(f"\nDateien kopiert : {sum(1 for v in c.copied.values() if v)}")
    if c.oversized:
        print(f"zu gross ({args.max_file_mb} MB):")
        for m in c.oversized:
            print(f"   {m['size']/1024/1024:7.1f} MB  {m['filename']}")
    if c.dropped:
        print("nicht uebernommen:")
        for t, why in c.dropped:
            print(f"   - {t[:55]:55} {why}")
    for w in dict.fromkeys(c.warnings):
        print("WARNUNG:", w)


if __name__ == "__main__":
    main()
