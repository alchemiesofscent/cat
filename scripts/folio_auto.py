"""Fill folio links in data/folio_links.csv automatically where the library's IIIF manifest names its pages by folio.

Deterministic only: a row is filled when the manifest has a page labelled exactly with the start folio
('16r', 'fol. 16r'); nothing is estimated. Covered: Gallica (newer scans are labelled, older ones say 'NP' and are
skipped) and the Bodleian. Other viewers (Vatican, Escorial, Ambrosiana, Internet Culturale) number images, not folios,
and stay for entry by hand. Filled rows get note 'auto: ...'; rows filled by hand are never touched.

Usage: python3 scripts/folio_auto.py
"""
import csv, hashlib, json, re, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILE = ROOT / "data" / "folio_links.csv"
CACHE = ROOT / "cache" / "manifests"
UA = "cat-catalogue/1.0 (scholarly catalogue of Greek medical manuscripts)"


def get_json(url):
    f = CACHE / (hashlib.sha1(url.encode()).hexdigest() + ".json")
    if f.exists():
        return json.loads(f.read_text())
    CACHE.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        data = json.load(urllib.request.urlopen(req, timeout=90))
    except Exception as e:
        print("  fail", url, e)
        return None
    f.write_text(json.dumps(data))
    time.sleep(0.5)
    return data


def label(x):
    v = x.get("label")
    return v if isinstance(v, str) else (list(v.values())[0][0] if v else "")


def canvases(m):
    return m.get("items") or (m.get("sequences") or [{}])[0].get("canvases") or []


def norm_folio(s):
    """'fol. 16r' / 'f. 016 r' / '16r' -> '16r'; bare '16' -> '16r'."""
    m = re.fullmatch(r"\s*(?:fol\.?|f\.?|folio)?\s*0*(\d+)\s*([rv])?\s*", (s or "").lower())
    return f"{m[1]}{m[2] or 'r'}" if m else None


def find(m, start):
    want = norm_folio(start)
    if not want:
        return None
    for i, c in enumerate(canvases(m)):
        if norm_folio(label(c)) == want:
            return i, c, label(c)
    return None


def gallica(url, start):
    a = re.search(r"ark:/12148/(btv1b\w+?)(?:/|$|\.|\?)", url)
    if not a:
        return None
    m = get_json(f"https://openapi.bnf.fr/iiif/presentation/v3/ark:/12148/{a[1]}/manifest.json")
    hit = m and find(m, start)
    return (f"https://gallica.bnf.fr/ark:/12148/{a[1]}/f{hit[0] + 1}.item", hit[2]) if hit else None


def bodleian(url, start):
    u = re.search(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", url)
    if not u:
        return None
    m = get_json(f"https://iiif.bodleian.ox.ac.uk/iiif/manifest/{u[1]}.json")
    hit = m and find(m, start)
    if not hit:
        return None
    cid = re.search(r"canvas/([0-9a-f-]{36})", hit[1].get("@id") or hit[1].get("id", ""))
    return (f"https://digital.bodleian.ox.ac.uk/objects/{u[1]}/surfaces/{cid[1]}/", hit[2]) if cid else None


def main():
    with FILE.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    filled = 0
    for r in rows:
        if r["folio_url"].strip():
            continue
        u = r["manuscript_url"]
        res = gallica(u, r["start"]) if "gallica.bnf.fr" in u else bodleian(u, r["start"]) if "bodleian" in u else None
        if res:
            r["folio_url"], r["note"] = res[0], f"auto: page labelled '{res[1]}' in the library's IIIF manifest"
            filled += 1
    with FILE.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"filled {filled} rows automatically; {sum(1 for r in rows if r['folio_url'])} of {len(rows)} rows have a folio link")


if __name__ == "__main__":
    main()
