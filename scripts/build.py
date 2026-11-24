"""Build the static site in docs/ from data/catalogue.json. Standard library only.

Usage: python scripts/build.py
"""
import csv, html, json, re, shutil
from urllib.parse import urlencode
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / "data" / "catalogue.json").read_text())
MMFILE = ROOT / "data" / "medimanus.json"
MM = json.loads(MMFILE.read_text()) if MMFILE.exists() else {"witnesses": [], "retrieved": ""}
GVFILE = ROOT / "data" / "galenus_verbatim.json"
GV = json.loads(GVFILE.read_text())["works"] if GVFILE.exists() else {}
# catalogue entries that cover more than one TLG text
EXTRA_TLG = {"galenus-078": ["0057.090", "0057.091"], "galenus-042": ["0057.047"]}
# Galen works the CMG tables leave out because no Greek survives: known only through Arabic notes
EXTRA_WORKS = {"Galenus": [
    {"id": "galenus-ar-alim", "title_lat": "In Hippocratis De alimento commentaria",
     "note": "Lost in Greek; the Greek commentary printed by Kühn (XV 224–417) is a later forgery. Known through "
             "Ibn Riḍwān's Arabic notes, which quote the Hippocratic lemmata."},
    {"id": "galenus-ar-hum", "title_lat": "In Hippocratis De humoribus commentaria",
     "note": "Lost in Greek; the Greek commentary printed by Kühn (XVI 1–488) is a later forgery. Known through "
             "Ibn Riḍwān's Arabic notes, which quote the Hippocratic lemmata."}]}
for _a in DATA["authors"]:
    for _x in EXTRA_WORKS.get(_a["name"], []):
        if not any(w["id"] == _x["id"] for w in _a["works"]):
            _a["works"].append({"abbr": "", "title_gr": "", "prints": [], "editions": [], "editions_prep": None,
                                "translations": {}, "refs": {}, "mss": []} | _x)
GAFILE = ROOT / "data" / "graeco_arabic.json"
GA = json.loads(GAFILE.read_text()) if GAFILE.exists() else {"works": {}, "retrieved": ""}
WDFILE = ROOT / "data" / "work_dates.json"
WD = json.loads(WDFILE.read_text()) if WDFILE.exists() else {}
PKFILE = ROOT / "data" / "pinakes.json"
PK = json.loads(PKFILE.read_text()) if PKFILE.exists() else {"oeuvres": {}, "retrieved": ""}
CVFILE = ROOT / "data" / "cmg_viewer_volumes.json"
_CV = json.loads(CVFILE.read_text()) if CVFILE.exists() else {"volumes": [], "items": []}
CV_VOLS = set(_CV["volumes"])
CV_ITEMS = defaultdict(list)
for _i in _CV.get("items", []):
    if _i["series"] and _i["url"]:
        CV_ITEMS[(_i["collection"], _i["series"].replace(" ", ""))].append(_i)


def viewer_for_edition(w):
    """'Barigazzi: CMG V 1,1' -> the work's own entry in that CMG viewer volume (or the volume)."""
    import difflib
    text = "".join(t for t, _ in (w.get("editions") or []))
    out = []
    for coll, series in re.findall(r"\b(CMG|CML)\s+((?:Suppl\.\s*(?:Or\.\s*)?)?[IVX]+(?:\s*[\d,]+)?)", text):
        items = CV_ITEMS.get((coll, series.replace(" ", "")), [])
        if not items:
            continue
        def score(i):
            return difflib.SequenceMatcher(None, w["title_lat"].lower(), i["label"].split(", edidit")[0].lower()).ratio()
        best = max(items, key=score)
        if score(best) < 0.6:
            best = items[0]
        out.append((f"{coll} {series}", best["url"]))
    return out
CV_BASE = "https://alchemiesofscent.github.io/cmg-viewer/viewer/"
_CMG_RE = re.compile(r"cmg\.bbaw\.de/epubl/online/([A-Za-z0-9_]+?)\.(?:php|html)\?.*?\bpn=(\d+)", re.I)


def viewer_url(u):
    """Old BBAW scan page -> the same page in the CMG viewer (pn is the same physical scan order)."""
    m = _CMG_RE.search(u or "")
    if m and m[1] in CV_VOLS:
        return f"{CV_BASE}{m[1]}/?pn={m[2]}"
    return None


MM_BY_WORK = defaultdict(list)
for _w in MM["witnesses"]:
    MM_BY_WORK[_w["work"]].append(_w)

# shelfmark key for comparing the two sources: city + collection words + number
_CITY_KEY = {"par": "paris", "paris": "paris", "vat": "vatican", "vatican": "vatican", "vatikanstadt": "vatican",
             "laur": "florence", "florence": "florence", "florenz": "florence", "marc": "venice", "venice": "venice",
             "venedig": "venice", "vind": "vienna", "vienna": "vienna", "wien": "vienna", "monac": "munich",
             "mon": "munich", "munich": "munich", "münchen": "munich", "ambros": "milan", "milan": "milan",
             "mailand": "milan", "oxford": "oxford", "london": "london", "leiden": "leiden",
             "firenze": "florence", "venezia": "venice", "milano": "milan", "vaticano": "vatican",
             "napoli": "naples", "neapel": "naples", "naples": "naples", "roma": "rome", "rom": "rome", "rome": "rome",
             "modena": "modena", "cambridge": "cambridge", "berlin": "berlin", "leipzig": "leipzig",
             "madrid": "madrid", "heidelberg": "heidelberg", "bologna": "bologna", "haven": "newhaven",
             "yale": "newhaven", "bamberg": "bamberg", "zwickau": "zwickau", "wolfenbüttel": "wolfenbuttel",
             "leidensis": "leiden", "scal": "leiden", "vulc": "leiden",
             "escorial": "escorial", "scorial": "escorial", "scor": "escorial", "athos": "athos", "athous": "athos",
             "messan": "messina", "messina": "messina", "matrit": "madrid", "mosq": "moscow", "moscow": "moscow",
             "taur": "turin", "turin": "turin", "torino": "turin", "bonon": "bologna", "lips": "leipzig",
             "berol": "berlin", "oxon": "oxford", "neap": "naples", "leid": "leiden", "ambrosiana": "milan",
             "laurentianus": "florence", "parisinus": "paris", "vaticanus": "vatican", "marcianus": "venice",
             "vindobonensis": "vienna", "monacensis": "munich", "harley": "london", "sloane": "london", "arundel": "london",
             "sangall": "stgallen", "sang": "stgallen", "gallen": "stgallen", "dresd": "dresden", "dresden": "dresden",
             "cesena": "cesena", "malatest": "cesena", "istanbul": "istanbul", "haun": "copenhagen",
             "kopenhagen": "copenhagen", "copenhagen": "copenhagen", "brux": "brussels", "bruxelles": "brussels",
             "vindocin": "vendome", "laudun": "laon", "prag": "prague", "prague": "prague", "tolet": "toledo",
             "casin": "montecassino", "patm": "patmos", "jena": "jena", "erfurt": "erfurt", "zürich": "zurich",
             "wrocław": "wroclaw", "rehd": "wroclaw", "siena": "siena", "lincoln": "lincoln", "bourges": "bourges",
             "avranches": "avranches", "bursa": "bursa", "alexandria": "alexandria", "tehran": "tehran",
             "phillipps": "phillipps", "phill": "phillipps", "cheltenham": "phillipps", "hamburg": "hamburg",
             "bodmer": "cologny", "cologny": "cologny", "gallipoli": "gallipoli", "york": "newyork"}
_KEEP = {"suppl", "urb", "pal", "barb", "reg", "ottob", "coisl", "coislin", "barocc", "med", "hist", "phil", "theol",
         "harley", "add", "sloane", "lat", "chis", "ross"}


def ms_key(city_name, shelf):
    shelf = re.sub(r"\(.*?\)|=.*$", "", re.split(r",\s*(?:MS|ff?\.|f\.)", shelf)[0])
    words = re.findall(r"[A-Za-zÀ-ÿ]+", (city_name or "") + " " + shelf)
    c = next((_CITY_KEY[w.lower()] for w in words if w.lower() in _CITY_KEY), "")
    norm = lambda w: ("coisl" if w == "coislin" else "suppl" if w.startswith(("suppl", "supplément")) else
                      "add" if w == "additional" else "barocc" if w == "barocci" else w)
    fonds = sorted({norm(w.lower()) for w in words if norm(w.lower()) in _KEEP})
    nums = [str(int(n)) for n in re.findall(r"\d+", shelf)]
    if c == "milan":  # Ambrosiana: letter and sup./inf. belong to the shelfmark (C 80 inf. is not Q 80 sup.)
        m = re.search(r"\b([A-Z])\s*[,.]?\s*0*(\d+)\s*(sup|inf)", shelf)
        if m:
            fonds, nums = [f"{m[1].lower()}{m[3]}"], [str(int(m[2]))]
    if c == "escorial":  # Escorial: letter + Roman numeral + number (Ψ IV 14); Latin look-alikes read as Greek
        m = re.search(r"(?<![A-Za-zΑ-Ωα-ω])([A-Za-zΑ-Ωα-ω])\s*[.,]?\s*([IVX]+)\s*[.,]?\s*0*(\d+)", shelf)
        if m:
            g = str.maketrans("ABEZHIKMNOPTYX", "ΑΒΕΖΗΙΚΜΝΟΡΤΥΧ")
            fonds, nums = [m[1].upper().translate(g) + m[2]], [str(int(m[3]))]
    return f"{c}|{' '.join(fonds)}|{'.'.join(nums)}" if c and nums else None


ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV", "XV",
         "XVI", "XVII", "XVIII", "XIX", "XX", "XXI"]


def roman_c(cs):
    """[14, 15] -> 's. XIV–XV'"""
    cs = sorted({c for c in cs if 0 < c < len(ROMAN)})
    if not cs:
        return ""
    return "s. " + ROMAN[cs[0]] + (f"–{ROMAN[cs[-1]]}" if cs[-1] != cs[0] else "")


def _pk_centuries(c):
    """'14 (3/4)' -> [14]; '14-15' -> [14, 15]; fractions in brackets are parts of a century."""
    return [int(n) for n in re.findall(r"\d{1,2}", re.sub(r"\(.*?\)", "", c or "")) if 0 < int(n) < 22]


def _pk_part(c):
    m = re.search(r"\((\d/\d|in\.|ex\.|med\.)\)", c or "")
    return f" ({m[1]})" if m else ""


# manuscript dates: Pinakes first, MediManus for the rest
MSDATE = {}
for _o in PK["oeuvres"].values():
    for _x in _o["witnesses"]:
        _k = ms_key(_x["city"], f"{_x['fonds']} {_x['cote']}")
        _cs = _pk_centuries(_x["century"])
        if _k and _cs and _k not in MSDATE:
            MSDATE[_k] = {"cs": _cs, "part": _pk_part(_x["century"]), "date": _x["date"], "src": "Pinakes",
                          "url": f"https://pinakes.irht.cnrs.fr/notices/cote/{_x['cote_id']}/"}
for _sid, _x in (MM.get("all_manuscripts") or {}).items():
    _k = ms_key("", _sid)
    if _k and _x["centuries"] and _k not in MSDATE:
        MSDATE[_k] = {"cs": _x["centuries"], "date": "", "src": "MediManus", "url": _x["url"]}


# Pinakes: witnesses per catalogue work, and the digitization links on its shelfmark pages
PK_BY_WORK = defaultdict(list)
for _o in PK["oeuvres"].values():
    for _wid in _o["works"]:
        PK_BY_WORK[_wid].extend(_o["witnesses"])
PKDIG = {i: c["digitized"] for i, c in (PK.get("cotes") or {}).items() if c.get("digitized")}
PKDIG_BY_KEY = {}
for _o in PK["oeuvres"].values():
    for _x in _o["witnesses"]:
        _k = ms_key(_x["city"], f"{_x['fonds']} {_x['cote']}")
        if _k and _x["cote_id"] in PKDIG:
            PKDIG_BY_KEY.setdefault(_k, _x["cote_id"])

# shelfmarks corrected by scripts/pinakes_check.py (one digit off, same start folio)
PCFILE = ROOT / "data" / "pinakes_check.json"
PC = json.loads(PCFILE.read_text()) if PCFILE.exists() else {"fixes": [], "review": []}
for _f in PC["fixes"]:
    for _a in DATA["authors"]:
        for _w in _a["works"]:
            if _w["id"] != _f["work"]:
                continue
            for _m in _w["mss"]:
                if _m["shelfmark"] == _f["shelfmark"] and _m["folios"] == _f["folios"]:
                    _m["shelfmark"] = _f["set"]["shelfmark"]
                    _m["pk_fix"] = _f["cote_id"]
                    _m["corrected"] = "; ".join(x for x in (_m.get("corrected"), _f["reason"]) if x)

# within each city, list shelfmarks in natural order (Plut. 75.5 before 75.12), keeping the source's city order
_nat = lambda s: [(0, int(t), "") if t.isdigit() else (1, 0, t) for t in re.findall(r"\d+|[^\d\s.,]+", s.casefold())]
for _a in DATA["authors"]:
    for _w in _a["works"]:
        _first = {}
        for _i, _m in enumerate(_w["mss"]):
            _first.setdefault(_m["city"], _i)
        _w["mss"].sort(key=lambda m: (_first[m["city"]], _nat(m["shelfmark"])))


# sigla of the critical editions (scripts/sigla_check.py)
SIFILE = ROOT / "data" / "sigla_index.json"
SI = json.loads(SIFILE.read_text()) if SIFILE.exists() else {"by_work": {}, "by_ms": {}}


def sig_html(s):
    return (esc(s["base"]) + (f"<sup>{esc(s['sup'])}</sup>" if s.get("sup") else "")
            + (f"<sub>{esc(s['sub'])}</sub>" if s.get("sub") else ""))


def sig_cell(recs, tag="td"):
    """'Lᵇ (Olivieri, CMG VIII 1)', one per edition, each linked to the edition's sigla page."""
    groups = {}
    for r in recs:
        m = re.match(r"^(.*?, (?:CMG|CML) [IVXL]+) (\d+)$", r["edition"])  # 'Olivieri, CMG VIII 1' -> merge parts
        head, part = (m[1], m[2]) if m else (r["edition"], "")
        k = (head, r["siglum"]["base"], r["siglum"].get("sup", ""), r["siglum"].get("sub", ""))
        g = groups.setdefault(k, {"r": r, "parts": [], "links": []})
        if part and part not in g["parts"]:
            g["parts"].append(part)
            g["links"].append(r)
    out = []
    for (head, *_), g in groups.items():
        r = g["r"]
        if len(g["parts"]) > 1:
            parts = ", ".join(f'<a href="{esc(x["viewer"])}">{esc(p)}</a>' for p, x in zip(g["parts"], g["links"]))
            out.append(f'<span class="sig" title="{esc(r["printed"], quote=True)}"><span class="sg">{sig_html(r["siglum"])}</span> '
                       f'<span class="mmt">({esc(head)} {parts})</span></span>')
        else:
            out.append(f'<a class="sig" href="{esc(r["viewer"])}" title="{esc(r["printed"], quote=True)}">'
                       f'<span class="sg">{sig_html(r["siglum"])}</span> <span class="mmt">({esc(r["edition"])})</span></a>')
    return f"<{tag} class='sigc'>" + "<br>".join(out) + f"</{tag}>"


def ms_date(city_name, shelf):
    return MSDATE.get(ms_key(city_name, shelf))


def date_cell(d):
    if not d:
        return "<td class='dt' data-v='9999'></td>"
    tip = f"{d['date']} · {d['src']}" if d["date"] else d["src"]
    return (f"<td class='dt' data-v='{d['cs'][0]:02d}' title='{esc(tip, quote=True)}'>{esc(roman_c(d['cs']) + d.get('part', ''))}"
            + (f" <span class='mmt'>{esc(d['date'])}</span>" if d["date"] and len(d["date"]) < 14 else "") + "</td>")


ED_ORDER = {"Galenus": "Kühn", "Hippocrates": "Littré"}
_RV = {"I": 1, "V": 5, "X": 10, "L": 50}


def _roman(r):
    n = 0
    for a, b in zip(r, r[1:] + " "):
        v = _RV[a]
        n += -v if b in _RV and _RV[b] > v else v
    return n


def ed_key(w, editor):
    """Sort key from the location in Kühn / Littré, e.g. 'XVIIB, 345-887' -> vol 17, part B, p. 345."""
    loc = next(("".join(t for t, _ in p["loc"]) for p in w["prints"] if p["name"].startswith(editor)), "")
    m = re.match(r"\s*([IVXL]+)\s*([AB])?\s*(?:\([^)]*\))?\s*,\s*(\d+)", loc)
    if not m:
        return None
    return (_roman(m[1]) * 10 + (1 if m[2] == "B" else 0)) * 10000 + int(m[3])


_WPFILE = ROOT / "data" / "author_dates_wikipedia.json"
_WPD = json.loads(_WPFILE.read_text()) if _WPFILE.exists() else {}
WP_AUTH = _WPD.get("authors", {})
COMPILER_AUTH = _WPD.get("compiler", {})


def author_source(name):
    """(source name, url, note) for an author's date."""
    a = (PK.get("authors") or {}).get(name)
    if name in COMPILER_AUTH:
        return "S. Coughlin", "", "Date supplied by the compiler"
    if WP_AUTH.get(name, {}).get("override_pinakes"):
        return "Wikipedia", WP_AUTH[name]["url"], WP_AUTH[name]["quote"]
    if a and re.search(r"\d", a["century"]):
        return "Pinakes", a["url"], ""
    if name in WP_AUTH:
        return "Wikipedia", WP_AUTH[name]["url"], WP_AUTH[name]["quote"]
    return "", "", ""


def author_date(name):
    """Pinakes author record -> (label, sort year) e.g. ('s. V–IV BCE (460–377 BCE)', -460);
    Wikipedia (data/author_dates_wikipedia.json) where Pinakes has no usable date."""
    a = (PK.get("authors") or {}).get(name)
    if name in COMPILER_AUTH:
        return COMPILER_AUTH[name]["label"], COMPILER_AUTH[name]["year"]
    if WP_AUTH.get(name, {}).get("override_pinakes"):
        return WP_AUTH[name]["label"], WP_AUTH[name]["year"]
    if not a or not re.search(r"\d", a["century"]):
        w = WP_AUTH.get(name)
        return (w["label"], w["year"]) if w else ("", None)
    bce = "av. J.-C." in a["century"]
    cs = [int(n) for n in re.findall(r"\d+", a["century"].split("Remarque")[0])]
    label = "s. " + "–".join(ROMAN[c] for c in cs if c < len(ROMAN)) + (" BCE" if bce else " CE") + ("?" if "?" in a["century"] else "")
    ys = [int(y) for y in re.findall(r"\d{3,4}", a["date"])]
    if ys:
        dbce = "av" in a["date"]
        label += f" ({'–'.join(str(y) for y in ys[:2])}{' BCE' if dbce else ''})"
        year = -ys[0] if dbce else ys[0]
    else:
        year = -(cs[0] * 100 - 50) if bce else cs[0] * 100 - 50
    return label, year


def ed_label(w, editor):
    """'I, 1-39 K.' -> 'K. I 1–39'; Littré 'I,570--636' -> 'L. I 570–636'."""
    loc = next(("".join(t for t, _ in p["loc"]) for p in w["prints"] if p["name"].startswith(editor)), "")
    loc = re.sub(r"\s*K\.\s*$", "", loc.strip()).replace("--", "–").replace("-", "–")
    loc = "; ".join(re.sub(r"^([IVXL]+[AB]?)\s*,\s*", r"\1 ", part.strip()) for part in loc.split(";"))
    return f"{editor[0]}. {loc}" if loc else ""


def short_date(wd):
    """Compact date for the work list: first span only, e.g. '162–166 CE', '420–400 BCE'."""
    if not wd:
        return ""
    lab = wd.get("label", "")
    era = " BCE" if "BCE" in lab else " CE"
    m = re.search(r"(\d{2,3}(?:\s*[–/-]\s*\d{2,3})?)", lab.split(";")[0])
    return (m[1].replace("-", "–").replace(" ", "") + era) if m else ""


def fol_key(f):
    m = re.match(r"(\d+)\s*([rv]?)", f or "")
    return (int(m[1]), m[2] or "r") if m else None
OUT = ROOT / "docs"

CITY_EN = {"Florenz": "Florence", "Vatikanstadt": "Vatican City", "Venedig": "Venice",
           "Wien": "Vienna", "München": "Munich", "Mailand": "Milan", "Rom": "Rome",
           "Neapel": "Naples", "Genf": "Geneva", "Zürich": "Zurich", "Warschau": "Warsaw",
           "Freiburg (Schweiz)": "Fribourg", "Bayern": "Bavaria"}
LANG = {"de": "German", "en": "English", "fr": "French", "it": "Italian",
        "es": "Spanish", "other": "Other languages"}

esc = html.escape
# viewers that no longer resolve or now land on a generic page (checked Nov 2026): keep the record, mark the link.
# BL Viewer.aspx links redirect to a generic page (images offline since the 2023 cyber-attack); the old Teca
# ImageViewer times out; wdl.org redirects to a generic LoC page.
STALE_HOSTS = ("mss.bmlonline.it", "213.21.172.25", "163.1.169.40", "teca.bmlonline.it/ImageViewer",
               "bl.uk/manuscripts/Viewer.aspx", "www.wdl.org")

# data/relocations.csv maps an old (dead) witness URL + start folio to the library's current viewer.
# The catalogue keeps the original URL for provenance; only the rendered link changes.
RELOC = {}
_RFILE = ROOT / "data" / "relocations.csv"
if _RFILE.exists():
    with _RFILE.open(newline="", encoding="utf-8") as fh:
        for _r in csv.DictReader(fh):
            if _r["new_folio_url"] or _r["new_manuscript_url"]:
                RELOC[(_r["old_url_prefix_or_url"], _r["start"])] = _r


def stale(u):
    return bool(u) and any(h in u for h in STALE_HOSTS)


def go(m, folio_label="view"):
    """Link for witness m: relocated link first, then the stale check, then the stored URL."""
    u = m["url"]
    if m.get("pk_fix"):  # shelfmark corrected from Pinakes: the old link may be to the wrong manuscript
        d = PKDIG.get(m["pk_fix"])
        if d:
            return f'<a class="go" href="{esc(d[0]["url"])}" title="Digitization linked by Pinakes; opens the manuscript">view ms.</a>'
        if stale(u) or RELOC.get((u, m.get("start") or "")):
            return (f'<a class="go stale" href="https://pinakes.irht.cnrs.fr/notices/cote/{m["pk_fix"]}/" '
                    'title="Shelfmark corrected; see Pinakes for the manuscript">Pinakes</a>')
    r = RELOC.get((u, m.get("start") or ""))
    if r:
        note = " (approximate)" if r["method"] == "offset" else ""
        if r["new_folio_url"]:
            return f'<a class="go" href="{esc(r["new_folio_url"])}" title="Current viewer{note}">{folio_label}</a>'
        return (f'<a class="go" href="{esc(r["new_manuscript_url"])}" '
                f'title="Current viewer; opens the manuscript, not the folio">view ms.</a>')
    if stale(u) and PKDIG_BY_KEY.get(ms_key(m["city"], m["shelfmark"])):
        d = PKDIG[PKDIG_BY_KEY[ms_key(m["city"], m["shelfmark"])]]
        return f'<a class="go" href="{esc(d[0]["url"])}" title="Current digitization, linked by Pinakes; opens the manuscript">view ms.</a>'
    if stale(u):
        return f'<a class="go stale" href="{esc(u)}" title="This viewer has been retired; the link no longer resolves">old link</a>'
    return f'<a class="go" href="{esc(u)}">{folio_label}</a>'


def shelf_html(sm):
    """'Laur. Plut. 75.05 (libri VI–VIII)' -> shelfmark on one line, the contents note below it."""
    sm = dash(sm)
    m = re.match(r"^(.*?)\s*(\(.*\))\s*$", sm)
    if m and m[1]:
        return f'<span class="smm">{esc(m[1])}</span><span class="smx">{esc(m[2])}</span>'
    return f'<span class="smm">{esc(sm)}</span>'


def city(c):
    return CITY_EN.get(c, c) or "—"


def dash(s):
    return (s or "").replace("--", "–")


def rich(r):
    """Rich text [[text, url], ...] -> HTML. '$$' marks a WorldCat link in the sources."""
    if not r:
        return ""
    out = []
    for t, u in r:
        t = dash(t)
        if t.strip() == "$$" and u:
            out.append(f' <a class="wc" href="{esc(u)}" title="WorldCat record">WorldCat</a>')
            continue
        body = esc(t).replace("\n", "<br>")
        v = viewer_url(u)
        if v:
            out.append(f'<a href="{esc(v)}" title="Open in the CMG viewer">{body}</a>')
        else:
            out.append(f'<a href="{esc(u)}">{body}</a>' if u else body)
    s = re.sub(r";{2,}", ";", "".join(out))
    return re.sub(r"(<br>\s*)+$", "", re.sub(r"[;,]\s*$", "", s.strip()))


def ref_links(w):
    refs = dict(w.get("refs") or {})
    for k, v in list(refs.items()):
        txt = "".join(t for t, _ in v).strip()
        has_url = any(u for _, u in v)
        if k == "Pinakes" and not has_url and txt.isdigit():
            refs[k] = [[txt, f"https://pinakes.irht.cnrs.fr/notices/oeuvre/{txt}/"]]
        if k == "TLG" and not has_url:
            m = re.fullmatch(r"(\d{4})\.(\d{3})", txt)
            if m:
                refs[k] = [[txt, f"http://stephanus.tlg.uci.edu/Iris/Cite?{m[1]}:{m[2]}"]]
    return refs


def new_tab(h):
    """Links to other sites open in a new tab."""
    return re.sub(r"<a ((?:[^>](?!target=))*?href=['\"]https?://)", r'<a target="_blank" rel="noopener" \1', h)


def page(title, body, depth=0):
    up = "../" * depth
    body = new_tab(body)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<link rel="stylesheet" href="{up}style.css">
</head><body>
<header class="site"><a class="brand" href="{up}index.html">Ancient Greek Medical Authors</a>
<span class="tag">works · manuscripts · printed editions · translations</span>
<nav><a href="{up}index.html">Authors</a><a href="{up}manuscripts.html">Manuscripts</a><a href="{up}about.html">About</a></nav>
<form class="filter" action="{up}index.html" role="search"><input id="filter" name="q" type="search" placeholder="Filter this page · Enter searches everything" autocomplete="off" aria-label="Filter"></form>
</header>
<main>{body}</main>
<script src="{up}site.js" data-root="{up}"></script>
<footer>Compiled and built by Sean Coughlin, from the work catalogues he prepared for the CMG (2019–2020), with manuscript data from Pinakes (IRHT, retrieved {PK["retrieved"]}) and MediManus (CHS, retrieved {MM["retrieved"]}) Galen texts from Galenus Verbatim and Arabic texts from the Digital Corpus for Graeco-Arabic Studies. <a href="{up}about.html#versions">{VERSION}</a>, built {date.today().isoformat()}.</footer>
</body></html>"""


def witness_rows(mss, show_work=None, sig=None):
    rows = []
    for m in mss:
        sg = sig_cell(sig.get(ms_key(m["city"], m["shelfmark"]) or "-", [])) if sig is not None else ""
        view = go(m, f"view f. {esc(m['start'])}" if m["start"] else "view") if m["url"] else ""
        lead = f"<td>{show_work(m)}</td>" if show_work else ""
        rows.append(f"<tr>{lead}<td>{esc(city(m['city']))}</td><td class='sm'>{shelf_html(m['shelfmark'])}</td>{sg}"
                    + date_cell(ms_date(m["city"], m["shelfmark"])) +
                    f"<td class='fol'>{esc(dash(m['folios']))}"
                    + f"</td><td>{view}</td></tr>")
    return "".join(rows)


def core_differs(mm_title, our_title):
    """Show MediManus's title only when it says something extra, e.g. (partim) or (frag.)."""
    return "(" in mm_title


# MediManus search needs every word to match: search for its short author name plus a few distinctive title words
_MMT = json.loads((ROOT / "data" / "medimanus_titles.json").read_text()) if (ROOT / "data" / "medimanus_titles.json").exists() else {}
MM_AUTHOR = {v: k for k, v in (_MMT.get("authors") or {}).items()}
_MM_STOP = {"in", "de", "et", "ad", "a", "e", "ex", "sive", "seu", "qui", "quae", "quod", "eos", "liber", "libri", "librum",
            "libellus", "commentarius", "commentaria", "commentarii", "commentarium", "fragmenta", "opera", "secundum",
            "partim", "frag", "spurium", "hippocratis", "galeni"}


MMQ = json.loads((ROOT / "data" / "medimanus_queries.json").read_text()) if (ROOT / "data" / "medimanus_queries.json").exists() else {}


def mm_query(a, w, mmw):
    title = (mmw[0]["title"] if mmw else "") or w["title_lat"]
    title = re.sub(r"\s*[\(\[].*?[\)\]]|[?*/]", " ", title.split(";")[0])
    words = [x for x in re.findall(r"[A-Za-zÀ-ÿ]+", title) if x.lower() not in _MM_STOP and len(x) > 2][:2]
    author = MM_AUTHOR.get(a["name"]) or a["name"].replace("Ps.-", "").split()[0]
    return " ".join([author] + words)


def work_html(a, w):
    wd = WD.get(w["id"])
    ek = ed_key(w, ED_ORDER[a["name"]]) if a["name"] in ED_ORDER else None
    attrs = (f' data-ed="{ek}"' if ek else "") + (f' data-year="{wd["year"]}"' if wd and wd.get("year") is not None else "") + \
        (f' data-order="{wd["order"]}"' if wd and wd.get("order") else "")
    parts = [f'<section class="work" id="{w["id"]}"{attrs}>',
             f'<h3><a class="anchor" href="#{w["id"]}">{esc(w["title_lat"])}</a>'
             + (f' <span class="abbr">{esc(w["abbr"])}</span>' if w.get("abbr") else "") + "</h3>"]
    if w.get("title_gr"):
        parts.append(f'<p class="gr" lang="grc">{esc(w["title_gr"])}</p>')
    if wd:
        parts.append(f'<p class="wdate">{esc(wd["label"])}</p>')
    refs = ref_links(w)
    if refs:
        parts.append('<p class="refs">' + " · ".join(
            f'<span>{esc(k)} {rich(v)}</span>' for k, v in refs.items()) + "</p>")

    sigs = defaultdict(list)
    for r in SI["by_work"].get(w["id"], []):
        if not (r["status"] == "indirect" and any(ms_key(m["city"], m["shelfmark"]) == r["key"] for m in w["mss"])):
            sigs[r.get("key") or "?" + r["printed"]].append(r)  # unreadable shelfmarks are listed by their printed form
    sig = sigs if sigs else None
    sth = "<th>Siglum</th>" if sig is not None else ""
    if w["mss"]:
        parts.append(f'<h4>Manuscripts <span class="n">{len(w["mss"])} digitized</span></h4>'
                     f'<table class="mss sortable"><thead><tr><th>City</th><th>Shelfmark</th>{sth}<th>Date</th><th>Folios</th><th>Digitization</th></tr></thead>'
                     f'<tbody>{witness_rows(w["mss"], sig=sig)}</tbody></table>')
    else:
        parts.append('<h4>Manuscripts</h4><p class="none">No digitized manuscripts recorded in the catalogue.</p>')
    mmw = MM_BY_WORK.get(w["id"], [])
    if mmw:
        ours = defaultdict(list)
        for m in w["mss"]:
            ours[ms_key(m["city"], m["shelfmark"])].append(m)
        trs = []
        for x in sorted(mmw, key=lambda x: x["shelfmark"]):
            os_ = ours.get(ms_key("", x["shelfmark"]), [])
            starts = [o["start"] for o in os_ if o["start"]]
            if not os_:
                flag = '<span class="new" title="Not in the CMG list">new</span>'
            elif not x["start"] or not starts or fol_key(x["start"]) in {fol_key(f) for f in starts}:
                flag = '<span class="ok" title="Also in the CMG list">✓</span>'
            elif any(fol_key(f) and abs(fol_key(f)[0] - fol_key(x["start"])[0]) <= 1 for f in starts) if fol_key(x["start"]) else False:
                given = "; ".join(o["folios"] for o in os_ if o["folios"])
                flag = f'<span class="ok" title="Nearly the same start (CMG: {esc(given, quote=True)})">≈</span>'
            else:
                given = "; ".join(o["folios"] for o in os_ if o["folios"])
                flag = (f'<span class="diff" title="CMG list gives {esc(given, quote=True)}">'
                        f'CMG: f. {esc(", ".join(starts))}</span>')
            label = esc(x["title"]) if core_differs(x["title"], w["title_lat"]) else ""
            d = ms_date("", x["shelfmark"]) or ({"cs": x["centuries"], "date": "", "src": "MediManus"} if x.get("centuries") else None)
            trs.append(f"<tr><td class='sm'>{esc(x['shelfmark'])}</td>" + (sig_cell(sigs.get(ms_key('', x['shelfmark']), [])) if sig is not None else "") + date_cell(d) +
                       f"<td class='fol'>{esc(x['unit'] if x['folios'] else '')} {esc(x['folios'])}</td>"
                       f"<td class='mmt'>{label}</td><td>{flag}</td>"
                       f"<td><a class='go' href='{esc(x['url'])}'>MediManus</a></td></tr>")
        parts.append(f'<h4>In MediManus <span class="n">{len(mmw)}</span></h4>'
                     f'<table class="mss mm sortable"><thead><tr><th>Shelfmark</th>{sth}<th>Date</th><th>Folios</th><th></th><th>CMG list</th><th></th></tr></thead><tbody>{"".join(trs)}</tbody></table>')
    # digitized manuscripts Pinakes lists for this work that are in neither list above
    seen = {ms_key(m["city"], m["shelfmark"]) for m in w["mss"]} | {ms_key("", x["shelfmark"]) for x in mmw}
    extra, done = [], set()
    for x in PK_BY_WORK.get(w["id"], []):
        k = ms_key(x["city"], f"{x['fonds']} {x['cote']}")
        if x["cote_id"] in PKDIG and k not in seen and (x["cote_id"], x["folios"]) not in done:
            done.add((x["cote_id"], x["folios"]))
            extra.append(x)
    if extra:
        trs = []
        for x in sorted(extra, key=lambda x: (x["city"], x["fonds"], x["cote"])):
            links = " ".join(f'<a class="go" href="{esc(d["url"])}" title="{esc(d["label"], quote=True)}">view ms.</a>'
                             for d in PKDIG[x["cote_id"]][:2])
            d = {"cs": _pk_centuries(x["century"]), "part": _pk_part(x["century"]), "date": x["date"], "src": "Pinakes",
                 "url": f"https://pinakes.irht.cnrs.fr/notices/cote/{x['cote_id']}/"} if _pk_centuries(x["century"]) else None
            trs.append(f"<tr><td>{esc(city(x['city']))}</td><td class='sm'><a href='https://pinakes.irht.cnrs.fr/notices/cote/{x['cote_id']}/'>"
                       f"{esc(x['fonds'])} {esc(x['cote'])}</a></td>"
                       + (sig_cell(sigs.get(ms_key(x['city'], f"{x['fonds']} {x['cote']}"), [])) if sig is not None else "") + date_cell(d) +
                       f"<td class='fol'>{esc(x['folios'])}</td><td>{links}</td></tr>")
        parts.append(f'<h4>Also digitized, according to Pinakes <span class="n">{len(extra)}</span></h4>'
                     f'<table class="mss sortable"><thead><tr><th>City</th><th>Shelfmark</th>{sth}<th>Date</th><th>Folios</th><th>Digitization</th></tr></thead>'
                     f'<tbody>{"".join(trs)}</tbody></table>')
    # the editions' other manuscripts (not in any table above): one row per manuscript, all its sigla
    shown = seen | {ms_key(x["city"], f"{x['fonds']} {x['cote']}") for x in extra}
    rest = {k: v for k, v in sigs.items() if k not in shown}
    if rest:
        trs = []
        for k, recs in sorted(rest.items(), key=lambda kv: (kv[1][0]["city"], _nat(kv[1][0]["normalized"] or kv[1][0]["printed"]))):
            r = recs[0]
            pk = next((x.get("pinakes") for x in recs if x.get("pinakes")), None)
            d = ({"cs": _pk_centuries(pk["century"]), "part": _pk_part(pk["century"]), "date": pk["date"], "src": "Pinakes",
                  "url": f"https://pinakes.irht.cnrs.fr/notices/cote/{pk['cote_id']}/"} if pk and _pk_centuries(pk["century"])
                 else ms_date(r["city"], r["normalized"]))
            dig = PKDIG.get(pk["cote_id"]) if pk else None
            link = (f'<a class="go" href="{esc(dig[0]["url"])}" title="Digitization linked by Pinakes">view ms.</a>' if dig else "")
            unv = all(x["status"] == "unverified" for x in recs)
            ind = all(x["status"] == "indirect" for x in recs)
            flag = (' <span class="unv" title="Not listed for this work by Pinakes or MediManus; see SIGLA-CHECK.md">?</span>'
                    if unv else ' <span class="mmt" title="Commentary, translation or parallel text cited in the edition">(indirect tradition)</span>'
                    if ind else "")
            shelf = r["normalized"] or r["printed"]
            trs.append(f"<tr class='nd'><td>{esc(r['city'])}</td><td class='sm' title='{esc(r['printed'], quote=True)}'>{esc(shelf)}{flag}</td>"
                       + sig_cell(recs) + date_cell(d)
                       + f"<td class='fol'>{esc(r['folios'] or (pk['folios'] if pk else ''))}</td><td>{link}</td></tr>")
        parts.append(f'<h4>Other manuscripts used in the critical editions <span class="n">{len(rest)}</span></h4>'
                     '<table class="mss sortable"><thead><tr><th>City</th><th>Shelfmark</th><th>Siglum</th><th>Date</th><th>Folios</th><th></th></tr></thead>'
                     f'<tbody>{"".join(trs)}</tbody></table>')
    more = []
    pk = next((u for _, u in refs.get("Pinakes", []) if u), None)
    if pk:
        more.append(f'<a href="{esc(pk)}">Pinakes</a>')
    q = MMQ.get(w["id"]) or ("" if MMQ else mm_query(a, w, mmw))  # no link where MediManus finds nothing
    if q:
        more.append(f'<a href="https://medimanus.chs.harvard.edu/app/search?{esc(urlencode({"q": q}))}">MediManus</a>')
    if more:
        parts.append('<p class="more">Full manuscript tradition: ' + " · ".join(more) + "</p>")

    dl = []
    if w.get("editions"):
        ed_html = rich(w["editions"])
        if "cmg-viewer/viewer" not in ed_html:
            links = viewer_for_edition(w)
            if links:
                ed_html += " · " + " · ".join(f'<a class="cv" href="{esc(u)}">{esc(lbl)} in the CMG viewer</a>' for lbl, u in links)
        dl.append(("Authoritative edition(s)", ed_html))
    if w.get("editions_prep"):
        dl.append(("Edition in preparation", rich(w["editions_prep"])))
    if w["prints"]:
        dl.append(("Early printed editions", "<ul class='prints'>" + "".join(
            f"<li><span class='pn'>{esc(dash(p['name']))}</span> {rich(p['loc'])}</li>" for p in w["prints"]) + "</ul>"))
    tlg = "".join(t for t, _ in (w.get("refs") or {}).get("TLG", [])).strip()
    gv = [e for k in [tlg] + EXTRA_TLG.get(w["id"], []) for e in GV.get(k, [])]
    if gv:
        items = []
        for e in gv:
            ed = ", ".join(x for x in (f"ed. {e['editor']}" if e["editor"] else "", e["year"],
                                        f"vol. {e['vol']}" if e["vol"] else "",
                                        f"pp. {e['pp'].replace('-', '–')}" if e["pp"] else "") if x)
            crit = f"<span class='mmt'> (critical editions: {esc(e['critical'])})</span>" if e["critical"] else ""
            items.append(f"<li><a href='{esc(e['url'])}'>{esc(e['title'])}</a>, {esc(ed)}{crit}</li>")
        dl.append(("Online Greek text", "<ul class='prints'>" + "".join(items) +
                   "</ul><span class='mmt'>Galenus Verbatim (Mera Galeni Folia)</span>"))
    ga = GA["works"].get(w["id"], [])
    if ga:
        items = []
        for e in ga:
            kind = "translation" if e["type"].startswith("Translation") else "summary"
            who = "" if e["by"] in ("Galen", "Hippocrates", "ps-Galen") else f"{esc(e['by'])}, "
            of = f" <span class='mmt'>(of {esc(e['of'])})</span>" if e["of"].startswith("Galen") and a["name"] != "Galenus" else ""
            ed = esc(e["ed"])
            items.append(f"<li>{kind.capitalize()}: {who}<a href='{esc(e['url'])}' title='{esc(e['source'], quote=True)}'>"
                         f"{esc(e['title'])}</a>, {ed}{of}</li>")
        dl.append(("Arabic text online", "<ul class='prints'>" + "".join(items) +
                   "</ul><span class='mmt'>Digital Corpus for Graeco-Arabic Studies</span>"))
    for key, label in (("prints_single", "Separate editions"), ("prints_annotated", "Annotated prints"),
                       ("prints_note", "Notes on prints")):
        if w.get(key):
            dl.append((label, rich(w[key])))
    for lang, label in LANG.items():
        if w["translations"].get(lang):
            dl.append((f"Translations: {label}", rich(w["translations"][lang])))
    if w.get("translations_prep"):
        dl.append(("Translation in preparation", rich(w["translations_prep"])))
    if wd:
        rows_ = [f"{esc(d['by'])}: {esc(d['date'])}" + (f" <span class='mmt'>({esc(d['ref'])})</span>" if d["ref"] else "")
                 for d in wd.get("datings", [])]
        if wd.get("period"):
            rows_.append("Period: " + esc(wd["period"]) + (f" <span class='mmt'>(no. {wd['order']} in the relative chronology)</span>" if wd.get("order") else ""))
        if wd.get("note"):
            rows_.append(f"<span class='mmt'>{esc(wd['note'])}</span>")
        dl.append(("Date of composition", "<br>".join(rows_)))
    elif w.get("date"):
        dl.append(("Date", esc(w["date"])))
    if w.get("note") and w["note"].strip() not in ("--", "-"):
        dl.append(("Note", esc(w["note"])))
    if dl:
        parts.append("<dl>" + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in dl) + "</dl>")
    parts.append("</section>")
    return "".join(parts)


REPO = "https://github.com/alchemiesofscent/cat"
_vm = re.search(r"^## (v[\d.]+)", (ROOT / "CHANGELOG.md").read_text(), re.M) if (ROOT / "CHANGELOG.md").exists() else None
VERSION = _vm[1] if _vm else ""


def changelog_html():
    """CHANGELOG.md -> the version history on the About page, each version linked to its GitHub release."""
    f = ROOT / "CHANGELOG.md"
    if not f.exists():
        return ""
    out, open_ul = ['<h2 id="versions">Version history</h2>',
                    f'<p>Every version is published as a <a href="{REPO}/releases">release on GitHub</a>; '
                    f'the full record of changes is the <a href="{REPO}/commits/main">commit history</a>. '
                    f'Corrections to the source tables: <a href="{REPO}/blob/main/CORRECTIONS.md">CORRECTIONS.md</a>; '
                    f'checks against Pinakes: <a href="{REPO}/blob/main/PINAKES-CHECK.md">PINAKES-CHECK.md</a>; '
                    f'sigla to review: <a href="{REPO}/blob/main/SIGLA-CHECK.md">SIGLA-CHECK.md</a>.</p>'], False
    in_version = False
    for line in f.read_text().splitlines():
        m = re.match(r"## (v[\d.]+) · (.*)", line)
        if m:
            if open_ul:
                out.append("</ul>")
                open_ul = False
            out.append(f'<h3 class="ver"><a href="{REPO}/releases/tag/{m[1]}">{m[1]}</a> <span class="mmt">{esc(m[2])}</span></h3>')
            in_version = True
        elif line.startswith("- ") and in_version:
            if not open_ul:
                out.append("<ul>")
                open_ul = True
            out.append(f"<li>{esc(line[2:])}</li>")
        elif line.strip() and in_version:
            out.append(f"<p>{esc(line)}</p>")
    return "\n".join(out + (["</ul>"] if open_ul else []))


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "authors").mkdir(parents=True)
    shutil.copy(ROOT / "site" / "style.css", OUT / "style.css")
    shutil.copy(ROOT / "site" / "site.js", OUT / "site.js")
    shutil.copytree(ROOT / "site" / "fonts", OUT / "fonts")
    (OUT / ".nojekyll").write_text("")
    shutil.copy(ROOT / "data" / "catalogue.json", OUT / "catalogue.json")

    authors = DATA["authors"]
    search, by_ms = [], defaultdict(list)
    for a in authors:
        for w in a["works"]:
            search.append({"t": w["title_lat"], "g": w.get("title_gr", ""), "b": w.get("abbr", ""),
                           "a": a["name"], "u": f"authors/{a['id']}.html#{w['id']}", "n": len(w["mss"])})
            for m in w["mss"]:
                by_ms[(city(m["city"]), dash(m["shelfmark"]))].append((a, w, m))

    # author pages
    for a in authors:
        dated = sum(1 for w in a["works"] if w["id"] in WD)
        edn = ED_ORDER.get(a["name"])
        def _tl(w):
            el = ed_label(w, edn) if edn else ""
            dl_ = short_date(WD.get(w["id"]))
            return ((f'<span class="edl">{esc(el)}</span>' if el else '<span class="edl">–</span>' if edn else "")
                    + (f'<span class="chl">{esc(dl_)}</span>' if dl_ else '<span class="chl">–</span>'))
        toc = "".join(f'<li data-for="{w["id"]}">{_tl(w)}<span class="tt"><a href="#{w["id"]}">{esc(w["title_lat"])}</a>'
                      f'<span class="n">{len(w["mss"]) or ""}</span></span></li>' for w in a["works"])
        _lab, _ = author_date(a["name"])
        _src, _url, _quote = author_source(a["name"])
        _pkr = (PK.get("authors") or {}).get(a["name"])
        body = (f'<p class="crumb"><a href="../index.html">Authors</a></p><h1>{esc(a["name"])}</h1>'
                + (f'<p class="wdate">{esc(_lab)} <span class="mmt" title="{esc(_quote, quote=True)}">('
                   + (f'<a href="{esc(_url)}">{_src}</a>' if _url else esc(_src)) + ')</span>'
                   + (f' <span class="mmt">· Pinakes: <a href="{esc(_pkr["url"])}">{esc(_pkr["century"])}{(", " + esc(_pkr["date"])) if _pkr["date"] else ""}</a></span>'
                      if _src != "Pinakes" and _pkr and re.search(r"\d", _pkr["century"]) else "")
                   + '</p>' if _lab else "")
                + f'<p class="meta">{len(a["works"])} works · {sum(len(w["mss"]) for w in a["works"])} manuscript witnesses'
                f' · catalogue state {esc(a["source_date"][:4])}-{esc(a["source_date"][4:6])}-{esc(a["source_date"][6:])}</p>'
                + (f'<p class="sortsw" data-target="works">Order: <button data-mode="cat" class="on">catalogue</button>'
                   + (f'<button data-mode="chron">chronological</button>' if dated else "")
                   + (f'<button data-mode="ed">{ED_ORDER[a["name"]]}</button>' if a["name"] in ED_ORDER else "")
                   + (f' <span class="mmt">{dated} of {len(a["works"])} works dated</span>' if dated else "") + "</p>"
                   if dated or a["name"] in ED_ORDER else "")
                + (f'<ol class="toc">{toc}</ol>' if len(a["works"]) > 3 else "")
                + '<div id="works">' 
                + "".join(work_html(a, w) for w in a["works"]) + "</div>")
        (OUT / "authors" / f"{a['id']}.html").write_text(page(a["name"], body, 1))

    # index
    def _adate(a):
        lab, y = author_date(a["name"])
        src = author_source(a["name"])[0]
        return (f"<td class='dt' data-v='{(y if y is not None else 9999) + 10000:05d}' title='{esc(src)}'>{esc(lab)}"
                + (" <span class='mmt'>(W)</span>" if src == "Wikipedia" else " <span class='mmt'>(SC)</span>" if src == "S. Coughlin" else "") + "</td>")
    rows = "".join(
        f'<tr><td><a href="authors/{a["id"]}.html">{esc(a["name"])}</a></td>{_adate(a)}<td class="num">{len(a["works"])}</td>'
        f'<td class="num">{sum(len(w["mss"]) for w in a["works"])}</td></tr>' for a in authors)
    nw = sum(len(a["works"]) for a in authors)
    nm = sum(len(w["mss"]) for a in authors for w in a["works"])
    body = (f'<h1>Greek medical authors: works, manuscripts, editions</h1>'
            f'<p class="lede">For each work, the catalogue identifies the manuscripts that transmit it, specifies the opening folio '
            f'and links directly to the corresponding page of the digitized manuscript. It also lists early printed editions, '
            f'authoritative modern editions and translations. {len(authors)} authors, {nw} works, {nm} manuscript witnesses.</p>'
            '<ul id="hits"></ul>'
            '<p class="mmt">Click a column heading to sort, e.g. by date. Author dates from Pinakes; (W) = Wikipedia, where it is more precise or Pinakes has none; (SC) = supplied by the compiler.</p>'
            '<table class="authors sortable"><thead><tr><th>Author</th><th>Date</th><th class="num">Works</th><th class="num">Witnesses</th></tr></thead>'
            f'<tbody>{rows}</tbody></table>')
    (OUT / "index.html").write_text(page("Ancient Greek Medical Authors: works, manuscripts, editions", body))
    (OUT / "search.json").write_text(json.dumps(search, ensure_ascii=False))

    # manuscripts index
    by_city = defaultdict(list)
    for (c, sm), items in by_ms.items():
        by_city[c].append((sm, items))

    def natkey(s):
        return [int(x) if x.isdigit() else x.lower() for x in re.split(r"(\d+)", s)]

    sections = []
    for c in sorted(by_city, key=lambda x: (x == "—", x)):
        lis = []
        for sm, items in sorted(by_city[c], key=lambda x: natkey(x[0])):
            items.sort(key=lambda x: natkey(x[2]["start"] or ""))
            trs = "".join(
                f'<tr><td class="fol">{esc(dash(m["folios"]))}</td>'
                f'<td><a href="authors/{a["id"]}.html#{w["id"]}">{esc(a["name"])}, {esc(w["title_lat"])}</a></td>'
                f'<td>' + (go(m) if m["url"] else "") + "</td></tr>"
                for a, w, m in items)
            d = ms_date(items[0][2]["city"], items[0][2]["shelfmark"])
            sg = SI["by_ms"].get(ms_key(items[0][2]["city"], items[0][2]["shelfmark"]), [])
            if sg:
                trs += ("<tr><td class='fol'>Sigla</td><td colspan='2'>" + " · ".join(
                    f'<a class="sig" href="{esc(r["viewer"])}" title="{esc(r["printed"], quote=True)}"><span class="sg">{sig_html(r["siglum"])}</span></a> '
                    f'<span class="mmt">({esc(r["edition"])})</span>'
                    for r in {(r["edition"], json.dumps(r["siglum"])): r for r in sg}.values()) + "</td></tr>")
            lis.append(f'<details data-c="{d["cs"][0] if d else 99:02d}"><summary><span class="sm">{esc(sm)}</span> '
                       f'<span class="mdate">{esc(roman_c(d["cs"])) if d else ""}</span> <span class="n">{len(items)}</span></summary>'
                       f'<table class="mss"><tbody>{trs}</tbody></table></details>')
        sections.append(f'<section class="city"><h2 id="{esc(re.sub(r"[^a-z]+", "-", c.lower()))}">{esc(c)}</h2>' + "".join(lis) + "</section>")
    cities = " · ".join(f'<a href="#{esc(re.sub(r"[^a-z]+", "-", c.lower()))}">{esc(c)}</a>'
                        for c in sorted(by_city, key=lambda x: (x == "—", x)))
    body = (f'<h1>Manuscripts</h1><p class="lede">Each shelfmark opens to show the works it contains, in folio order, '
            f'with links to digitized leaf images. Dates are taken from Pinakes, otherwise MediManus. {len(by_ms)} shelfmarks.</p>'
            '<p class="sortsw" data-target="mslist">Order: <button data-mode="city" class="on">by city</button>'
            '<button data-mode="date">by date</button></p>'
            f'<p class="cities">{cities}</p><div id="mslist">' + "".join(sections) + "</div>")
    (OUT / "manuscripts.html").write_text(page("Manuscripts: Ancient Greek Medical Authors", body))

    about = (ROOT / "site" / "about.html").read_text() + changelog_html()
    (OUT / "about.html").write_text(page("About: Ancient Greek Medical Authors", about))
    print(f"built {len(authors)} authors, {nw} works, {nm} witnesses, {len(by_ms)} shelfmarks -> {OUT}")


if __name__ == "__main__":
    main()
