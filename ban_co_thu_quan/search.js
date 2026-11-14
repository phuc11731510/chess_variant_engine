const F = require('./features.js');
const pool = require('./pool.json').filter(x => Math.max(...x.r) <= 1.10);
const N = 13;
const target = Array.from({length: N}, (_, i) => 1.08 - i * (1.08 - 0.22) / (N - 1));
const famMax = { t: 2, p: 2, g: 2, cj: 2, chiral: 2, sv: 2, fb: 2, leap: 4 };
function cost(sel) {
  const pieces = sel.map(i => pool[i]);
  const cnt = Object.fromEntries(F.ORDER.map(k => [k, 0]));
  for (const x of pieces) for (const k of x.feat) cnt[k]++;
  let viol = 0;
  for (const k of F.ORDER) { const opts = F.RULE[k]; viol += Math.min(...opts.map(o => Math.abs(o - cnt[k]))); }
  const fam = {}; const coreSeen = new Set();
  for (const x of pieces) {
    fam[x.fam] = (fam[x.fam] || 0) + 1;
    if (x.core) { if (coreSeen.has(x.core)) viol += 2; coreSeen.add(x.core); }
  }
  for (const k in fam) if (fam[k] > famMax[k]) viol += fam[k] - famMax[k];
  const v = pieces.map(x => x.avg).sort((a, b) => b - a);
  let err = 0; for (let i = 0; i < N; i++) err += (v[i] - target[i]) ** 2;
  // nhẹ: ưu tiên chuỗi ngắn (gọn)
  const len = pieces.reduce((s, x) => s + x.p.length, 0);
  return { total: viol * 10 + err * 200 + len * 0.01, viol, err };
}
function anneal(seed) {
  let s = seed; const rnd = () => (s = (s * 1103515245 + 12345) % 2147483648) / 2147483648;
  let sel = []; while (sel.length < N) { const i = Math.floor(rnd() * pool.length); if (!sel.includes(i)) sel.push(i); }
  let c = cost(sel); let best = { sel: sel.slice(), c };
  const iters = 400000;
  for (let it = 0; it < iters; it++) {
    const temp = 3 * (1 - it / iters) + 0.01;
    const j = Math.floor(rnd() * N); let i;
    do { i = Math.floor(rnd() * pool.length); } while (sel.includes(i));
    const old = sel[j]; sel[j] = i;
    const c2 = cost(sel);
    if (c2.total < c.total || rnd() < Math.exp((c.total - c2.total) / temp)) { c = c2; if (c.total < best.c.total) best = { sel: sel.slice(), c }; }
    else sel[j] = old;
  }
  return best;
}
const results = [];
for (let seed = 1; seed <= Number(process.env.R || 8); seed++) results.push(anneal(seed * 7919));
results.sort((a, b) => a.c.total - b.c.total);
for (const r of results.slice(0, 4)) {
  console.log('cost', r.c.total.toFixed(3), 'viol', r.c.viol, 'err', r.c.err.toFixed(4));
  for (const i of r.sel.sort((a, b) => pool[b].avg - pool[a].avg)) { const x = pool[i]; console.log('  ', x.p.padEnd(28), x.r.map(v => v.toFixed(2)).join(' '), 'avg', x.avg.toFixed(2), x.fam, x.feat.join(',')); }
  console.log(F.tally(r.sel.map(i => pool[i].p)).cnt);
}
