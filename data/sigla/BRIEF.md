# Brief for transcribing sigla pages

You are transcribing the sigla lists (conspectus siglorum) of printed critical editions of Greek and Latin medical
texts, for a catalogue of manuscripts (repo /home/seanm/github/cat-gv). Accuracy matters more than speed: these sigla
are shown publicly next to manuscripts.

1. Read /home/seanm/github/cat-gv/data/sigla/README.md (file format, rules, house form for shelfmarks) and the worked
   example /home/seanm/github/cat-gv/data/sigla/cmg_08_01.json. Follow them exactly.
2. For each of your volumes, /home/seanm/github/cat-gv/data/sigla_pages.json gives the title, series, the sigla
   sections (TOC label) and their pages: canvas number `n`, an `image` URL (IIIF, 1600 px wide). The IIIF service base
   is the image URL without `/full/1600,/0/default.jpg`. Local copies: /home/seanm/github/cat-gv/cache/sigla/<volume>/p<n>.jpg;
   if one is missing, download it with curl from the `image` URL into that path.
3. Read each page image. Then read every siglum from a zoomed crop: fetch a IIIF region with curl, e.g.
   `curl -s "<service base>/<x>,<y>,<w>,<h>/600,/0/default.jpg" -o /tmp/claude-1000/-home-seanm-github/d2e94c97-f250-45bc-ae75-8fcfe3a2a4bb/scratchpad/sig_<volume>_<k>.jpg`
   (coordinates in full-image pixels; the full image is about 1654 px wide, so multiply coordinates read in the
   1600-px copy by about 1.03) and read that file. Small superscripts (a/o/c/e, 1/2) and Greek letters are easy to
   misread at page size. Zoom on shelfmark numbers too when they are small or blurred.
4. If a list clearly continues past the last page you were given, look at the next page: same service base with the
   image number at the end of the service id increased by one (e.g. CMG_08_01_0017 → CMG_08_01_0018). Include its
   entries and set continues_on_next_page accordingly. If a section has no sigla list at all (a bibliography, or
   critical signs only), write it with an empty `entries` list and say so in `uncertain`.
5. Take editor surname(s) and year from the volume title in sigla_pages.json (not from `editors`, which can be
   misspelled). For `works`, name the work(s) each list is for, as the volume names them.
6. Write one file per volume, /home/seanm/github/cat-gv/data/sigla/<volume>.json, as soon as that volume is done, and
   check it parses: `python3 -c 'import json,sys;json.load(open(sys.argv[1]))' <file>`. If the file already exists,
   skip that volume. Do not edit any other file in the repo and do not run git.

Never guess a shelfmark number: if you cannot read it, put your best reading in `printed`, leave `normalized` empty
and say so in `uncertain`. Put "transcribed_by": "Claude agent, zoomed crops" in each file.

When finished, reply with a short report: per volume, the number of entries and anything in `uncertain`. Nothing else.
