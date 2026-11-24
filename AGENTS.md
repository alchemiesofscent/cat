# Note for the next agent

Read this first, then `ROADMAP.md` (what is next), `README.md` (what each script does) and `CHANGELOG.md`
(what is published). Last updated 24 Nov 2026.

## What this is

**Ancient Greek Medical Authors** (https://alchemiesofscent.github.io/cat/): a static catalogue of Greek (and some
Latin) medical works, compiled and built by Sean Coughlin. For each work: the manuscripts that transmit it, **the
folio where the text begins, linked straight to that page of the digitization**, the sigla of the critical editions,
dates, early prints, modern editions, translations. Public repo `alchemiesofscent/cat`, GitHub Pages from
`main:/docs`. Sean is the scholar and decides; we build.

## How it works

- Source: Sean's 2019–2020 CMG work tables in `/mnt/d/onedrive/13 CMG` (Word/Excel). **Never edit them.**
  `scripts/extract.py` reads them into `data/catalogue.json` (needs python-docx/openpyxl); corrections to the
  source go in `data/corrections.json` (logged in CORRECTIONS.md).
- Everything else is pulled from other sources into `data/*.json` by its own script (MediManus, Pinakes, Galenus
  Verbatim, CMG viewer, Graeco-Arabic corpus, Wikipedia dates, sigla transcriptions) and combined by
  `scripts/build.py` (standard library only) into `docs/`.
- Rebuild after any data change: `python3 scripts/pinakes_check.py && python3 scripts/sigla_check.py && python3 scripts/build.py`
  (the two checks feed the build). Weekly GitHub Action refreshes MediManus and the Graeco-Arabic list.
- Caches (Pinakes pages, sigla page images, IIIF manifests) are in `cache/` (gitignored) in `~/github/cat`.
  Pinakes is fetched slowly (12 s per page) and has a bot guard: never bulk-fetch it fast.

## Rules Sean has set

- **Show only manuscripts linked at the start folio** (v0.1). Manuscript-level links, the MediManus comparison,
  Pinakes' other digitizations and the editions' other manuscripts are hidden (`SHOW_UNLINKED = False` in build.py)
  until their folio links exist. Folio links must be exact: no estimating image numbers (tried; drifts badly).
- Focus on **manuscripts with a siglum in a critical edition**; then the author with the most missing links first.
- Shelfmarks: city in its own column, shelfmark without the city abbreviation (Florence | Plut. 75.12); no † marks
  in tables (corrections are listed in CORRECTIONS.md / PINAKES-CHECK.md instead).
- Greek never italic (GFS Porson); Latin/English in Libre Baskerville.
- Links to other sites open in a new tab.
- Releases: **v0.1 = everything of 24 Nov 2026**. Keep the current release in step with the site: after pushing,
  re-create the release at the new commit (`gh release delete vX --cleanup-tag`, then `gh release create` with the
  notes from CHANGELOG.md). New version numbers weekly, when there is something to publish.
- Work on `main` only; one branch, one working copy (`~/github/cat`).
- Credit: "Compiled and built by Sean Coughlin". MediManus data used with the permission of CHS (Sean asked them).

## What was done (v0.1)

Catalogue + corrections; MediManus import and comparison; dead-link relocation; Pinakes dates and shelfmark/link
checks (auto-fixes for one-digit slips, review list); sigla of 77 cmg-viewer volumes transcribed by agents and
checked (`data/sigla/`, SIGLA-CHECK.md); dates and Kühn/Littré ordering; Galenus Verbatim, CMG viewer and
Graeco-Arabic links; filter/search; 93 extra folio links filled automatically from folio-labelled IIIF manifests
(Bodleian, newer Gallica scans). Details in CHANGELOG.md and the git log.

## What is next (v0.2, week of 1 Dec 2026; reminder in Sean's calendar)

See ROADMAP.md. In order:
1. **Folio-link entry page** `scripts/folio_entry.py` (local server, localhost:8765) writing into
   `data/folio_links.csv`; the 63 rows with a siglum come first. `scripts/folio_worklist.py` regenerates the worklist
   (keeps filled rows); `scripts/folio_auto.py` fills what IIIF manifests label by folio.
2. Find digitizations for the 187 manuscripts with a siglum but no known digitization.
3. Review lists: PINAKES-CHECK.md, SIGLA-CHECK.md, open shelfmark questions (one question at a time to Sean,
   with the evidence).
4. A page for each manuscript.
5. Bring the hidden tables back as their folio links are filled in.

## Open questions for Sean

Ambros. C 80 inf. vs Q 3 sup. (same folios, three Galen works); Vat. Barb. gr. 5 vs 4 (De libris propriis);
Vind. med. gr. 4 end folio; Estense α.P.5.20 end folio; Laur. Plut. 74.5 f. 55 or 56r; the Pinakes numbers given
for Diocles and Herophilus lead to other authors.
