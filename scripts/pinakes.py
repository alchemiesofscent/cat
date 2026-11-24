"""Fetch Pinakes (IRHT) work pages for every catalogue work with a Pinakes number and extract the
witness list with dates: data/pinakes.json.

Pinakes guards against bulk access, so this is deliberately slow and resumable:
one request every DELAY seconds, every page cached in cache/pinakes/, and the run stops at the
first guard page (re-run later to continue).

Usage: python3 scripts/pinakes.py            # fetch what is missing, then parse
       python3 scripts/pinakes.py --parse    # parse the cache only
"""
import html, json, re, sys, time, urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "pinakes"
DELAY = 12
URL = "https://pinakes.irht.cnrs.fr/notices/oeuvre/{}/"
UA = "Mozilla/5.0 (cat-catalogue; scholarly catalogue of Greek medical manuscripts)"


def work_ids():
    cat = json.loads((ROOT / "data" / "catalogue.json").read_text())
    ids = {}
    for a in cat["authors"]:
        for w in a["works"]:
            for t, u in (w.get("refs") or {}).get("Pinakes", []):
                for n in re.findall(r"\d+", (u or "") + " " + t):
                    if len(n) <= 6:
                        ids.setdefault(n, []).append(w["id"])
                        break
    return ids


def fetch(ids):
    CACHE.mkdir(parents=True, exist_ok=True)
    todo = [i for i in ids if not (CACHE / f"oeuvre_{i}.html").exists()]
    print(f"{len(ids)} Pinakes works, {len(todo)} to fetch")
    for n, i in enumerate(todo, 1):
        req = urllib.request.Request(URL.format(i), headers={"User-Agent": UA})
        try:
            page = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
        except Exception as e:
            print(f"stop at {i}: {e}")
            return False
        if "sentinel-guard-page" in page or "Service temporairement indisponible" in page:
            print(f"stop at {i}: Pinakes guard page after {n - 1} fetches; re-run later")
            return False
        (CACHE / f"oeuvre_{i}.html").write_text(page)
        print(f"  {n}/{len(todo)} oeuvre {i}", flush=True)
        time.sleep(DELAY)
    return True


def author_ids():
    """Pinakes author number for each catalogue author, from the cached work pages."""
    cat = json.loads((ROOT / "data" / "catalogue.json").read_text())
    ids = work_ids()
    out = {}
    for a in cat["authors"]:
        for w in a["works"]:
            for i, ws in ids.items():
                f = CACHE / f"oeuvre_{i}.html"
                if w["id"] in ws and f.exists():
                    m = re.search(r"/notices/auteur/(\d+)/", f.read_text())
                    if m and a["name"] not in out:
                        out[a["name"]] = m[1]
    return out


def fetch_authors():
    todo = [(n, i) for n, i in author_ids().items() if not (CACHE / f"auteur_{i}.html").exists()]
    print(f"{len(todo)} author pages to fetch")
    for n, (name, i) in enumerate(todo, 1):
        req = urllib.request.Request(f"https://pinakes.irht.cnrs.fr/notices/auteur/{i}/", headers={"User-Agent": UA})
        try:
            page = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
        except Exception as e:
            print(f"stop at author {i}: {e}"); return False
        if "sentinel-guard-page" in page:
            print(f"stop at author {i}: guard page"); return False
        (CACHE / f"auteur_{i}.html").write_text(page)
        print(f"  author {n}/{len(todo)} {name}", flush=True)
        time.sleep(DELAY)
    return True


def cell(c):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", c))).strip()


def parse(ids):
    out = {}
    for i, works in ids.items():
        f = CACHE / f"oeuvre_{i}.html"
        if not f.exists():
            continue
        t = f.read_text()
        wits = []
        for row in re.findall(r"<tr>(.*?)</tr>", t, re.S):
            cote = re.search(r"/notices/cote/(\d+)/", row)
            if not cote:
                continue
            tds = [cell(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
            if len(tds) < 8:
                continue
            wits.append({"country": tds[0], "city": tds[1], "library": tds[2], "fonds": tds[3],
                         "cote": tds[4], "cote_id": cote[1], "folios": tds[5],
                         "century": tds[6], "date": tds[7]})
        out[i] = {"works": works, "witnesses": wits}
    authors = {}
    for name, i in author_ids().items():
        f = CACHE / f"auteur_{i}.html"
        if not f.exists():
            continue
        t = cell(re.sub(r"<(script|style)[^>]*>.*?</\1>", "", f.read_text(), flags=re.S))
        cen = re.search(r"Siècle\s*:\s*(.*?)\s*(?:Date\s*:|Identifiants|Oeuvres)", t)
        dat = re.search(r"Date\s*:\s*(.*?)\s*(?:Identifiants|Oeuvres|Lien)", t)
        title = re.search(r"Notice\s*:\s*([^<|]+)", f.read_text())
        pname = html.unescape(title[1]).strip() if title else ""
        norm = lambda x: x[:4].lower().replace("j", "i").replace("u", "v")
        same = norm(pname) == norm(name.replace("Ps.-", ""))
        if not same:
            print(f"  skip {name}: Pinakes number in the catalogue leads to '{pname}'")
            continue
        authors[name] = {"pinakes_id": i, "pinakes_name": pname, "century": cen[1] if cen else "", "date": dat[1] if dat else "",
                         "url": f"https://pinakes.irht.cnrs.fr/notices/auteur/{i}/"}
    (ROOT / "data" / "pinakes.json").write_text(json.dumps(
        {"source": "Pinakes, IRHT (pinakes.irht.cnrs.fr)", "retrieved": date.today().isoformat(),
         "oeuvres": out, "authors": authors}, ensure_ascii=False, indent=1))
    print(f"{len(authors)} author records")
    print(f"parsed {len(out)} Pinakes works, {sum(len(v['witnesses']) for v in out.values())} witnesses")


if __name__ == "__main__":
    ids = work_ids()
    if "--parse" not in sys.argv:
        if fetch(ids):
            fetch_authors()
    parse(ids)
