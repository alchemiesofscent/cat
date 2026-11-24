"""Arabic translations and summaries of Galen and Hippocrates in the Digital Corpus for Graeco-Arabic
Studies (graeco-arabic-studies.org/texts): data/graeco_arabic.json, keyed by catalogue work id.

The texts page lists each Greek work with its Arabic translations and the Arabic summaries made of it
(Alexandrian Summaries, Ibn Zurʿah, Maimonides, Ḥunayn, Ibn Riḍwān). MAP joins the corpus's Latin
title to our catalogue id; texts of works not in MAP are reported and left out.

Usage: python3 scripts/graeco_arabic.py
"""
import html, json, re, urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://www.graeco-arabic-studies.org"
UA = "Mozilla/5.0 (cat-catalogue; scholarly catalogue of Greek medical manuscripts)"

MAP = {
    ("Galen", "Ad Glauconem de methodo medendi"): "galenus-062",
    ("Galen", "Adhortatio ad artes addiscendas/Protrepticus"): "galenus-001",
    ("Galen", "Ars medica"): "galenus-006",
    ("Galen", "Compendium Timaei Platonis"): "galenus-091",
    ("Galen", "De anatomicis administrationibus"): "galenus-010",
    ("Galen", "De bono habitu"): "galenus-024",
    ("Galen", "De causis contentivis"): "galenus-092",
    ("Galen", "De consuetudinibus"): "galenus-094",
    ("Galen", "De crisibus"): "galenus-059",
    ("Galen", "De diebus decretoriis"): "galenus-060",
    ("Galen", "De elementis ex Hippocrate"): "galenus-007",
    ("Galen", "De facultatibus naturalibus"): "galenus-009",
    ("Galen", "De febrium differentiis"): "galenus-041",
    ("Galen", "De inaequali intemperie"): "galenus-050",
    ("Galen", "De musculorum dissectione ad tirones"): "galenus-086",
    ("Galen", "De nervorum dissectione"): "galenus-013",
    ("Galen", "De nominibus medicinalibus"): "galenus-102",
    ("Galen", "De optima corporis nostri constitutione"): "galenus-023",
    ("Galen", "De optimo medico cognoscendo"): "galenus-098",
    ("Galen", "De ossibus ad tirones"): "galenus-011",
    ("Galen", "De partibus artis medicativae"): "galenus-103",
    ("Galen", "De partium homoeomerium differentia"): "galenus-100",
    ("Galen", "De pulsibus ad tirones"): "galenus-053",
    ("Galen", "De sectis ad eos qui introducuntur"): "galenus-004",
    ("Galen", "De septimestri partu"): "galenus-105",
    ("Galen", "De temperamentis"): "galenus-008",
    ("Galen", "De venarum arteriarumque dissectione"): "galenus-012",
    ("Galen", "De victu attenuante"): "galenus-106",
    ("Galen", "In Hippocratis Aphorismos"): "galenus-079",
    ("Galen", "In Hippocratis Aphorismos I–V"): "galenus-079",
    ("Galen", "In Hippocratis Aphorismos VI–VII"): "galenus-079",
    ("Galen", "In Hippocratis De officina medici"): "galenus-085",
    ("Galen", "In Hippocratis Epidemiarum librum I"): "galenus-078",
    ("Galen", "In Hippocratis Epidemiarum librum II"): "galenus-078",
    ("Galen", "In Hippocratis Epidemiarum librum VI"): "galenus-078",
    ("Galen", "Quod animi mores corporis temperamenta sequantur"): "galenus-025",
    ("Galen", "Quod optimus medicus sit quoque philosophus"): "galenus-003",
    ("ps-Galen", "De diaeta in morbis acutis secundum Hippocratem"): "galenus-090",
    # Galen's commentaries lost in Greek, known through Ibn Riḍwān's notes: shown with the Hippocratic work
    ("Galen", "In Hippocratis De alimento"): "hippocrates-056",
    ("Galen", "In Hippocratis De humoribus"): "hippocrates-020",
    ("Hippocrates", "Aphorismi"): "hippocrates-012",
    ("Hippocrates", "De aere, aquis, locis"): "hippocrates-002",
    ("Hippocrates", "De alimento"): "hippocrates-056",
    ("Hippocrates", "De diaeta in morbis acutis"): "hippocrates-004",
    ("Hippocrates", "De genitura"): "hippocrates-041",
    ("Hippocrates", "De humoribus"): "hippocrates-020",
    ("Hippocrates", "De natura hominis"): "hippocrates-024",
    ("Hippocrates", "De natura pueri"): "hippocrates-042",
    ("Hippocrates", "De officina medici"): "hippocrates-008",
    ("Hippocrates", "De salubri diaeta"): "hippocrates-024",
    ("Hippocrates", "De superfoetatione"): "hippocrates-047",
    ("Hippocrates", "Iusiurandum"): "hippocrates-013",
    ("Hippocrates", "Prognosticon"): "hippocrates-003",
}


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def parse_work(s):
    """'Galen , Ars medica (Τέχνη ἰατρική) English: The Art of Medicine' -> parts."""
    m = re.match(r"(.*?) , (.*?)(?: \(([^()]*)\))? English: (.*)$", s)
    return m.groups() if m else (None, s, None, None)


def main():
    req = urllib.request.Request(BASE + "/texts", headers={"User-Agent": UA})
    page = urllib.request.urlopen(req, timeout=120).read().decode("utf-8", "replace")
    rows = []
    for b in page.split('data-object="text"')[1:]:
        v = re.search(r'href="(/view/[^"]+)">([^<]*)</a>', b)
        w = re.search(r"<h4[^>]*>Work</h4>\s*<p>(.*?)</p>", b, re.S)
        ty = re.search(r"<b>Type:</b>(.*?)<br>", b, re.S)
        src = re.search(r">Source</h4>\s*<p>(.*?)</p>", b, re.S)
        if v and w:
            by, title, gr, en = parse_work(clean(w[1]))
            rows.append({"url": BASE + v[1], "ed": clean(v[2]), "by": by, "title": title, "gr": gr, "en": en,
                         "type": clean(ty[1]) if ty else "", "source": clean(src[1]) if src else ""})
    # Greek title -> (author, Latin title) of the Greek work the corpus files the text under
    greek = {}
    for r in rows:
        if r["by"] in ("Galen", "Hippocrates", "ps-Galen", "ps-Hippocrates") and r["gr"]:
            greek.setdefault(r["gr"], (r["by"], r["title"]))
    out, skipped = {}, set()
    for r in rows:
        if "Arabic" not in r["type"] or not r["gr"]:
            continue
        if r["gr"].startswith("Εἰς") and "περὶ χυμῶν" in r["gr"]:  # no Greek-work entry of its own
            key = ("Galen", "In Hippocratis De humoribus")
        elif r["gr"] in greek:
            key = greek[r["gr"]]
        else:
            continue
        wid = MAP.get(key)
        if not wid:
            skipped.add(key)
            continue
        lst = out.setdefault(wid, [])
        if r["url"] not in [x["url"] for x in lst]:
            lst.append({k: r[k] for k in ("url", "ed", "by", "title", "en", "type", "source")}
                       | {"of": f"{key[0]}, {key[1]}"})
    for k in sorted(skipped):
        print("not in catalogue:", k)
    (ROOT / "data" / "graeco_arabic.json").write_text(json.dumps(
        {"source": "Digital Corpus for Graeco-Arabic Studies (graeco-arabic-studies.org)",
         "retrieved": date.today().isoformat(), "works": out}, ensure_ascii=False, indent=1))
    print(f"{sum(len(v) for v in out.values())} Arabic texts for {len(out)} catalogue works")


if __name__ == "__main__":
    main()
