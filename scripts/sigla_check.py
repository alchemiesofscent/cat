"""Match the transcribed sigla (data/sigla/<volume>.json) to catalogue works and manuscripts, check them, and write
data/sigla_index.json (used by scripts/build.py) and SIGLA-CHECK.md (the review list).

Works: a volume belongs to the catalogue works whose edition links point into it (as in build.viewer_for_edition);
a volume with one list per work is split by the list's work names. Manuscripts: by shelfmark key (build.ms_key).

Checks (failures go to SIGLA-CHECK.md; entries are still shown, because the printed list is the authority for its
edition):
- the shelfmark could not be keyed (no city or number recognised);
- the manuscript is not known for this work to the CMG list, Pinakes or MediManus;
- the same siglum is used twice in one list for different manuscripts (unless the list says so);
- a volume or list that could not be tied to a catalogue work;
- the Wellmann Dioscorides lists against the TEI witness list in wellmann-edition.

Usage: python3 scripts/sigla_check.py
"""
import difflib, json, re, sys
from collections import defaultdict
from pathlib import Path

sys.argv = sys.argv[:1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build as B  # noqa: E402

ROOT = B.ROOT
SIG = ROOT / "data" / "sigla"
PAGES = json.loads((ROOT / "data" / "sigla_pages.json").read_text())
TEI_WELLMANN = Path.home() / "github" / "wellmann-edition" / "sources" / "sigla" / "listWit.xml"


def sig_text(s):
    return s["base"] + (f"^{s['sup']}" if s.get("sup") else "") + (f"_{s['sub']}" if s.get("sub") else "")


def norm_title(t):
    t = re.sub(r"\(.*?\)|\[.*?\]", " ", t.lower())
    return re.sub(r"[^a-z ]", " ", t.replace("j", "i").replace("v", "u")).split()


STOP = {"de", "in", "et", "ad", "librum", "libri", "liber", "commentarii", "commentarium", "commentaria", "commentarius",
        "fragmenta", "hippocratis", "galeni", "sive", "qui", "quae", "eos", "the", "on", "of"}


def similar(a, b):
    """Share of b's significant title words found in a (and the plain string ratio, whichever is higher)."""
    ta, tb = set(norm_title(a)) - STOP, set(norm_title(b)) - STOP
    cover = len(ta & tb) / len(tb) if tb else 0
    return max(cover if len(tb) >= 2 or cover == 1 else 0,
               difflib.SequenceMatcher(None, " ".join(norm_title(a)), " ".join(norm_title(b))).ratio())


ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50}


def arabic(r):
    n = 0
    for i, c in enumerate(r):
        v = ROMAN[c]
        n += -v if i + 1 < len(r) and ROMAN[r[i + 1]] > v else v
    return n


def series_key(coll, s):
    """'CMG', 'XI 1,4' / '11 1,4' -> 'CMG|11.1.4'; 'Suppl. Or. V 2' -> 'CMG|suppl.or.5.2'."""
    s = re.sub(r"\b[IVXL]+\b", lambda m: str(arabic(m[0])), s)
    return f"{coll}|" + ".".join(re.findall(r"suppl|or|\d+", s.lower()))


def volume_works():
    """volume id -> catalogue works whose edition note names the volume's series number (CMG XI 1,4 ...)."""
    by_series = {}
    for v, d in PAGES.items():
        if d.get("series") and d.get("collection") in ("CMG", "CML"):
            by_series[series_key(d["collection"], d["series"])] = v
    out = defaultdict(list)
    for a in B.DATA["authors"]:
        for w in a["works"]:
            text = "".join(t for t, _ in (w.get("editions") or []))
            for coll, ser in re.findall(r"\b(CMG|CML)\s+((?:Suppl\.\s*(?:Or\.\s*)?)?[IVXL\d]+(?:\s*[\d,]+)?)", text):
                v = by_series.get(series_key(coll, ser))
                if v and w not in [x for _, x in out[v]]:
                    out[v].append((a, w))
    return out


def all_works(title):
    """Works of the authors named in a volume title (for volumes no edition note points to)."""
    t = " ".join(norm_title(title))
    return [(a, w) for a in B.DATA["authors"] for w in a["works"]
            if any(len(x) > 3 and x[:5] in t for x in norm_title(a["name"].replace("Ps.-", ""))[:1])]


def match_section(sec, cands):
    """Works this list is for: by the list's work names among the volume's works."""
    names = sec.get("works") or []
    if len(cands) == 1 and len(names) <= 1:
        return cands
    hits = []
    for n in names:
        scored = sorted(((max(similar(n, w["title_lat"]),
                              1.0 if w.get("abbr") and len(w["abbr"]) > 3 and w["abbr"].lower().strip(". ") in n.lower() else 0), a, w)
                         for a, w in cands), key=lambda x: -x[0])
        if scored and scored[0][0] >= 0.75:
            hits.append((scored[0][1], scored[0][2]))
    return list({w["id"]: (a, w) for a, w in hits}.values()) or (cands if len(cands) == 1 else [])


# lists the title matching cannot tie (titles worded differently): (volume, words in the list's work name) -> works
MANUAL = {
    ("cmg_02", ""): ["aretaeus-cappadox-001", "aretaeus-cappadox-002", "aretaeus-cappadox-003", "aretaeus-cappadox-004"],
    ("cmg_03_01", ""): ["rufus-ephesius-001"],
    ("cmg_05_04_02", "bonis malisque"): ["galenus-035"],
    ("cmg_05_10_03", "iulianum"): ["galenus-081"],
    ("cmg_06_02_02", "reliquiae"): ["oribasius-001"],
    ("cmg_06_02_02", "incerti"): ["oribasius-002"],
    ("wa_galen_ut_resp", ""): ["galenus-019"],
    ("cmg_01_02_01", "septimestri"): ["hippocrates-039"],
    ("cmg_01_02_01", "octimestri"): ["hippocrates-040"],
    ("cmg_05_12_06", ""): ["galenus-079"],
    ("suppl_or_05_01", ""): ["galenus-078"],
    ("suppl_or_05_02", ""): ["galenus-078"],
    ("suppl_or_05_03", ""): ["galenus-078"],
    ("cmg_11_02_01", ""): [],  # Ps.-Galen, In Hipp. De septimanis (Arabic): not in the catalogue
}
INDIRECT = re.compile(r"^(Gal|Lat|Ar|Arab|Nic|Hipp|Orib|Theoph|Syr|Hebr|Pall|Aet|Paul|Hunain|Ḥun)\b|\(", re.I)


def indirect(e):
    """Witness of the indirect tradition: a commentary, translation or parallel text, not a copy of the work."""
    note = (e.get("note") or "").lower()
    return (e["type"] == "translation" or bool(INDIRECT.search(e["siglum"]["base"]))
            or any(k in note for k in ("parallel", "latin version", "arabic version", "translation", "indirect", "commentary",
                                        "manuscript of", "not a witness", "not of galen", "witness of the", "sub hipp",
                                        "sub orib", "sub gal", "hippocratic", "hippocratici", "aristotel", "hebrew",
                                        "excerpt")))


def manual(vol, sec):
    names = " ".join(sec.get("works") or []).lower() + " " + sec.get("label", "").lower()
    ids = next((v for (vv, k), v in MANUAL.items() if vv == vol and k in names), None)
    if ids is None:
        return None
    return [(a, w) for a in B.DATA["authors"] for w in a["works"] if w["id"] in ids]


def loose(k):
    """Key without 'med' (Vindobonensis 51 = Vind. med. gr. 51) and with Heidelberg Palatini as Vatican."""
    if not k:
        return k
    c, f, n = k.split("|")
    return f"{'vatican' if c == 'heidelberg' else c}|{' '.join(x for x in f.split() if x != 'med')}|{n}"


def known_keys(w):
    ours = {loose(B.ms_key(m["city"], m["shelfmark"])): i for i, m in enumerate(w["mss"])}
    pk = {loose(B.ms_key(x["city"], f"{x['fonds']} {x['cote']}")): x for x in B.PK_BY_WORK.get(w["id"], [])}
    mm = {loose(B.ms_key("", x["shelfmark"])): x for x in B.MM_BY_WORK.get(w["id"], [])}
    return ours, pk, mm


def wellmann_tei():
    if not TEI_WELLMANN.exists():
        return None
    t = TEI_WELLMANN.read_text()
    return {re.sub(r"\s+", "", n): re.sub(r"<[^>]+>|\s+", " ", txt).strip()
            for n, txt in re.findall(r'<witness[^>]*\bn="([^"]+)"[^>]*>(.*?)</witness>', t, re.S)}


def main():
    vw = volume_works()
    index = {"by_work": defaultdict(list), "by_ms": defaultdict(list)}
    review = defaultdict(list)
    n_entries = n_attached = n_other = 0
    for f in sorted(SIG.glob("*.json")):
        d = json.loads(f.read_text())
        vol = d["volume"]
        eds = [x.strip() for x in re.split(r"/|;| et |, ", d.get("editor", "")) if x.strip()]
        editor = eds[0] + " et al." if len(eds) > 2 else "/".join(eds)
        ed = ", ".join(x for x in (editor, d.get("series", "")) if x) or vol
        if not d.get("series") and d.get("year"):
            ed += f" {d['year']}"
        for u in d.get("uncertain") or []:
            review["Uncertain readings (from the transcriber)"].append(f"{ed}: {u}")
        cands = vw.get(vol) or []
        for sec in d["sections"]:
            works = manual(vol, sec)
            if works is None:
                works = match_section(sec, cands)
            if not works and manual(vol, sec) is None:  # volume not linked from the catalogue: try the author's works
                works = match_section(sec, all_works(PAGES.get(vol, {}).get("title", "")))
            page = sec["pages"][0] if sec.get("pages") else None
            viewer = f"{B.CV_BASE}{vol}/?pn={page}" if page else ""
            if not works:
                review["Lists for works not in the catalogue (or not tied to one)"].append(
                    f"{ed} ({vol}), “{sec['label']}”: {'; '.join(sec.get('works') or []) or 'no work named'}")
                continue
            seen = defaultdict(set)
            for e in sec["entries"]:
                if e["type"] not in ("manuscript", "papyrus"):
                    continue
                n_entries += 1
                key = B.ms_key(e.get("city", ""), e.get("normalized", "")) or B.ms_key("", e.get("normalized", ""))
                if not indirect(e):
                    seen[sig_text(e["siglum"])].add(key)
                rec = {"siglum": e["siglum"], "edition": ed, "volume": vol, "viewer": viewer, "printed": e["printed"],
                       "normalized": e.get("normalized", ""), "city": e.get("city", ""), "folios": e.get("folios", ""),
                       "date": e.get("date", ""), "key": key}
                if key:
                    index["by_ms"][key].append(rec | {"works": [w["id"] for _, w in works]})
                lk = loose(key)
                for a, w in works:
                    ours, pk, mm = known_keys(w)
                    if lk and lk in ours:
                        x_key = B.ms_key(w["mss"][ours[lk]]["city"], w["mss"][ours[lk]]["shelfmark"])
                    else:
                        x_key = key
                    if indirect(e):
                        status = "indirect"
                    elif lk and lk in ours:
                        status = "ours"
                        n_attached += 1
                    elif lk and lk in pk:
                        status = "pinakes"
                    elif lk and lk in mm:
                        status = "medimanus"
                    else:
                        status = "unverified"
                    if status != "ours":
                        n_other += 1
                    x = rec | {"status": status, "key": x_key}
                    if lk and lk in pk:
                        x["pinakes"] = {"cote_id": pk[lk]["cote_id"], "folios": pk[lk]["folios"],
                                        "century": pk[lk]["century"], "date": pk[lk]["date"]}
                    index["by_work"][w["id"]].append(x)
                    if not key:
                        review["Shelfmarks that could not be read as city + number"].append(
                            f"{w['id']} · {sig_text(e['siglum'])} ({ed}) = {e['printed']} → “{e.get('normalized', '')}”")
                    elif status == "unverified":
                        review["Not known for this work to the CMG list, Pinakes or MediManus"].append(
                            f"{w['id']} {w['title_lat']} · {sig_text(e['siglum'])} ({ed}) = {e['printed']} → {e.get('normalized', '')}")
            for s, keys in seen.items():
                if len(keys) > 1 and not any("one siglum" in (e.get("note") or "").lower() for e in sec["entries"]
                                             if sig_text(e["siglum"]) == s):
                    review["Same siglum for different manuscripts in one list"].append(f"{ed}, “{sec['label']}”: {s}")
    # Wellmann's Dioscorides: transcription against the TEI witness list
    tei = wellmann_tei()
    if tei:
        for f in sorted(SIG.glob("wa_dioscurides*.json")):
            d = json.loads(f.read_text())
            ours = {sig_text(e["siglum"]).replace("^", "").replace("_", ""): e["printed"]
                    for s in d["sections"] for e in s["entries"] if e["type"] in ("manuscript", "papyrus")}
            for s in sorted(set(ours) - set(tei)):
                review["Wellmann (Dioscorides): sigla not in the TEI witness list"].append(f"{d['volume']}: {s} = {ours[s]}")
    index["by_work"] = dict(index["by_work"])
    index["by_ms"] = dict(index["by_ms"])
    (ROOT / "data" / "sigla_index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1))
    L = ["# Sigla: check", "",
         f"Generated by `scripts/sigla_check.py` from `data/sigla/*.json`; do not edit. {n_entries} manuscript sigla; "
         f"{n_attached} attached to a digitized manuscript in the CMG list, {n_other} shown as other manuscripts of the "
         f"edition. Fix a transcription in `data/sigla/<volume>.json` and re-run.", ""]
    for k, v in review.items():
        L += [f"## {k} ({len(v)})", ""] + [f"- {x}" for x in v] + [""]
    (ROOT / "SIGLA-CHECK.md").write_text("\n".join(L))
    print(f"{n_entries} manuscript sigla, {n_attached} attached to our witnesses, {n_other} other; "
          + ", ".join(f"{k}: {len(v)}" for k, v in review.items()))


if __name__ == "__main__":
    main()
