# Sigla of the critical editions

One JSON file per cmg-viewer volume (`<volume>.json`), transcribed from the volume's sigla pages
(Conspectus siglorum / codicum, Sigla, Signorum explicatio ...) listed in `data/sigla_pages.json`.
`scripts/sigla_check.py` matches the entries to the catalogue and writes `SIGLA-CHECK.md`; `scripts/build.py`
shows them. `cmg_08_01.json` (Olivieri, Aetius I–IV) is the worked example.

## File format

```json
{
 "volume": "cmg_08_01",
 "editor": "Olivieri",            // surname(s) as on the title page, "Mewaldt/Helmreich/Westenberger"
 "series": "CMG VIII 1",          // or "CMG Suppl. 2", "CML II", "" for volumes outside the series
 "year": "1935",
 "sections": [
  {
   "label": "Signorum explicatio",          // the TOC label
   "pages": [17],                           // canvas numbers actually used
   "works": ["Aetius, Libri medicinales I–IV"],  // the work(s) this list is for, as the volume names them
   "continues_on_next_page": false,         // true if the list runs on past the last page you were given
   "entries": [
    {"siglum": {"base": "L", "sup": "b", "sub": ""},
     "type": "manuscript",                  // manuscript | papyrus | group | edition | translation | other
     "printed": "Codex Laurentianus LXXV, 12",   // verbatim, ditto marks resolved
     "normalized": "Laur. Plut. 75.12",     // house form, see below; "" unless manuscript or papyrus
     "city": "Florence",
     "folios": "",                          // as printed, if given
     "date": "",                            // as printed, if given ("s. XIV", "a. 1453")
     "note": ""}
   ]
  }
 ],
 "transcribed_by": "...",
 "uncertain": ["free text: anything you could not read with confidence, with the siglum"]
}
```

## Rules

- **Superscripts and subscripts** go in `sup` / `sub`, never as Unicode modifier letters. Greek sigla stay Greek
  (`{"base": "Θ"}`). Read every siglum from a zoomed crop (see the brief); small superscripts (a/o/c/e) are easy to confuse.
- **Ditto marks** („ ” ") repeat the words above: write them out in `printed`.
- One siglum for two manuscripts ("Z = Suppl. gr. 630. 632") → two entries with the same siglum, a note on both.
- Hands and correctors (A², A^c, "manus recentior") → `type: "other"` unless the volume lists them as separate witnesses.
- Hyparchetypes, families, consensus signs (ω, α = consensus codicum) → `group`. Printed editions (Ald., Bas., Chart.,
  K = Kühn) → `edition`. Latin/Arabic/Syriac translations → `translation`.
- If a volume has several lists (one per work), make one section per list, with that list's work(s).

## House form for `normalized`

`Par. gr. 2192` · `Par. Suppl. gr. 1240` · `Par. Coisl. 335` · `Vat. gr. 298` · `Vat. Pal. gr. 199` · `Vat. Urb. gr. 64` ·
`Vat. Barb. gr. 4` · `Vat. Ottob. gr. 311` · `Vat. Reg. gr. 173` · `Laur. Plut. 75.20` (Roman numerals → Arabic, comma → point) ·
`Laur. Conv. Soppr. 9` · `Marc. gr. 289` · `Marc. gr. Z. 269` (keep Z./App. if printed) · `Vind. med. gr. 6` · `Vind. phil. gr. 37` ·
`Ambros. C 80 inf.` · `Mon. gr. 71` · `Oxon. Barocc. 224` · `Harley 6326` · `Add. 11888` · `Leid. Voss. gr. Q 3` ·
`Scorial. Ψ IV 14` · `Matrit. 4616` · `Athos, Lavra Ω 63` · `Bonon. 3632` · `Mosq. 466` · `Neap. III D 15` ·
`Berol. Phill. 1529` · `Lips. 50` · `Taur. B VI 9`. Papyri: `P.Oxy. 2547`, `P.Berol. 21141`.
When unsure, keep the city word the volume uses and the full number; never guess a number.
