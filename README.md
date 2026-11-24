# Medici Graeci: works, manuscripts, editions

Compiled and built by Sean Coughlin.

A small static catalogue of Greek (and some Latin) medical authors. For each work it lists the digitized
manuscripts that transmit it, with the folio where the text begins and a link to that page. It also
lists early printed editions, authoritative modern editions and translations.

- `data/catalogue.json` holds all the data: authors → works → witnesses, prints, editions, translations, reference numbers.
- `data/relocations.csv` maps dead digitization links (old URL + start folio) to the library's current viewer, with method, verification and evidence notes. `build.py` renders the new link; the catalogue keeps the original URL.
- `scripts/extract.py` regenerates the JSON from the 2019–2020 catalogue tables (Word/Excel).
- `scripts/build.py` writes the site to `docs/` (standard library only). GitHub Pages serves `docs/`.
- `site/` holds the CSS, search script and About page.

```
python -m venv .venv && .venv/bin/pip install python-docx openpyxl
.venv/bin/python scripts/extract.py "/mnt/d/onedrive/13 CMG"   # only when the source tables change
python3 scripts/build.py
```

`scripts/medimanus.py` imports MediManus (CHS) witnesses and start folios into `data/medimanus.json` (used with CHS permission). Titles are mapped to catalogue works through the reviewed concordance `data/medimanus_titles.json`.
`scripts/galenus_verbatim.py` imports the Galenus Verbatim edition index into `data/galenus_verbatim.json` (Galen works → online Greek text by TLG number).

- `scripts/pinakes.py` fetches the Pinakes (IRHT) work and author pages slowly (one request every 12 s, cached, stops at the bot guard) and writes `data/pinakes.json`: dated witnesses and author dates.
- `scripts/work_dates.py` writes `data/work_dates.json`: Galen (Coughlin chronology table, 2019: Ilberg, Bardong, Peterson, Hankinson) and Hippocrates (Craik).
- `scripts/cmg_viewer.py` lists the volumes in the CMG viewer; links to old BBAW scan pages open there instead.
- `data/relocations.csv` maps dead digitization links to the libraries' current viewers.

Witness lists cover digitized manuscripts only. For the full tradition, see Pinakes, Biblissima and MediManus,
which each work page links to.

## Style rules

- Latin and English are set in Libre Baskerville; Greek in GFS Porson (both self-hosted, OFL, in `site/fonts/`).
- Greek is set in GFS Porson and is never italic. Porson has no italic face, and the stylesheet stops browsers from faking one (`font-synthesis-style: none`), so Greek inside italic text stays upright.
