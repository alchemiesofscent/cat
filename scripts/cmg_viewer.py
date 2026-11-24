"""Record which volumes the CMG viewer (alchemiesofscent.github.io/cmg-viewer) serves:
data/cmg_viewer_volumes.json. build.py rewrites links to the old BBAW scan pages
(cmg.bbaw.de/epubl/online/<volume>.php?...pn=N) into viewer links with the same pn.

Usage: python3 scripts/cmg_viewer.py
"""
import json, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
URL = "https://alchemiesofscent.github.io/cmg-viewer/data/catalogue.json"

data = json.load(urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "cat-catalogue/1.0"}), timeout=120))
vols = sorted({i["volumeId"] for i in data["items"]})
if len(vols) < 50:
    raise SystemExit(f"only {len(vols)} volumes; not overwriting")
base = URL.rsplit("/data/", 1)[0] + "/"
items = [{"volume": i["volumeId"], "series": i.get("seriesNumber") or "", "collection": i.get("collection") or "",
          "label": i.get("label") or "", "url": i.get("viewerDeepLink") or i.get("viewerUrl") or ""}
         for i in data["items"]]
for i in items:
    if i["url"] and not i["url"].startswith("http"):
        i["url"] = base + i["url"].lstrip("./")
(ROOT / "data" / "cmg_viewer_volumes.json").write_text(json.dumps(
    {"source": URL, "generatedAt": data.get("generatedAt"), "volumes": vols, "items": items},
    ensure_ascii=False, indent=1))
print(len(vols), "viewer volumes")
