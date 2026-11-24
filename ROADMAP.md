# Roadmap

Releases: weekly, when there is something to publish, until the catalogue settles (v0.2, v0.3 …). Between releases the
site is updated as changes are pushed, and the current release notes are kept in step.

## v0.2 (week of 1 December 2026): folio links, review lists, a page for each manuscript

In v0.1 the site shows only manuscripts linked at the start folio. v0.2 brings back, as the folio links are filled in,
the tables now hidden (`SHOW_UNLINKED` in scripts/build.py): the MediManus comparison, the digitized manuscripts known
to Pinakes, and the editions' other manuscripts (with a ? where Pinakes and MediManus do not list them for the work).

### 1. Folio links (the core of v0.2)

**Focus: manuscripts with a siglum in a critical edition of the work.** The worklist (`data/folio_links.csv`, 1,047
rows, 242 manuscripts) puts first the 66 rows (about 40 manuscripts) whose manuscript has a siglum for that work,
with the siglum shown; within them, and then for the rest, the author with the most missing first.

**1c. Find digitizations for sigla manuscripts.** Of the 354 manuscripts with a siglum, 187 have no known
digitization. Look them up in the libraries' own catalogues (Vatican, BnF, BSB, ONB, Laurenziana, Marciana,
Ambrosiana, Escorial, Bodleian), add what is found to the worklist, and list the rest as "not digitized (checked)".

Counts for all rows, for reference:

| Author | Missing | | Author | Missing |
|---|---|---|---|---|
| Hippocrates | 723 | | Palladius | 12 |
| Galen | 120 | | Meletius | 11 |
| Aetius | 35 | | Alexander of Tralles | 9 |
| Paul of Aegina | 30 | | Archigenes, Aretaeus | 8 each |
| Dioscorides | 26 | | Rufus, Stephanus | 5 each |
| Oribasius | 20 | | 13 others | 1–4 each |

**1a. Automatic, where the viewer labels its folios.** Read each digitization's IIIF manifest; where the canvases
carry folio labels (Bodleian, e-codices, ONB, BSB, Heidelberg; to be tested for Gallica colour scans), link the start
folio directly. Rows filled this way are marked `source: auto` in the worklist and are never overwritten by hand
entries or vice versa. Test first on Gallica: if colour scans are labelled, a large part of the 508 Gallica rows goes.

**1b. Entry page for the rest** (`scripts/folio_entry.py`, run locally: `python3 scripts/folio_entry.py`, then
open http://localhost:8765).
- One manuscript at a time, because one manuscript usually carries many works (Hippocrates: Par. gr. 2140, 2141,
  2142… each with dozens): open it once, enter every work's start page in turn.
- For each row: work, shelfmark, Pinakes folios and start folio, a button that opens the manuscript in the viewer,
  a box for the page address. Enter = save and go to the next row; Skip; "Not in this manuscript" (with a note).
- Saves straight into `data/folio_links.csv` (with who and when), so nothing is lost if the page is closed.
- Progress per author and overall at the top; works in the order above.
- Checks on save: the address is on the same viewer as the manuscript link, and for Gallica and the Vatican the
  image number is plausible for the folio (warning only).
- Publishing: say "publish the folio links" and the site is rebuilt and pushed, and the v0.2 notes updated.

### 2. Review lists

- Open shelfmark questions put to Sean one at a time, with the evidence: Ambros. C 80 inf. / Q 3 sup.;
  Vat. Barb. gr. 5 / 4; Vind. med. gr. 4 (end folio); Estense α.P.5.20 (end folio); Laur. Plut. 74.5 (f. 55 / 56r);
  the Pinakes numbers for Diocles and Herophilus.
- PINAKES-CHECK.md (69 to check): sorted into "outside Pinakes, fine" (papyri, Latin manuscripts) and "needs a look";
  only the second group goes to Sean.
- SIGLA-CHECK.md: a second, independent reading of the sigla pages where the agents marked a reading uncertain;
  readings where the two agree are settled, the rest go to Sean.

### 3. A page for each manuscript

`manuscripts/<city>-<shelfmark>.html`: every work in the manuscript in folio order with start folio and link, its
sigla in every edition, date (Pinakes, MediManus), digitization, Pinakes and MediManus records. A stable address to
cite and link to; the manuscripts list and the work pages link to it.

### Later (v0.3)

Sigla from volumes without a conspectus in their table of contents (CMG I 1, Diels, Supplementa, dissertations);
works the editions cover that are not in the catalogue (Leo, Anonymus Londinensis, Definitiones medicae, CML IV,
Ps.-Galen De fasciis); the 24 unresolved dead links; downloads (CSV/JSON) and a "How to cite" note.
