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
             "leidensis": "leiden", "scal": "leiden", "vulc": "leiden"}
_KEEP = {"suppl", "urb", "pal", "barb", "reg", "ottob", "coisl", "coislin", "barocc", "med", "hist", "phil", "theol",
         "harley", "add", "sloane", "lat", "chis", "ross"}


def ms_key(city_name, shelf):
    shelf = re.sub(r"\(.*?\)|=.*$", "", re.split(r",\s*(?:MS|ff?\.|f\.)", shelf)[0])
    words = re.findall(r"[A-Za-zÀ-ÿ]+", (city_name or "") + " " + shelf)
    c = next((_CITY_KEY[w.lower()] for w in words if w.lower() in _CITY_KEY), "")
    norm = lambda w: "coisl" if w == "coislin" else "suppl" if w.startswith(("suppl", "supplément")) else w
    fonds = sorted({norm(w.lower()) for w in words if norm(w.lower()) in _KEEP})
    nums = [str(int(n)) for n in re.findall(r"\d+", shelf)]
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
WP_AUTH = json.loads(_WPFILE.read_text())["authors"] if _WPFILE.exists() else {}


def author_source(name):
    """(source name, url, note) for an author's date."""
    a = (PK.get("authors") or {}).get(name)
    if a and re.search(r"\d", a["century"]):
        return "Pinakes", a["url"], ""
    if name in WP_AUTH:
        return "Wikipedia", WP_AUTH[name]["url"], WP_AUTH[name]["quote"]
    return "", "", ""


def author_date(name):
    """Pinakes author record -> (label, sort year) e.g. ('s. V–IV BCE (460–377 BCE)', -460);
    Wikipedia (data/author_dates_wikipedia.json) where Pinakes has no usable date."""
    a = (PK.get("authors") or {}).get(name)
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
    r = RELOC.get((u, m.get("start") or ""))
    if r:
        note = " (approximate)" if r["method"] == "offset" else ""
        if r["new_folio_url"]:
            return f'<a class="go" href="{esc(r["new_folio_url"])}" title="Current viewer{note}">{folio_label}</a>'
        return (f'<a class="go" href="{esc(r["new_manuscript_url"])}" '
                f'title="Current viewer; opens the manuscript, not the folio">view ms.</a>')
    if stale(u):
        return f'<a class="go stale" href="{esc(u)}" title="This viewer has been retired; the link no longer resolves">old link</a>'
    return f'<a class="go" href="{esc(u)}">{folio_label}</a>'


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


def page(title, body, depth=0):
    up = "../" * depth
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<link rel="stylesheet" href="{up}style.css">
</head><body>
<header class="site"><a class="brand" href="{up}index.html">Medici Graeci</a>
<span class="tag">works · manuscripts · printed editions · translations</span>
<nav><a href="{up}index.html">Authors</a><a href="{up}manuscripts.html">Manuscripts</a><a href="{up}about.html">About</a></nav>
<form class="filter" action="{up}index.html" role="search"><input id="filter" name="q" type="search" placeholder="Filter this page · Enter searches everything" autocomplete="off" aria-label="Filter"></form>
</header>
<main>{body}</main>
<script src="{up}site.js" data-root="{up}"></script>
<footer>Compiled and built by Sean Coughlin, from the work catalogues he prepared for the CMG (2019–2020), with manuscript data from Pinakes (IRHT, retrieved {PK["retrieved"]}) and MediManus (CHS, retrieved {MM["retrieved"]}) and Galen texts from Galenus Verbatim. Built {date.today().isoformat()}.</footer>
</body></html>"""


def witness_rows(mss, show_work=None):
    rows = []
    for m in mss:
        view = go(m, f"view f. {esc(m['start'])}" if m["start"] else "view") if m["url"] else ""
        lead = f"<td>{show_work(m)}</td>" if show_work else ""
        rows.append(f"<tr>{lead}<td>{esc(city(m['city']))}</td><td class='sm'>{esc(dash(m['shelfmark']))}</td>"
                    + date_cell(ms_date(m["city"], m["shelfmark"])) +
                    f"<td class='fol'>{esc(dash(m['folios']))}"
                    + (f" <span class='corr' title='Corrected: {esc(m['corrected'], quote=True)}'>†</span>" if m.get("corrected") else "")
                    + f"</td><td>{view}</td></tr>")
    return "".join(rows)


def core_differs(mm_title, our_title):
    """Show MediManus's title only when it says something extra, e.g. (partim) or (frag.)."""
    return "(" in mm_title


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

    if w["mss"]:
        parts.append(f'<h4>Manuscripts <span class="n">{len(w["mss"])} digitized</span></h4>'
                     '<table class="mss sortable"><thead><tr><th>City</th><th>Shelfmark</th><th>Date</th><th>Folios</th><th>Digitization</th></tr></thead>'
                     f'<tbody>{witness_rows(w["mss"])}</tbody></table>')
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
            trs.append(f"<tr><td class='sm'>{esc(x['shelfmark'])}</td>" + date_cell(d) +
                       f"<td class='fol'>{esc(x['unit'] if x['folios'] else '')} {esc(x['folios'])}</td>"
                       f"<td class='mmt'>{label}</td><td>{flag}</td>"
                       f"<td><a class='go' href='{esc(x['url'])}'>MediManus</a></td></tr>")
        parts.append(f'<h4>In MediManus <span class="n">{len(mmw)}</span></h4>'
                     f'<table class="mss mm sortable"><thead><tr><th>Shelfmark</th><th>Date</th><th>Folios</th><th></th><th>CMG list</th><th></th></tr></thead><tbody>{"".join(trs)}</tbody></table>')
    more = []
    pk = next((u for _, u in refs.get("Pinakes", []) if u), None)
    if pk:
        more.append(f'<a href="{esc(pk)}">Pinakes</a>')
    q = re.sub(r"\s*\(.*?\)|[?*]", "", w["title_lat"].split(";")[0]).strip()
    more.append(f'<a href="https://medimanus.chs.harvard.edu/app/search?{esc(urlencode({"q": q}))}">MediManus</a>')
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
        toc = "".join(f'<li data-for="{w["id"]}"><a href="#{w["id"]}">{esc(w["title_lat"])}</a>'
                      f'<span class="n">{len(w["mss"]) or ""}</span></li>' for w in a["works"])
        _lab, _ = author_date(a["name"])
        _src, _url, _quote = author_source(a["name"])
        body = (f'<p class="crumb"><a href="../index.html">Authors</a></p><h1>{esc(a["name"])}</h1>'
                + (f'<p class="wdate">{esc(_lab)} <span class="mmt" title="{esc(_quote, quote=True)}">(<a href="{esc(_url)}">{_src}</a>)</span></p>' if _lab else "")
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
                + (" <span class='mmt'>(W)</span>" if src == "Wikipedia" else "") + "</td>")
    rows = "".join(
        f'<tr><td><a href="authors/{a["id"]}.html">{esc(a["name"])}</a></td>{_adate(a)}<td class="num">{len(a["works"])}</td>'
        f'<td class="num">{sum(len(w["mss"]) for w in a["works"])}</td></tr>' for a in authors)
    nw = sum(len(a["works"]) for a in authors)
    nm = sum(len(w["mss"]) for a in authors for w in a["works"])
    body = (f'<h1>Greek medical authors: works, manuscripts, editions</h1>'
            f'<p class="lede">For each work: the manuscripts that transmit it, <strong>the folio where the text begins</strong>, '
            f'and a link straight to that page of the digitized manuscript, along with early printed editions, '
            f'authoritative modern editions and translations. {len(authors)} authors, {nw} works, {nm} manuscript witnesses.</p>'
            '<ul id="hits"></ul>'
            '<p class="mmt">Click a column heading to sort, e.g. by date. Author dates from Pinakes; (W) = from Wikipedia where Pinakes has none.</p>'
            '<table class="authors sortable"><thead><tr><th>Author</th><th>Date</th><th class="num">Works</th><th class="num">Witnesses</th></tr></thead>'
            f'<tbody>{rows}</tbody></table>')
    (OUT / "index.html").write_text(page("Medici Graeci: works, manuscripts, editions", body))
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
            lis.append(f'<details data-c="{d["cs"][0] if d else 99:02d}"><summary><span class="sm">{esc(sm)}</span> '
                       f'<span class="mdate">{esc(roman_c(d["cs"])) if d else ""}</span> <span class="n">{len(items)}</span></summary>'
                       f'<table class="mss"><tbody>{trs}</tbody></table></details>')
        sections.append(f'<section class="city"><h2 id="{esc(re.sub(r"[^a-z]+", "-", c.lower()))}">{esc(c)}</h2>' + "".join(lis) + "</section>")
    cities = " · ".join(f'<a href="#{esc(re.sub(r"[^a-z]+", "-", c.lower()))}">{esc(c)}</a>'
                        for c in sorted(by_city, key=lambda x: (x == "—", x)))
    body = (f'<h1>Manuscripts</h1><p class="lede">{len(by_ms)} shelfmarks. Open one to see the works it contains, '
            f'in folio order, with links to the digitized pages. Dates from Pinakes, otherwise MediManus.</p>'
            '<p class="sortsw" data-target="mslist">Order: <button data-mode="city" class="on">by city</button>'
            '<button data-mode="date">by date</button></p>'
            f'<p class="cities">{cities}</p><div id="mslist">' + "".join(sections) + "</div>")
    (OUT / "manuscripts.html").write_text(page("Manuscripts: Medici Graeci", body))

    about = (ROOT / "site" / "about.html").read_text()
    (OUT / "about.html").write_text(page("About: Medici Graeci", about))
    print(f"built {len(authors)} authors, {nw} works, {nm} witnesses, {len(by_ms)} shelfmarks -> {OUT}")


if __name__ == "__main__":
    main()
