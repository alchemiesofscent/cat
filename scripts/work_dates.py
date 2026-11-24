"""Build data/work_dates.json: dates of composition for catalogue works.

- Galen: the chronology table "Galen Date Tables with References 190129.xlsx" (sheet MASTER), joined on
  Fichtner number: period, relative order, and the datings of Ilberg, Bardong, Peterson, Hankinson.
- Hippocrates: Craik's dates, already in the catalogue (work 'date', years BCE).

Each entry has 'year' (a single number for sorting; negative = BCE), 'label' (display text) and,
for Galen, 'order' (position in the relative chronology) and 'datings' (one row per authority).

Usage: python scripts/work_dates.py ["/mnt/d/onedrive/13 CMG"]   (needs openpyxl for Galen)
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(sys.argv[1] if len(sys.argv) > 1 else "/mnt/d/onedrive/13 CMG")
AUTHORITIES = (("Ilberg", 6, 7), ("Bardong", 8, 9), ("Peterson", 10, 11), ("Hankinson", 12, 13))


def first_year(s):
    m = re.search(r"\b(1\d\d|2[01]\d)\b", str(s or ""))
    return int(m[1]) if m else None


def clean(v):
    return re.sub(r"\s+", " ", str(v)).strip() if v not in (None, "", "-") else ""


def galen(cat):
    import openpyxl
    ws = openpyxl.load_workbook(SRC / "Galen" / "Galen Date Tables with References 190129.xlsx",
                                data_only=True)["MASTER"]
    rows = list(ws.iter_rows(values_only=True))[1:]
    by_f = {}
    for r in rows:
        if r[0] is None:
            continue
        datings = [{"by": name, "date": clean(r[i]).replace(" - ", "–"), "ref": clean(r[p])}
                   for name, i, p in AUTHORITIES if clean(r[i])]
        period = clean(r[5])
        year = next((first_year(d["date"]) for d in sorted(datings, key=lambda d: d["by"] != "Bardong")
                     if first_year(d["date"])), None) or first_year(period)
        label = next((d["date"] for d in datings if d["by"] == "Bardong"), "") or \
            (datings[0]["date"] if datings else re.sub(r"^\d\.\s*", "", period))
        by_f[str(int(r[0]))] = {"year": year, "label": f"{label} CE" if datings else label,
                                "order": int(r[4]) if str(r[4]).strip().isdigit() else None,
                                "period": re.sub(r"^\d\.\s*", "", period), "datings": datings,
                                "note": clean(r[19]) if len(r) > 19 else ""}
    out, miss = {}, []
    for a in cat["authors"]:
        if a["name"] != "Galenus":
            continue
        for w in a["works"]:
            f = "".join(t for t, _ in w["refs"].get("Fichtner", [])).strip().lstrip("0")
            if f in by_f:
                out[w["id"]] = by_f[f]
            else:
                miss.append(w["title_lat"])
    print(f"Galen: {len(out)} works dated; undated: {len(miss)}")
    return out


def hippocrates(cat):
    out = {}
    for a in cat["authors"]:
        if a["name"] != "Hippocrates":
            continue
        for w in a["works"]:
            d = (w.get("date") or "").strip()
            ys = [int(y) for y in re.findall(r"\d{3}", d)]
            if ys:
                out[w["id"]] = {"year": -round(sum(ys) / len(ys)),
                                "label": d.replace("--", "–") + " BCE", "datings": [
                                    {"by": "Craik", "date": d.replace("--", "–") + " BCE",
                                     "ref": "E. Craik, The ‘Hippocratic’ Corpus (2015)"}]}
    print(f"Hippocrates: {len(out)} works dated")
    return out


if __name__ == "__main__":
    cat = json.loads((ROOT / "data" / "catalogue.json").read_text())
    data = {**hippocrates(cat), **galen(cat)}
    (ROOT / "data" / "work_dates.json").write_text(json.dumps(data, ensure_ascii=False, indent=1))
