const S = require('./betza_sim.js'); const F = require('./features.js'); const fs = require('fs');
const pool = require('./pool.json');
const Qv = [0.6,0.4,0.2].map(d => S.mobility('WWFF', d, 8000).score);
const have = new Set(pool.map(x => x.p));
const cores = { t: ['t[FD]','t[WA]','t[FC]','t[WZ]','t[FH]','t[WG]'], cj: ['N[cj]N','nN[cj]nN','Z[cj]W','C[cj]F'] };
const adds = ['','W','F','D','A','H','G','N','C','Z','nN','nA','nD','W2','F2','sW','vW','sH','vH','sD','vD','NH','NG','ZG','HG','CH','DH','AG','NA','ND','nNA','nNC','nNZ','nNH','nNG'];
const leaps = ['nNA','nNC','nNZ','nND','nNH','nNG','nAN','NnA','NnD','CnA','ZnD','nNnA','nNnD','vvNA','ffNbbN'];
const rand = S.rng(5); const boards = [];
for (let i = 0; i < 60; i++) { const s = Math.floor(rand()*100); boards.push({board: S.randomBoard(rand, [0.1,0.3,0.5][i%3], s), x: s%10, y: Math.floor(s/10)}); }
const sig = p => boards.map(b => S.genMoves(b.board, S.parse(p), b.x, b.y).map(m => m.to+':'+m.caps).sort().join(';')).join('|');
function add(p, fam, core, a) {
  if (have.has(p)) return; have.add(p);
  if (core && a) { const sp = sig(p); if (sig(core) === sp || sig(a) === sp) return; }
  if (S.reachability(p) < 100) return;
  const r = [0.6,0.4,0.2].map((d,i) => S.mobility(p, d, 2500, 3).score / Qv[i]);
  if (Math.max(...r) > 1.12) return;
  pool.push({ p, fam, core, add: a, r, avg: (r[0]+r[1]+r[2])/3, feat: [...F.features(p)] });
}
for (const [fam, list] of Object.entries(cores)) for (const c of list) for (const a of adds) add(a + c, fam, c, a);
for (const l of leaps) add(l, 'leap', '', l);
fs.writeFileSync('pool.json', JSON.stringify(pool)); console.log(pool.length);
