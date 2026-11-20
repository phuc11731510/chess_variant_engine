const S = require('./betza_sim.js');
const F = require('./features.js');
const fs = require('fs');
const T = 2500;
const cores = {
  t: ['t[FWW]','t[WFF]','t[WnA]','t[FnD]','t[fFfWW]t[bFbWW]'],
  p: ['mWWFFcpWWFF','pWWFF','mWWcpWW','pWW','mFFcpFF','pFF','mW4cpW4','mF4cpF4'],
  g: ['gWWFF','gWW','gFF','gW3','gF3','gW3gF3'],
  cj: ['mWW[cj]WW','mFF[cj]FF','mWW[cj1]WW','mFF[cj1]FF','mWWFF[cj1]WWFF','D[cj]W','A[cj]F','N[cj]N','mW[cj]W','mF[cj]F'],
  chiral: ['frNlfNblNrbN','lfFFrbFFrfFlbF','frZlfZblZrbZ','frClfCblCrbC','frWWblW','frWWblWW'],
  sv: ['vWWsW','sWWvW','vWWsF','sWWvF','vWWsD','sWWvD','vFFsW'],
  fb: ['fWWbFF','fFFbWW','fWWbF','fFFbW','fWWbN','fFFbN'],
  leap: [''],
};
const addons = ['','W','F','D','A','H','G','N','C','Z','nN','nD','nA','nH','nG','nC','nZ','W2','F2','F3','W3','sW','vW','sH','vH','sD','vD','WF','WD','FD','FA','WA','NH','NG','CZ','CH','ZG','HG','WH','FG','WG','FH','WZ','FC','FZ','WC','NC','NZ','NA','ND','DH','AG','nNH','nNG','nNC','nNZ'];
const Qv = [0.6,0.4,0.2].map(d => S.mobility('WWFF', d, 8000).score);
function sig(p, boards) { return boards.map(b => S.genMoves(b.board, S.parse(p), b.x, b.y).map(m => m.to+':'+m.caps).sort().join(';')).join('|'); }
const rand = S.rng(99);
const boards = [];
for (let i = 0; i < 60; i++) { const s = Math.floor(rand()*100); boards.push({board: S.randomBoard(rand, [0.1,0.3,0.5][i%3], s), x: s%10, y: Math.floor(s/10)}); }
const pool = [];
let n = 0;
for (const [fam, list] of Object.entries(cores)) for (const core of list) for (const add of addons) {
  if (fam === 'leap' && add === '') continue;
  const p = add + core;
  if (!core && add.length < 2) continue;
  // bỏ phần ghép thừa
  if (core && add) { const sp = sig(p, boards); if (sig(core, boards) === sp || sig(add, boards) === sp) continue; }
  let reach; try { reach = S.reachability(p); } catch (e) { continue; }
  if (reach < 100) continue;
  const r = [0.6,0.4,0.2].map((d,i) => S.mobility(p, d, T, 3).score / Qv[i]);
  if (Math.max(...r) > 1.12) continue;
  const avg = (r[0]+r[1]+r[2])/3;
  if (avg < 0.15) continue;
  pool.push({ p, fam, core, add, r, avg, feat: [...F.features(p)] });
  if (++n % 50 === 0) process.stderr.write(n + ' ');
}
fs.writeFileSync('pool.json', JSON.stringify(pool));
console.log('\npool size', pool.length);
