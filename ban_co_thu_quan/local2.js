const src = require('fs').readFileSync('search6.js', 'utf8');
const code = src.slice(0, src.indexOf('function anneal')).replace(/^const /gm, 'var ');
const { pool, cost, M } = new Function('require', code + '; return { pool, cost, M };')(require);
const start = process.argv.slice(2).map(p => { const i = pool.findIndex(x => x.p === p); if (i < 0) throw new Error('missing ' + p); return i; });
const singles = [];
for (let j = 0; j < M; j++) for (let i = 0; i < pool.length; i++) { if (start.includes(i)) continue; const s = start.slice(); s[j] = i; singles.push({ s, c: cost(s) }); }
singles.sort((a, b) => a.c.total - b.c.total);
const res = singles.filter(x => x.c.viol === 0).slice(0, 5);
for (const first of singles.slice(0, 400)) {
  for (let k = 0; k < M; k++) for (let i = 0; i < pool.length; i++) {
    if (first.s.includes(i)) continue; if (first.s[k] !== start[k]) continue;
    const s = first.s.slice(); s[k] = i; const c = cost(s); if (c.viol === 0) res.push({ s, c });
  }
}
res.sort((a, b) => a.c.total - b.c.total);
const seen = new Set();
for (const r of res) {
  const key = r.s.slice().sort().join(','); if (seen.has(key)) continue; seen.add(key); if (seen.size > 6) break;
  console.log('cost', r.c.total.toFixed(3), 'err', r.c.err.toFixed(4), 'design', r.c.design, '| +', r.s.filter(i => !start.includes(i)).map(i => pool[i].p + '(' + pool[i].avg.toFixed(2) + ')').join(' '), '| -', start.filter(i => !r.s.includes(i)).map(i => pool[i].p).join(' '));
}
