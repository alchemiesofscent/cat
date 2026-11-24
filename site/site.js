// Header filter on every page, global search on the index, sortable tables, order switches.
(() => {
  const root = document.currentScript.dataset.root || "";
  const fold = s => (s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  const box = document.getElementById("filter");
  const hits = document.getElementById("hits");

  // ---- filter this page
  const items = () => [
    ...document.querySelectorAll("section.work, #mslist details, table.authors tbody tr, ol.toc li"),
  ];
  const cache = new Map();
  const text = el => cache.get(el) ?? (cache.set(el, fold(el.textContent)), cache.get(el));
  function filterPage(q) {
    const terms = fold(q).split(/\s+/).filter(Boolean);
    for (const el of items()) {
      const show = terms.every(t => text(el).includes(t));
      el.hidden = !show;
      if (show && terms.length && el.tagName === "DETAILS") el.open = true;
    }
    for (const sec of document.querySelectorAll("section.city"))
      sec.hidden = terms.length > 0 && !sec.querySelector("details:not([hidden])");
  }

  // ---- global search (index page)
  let data = null;
  async function globalSearch(q) {
    if (!hits) return;
    const terms = fold(q).split(/\s+/).filter(Boolean);
    hits.innerHTML = "";
    if (!terms.length) return;
    data = data || (await (await fetch(root + "search.json")).json()).map(d => ({ ...d, k: fold([d.t, d.g, d.b, d.a].join(" ")) }));
    data.filter(d => terms.every(t => d.k.includes(t))).slice(0, 40).forEach(d => {
      const li = document.createElement("li");
      li.innerHTML = '<a></a> <span class="a"></span>';
      li.firstChild.href = root + d.u;
      li.firstChild.textContent = d.t + (d.b ? ` (${d.b})` : "");
      li.lastChild.textContent = `${d.a}${d.n ? " · " + d.n + " mss" : ""}`;
      hits.appendChild(li);
    });
  }

  if (box) {
    const q0 = new URLSearchParams(location.search).get("q");
    if (q0 && hits) box.value = q0;
    const run = () => { filterPage(box.value); globalSearch(box.value); };
    box.addEventListener("input", run);
    box.form.addEventListener("submit", e => { if (hits) { e.preventDefault(); run(); } });
    if (box.value) run();
  }

  // ---- sortable tables: click a header
  for (const table of document.querySelectorAll("table.sortable")) {
    table.querySelectorAll("th").forEach((th, i) => {
      th.addEventListener("click", () => {
        const tb = table.tBodies[0];
        const dir = th.dataset.dir === "asc" ? -1 : 1;
        table.querySelectorAll("th").forEach(h => delete h.dataset.dir);
        th.dataset.dir = dir === 1 ? "asc" : "desc";
        const val = tr => { const c = tr.children[i]; return c ? (c.dataset.v ?? c.textContent.trim()) : ""; };
        [...tb.rows].sort((a, b) => dir * val(a).localeCompare(val(b), undefined, { numeric: true }))
          .forEach(r => tb.appendChild(r));
      });
    });
  }

  // ---- order switches
  for (const sw of document.querySelectorAll(".sortsw")) {
    const target = document.getElementById(sw.dataset.target);
    if (!target) continue;
    const toc = document.querySelector("ol.toc");
    const kids = [...target.children];
    kids.forEach((k, i) => (k.dataset.i = i));
    const num = (el, key, dflt) => (el.dataset[key] !== undefined && el.dataset[key] !== "" ? +el.dataset[key] : dflt);
    sw.addEventListener("click", e => {
      const b = e.target.closest("button");
      if (!b) return;
      sw.querySelectorAll("button").forEach(x => x.classList.toggle("on", x === b));
      const mode = b.dataset.mode;
      if (sw.dataset.target === "works") {
        const key = {
          cat: el => [num(el, "i", 0)],
          chron: el => [num(el, "year", 1e6), num(el, "order", 1e6), num(el, "i", 0)],
          ed: el => [num(el, "ed", 1e9), num(el, "i", 0)],
        }[mode];
        const cmp = (a, b) => { const x = key(a), y = key(b); for (let i = 0; i < x.length; i++) if (x[i] !== y[i]) return x[i] - y[i]; return 0; };
        const sorted = [...target.children].sort(cmp);
        sorted.forEach(el => target.appendChild(el));
        if (toc) {
          sorted.forEach(el => { const li = toc.querySelector(`li[data-for="${el.id}"]`); if (li) toc.appendChild(li); });
          toc.classList.toggle("mode-ed", mode === "ed");
          toc.classList.toggle("mode-chron", mode === "chron");
        }
      } else {
        // manuscripts page: by city (original grouping) or one list by date
        if (mode === "date") {
          const all = [...target.querySelectorAll("details")];
          all.forEach(d => (d.dataset.home = d.dataset.home || [...document.querySelectorAll("section.city")].indexOf(d.closest("section.city"))));
          let flat = document.getElementById("flat");
          if (!flat) { flat = document.createElement("div"); flat.id = "flat"; target.prepend(flat); }
          all.sort((a, b) => (+a.dataset.c - +b.dataset.c) || a.textContent.localeCompare(b.textContent, undefined, { numeric: true }))
            .forEach(d => {
              if (!d.querySelector(".cityname")) {
                const s = document.createElement("span");
                s.className = "cityname n";
                s.textContent = d.closest("section.city")?.querySelector("h2")?.textContent || "";
                d.querySelector("summary").prepend(s);
              }
              flat.appendChild(d);
            });
          document.querySelectorAll("section.city").forEach(s => (s.hidden = true));
          document.querySelector(".cities").hidden = true;
        } else {
          const secs = [...document.querySelectorAll("section.city")];
          [...target.querySelectorAll("details")].sort((a, b) => +a.dataset.i - +b.dataset.i);
          document.querySelectorAll("#flat details").forEach(d => secs[+d.dataset.home].appendChild(d));
          secs.forEach(s => {
            [...s.querySelectorAll("details")].sort((a, b) => +a.dataset.order - +b.dataset.order).forEach(d => s.appendChild(d));
            s.hidden = false;
          });
          document.querySelectorAll(".cityname").forEach(x => x.remove());
          document.querySelector(".cities").hidden = false;
        }
      }
    });
  }
  // remember original order of manuscripts within each city
  document.querySelectorAll("section.city").forEach(s => s.querySelectorAll("details").forEach((d, i) => (d.dataset.order = i)));
})();
