"""Import MediManus (CHS) manuscript records: which works each manuscript contains, from which folio.

Fetches the MediManus collection listing (one request, used with CHS's permission), parses each
manuscript's 'Author and title' field, maps works to catalogue ids via data/medimanus_titles.json,
and writes data/medimanus.json. Unreviewed titles are reported, never guessed.

Usage: python3 scripts/medimanus.py            # fetch live, then build data/medimanus.json
       python3 scripts/medimanus.py --offline  # reuse cache/medimanus_search.json
"""
import difflib, json, re, sys, unicodedata, urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache" / "medimanus_search.json"
API = "https://medimanus.chs.harvard.edu/app/api/madoc/search/api?page=1&page_size=1000"
COLLECTION = "7388"
PAGE = "https://medimanus.chs.harvard.edu/app/en/collections/7388/manifests/{}"


def fetch():
    body = json.dumps({"facets": [{"type": "metadata", "subtype": "ll.city"}], "facet_fields": [], "contexts": [f"urn:madoc:collection:{COLLECTION}"],
                       "ordering": {"type": "metadata", "subtype": "ll.mss_short_id", "direction": "ascending"}})
    req = urllib.request.Request(API, data=body.encode(), method="POST",
                                 headers={"Content-Type": "application/json", "User-Agent": "cat-catalogue/1.0"})
    with urllib.request.urlopen(req, timeout=180) as r:
        data = json.load(r)
    n, total = len(data["results"]), data["pagination"]["totalResults"]
    if n == 0 or n < total:
        raise SystemExit(f"MediManus returned {n} of {total} manuscripts; keeping the previous data")
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_text(json.dumps(data, ensure_ascii=False))
    return data


def md(r, key):
    return [m["value"]["en"][0] for m in r["metadata"] if m["label"]["en"][0] == key]


def split_top(s):
    out, depth, cur = [], 0, ""
    for ch in s:
        depth += (ch == "(") - (ch == ")")
        if ch == ";" and depth == 0:
            out.append(cur.strip()); cur = ""
        else:
            cur += ch
    return [x for x in out + [cur.strip()] if x]


FOL = re.compile(r"\s*\(((?:ff?\.|pp?\.)?\s*[\dA-Za-z\[\]\-–\s,.?]*\d[\dA-Za-z\[\]\-–\s,.?]*|r-v)\)\s*$")


def norm(t):
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"\(.*?\)", "", t).replace("v", "u").replace("j", "i")
    return " ".join(re.sub(r"[^a-z ]", " ", t).split())


def core(t):
    return re.sub(r"\s*\([^()]*\)", "", t).strip()


def main():
    data = json.loads(CACHE.read_text()) if "--offline" in sys.argv else fetch()
    cat = json.loads((ROOT / "data" / "catalogue.json").read_text())
    conc = json.loads((ROOT / "data" / "medimanus_titles.json").read_text())
    authors = {a["name"]: a for a in cat["authors"]}
    out, unreviewed = [], {}
    for r in data["results"]:
        sid = md(r, "LL.MSS_Short_ID")[0]
        mid = r["resource_id"].split(":")[-1]
        for entry in split_top((md(r, "LL.Author_and_title") or [""])[0]):
            m = FOL.search(entry)
            folios = m.group(1).strip() if m else ""
            body = entry[:m.start()] if m else entry
            if "," not in body:
                continue
            au, title = (x.strip() for x in body.split(",", 1))
            our = conc["authors"].get(au)
            if not our:
                continue
            key = f"{au}|{core(title)}"
            if key in conc["titles"]:
                wid = conc["titles"][key]
            else:
                best, score = None, 0
                for w in authors[our]["works"]:
                    s = difflib.SequenceMatcher(None, norm(title), norm(w["title_lat"])).ratio()
                    if s > score:
                        best, score = w, s
                wid = best["id"] if score >= 0.95 else None
                if wid is None:
                    unreviewed[key] = unreviewed.get(key, 0) + 1
            if not wid:
                continue
            fol = re.sub(r"^(ff?|pp?)\.\s*", "", folios).replace("-", "–")
            start = re.split(r"\s*[–,]\s*", fol)[0] if fol else ""
            out.append({"work": wid, "shelfmark": sid, "folios": fol,
                        "unit": "pp." if folios.startswith("p") else "ff.",
                        "start": start, "title": title, "url": PAGE.format(mid)})
    (ROOT / "data" / "medimanus.json").write_text(json.dumps(
        {"source": "MediManus, Center for Hellenic Studies (medimanus.chs.harvard.edu)",
         "retrieved": date.today().isoformat(), "manuscripts": len(data["results"]), "witnesses": out},
        ensure_ascii=False, indent=1))
    print(f"{len(data['results'])} MediManus manuscripts -> {len(out)} witnesses of {len({o['work'] for o in out})} catalogue works")
    if unreviewed:
        print(f"{len(unreviewed)} titles by catalogue authors not yet in medimanus_titles.json:")
        for k, n in sorted(unreviewed.items()):
            print(f"  {n:3}  {k}")


if __name__ == "__main__":
    main()
