const F = require('./features.js');
const src = require('fs').readFileSync('search2.js','utf8');
const pool = require('./pool.json').filter(x => Math.max(...x.r) <= 1.10 && !/^WF/.test(x.add) && !(x.core==='t[FWW]' && x.add.includes('F')));
const code = src.slice(src.indexOf('const N = 13'), src.indexOf('function anneal')).replace(/^const /gm, 'var ');
const { N, cost } = new Function('F', 'pool', code + '; return { N, cost };')(F, pool);
const start = process.argv.slice(2).map(p => { const i = pool.findIndex(x => x.p === p); if (i < 0) throw new Error('missing ' + p); return i; });
let best = { sel: start, c: cost(start) }; console.log('start', best.c, F.tally(start.map(i=>pool[i].p)).bad);
const cands = [];
for (let j = 0; j < N; j++) for (let i = 0; i < pool.length; i++) { if (start.includes(i)) continue; const s = start.slice(); s[j] = i; const c = cost(s); if (c.viol === 0) cands.push({ s, c }); }
// đôi
for (let j = 0; j < N; j++) for (let k = j + 1; k < N; k++) for (let i = 0; i < pool.length; i += 1) {
  if (start.includes(i)) continue; const s1 = start.slice(); s1[j] = i; const c1 = cost(s1);
  if (c1.viol > 2) continue;
  for (let i2 = 0; i2 < pool.length; i2++) { if (s1.includes(i2)) continue; const s = s1.slice(); s[k] = i2; const c = cost(s); if (c.viol === 0) cands.push({ s, c }); }
}
cands.sort((a, b) => a.c.total - b.c.total);
for (const r of cands.slice(0, 5)) {
  console.log('cost', r.c.total.toFixed(3), 'err', r.c.err.toFixed(4), 'design', r.c.design, ' changes:', r.s.filter(i => !start.includes(i)).map(i => pool[i].p).join(' + '), ' removed:', start.filter(i => !r.s.includes(i)).map(i => pool[i].p).join(' + '));
}
