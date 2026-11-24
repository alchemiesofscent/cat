"""Worklist for folio-level links, filled in by hand: data/folio_links.csv.

One row per work × manuscript whose link opens only the manuscript (Pinakes' digitization links, and catalogue
witnesses whose old link could only be relocated to the manuscript). Open `manuscript_url`, find the start folio,
paste the page's URL into `folio_url`. scripts/build.py then links that row at the folio ("view f. 52v").

Re-running adds new rows and keeps everything already filled in. Rows are sorted for working through: the author with
the most missing links first, then manuscript by manuscript (most works first), folios ascending.
Usage: python3 scripts/folio_worklist.py
"""
import csv, re, sys
from pathlib import Path

sys.argv = sys.argv[:1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build as B  # noqa: E402

FILE = B.ROOT / "data" / "folio_links.csv"
COLS = ["work_id", "author", "work", "city", "shelfmark", "siglum", "folios", "start", "manuscript_url", "folio_url", "note", "source"]


def start(f):
    m = re.match(r"\s*0*(\d+\s*[rv]?)", f or "")
    return m[1].replace(" ", "") if m else ""


def rows():
    for a in B.DATA["authors"]:
        for w in a["works"]:
            seen = {B.ms_key(m["city"], m["shelfmark"]) for m in w["mss"]} | \
                   {B.ms_key("", x["shelfmark"]) for x in B.MM_BY_WORK.get(w["id"], [])}
            for m in w["mss"]:
                h = B.go(m)
                if "view ms." in h or "old link" in h or ">Pinakes<" in h:
                    u = re.search(r'href="([^"]+)"', h)
                    yield {"work_id": w["id"], "author": a["name"], "work": w["title_lat"], "city": B.city(m["city"]),
                           "shelfmark": B.display_shelf(m["city"], m["shelfmark"]), "folios": m["folios"],
                           "start": m.get("start") or start(m["folios"]), "manuscript_url": u[1] if u else m["url"],
                           "source": "catalogue"}
            done = set()
            for x in B.PK_BY_WORK.get(w["id"], []):
                k = B.ms_key(x["city"], f"{x['fonds']} {x['cote']}")
                if x["cote_id"] in B.PKDIG and k not in seen and (x["cote_id"], x["folios"]) not in done:
                    done.add((x["cote_id"], x["folios"]))
                    yield {"work_id": w["id"], "author": a["name"], "work": w["title_lat"], "city": B.city(x["city"]),
                           "shelfmark": B.pk_shelf(x), "folios": x["folios"], "start": start(x["folios"]),
                           "manuscript_url": B.PKDIG[x["cote_id"]][0]["url"], "source": f"pinakes:{x['cote_id']}"}


def sigla():
    """(work id, shelfmark key) -> 'Lᵇ (Olivieri, CMG VIII 1); ...' for manuscripts with a siglum in an edition of the work."""
    out = {}
    for wid, recs in B.SI["by_work"].items():
        for r in recs:
            if r.get("key") and r["status"] != "indirect":
                s = r["siglum"]["base"] + (f"^{r['siglum']['sup']}" if r["siglum"].get("sup") else "")
                out.setdefault((wid, r["key"]), []).append(f"{s} ({r['edition']})")
    return {k: "; ".join(dict.fromkeys(v)) for k, v in out.items()}


def edition_rows(have):
    """Manuscripts of an edition's sigla list with a digitization known to Pinakes, not yet in the worklist."""
    for a in B.DATA["authors"]:
        for w in a["works"]:
            for r in B.SI["by_work"].get(w["id"], []):
                pk = r.get("pinakes")
                if r["status"] in ("indirect", "ours") or not r.get("key") or not pk or pk["cote_id"] not in B.PKDIG:
                    continue
                if (w["id"], r["key"]) in have:
                    continue
                have.add((w["id"], r["key"]))
                yield {"work_id": w["id"], "author": a["name"], "work": w["title_lat"], "city": r["city"],
                       "shelfmark": B.display_shelf(r["city"], r["normalized"] or r["printed"]),
                       "folios": r["folios"] or pk["folios"], "start": start(r["folios"] or pk["folios"]),
                       "manuscript_url": B.PKDIG[pk["cote_id"]][0]["url"], "source": f"edition:{r['volume']}"}


def main():
    old = {}
    if FILE.exists():
        with FILE.open(newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                old[(r["work_id"], r["shelfmark"], r["folios"])] = r
    out = []
    base = list(rows())
    have = {(r["work_id"], B.ms_key(r["city"], r["shelfmark"])) for r in base}
    sg = sigla()
    for r in base + list(edition_rows(have)):
        r["siglum"] = sg.get((r["work_id"], B.ms_key(r["city"], r["shelfmark"])), "")
        k = (r["work_id"], r["shelfmark"], r["folios"])
        prev = old.pop(k, {})
        out.append({c: (prev.get(c) or r.get(c, "")) for c in COLS})
    out += [r for r in old.values() if r["folio_url"]]  # keep rows filled in earlier even if the source row has gone
    # work order: the author with the most missing links first; within an author, manuscript by manuscript
    # (one manuscript usually carries several works), the manuscripts with most works first, folios ascending
    from collections import Counter
    # manuscripts with a siglum in a critical edition of the work come first
    per_author = Counter((bool(r["siglum"]), r["author"]) for r in out if not r["folio_url"])
    per_ms = Counter((r["author"], r["city"], r["shelfmark"]) for r in out)
    nat = lambda s: [int(t) if t.isdigit() else t for t in re.findall(r"\d+|\D+", s or "")]
    out.sort(key=lambda r: (not r["siglum"], -per_author[(bool(r["siglum"]), r["author"])], r["author"], -per_ms[(r["author"], r["city"], r["shelfmark"])],
                            r["city"], nat(r["shelfmark"]), nat(r["start"])))
    with FILE.open("w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=COLS)
        wr.writeheader()
        wr.writerows(out)
    filled = sum(1 for r in out if r["folio_url"])
    print(f"{sum(1 for r in out if r['siglum'])} rows with a siglum in an edition (done first); ", end="")
    print(f"{len(out)} rows ({len({(r['city'], r['shelfmark']) for r in out})} manuscripts), {filled} filled in -> {FILE}")


if __name__ == "__main__":
    main()
