"""Build the static site in docs/ from data/catalogue.json. Standard library only.

Usage: python scripts/build.py
"""
import html, json, re, shutil
from urllib.parse import urlencode
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / "data" / "catalogue.json").read_text())
OUT = ROOT / "docs"

CITY_EN = {"Florenz": "Florence", "Vatikanstadt": "Vatican City", "Venedig": "Venice",
           "Wien": "Vienna", "München": "Munich", "Mailand": "Milan", "Rom": "Rome",
           "Neapel": "Naples", "Genf": "Geneva", "Zürich": "Zurich", "Warschau": "Warsaw",
           "Freiburg (Schweiz)": "Fribourg", "Bayern": "Bavaria"}
LANG = {"de": "German", "en": "English", "fr": "French", "it": "Italian",
        "es": "Spanish", "other": "Other languages"}

esc = html.escape
# hosts that no longer resolve (checked Nov 2026): keep the record, mark the link
STALE_HOSTS = ("mss.bmlonline.it", "213.21.172.25", "163.1.169.40")


def stale(u):
    return bool(u) and any(h in u for h in STALE_HOSTS)


def go(u, label):
    if stale(u):
        return f'<a class="go stale" href="{esc(u)}" title="This viewer has been retired; the link no longer resolves">old link</a>'
    return f'<a class="go" href="{esc(u)}">{label}</a>'


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
<nav><a href="{up}index.html">Authors</a><a href="{up}manuscripts.html">Manuscripts</a><a href="{up}about.html">About</a></nav></header>
<main>{body}</main>
<footer>Compiled from the CMG work catalogues (2019–2020). Built {date.today().isoformat()}.</footer>
</body></html>"""


def witness_rows(mss, show_work=None):
    rows = []
    for m in mss:
        view = go(m["url"], f"view f. {esc(m['start'])}" if m["start"] else "view") if m["url"] else ""
        lead = f"<td>{show_work(m)}</td>" if show_work else ""
        rows.append(f"<tr>{lead}<td>{esc(city(m['city']))}</td><td class='sm'>{esc(dash(m['shelfmark']))}</td>"
                    f"<td class='fol'>{esc(dash(m['folios']))}"
                    + (f" <span class='corr' title='Corrected: {esc(m['corrected'], quote=True)}'>†</span>" if m.get("corrected") else "")
                    + f"</td><td>{view}</td></tr>")
    return "".join(rows)


def work_html(a, w):
    parts = [f'<section class="work" id="{w["id"]}">',
             f'<h3><a class="anchor" href="#{w["id"]}">{esc(w["title_lat"])}</a>'
             + (f' <span class="abbr">{esc(w["abbr"])}</span>' if w.get("abbr") else "") + "</h3>"]
    if w.get("title_gr"):
        parts.append(f'<p class="gr" lang="grc">{esc(w["title_gr"])}</p>')
    refs = ref_links(w)
    if refs:
        parts.append('<p class="refs">' + " · ".join(
            f'<span>{esc(k)} {rich(v)}</span>' for k, v in refs.items()) + "</p>")

    if w["mss"]:
        parts.append(f'<h4>Manuscripts <span class="n">{len(w["mss"])} digitized</span></h4>'
                     '<table class="mss"><thead><tr><th>City</th><th>Shelfmark</th><th>Folios</th><th>Digitization</th></tr></thead>'
                     f'<tbody>{witness_rows(w["mss"])}</tbody></table>')
    else:
        parts.append('<h4>Manuscripts</h4><p class="none">No digitized manuscripts recorded in the catalogue.</p>')
    more = []
    pk = next((u for _, u in refs.get("Pinakes", []) if u), None)
    if pk:
        more.append(f'<a href="{esc(pk)}">Pinakes</a>')
    q = re.sub(r"\s*\(.*?\)|[?*]", "", w["title_lat"].split(";")[0]).strip()
    more.append(f'<a href="https://medimanus.chs.harvard.edu/app/search?{esc(urlencode({"q": q}))}">MediManus</a>')
    parts.append('<p class="more">Full manuscript tradition: ' + " · ".join(more) + "</p>")

    dl = []
    if w.get("editions"):
        dl.append(("Authoritative edition(s)", rich(w["editions"])))
    if w.get("editions_prep"):
        dl.append(("Edition in preparation", rich(w["editions_prep"])))
    if w["prints"]:
        dl.append(("Early printed editions", "<ul class='prints'>" + "".join(
            f"<li><span class='pn'>{esc(dash(p['name']))}</span> {rich(p['loc'])}</li>" for p in w["prints"]) + "</ul>"))
    for key, label in (("prints_single", "Separate editions"), ("prints_annotated", "Annotated prints"),
                       ("prints_note", "Notes on prints")):
        if w.get(key):
            dl.append((label, rich(w[key])))
    for lang, label in LANG.items():
        if w["translations"].get(lang):
            dl.append((f"Translations: {label}", rich(w["translations"][lang])))
    if w.get("translations_prep"):
        dl.append(("Translation in preparation", rich(w["translations_prep"])))
    if w.get("date"):
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
    shutil.copy(ROOT / "site" / "search.js", OUT / "search.js")
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
        toc = "".join(f'<li><a href="#{w["id"]}">{esc(w["title_lat"])}</a>'
                      f'<span class="n">{len(w["mss"]) or ""}</span></li>' for w in a["works"])
        body = (f'<p class="crumb"><a href="../index.html">Authors</a></p><h1>{esc(a["name"])}</h1>'
                f'<p class="meta">{len(a["works"])} works · {sum(len(w["mss"]) for w in a["works"])} manuscript witnesses'
                f' · catalogue state {esc(a["source_date"][:4])}-{esc(a["source_date"][4:6])}-{esc(a["source_date"][6:])}</p>'
                + (f'<ol class="toc">{toc}</ol>' if len(a["works"]) > 3 else "")
                + "".join(work_html(a, w) for w in a["works"]))
        (OUT / "authors" / f"{a['id']}.html").write_text(page(a["name"], body, 1))

    # index
    rows = "".join(
        f'<tr><td><a href="authors/{a["id"]}.html">{esc(a["name"])}</a></td><td class="num">{len(a["works"])}</td>'
        f'<td class="num">{sum(len(w["mss"]) for w in a["works"])}</td></tr>' for a in authors)
    nw = sum(len(a["works"]) for a in authors)
    nm = sum(len(w["mss"]) for a in authors for w in a["works"])
    body = (f'<h1>Greek medical authors: works, manuscripts, editions</h1>'
            f'<p class="lede">For each work: the manuscripts that transmit it, <strong>the folio where the text begins</strong>, '
            f'and a link straight to that page of the digitized manuscript, along with early printed editions, '
            f'authoritative modern editions and translations. {len(authors)} authors, {nw} works, {nm} manuscript witnesses.</p>'
            '<div class="search"><input id="q" type="search" placeholder="Search a work: Latin or Greek title, abbreviation, author …" autocomplete="off">'
            '<ul id="hits"></ul></div>'
            '<table class="authors"><thead><tr><th>Author</th><th class="num">Works</th><th class="num">Witnesses</th></tr></thead>'
            f'<tbody>{rows}</tbody></table><script src="search.js"></script>')
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
                f'<td>' + (go(m["url"], "view") if m["url"] else "") + "</td></tr>"
                for a, w, m in items)
            lis.append(f'<details><summary><span class="sm">{esc(sm)}</span> <span class="n">{len(items)}</span></summary>'
                       f'<table class="mss"><tbody>{trs}</tbody></table></details>')
        sections.append(f'<h2 id="{esc(re.sub(r"[^a-z]+", "-", c.lower()))}">{esc(c)}</h2>' + "".join(lis))
    cities = " · ".join(f'<a href="#{esc(re.sub(r"[^a-z]+", "-", c.lower()))}">{esc(c)}</a>'
                        for c in sorted(by_city, key=lambda x: (x == "—", x)))
    body = (f'<h1>Manuscripts</h1><p class="lede">{len(by_ms)} shelfmarks. Open one to see the works it contains, '
            f'in folio order, with links to the digitized pages.</p><p class="cities">{cities}</p>'
            + "".join(sections))
    (OUT / "manuscripts.html").write_text(page("Manuscripts: Medici Graeci", body))

    about = (ROOT / "site" / "about.html").read_text()
    (OUT / "about.html").write_text(page("About: Medici Graeci", about))
    print(f"built {len(authors)} authors, {nw} works, {nm} witnesses, {len(by_ms)} shelfmarks -> {OUT}")


if __name__ == "__main__":
    main()
