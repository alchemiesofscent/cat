# Medici Graeci: works, manuscripts, editions

Compiled and built by Sean Coughlin.

A small static catalogue of Greek (and some Latin) medical authors. For each work it lists the digitized
manuscripts that transmit it, with the folio where the text begins and a link to that page. It also
lists early printed editions, authoritative modern editions and translations.

- `data/catalogue.json` holds all the data: authors → works → witnesses, prints, editions, translations, reference numbers.
- `scripts/extract.py` regenerates the JSON from the 2019–2020 catalogue tables (Word/Excel).
- `scripts/build.py` writes the site to `docs/` (standard library only). GitHub Pages serves `docs/`.
- `site/` holds the CSS, search script and About page.

```
python -m venv .venv && .venv/bin/pip install python-docx openpyxl
.venv/bin/python scripts/extract.py "/mnt/d/onedrive/13 CMG"   # only when the source tables change
python3 scripts/build.py
```

`scripts/medimanus.py` imports MediManus (CHS) witnesses and start folios into `data/medimanus.json` (used with CHS permission). Titles are mapped to catalogue works through the reviewed concordance `data/medimanus_titles.json`.

Witness lists cover digitized manuscripts only. For the full tradition, see Pinakes, Biblissima and MediManus,
which each work page links to.

## Style rules

- Greek is set in GFS Porson and is never italic. Porson has no italic face, and the stylesheet stops browsers from faking one (`font-synthesis-style: none`), so Greek inside italic text stays upright.
