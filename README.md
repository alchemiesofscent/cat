# Ancient Greek Medical Authors: works, manuscripts, editions

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
`scripts/pinakes_check.py` checks every shelfmark against Pinakes' witness list for the work: one-digit slips with the same start folio are corrected at build time (`data/pinakes_check.json`), the rest are listed in `PINAKES-CHECK.md`. `scripts/pinakes.py` also fetches each witness's Pinakes shelfmark page for its digitization link.
Sigla: `scripts/sigla_pages.py` finds the sigla pages in every cmg-viewer volume (IIIF table of contents) and downloads them; the transcriptions are in `data/sigla/<volume>.json` (format and brief in `data/sigla/README.md`, `BRIEF.md`); `scripts/sigla_check.py` ties them to works and manuscripts (`data/sigla_index.json`) and writes the review list `SIGLA-CHECK.md`.
`scripts/medimanus_queries.py` tests the MediManus search link of every work (MediManus needs every search word to match, so fewer words find more) and keeps the most specific query that finds something: `data/medimanus_queries.json`.
Folio links: `scripts/folio_auto.py` fills `data/folio_links.csv` from the library's IIIF manifest where pages are labelled by folio (newer Gallica scans, the Bodleian); the rest by hand: `scripts/folio_worklist.py` writes `data/folio_links.csv`, one row per work × manuscript whose link opens only the manuscript (mostly Gallica and Vatican, whose viewers do not label folios). Open `manuscript_url`, find the start folio, paste that page's address into `folio_url`; the next build links the row at the folio. Re-running the script adds new rows and keeps what is filled in.
`scripts/graeco_arabic.py` reads the Digital Corpus for Graeco-Arabic Studies text list into `data/graeco_arabic.json` (Arabic translations and summaries of Galen and Hippocrates → catalogue work, through the title table `MAP`).

- `scripts/pinakes.py` fetches the Pinakes (IRHT) work and author pages slowly (one request every 12 s, cached, stops at the bot guard) and writes `data/pinakes.json`: dated witnesses and author dates.
- `scripts/work_dates.py` writes `data/work_dates.json`: Galen (Coughlin chronology table, 2019: Ilberg, Bardong, Peterson, Hankinson) and Hippocrates (Craik).
- `scripts/cmg_viewer.py` lists the volumes in the CMG viewer; links to old BBAW scan pages open there instead.
- `data/relocations.csv` maps dead digitization links to the libraries' current viewers.

Witness lists cover digitized manuscripts only. For the full tradition, see Pinakes, Biblissima and MediManus,
which each work page links to.

## Style rules

- Latin and English are set in Libre Baskerville; Greek in GFS Porson (both self-hosted, OFL, in `site/fonts/`).
- Greek is set in GFS Porson and is never italic. Porson has no italic face, and the stylesheet stops browsers from faking one (`font-synthesis-style: none`), so Greek inside italic text stays upright.
