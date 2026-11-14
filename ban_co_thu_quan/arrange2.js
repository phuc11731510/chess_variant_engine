// Xếp lại thế đầu cho một bộ quân cố định: không ăn được quân trong 2 nước liên tiếp, không chiếu được trong 2 nước,
// quân hoàng gia ở hàng 1 (ưu tiên cột giữa), ưu tiên đối xứng trái/phải. Đen đối xứng trục.
const S = require('./betza_sim.js'); const U = require('./setup.js');
const design = require('./design2.json');
const safe = require('./safe_all.json');
const [seed, iters, out] = [Number(process.argv[2] || 1), Number(process.argv[3] || 400), process.argv[4] || 'arr.json'];
let rs = seed; const rnd = () => (rs = (rs * 1103515245 + 12345) % 2147483648) / 2147483648;
const comps = { P: S.parse('mfWcfFimfnD'), T: S.parse('fKifmnDifmnA'), K: S.parse('WFmnDmnAmnN') };
for (const p of Object.keys(design.count)) comps[p] = S.parse(p);
const FREE = U.FREE;
const pieces = []; for (const [p, n] of Object.entries(design.count)) for (let k = 0; k < n; k++) pieces.push(p);
pieces.push('K');
const KSQ = (process.env.KSQ || 'a1,b1,c1,d1,e1,f1,g1,h1,i1,j1').split(',').map(U.idx);
const okSq = (p, i) => p === 'K' ? KSQ.includes(i) : safe[p].includes(U.nm(i));
function makeBoard(arr) {
  const b = new Array(100).fill(null);
  const put = (i, t) => { b[i] = { c: 'w', t, moved: false }; const x = i % 10, y = Math.floor(i / 10); b[(9 - y) * 10 + x] = { c: 'b', t, moved: false }; };
  for (const [i, t] of Object.entries(U.FIXED)) put(+i, t);
  FREE.forEach((sq, k) => put(sq, arr[k]));
  return b;
}
const gen = (bb, c) => { const a = new Int8Array(100); for (let i = 0; i < 100; i++) if (bb[i]) a[i] = bb[i].c === c ? 1 : 2; const o = [];
  for (let i = 0; i < 100; i++) { const p = bb[i]; if (!p || p.c !== c) continue; for (const m of S.genMoves(a, comps[p.t], i % 10, Math.floor(i / 10), c === 'w' ? 1 : -1, p.moved)) o.push({ from: i, to: m.to, caps: m.caps }); } return o; };
function nCaps(b) { let n = 0; for (const c of ['w', 'b']) for (const m1 of gen(b, c)) { if (m1.caps.length) { n++; continue; } const b1 = U.apply(b, m1); if (gen(b1, c).some(m => m.caps.length)) n++; } return n; }
function nChecks(b) {
  let n = 0;
  for (const c of ['w', 'b']) {
    const o = c === 'w' ? 'b' : 'w';
    const att = bb => { const k = bb.findIndex(p => p && p.c === o && p.t === 'K'); return gen(bb, c).some(m => m.caps.includes(k)); };
    for (const m1 of gen(b, c)) { const b1 = U.apply(b, m1); if (att(b1)) { n++; continue; } if (gen(b1, c).some(m2 => att(U.apply(b1, m2)))) n++; }
  }
  return n;
}
const mir = k => FREE.indexOf((FREE[k] - FREE[k] % 10) + (9 - FREE[k] % 10));
function cost(arr) {
  let badSq = 0; for (let k = 0; k < FREE.length; k++) if (!okSq(arr[k], FREE[k])) badSq++;
  if (badSq) return { c: 5000 * badSq, badSq };
  const b = makeBoard(arr);
  const caps = nCaps(b);
  let asym = 0; for (let k = 0; k < FREE.length; k++) { const m = mir(k); if (arr[k] !== 'K' && arr[m] !== 'K' && arr[k] !== arr[m]) asym++; }
  const kcen = 0;
  if (caps) return { c: 1000 * caps + asym / 2 + kcen, caps };
  const chk = nChecks(b);
  return { c: 100 * chk + asym / 2 + 2 * kcen, caps, chk, asym: asym / 2, kcen };
}
// khởi đầu từ thế của bộ giải
const start = process.env.START ? require('./' + process.env.START).setup : design.setup;
let arr = FREE.map(sq => start[U.nm(sq)]);
{ // đưa vua về ô cho phép: đổi chỗ với quân đang đứng ở đó (ưu tiên quân an toàn ở ô cũ của vua)
  const kk = arr.indexOf('K');
  if (!KSQ.includes(FREE[kk])) {
    const cands = KSQ.map(sq => FREE.indexOf(sq)).sort((a, b) => (okSq(arr[b], FREE[kk]) ? 1 : 0) - (okSq(arr[a], FREE[kk]) ? 1 : 0));
    const j = cands[Math.floor(rnd() * cands.length)];
    [arr[kk], arr[j]] = [arr[j], arr[kk]];
  }
}
let cur = cost(arr), best = { arr: arr.slice(), e: cur };
for (let it = 0; it < iters; it++) {
  const temp = 30 * (1 - it / iters) + 0.3;
  const na = arr.slice(); const x = Math.floor(rnd() * FREE.length), y = Math.floor(rnd() * FREE.length);
  if (x === y || na[x] === na[y]) continue;
  [na[x], na[y]] = [na[y], na[x]];
  const e = cost(na);
  if (e.c < cur.c || rnd() < Math.exp((cur.c - e.c) / temp)) { arr = na; cur = e; if (e.c < best.e.c) { best = { arr: na.slice(), e }; } }
}
const res = { setup: Object.fromEntries(FREE.map((sq, k) => [U.nm(sq), best.arr[k]])), e: best.e };
require('fs').writeFileSync(out, JSON.stringify(res));
console.log(out, JSON.stringify(best.e), JSON.stringify(res.setup));
