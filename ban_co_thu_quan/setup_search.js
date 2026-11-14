const U = require('./setup.js');
const [wT, wS, wM, seed, iters, out] = process.argv.slice(2).map((x, i) => i < 5 ? Number(x) : x);
let s = seed; const rnd = () => (s = (s * 1103515245 + 12345) % 2147483648) / 2147483648;
const FREE = U.FREE, KSQ = ['d1', 'e1', 'f1', 'g1'].map(U.idx);
const mir = i => (i - i % 10) + (9 - i % 10);
function evaluate(a) {
  const b = U.makeBoard(a);
  const vw = U.threats(b, 'w', 40).n, vb = U.threats(b, 'b', 40).n;
  const types = new Set([...a.values()].filter(t => t !== 'K'));
  const cnt = {}; for (const t of a.values()) cnt[t] = (cnt[t] || 0) + 1;
  let over = 0; for (const t in cnt) if (t !== 'K' && cnt[t] > 3) over += cnt[t] - 3;
  let asym = 0; for (const sq of FREE) { const t = a.get(sq), u = a.get(mir(sq)); if (t !== 'K' && u !== 'K' && t !== u) asym++; }
  const mob = U.allMoves(b, 'w').length;
  const cost = 100 * (vw + vb) + 20 * over + wT * (12 - types.size) + wS * asym / 2 - wM * mob / 10;
  return { cost, vw, vb, types: types.size, asym: asym / 2, mob };
}
// khởi tạo ngẫu nhiên
const T = U.TYPES;
let a = new Map(); const ks = KSQ[Math.floor(rnd() * KSQ.length)];
for (const sq of FREE) a.set(sq, sq === ks ? 'K' : T[Math.floor(rnd() * T.length)]);
let cur = evaluate(a), best = { a: new Map(a), e: cur };
for (let it = 0; it < iters; it++) {
  const temp = 8 * (1 - it / iters) + 0.05;
  const na = new Map(a); const r = rnd();
  if (r < 0.45) { const sq = FREE[Math.floor(rnd() * FREE.length)]; if (na.get(sq) === 'K') continue; na.set(sq, T[Math.floor(rnd() * T.length)]); }
  else { const x = FREE[Math.floor(rnd() * FREE.length)], y = FREE[Math.floor(rnd() * FREE.length)]; if (x === y) continue;
    const tx = na.get(x), ty = na.get(y); if ((tx === 'K' && !KSQ.includes(y)) || (ty === 'K' && !KSQ.includes(x))) continue; na.set(x, ty); na.set(y, tx); }
  const e = evaluate(na);
  if (e.cost < cur.cost || rnd() < Math.exp((cur.cost - e.cost) / temp)) { a = na; cur = e; if (e.cost < best.e.cost) best = { a: new Map(na), e }; }
}
const b = U.makeBoard(best.a);
require('fs').writeFileSync(out, JSON.stringify({ code: U.code(b), e: best.e, params: { wT, wS, wM, seed } }));
console.log(out, U.code(b), JSON.stringify(best.e));
