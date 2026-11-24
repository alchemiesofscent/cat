"""Find the sigla pages (Conspectus siglorum / codicum, Sigla, Signorum explicatio ...) in every cmg-viewer volume
and download their page images: data/sigla_pages.json, cache/sigla/<volume>/<page>.jpg.

A sigla section runs from its table-of-contents entry to the next entry. Sections longer than MAX_PAGES are cut
(the conspectus is short; a long range means the next TOC entry is far away).

Usage: python3 scripts/sigla_pages.py [--no-images]
"""
import json, re, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://alchemiesofscent.github.io/cmg-viewer/"
CACHE = ROOT / "cache" / "sigla"
UA = "cat-catalogue/1.0 (scholarly catalogue of Greek medical manuscripts)"
SIGLA = re.compile(r"sigl|conspectus cod|signorum|codices|sigles|siglen|handschriften", re.I)
MAX_PAGES = 6
WIDTH = 1600  # image width for transcription


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=120).read()


def label(x):
    v = x.get("label")
    return (list(v.values())[0][0] if isinstance(v, dict) else v) or ""


def meta(m, key):
    return next((label({"label": x["value"]}) for x in m.get("metadata", []) if label(x) == key), "")


def main():
    vols = json.loads((ROOT / "data" / "cmg_viewer_volumes.json").read_text())["volumes"]
    out = {}
    for v in vols:
        m = json.loads(get(f"{BASE}iiif/{v}/manifest.json"))
        canv = [c["id"] for c in m["items"]]
        idx = {c: i for i, c in enumerate(canv)}
        flat = []  # (label, first canvas index) in TOC order

        def walk(r):
            first = next((idx[i["id"]] for i in r.get("items", []) if i.get("type") == "Canvas" and i["id"] in idx), None)
            flat.append((label(r), first))
            for c in r.get("items", []):
                if c.get("type") == "Range":
                    walk(c)
        for r in m.get("structures", []):
            walk(r)
        starts = sorted({f for _, f in flat if f is not None})
        secs = []
        for lab, f in flat:
            if f is None or not SIGLA.search(lab) or re.search(r"notarum", lab, re.I):
                continue
            nxt = next((s for s in starts if s > f), len(canv))
            pages = list(range(f, min(nxt, f + MAX_PAGES)))
            secs.append({"label": lab, "pages": [
                {"n": int(re.search(r"/p(\d+)$", canv[i])[1]), "label": label(m["items"][i]),
                 "image": m["items"][i]["items"][0]["items"][0]["body"]["service"][0]["id"] + f"/full/{WIDTH},/0/default.jpg",
                 "viewer": f"{BASE}viewer/{v}/?pn={re.search(r'/p(\d+)$', canv[i])[1]}"} for i in pages],
                "truncated": nxt - f > MAX_PAGES})
        if secs:
            out[v] = {"title": label(m), "series": meta(m, "Series number"), "collection": meta(m, "Collection"),
                      "editors": meta(m, "Contributors"), "sections": secs}
    (ROOT / "data" / "sigla_pages.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    n = sum(len(s["pages"]) for v in out.values() for s in v["sections"])
    print(f"{len(out)} volumes with sigla pages, {sum(len(v['sections']) for v in out.values())} sections, {n} pages")
    if "--no-images" in sys.argv:
        return
    for v, d in out.items():
        for s in d["sections"]:
            for p in s["pages"]:
                f = CACHE / v / f"p{p['n']}.jpg"
                if f.exists():
                    continue
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_bytes(get(p["image"]))
                time.sleep(0.5)
    print("images in", CACHE)


if __name__ == "__main__":
    main()
