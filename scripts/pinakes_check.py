"""Check every catalogue witness against the witnesses Pinakes lists for the same work.

Writes data/pinakes_check.json and PINAKES-CHECK.md:
- 'fixes': the shelfmark is not in Pinakes for this work, and Pinakes lists exactly one manuscript of the same
  collection whose number differs by one digit (or two swapped digits) and whose start folio agrees (±1).
  scripts/build.py applies these, marks them as corrected, and takes the link from Pinakes.
- 'review': not in Pinakes or MediManus for this work, and no such single candidate. Listed for checking by hand;
  candidates with the same start folio are given.
A fix by hand in data/corrections.json always wins, because this check reads the corrected catalogue.

Usage: python3 scripts/pinakes_check.py   (after scripts/pinakes.py --parse)
"""
import json, re, sys
from pathlib import Path

sys.argv = sys.argv[:1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build as B  # noqa: E402  (shelfmark keys, MediManus index)

ROOT = B.ROOT


def start(f):
    m = re.match(r"0*(\d+)", (f or "").strip())
    return int(m[1]) if m else None


def near(a, b):
    """'6236' ~ '6326', '2161' ~ '2163', '5' ~ '4': same length, one digit changed or two neighbours swapped."""
    if len(a) != len(b) or a == b:
        return False
    d = [i for i in range(len(a)) if a[i] != b[i]]
    return len(d) == 1 or (len(d) == 2 and d[1] == d[0] + 1 and a[d[0]] == b[d[1]] and a[d[1]] == b[d[0]])


def renumber(shelf, old, new):
    """Replace the number that differs in our own spelling of the shelfmark."""
    o, n = old.split("."), new.split(".")
    for a, b in zip(o, n):
        if a != b:
            return re.sub(rf"(?<!\d)0*{a}(?!\d)", b, shelf, count=1)
    return shelf


def url_shelf(u, city):
    """The shelfmark number a viewer URL names, where it names one (BL, Vatican, Heidelberg), else None."""
    m = (re.search(r"bl\.uk/manuscripts/Viewer\.aspx\?ref=[a-z]+_ms_(\d+)", u or "") or
         re.search(r"MSS_[A-Za-z.]*?gr\.(\d+)", u or "") or re.search(r"cpgraec(\d+)|bav_pal_gr_(\d+)", u or ""))
    return next((str(int(g)) for g in m.groups() if g), None) if m else None


VAT_FONDS = {"Vat": "", "Barb": "barb", "Urb": "urb", "Pal": "pal", "Ott": "ottob", "Reg": "reg", "Chig": "chis"}


def url_key(u):
    """Shelfmark key a viewer URL spells out itself (Vatican, British Library, Heidelberg), else None."""
    u = u or ""
    m = re.search(r"MSS_([A-Za-z]+)\.gr\.(\d+)", u)
    if m:
        return f"vatican|{VAT_FONDS.get(m[1], m[1].lower())}|{int(m[2])}"
    m = re.search(r"ref=([a-z]+)_ms_(\d+)", u)
    if m:
        return f"london|{'' if m[1] == 'arundel' else m[1]}|{int(m[2])}"
    m = re.search(r"cpgraec(\d+)|bav_pal_gr_(\d+)", u)
    if m:
        return f"vatican|pal|{int(m[1] or m[2])}"  # Vat. Pal. gr., digitized in Heidelberg
    return None


def url_ident(u):
    """Manuscript-level identity of a viewer URL (page and zoom parts removed), for matching Pinakes' links."""
    u = u or ""
    for pat in (r"ark:/12148/(btv1b\w+?)(?:/|$|\.|\?)", r"(DTL_\d+)", r"e-codices\.unifr\.ch/\w\w/(?:list/one/)?(\w+/\w+)",
                r"(bsb\d{8})", r"plutei/id/(\d+)", r"(MSS_[\w.]+?)(?:/|$)", r"internetculturale\.it/.*?id=([^&]+)"):
        m = re.search(pat, u)
        if m:
            return m[1]
    return None


def same_ms(a, b):
    """Two shelfmark keys name the same manuscript (city and first number; collection words may differ)."""
    a, b = (x.replace("heidelberg|", "vatican|") if x else x for x in (a, b))
    return bool(a and b) and a.split("|")[0] == b.split("|")[0] and a.split("|")[2].split(".")[0] == b.split("|")[2].split(".")[0] \
        and (a.split("|")[2] == b.split("|")[2] or "." not in a.split("|")[2] + b.split("|")[2])


def link_check():
    """Does each link open the manuscript the catalogue names? Evidence: the URL itself, or Pinakes linking
    the same digitization to a shelfmark."""
    by_ident = {}
    for o in B.PK["oeuvres"].values():
        for x in o["witnesses"]:
            for d in (B.PK.get("cotes") or {}).get(x["cote_id"], {}).get("digitized", []):
                i = url_ident(d["url"])
                if i:
                    by_ident.setdefault(i, (B.ms_key(x["city"], f"{x['fonds']} {x['cote']}"), f"{x['fonds']} {x['cote']}"))
    n, bad = 0, []
    for a in B.DATA["authors"]:
        for w in a["works"]:
            for m in w["mss"]:
                k = B.ms_key(m["city"], m["shelfmark"])
                said, how = url_key(m["url"]), "the URL"
                if not said and url_ident(m["url"]) in by_ident:
                    said, label = by_ident[url_ident(m["url"])]
                    how = f"Pinakes ({label})"
                if not said:
                    continue
                n += 1
                if not same_ms(k, said):
                    bad.append({"work": w["id"], "title": w["title_lat"], "shelfmark": m["shelfmark"], "folios": m["folios"],
                                "url": m["url"], "link_names": said, "evidence": how})
    return n, bad


def main():
    # build.py applies the previous run's fixes on import; check the catalogue as extracted
    B.DATA = json.loads((ROOT / "data" / "catalogue.json").read_text())
    by_work = {}
    for o in B.PK["oeuvres"].values():
        for wid in o["works"]:
            by_work.setdefault(wid, []).extend(o["witnesses"])
    pkkey = lambda x: B.ms_key(x["city"], f"{x['fonds']} {x['cote']}")
    fixes, review, n_ok, n_all = [], [], 0, 0
    for a in B.DATA["authors"]:
        for w in a["works"]:
            if w["id"] not in by_work:
                continue
            pks = {}
            for x in by_work[w["id"]]:
                pks.setdefault(pkkey(x), x)
            ours = {B.ms_key(m["city"], m["shelfmark"]) for m in w["mss"]}
            mm = {B.ms_key("", x["shelfmark"]) for x in B.MM_BY_WORK.get(w["id"], [])}
            for m in w["mss"]:
                n_all += 1
                k = B.ms_key(m["city"], m["shelfmark"])
                if k in pks or k in mm:
                    n_ok += 1
                    continue
                c, f, num = (k or "||").split("|")
                # same city and number, collection named differently ('Vind. gr.' / 'med. gr.'): a spelling, not an error
                if k and any(kk and kk.split("|")[0] == c and kk.split("|")[2] == num and
                             set(kk.split("|")[1].split()) ^ set(f.split()) <= {"med"} for kk in pks):
                    n_ok += 1
                    continue
                s0 = start(m["folios"])
                same_fol = [x for kk, x in pks.items() if kk and kk not in ours and kk.split("|")[0] == c
                            and s0 is not None and start(x["folios"]) is not None and abs(start(x["folios"]) - s0) <= 1]
                strong = [x for x in same_fol if pkkey(x).split("|")[1] == f and near(num, pkkey(x).split("|")[2])]
                rec = {"work": w["id"], "title": w["title_lat"], "city": m["city"], "shelfmark": m["shelfmark"],
                       "folios": m["folios"]}
                named = url_shelf(m["url"], m["city"])
                if len(strong) == 1 and named == num:
                    rec["note"] = (f"Pinakes lists {strong[0]['fonds']} {strong[0]['cote']} (f. {strong[0]['folios']}), "
                                   f"but the catalogue's link is to {m['shelfmark']}")
                    strong = []
                if len(strong) == 1:
                    x = strong[0]
                    new = renumber(m["shelfmark"], num, pkkey(x).split("|")[2])
                    fixes.append(rec | {"set": {"shelfmark": new}, "cote_id": x["cote_id"],
                                        "pinakes": f"{x['fonds']} {x['cote']}, f. {x['folios']}",
                                        "reason": f"Pinakes lists {x['fonds']} {x['cote']} (f. {x['folios']}) for this work, "
                                                  f"not {m['shelfmark']}"})
                else:
                    review.append(rec | {"candidates": [f"{x['fonds']} {x['cote']}, f. {x['folios']}" for x in same_fol][:4]})
    n_links, link_bad = link_check()
    (ROOT / "data" / "pinakes_check.json").write_text(json.dumps(
        {"checked": n_all, "confirmed": n_ok, "fixes": fixes, "review": review,
         "links_checked": n_links, "link_mismatch": link_bad}, ensure_ascii=False, indent=1))
    L = ["# Shelfmarks checked against Pinakes", "",
         f"{n_all} witnesses of works with a Pinakes number; {n_ok} are listed by Pinakes or MediManus for the same work.",
         "Generated by `scripts/pinakes_check.py`; do not edit. To overrule a line, add a fix to `data/corrections.json`.", "",
         f"## Corrected automatically ({len(fixes)})", "",
         "One manuscript of the same collection, one digit apart, same start folio.", "",
         "| Work | Catalogue | Pinakes |", "|---|---|---|"]
    L += [f"| {r['work']} {r['title']} | {r['shelfmark']}, f. {r['folios']} | {r['pinakes']} |" for r in fixes]
    L += ["", f"## To check by hand ({len(review)})", "",
          "Not listed by Pinakes or MediManus for this work. Papyri and Latin manuscripts are often simply outside Pinakes; "
          "Pinakes' list for a work can also be incomplete.", "",
          "| Work | Catalogue | Pinakes manuscripts with the same start folio |", "|---|---|---|"]
    L += [f"| {r['work']} {r['title']} | {r['city']}: {r['shelfmark']}, f. {r['folios']} | "
          f"{r.get('note') or '; '.join(r['candidates'])} |"
          for r in review]
    L += ["", f"## Links that open a different manuscript ({len(link_bad)} of {n_links} checkable links)", "",
          "The link's manuscript is known from the URL itself (Vatican, British Library, Heidelberg) or because Pinakes "
          "links the same digitization to a shelfmark (Gallica, ONB, e-codices, BSB, Teca). Shelfmarks corrected above "
          "are shown as read from the catalogue.", "",
          "| Work | Catalogue | Link opens | Evidence |", "|---|---|---|---|"]
    L += [f"| {r['work']} {r['title']} | {r['shelfmark']}, f. {r['folios']} | [{r['link_names'].replace('|', ' ').replace('  ', ' ')}]({r['url'].strip()}) | {r['evidence']} |"
          for r in link_bad]
    (ROOT / "PINAKES-CHECK.md").write_text("\n".join(L).replace("–", "–") + "\n")
    print(f"checked {n_all}, confirmed {n_ok}, auto-fixed {len(fixes)}, to review {len(review)}; "
          f"links checked {n_links}, opening another manuscript {len(link_bad)}")
    for r in fixes:
        print("  fix", r["work"], r["shelfmark"], "->", r["set"]["shelfmark"])


if __name__ == "__main__":
    main()
