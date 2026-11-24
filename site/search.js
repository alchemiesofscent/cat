(async () => {
  const q = document.getElementById('q'), hits = document.getElementById('hits');
  const data = await (await fetch('search.json')).json();
  const fold = s => (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  data.forEach(d => d.k = fold([d.t, d.g, d.b, d.a].join(' ')));
  q.addEventListener('input', () => {
    const terms = fold(q.value).split(/\s+/).filter(Boolean);
    hits.innerHTML = '';
    if (!terms.length) return;
    data.filter(d => terms.every(t => d.k.includes(t))).slice(0, 40).forEach(d => {
      const li = document.createElement('li');
      li.innerHTML = `<a href="${d.u}"></a> <span class="a"></span>`;
      li.firstChild.textContent = d.t + (d.b ? ` (${d.b})` : '');
      li.lastChild.textContent = `${d.a}${d.n ? ' · ' + d.n + ' mss' : ''}`;
      hits.appendChild(li);
    });
  });
})();
