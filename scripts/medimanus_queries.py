"""Test the MediManus search link of every work and keep, for each, the most specific query that finds something:
author + two title words, then author + one word, then the title words alone, then the author alone.
Writes data/medimanus_queries.json (work id -> query), which build.py uses for the 'MediManus' search link.

MediManus requires every search word to match, so fewer words find more.
Usage: python3 scripts/medimanus_queries.py
"""
import json, re, sys, time, urllib.request
from pathlib import Path

sys.argv = sys.argv[:1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build as B  # noqa: E402
import medimanus as M  # noqa: E402


def hits(text):
    body = json.dumps({"fulltext": text, "facets": [], "facet_fields": [],
                       "contexts": [f"urn:madoc:collection:{M.COLLECTION}"]}).encode()
    req = urllib.request.Request(M.API.replace("page_size=1000", "page_size=1"), data=body, method="POST",
                                 headers={"Content-Type": "application/json", "User-Agent": "cat-catalogue/1.0"})
    for _ in range(3):
        try:
            d = json.load(urllib.request.urlopen(req, timeout=120))
            return d.get("pagination", {}).get("totalResults", len(d.get("results", [])))
        except Exception:
            time.sleep(3)
    return -1  # unknown (server error): treat as usable


def main():
    out = {}
    for a in B.DATA["authors"]:
        for w in a["works"]:
            full = B.mm_query(a, w, B.MM_BY_WORK.get(w["id"], []))
            author = B.MM_AUTHOR.get(a["name"]) or a["name"].replace("Ps.-", "").split()[0]
            words = full[len(author):].split()
            for q in [full, " ".join([author] + words[:1]), " ".join(words), author]:
                if not q.strip():
                    continue
                n = hits(q)
                time.sleep(0.5)
                if n != 0:
                    out[w["id"]] = q
                    break
            print(w["id"], "->", out.get(w["id"], "(nothing found)"), flush=True)
    (B.ROOT / "data" / "medimanus_queries.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
