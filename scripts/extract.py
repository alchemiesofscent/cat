"""Extract the CMG work catalogues (Word/Excel, 2019-2020) into data/catalogue.json.

Sources (not committed; read from the OneDrive folder):
  Hippocrates/Hippocrates_Werke_<date>.docx      35-column "Werke" table
  Other Authors/<Author>_Werke_<date>.docx        same 35-column table, one file per author
  Galen/Galen DB.xlsx                              titles, Kuehn, editions, Diels/Pinakes/TLG/Fichtner
  Mss/galen mss table.docx                         Galen manuscripts with digitization links (Nov 2020)

Usage: python scripts/extract.py ["/mnt/d/onedrive/13 CMG"]
"""
import difflib, json, re, sys, unicodedata
from pathlib import Path

import docx
import openpyxl
from docx.oxml.ns import qn

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else "/mnt/d/onedrive/13 CMG")
OUT = Path(__file__).resolve().parent.parent / "data" / "catalogue.json"

W_T, W_DEL, W_INS, W_HL, W_TAB, W_BR, W_P = (qn(x) for x in
    ("w:t", "w:del", "w:ins", "w:hyperlink", "w:tab", "w:br", "w:p"))
R_ID = qn("r:id")


# ---------- rich text: list of [text, url_or_None] ----------

def clean(s):
    s = s.replace("\xa0", " ").replace("\t", " ")
    return re.sub(r"[ ]{2,}", " ", s)


def merge(segs):
    out = []
    for t, u in segs:
        if not t:
            continue
        if out and out[-1][1] == u:
            out[-1][0] += t
        else:
            out.append([t, u])
    # trim outer whitespace
    while out and not out[0][0].strip():
        out.pop(0)
    while out and not out[-1][0].strip():
        out.pop()
    if out:
        out[0][0] = out[0][0].lstrip()
        out[-1][0] = out[-1][0].rstrip()
    return out


def cell_rich(cell, rels):
    """Walk the cell XML in document order; skip tracked deletions; keep hyperlinks."""
    segs = []

    def walk(el, url):
        for ch in el:
            tag = ch.tag
            if tag == W_DEL:
                continue
            if tag == W_HL:
                rid = ch.get(R_ID)
                u = rels[rid].target_ref if rid in rels else None
                walk(ch, u or url)
            elif tag == W_T:
                segs.append([clean(ch.text or ""), url])
            elif tag in (W_TAB,):
                segs.append([" ", url])
            elif tag == W_BR:
                segs.append(["\n", None])
            elif tag == W_P:
                if segs:
                    segs.append(["\n", None])
                walk(ch, url)
            else:
                walk(ch, url)

    walk(cell._tc, None)
    return merge(segs)


def plain(rich):
    return "".join(t for t, _ in rich).strip()


# ---------- manuscript cell -> witnesses ----------

def split_rich(rich, seps=";\n"):
    """Split rich text on separator chars; returns list of rich pieces."""
    pieces, cur = [], []
    for t, u in rich:
        buf = ""
        for ch in t:
            if ch in seps:
                if buf:
                    cur.append([buf, u]); buf = ""
                pieces.append(merge(cur)); cur = []
            else:
                buf += ch
        if buf:
            cur.append([buf, u])
    pieces.append(merge(cur))
    return [p for p in pieces if plain(p)]


CITY_RE = re.compile(r"\s*([A-ZÄÖÜ][^\d:;,]{1,30}?):\s*")
FOL_RE = re.compile(r",?\s*(?:\b[Ff]ol\.?|\bvol\.|\bff?\.)\s*(?=\d)|,?\s*\bp\.\s+(?=\d)")
TAIL_FOL_RE = re.compile(r",\s+(\d+[rv]?(?:\(\d+\))?(?:\s*[–—-]+\s*\d*[rv]?)?(?:\s*,\s*\d+[rv]?(?:\s*[–—-]+\s*\d*[rv]?)?)*)\s*$")
SHELF_CITY = [("Par.", "Paris"), ("Vat.", "Vatikanstadt"), ("Marc.", "Venedig"),
              ("Laur.", "Florenz"), ("Vind.", "Wien"), ("Ambros.", "Mailand"),
              ("Monac.", "München"), ("Mon.", "München")]
CITY_FIX = {"Vatikanstandt": "Vatikanstadt"}


def parse_witness(text, url, city):
    text = text.strip(" ,")
    parts = FOL_RE.split(text, maxsplit=1)
    if len(parts) > 1:
        shelf, folios = parts[0], parts[1]
    else:
        m = TAIL_FOL_RE.search(text)
        shelf, folios = (text[:m.start()], m.group(1)) if m else (text, "")
    folios = folios.strip(" ,").replace("--", "–")
    start = re.split(r"\s*[–—-]+\s*|,\s*", folios)[0] if folios else ""
    if not city:
        city = next((c for pre, c in SHELF_CITY if shelf.startswith(pre)), "")
    return {"city": CITY_FIX.get(city, city), "shelfmark": shelf.strip(" ,"),
            "folios": folios, "start": start, "url": url, "raw": text}


SPLIT_RE = re.compile(r",\s+(?=[A-Z][A-Za-z]*\.?\s)")


def witnesses(rich):
    """Parse a manuscripts cell into witnesses, keeping each one's own link."""
    out, city = [], ""
    for piece in split_rich(rich):
        # plain text with per-character url map
        text, umap = "", []
        for t, u in piece:
            text += t
            umap += [u] * len(t)
        pos = 0
        while True:  # leading "City:" labels, e.g. "Papyri: Oxford:"
            m = CITY_RE.match(text, pos)
            if not m:
                break
            if m.group(1).strip() != "Papyri":
                city = m.group(1).strip()
            pos = m.end()
        bounds = [pos] + [m.end() for m in SPLIT_RE.finditer(text, pos)] + [len(text) + 2]
        for a, b in zip(bounds, bounds[1:]):
            sub = text[a:b - 2] if b <= len(text) else text[a:]
            if not sub.strip(" ,"):
                continue
            urls = [u for u in umap[a:a + len(sub)] if u]
            out.append(parse_witness(sub, urls[0] if urls else None, city))
    return [w for w in out if w["shelfmark"]]


# ---------- the 35-column Werke tables ----------

def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


TRANS_LANG = {20: "de", 21: "en", 22: "fr", 23: "it", 24: "es", 25: "other"}


def read_werke(path):
    d = docx.Document(path)
    rels = d.part.rels
    paras = [p.text.strip() for p in d.paragraphs if p.text.strip()]
    t = d.tables[0]
    rows = t.rows
    hi = next(i for i, r in enumerate(rows[:3])
              if plain(cell_rich(r.cells[0], rels)).startswith("lat. Titel"))
    header = [plain(cell_rich(c, rels)) for c in rows[hi].cells]
    works = []
    for r in rows[hi + 1:]:
        cells = [cell_rich(c, rels) for c in r.cells]
        if not plain(cells[0]):
            continue
        prints = []
        for i in range(3, 14):
            name = re.sub(r"^Drucke:\s*", "", header[i]).strip()
            if not cells[i] or re.fullmatch(r"Ed\d+", name) or not plain(cells[i]):
                continue
            prints.append({"name": name, "loc": cells[i]})
        trans = {TRANS_LANG[i]: cells[i] for i in TRANS_LANG if plain(cells[i])}
        works.append({
            "title_lat": plain(cells[0]),
            "abbr": plain(cells[1]),
            "title_gr": plain(cells[2]),
            "prints": prints,
            "prints_annotated": cells[14] or None,
            "prints_single": cells[15] or None,
            "prints_note": cells[16] or None,
            "editions": cells[17] or None,
            "editions_prep": cells[18] or None,
            "translations": trans,
            "translations_prep": cells[26] or None,
            "mss": witnesses(cells[27]),
            "date": plain(cells[28]),
            "note": plain(cells[29]),
            "refs": {k: cells[i] for k, i in
                     (("Diels", 30), ("Kibre", 31), ("Pinakes", 32), ("TLG", 33), ("Fichtner", 34))
                     if plain(cells[i])},
        })
    name = paras[1] if len(paras) > 1 and paras[0].startswith("CMG Catalogue") else \
        re.sub(r"\s*Werke.*$", "", paras[0]) if paras else path.stem
    if not paras or not name or name.strip() == "Author":
        name = re.split(r"[ _]Werke", path.stem)[0].replace("_", " ")
    return name.strip(), works


# ---------- Galen ----------

def norm_title(s):
    return re.sub(r"[^a-z]", "", (s or "").lower().replace("*", ""))


def read_galen():
    wb = openpyxl.load_workbook(SRC / "Galen" / "Galen DB.xlsx")
    ws = wb["Sheet1"]
    rows = list(ws.iter_rows())
    hdr = [clean(str(c.value or "")).strip() for c in rows[0]]
    col = {h: i for i, h in enumerate(hdr)}

    def rc(c):
        v = c.value
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        if isinstance(v, float) and v.is_integer():
            v = int(v)
        if isinstance(v, float):
            v = f"{v:.3f}"
        return merge([[clean(str(v)), c.hyperlink.target if c.hyperlink else None]])

    d = docx.Document(SRC / "Mss" / "galen mss table.docx")
    rels = d.part.rels
    mss = {}
    for r in d.tables[0].rows:
        title = plain(cell_rich(r.cells[0], rels))
        mss[norm_title(title)] = witnesses(cell_rich(r.cells[1], rels))

    works, matched = [], set()
    for r in rows[1:]:
        lat = clean(str(r[col["lat. Titel"]].value or "")).strip()
        if not lat:
            continue
        key = norm_title(lat)
        if key not in mss:
            close = difflib.get_close_matches(key, list(mss), n=1, cutoff=0.85)
            key = close[0] if close else key
        w = mss.get(key, [])
        if key in mss:
            matched.add(key)
        tlg = r[col["TLG"]].value
        refs = {}
        for k, h in (("Diels", "Diels"), ("Pinakes", "Pinakes"), ("Fichtner", "Fichtner")):
            v = rc(r[col[h]])
            if v:
                refs[k] = v
        if tlg:
            refs["TLG"] = [[f"0057.{int(round(float(tlg) % 1 * 1000)):03d}"
                            if isinstance(tlg, float) else str(tlg), None]]
        works.append({
            "title_lat": lat,
            "abbr": "",
            "title_gr": clean(str(r[col["gr. Titel"]].value or "")).strip(),
            "prints": [{"name": "Kühn (1821–1833)", "loc": rc(r[col["Kühn"]])}] if rc(r[col["Kühn"]]) else [],
            "editions": rc(r[col["maßgebliche Edition(en)"]]),
            "editions_prep": rc(r[col["Edition(en) in Vorbereitung"]]),
            "translations": {},
            "mss": w,
            "refs": refs,
        })
    unmatched = [k for k in mss if k not in matched and mss[k]]
    return works, unmatched


# ---------- main ----------

def latest_werke():
    files = list((SRC / "Other Authors").glob("*Werke*.docx"))
    files = [f for f in files if not f.name.startswith(("Template", "~$"))]
    files += sorted((SRC / "Hippocrates").glob("Hippocrates_Werke_*.docx"))[-1:]
    return sorted(files)


def main():
    authors = []
    report = []
    for f in latest_werke():
        name, works = read_werke(f)
        date = re.search(r"(\d{6})", f.name)
        authors.append({"name": name, "source": f.name,
                        "source_date": "20" + date.group(1) if date else "", "works": works})
        report.append((name, len(works), sum(len(w["mss"]) for w in works),
                       sum(1 for w in works for m in w["mss"] if m["url"])))
    gworks, unmatched = read_galen()
    authors.append({"name": "Galenus", "source": "Galen DB.xlsx + galen mss table.docx",
                    "source_date": "20201127", "works": gworks})
    report.append(("Galenus", len(gworks), sum(len(w["mss"]) for w in gworks),
                   sum(1 for w in gworks for m in w["mss"] if m["url"])))

    # ids
    seen = set()
    for a in authors:
        a["id"] = slug(a["name"].split(" and ")[0])[:40]
        for i, w in enumerate(a["works"], 1):
            w["id"] = f"{a['id']}-{i:03d}"
            assert w["id"] not in seen
            seen.add(w["id"])
    authors.sort(key=lambda a: a["name"].lower())

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({"authors": authors}, ensure_ascii=False, indent=1))
    for row in sorted(report):
        print(f"{row[0][:45]:45} works {row[1]:4}  mss {row[2]:5}  linked {row[3]:5}")
    print("TOTAL works", sum(r[1] for r in report), "mss", sum(r[2] for r in report),
          "linked", sum(r[3] for r in report))
    if unmatched:
        print("Galen mss rows not matched to a DB title:", unmatched)


if __name__ == "__main__":
    main()
