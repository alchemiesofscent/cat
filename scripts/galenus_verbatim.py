"""Import the Galenus Verbatim edition index (Mera Galeni Folia) into data/galenus_verbatim.json.

Mera Galeni Folia (https://galenus-verbatim.github.io/mera-galeni-folia/) publishes one page per
edition of each Galen work, addressed by CTS URN (tlg0057.tlgNNN.<edition>). Catalogue works carry
TLG numbers (0057.NNN), so each work can link to its online Greek text.

Usage: python3 scripts/galenus_verbatim.py
"""
import html, json, re, urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://galenus-verbatim.github.io"
INDEX = BASE + "/mera-galeni-folia/"
LINK = re.compile(r'<a [^>]*href="(/mera-galeni-folia/urn:cts:greekLit:(tlg\d{4})\.(tlg\d{3})\.([^/"]+)/)"')


def text(fragment):
    t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()
    return re.sub(r"\s+([,.])", r"\1", t)


def main():
    req = urllib.request.Request(INDEX, headers={"User-Agent": "cat-catalogue/1.0"})
    page = urllib.request.urlopen(req, timeout=60).read().decode()
    blocks = re.split(r'(?=<a [^>]*href="/mera-galeni-folia/urn:cts)', page)[1:]
    out = {}
    for b in blocks:
        m = LINK.match(b)
        if not m:
            continue
        path, auth, work, edition = m.groups()
        t = text(b)
        urn = f"urn:cts:greekLit:{auth}.{work}.{edition}"
        label = t.split(urn)[0].strip(" .")
        ed = re.search(r"ed\. ([^,]+), ([\d\-]+)(?:, vol\. ([^,]+))?(?:, pp\. ([\d\- ]+))?", label)
        crit = re.search(r"editio\(nes\) critica\(e\):\s*(.*?)(?:\s+translatio Latina:|$)", t)
        tlg = f"{auth[3:]}.{work[3:]}"
        out.setdefault(tlg, []).append({
            "urn": urn, "url": BASE + path, "title": label.split(" , ed.")[0].split(", ed.")[0].strip(),
            "editor": ed[1].strip() if ed else "", "year": ed[2] if ed else "",
            "vol": (ed[3] or "").strip() if ed else "", "pp": (ed[4] or "").strip() if ed else "",
            "critical": crit[1].strip(" .") if crit else "",
        })
    if len(out) < 50:
        raise SystemExit(f"only {len(out)} works parsed from {INDEX}; not overwriting")
    (ROOT / "data" / "galenus_verbatim.json").write_text(json.dumps(
        {"source": INDEX, "retrieved": date.today().isoformat(), "works": out}, ensure_ascii=False, indent=1))
    print(f"{sum(len(v) for v in out.values())} editions of {len(out)} works")


if __name__ == "__main__":
    main()
