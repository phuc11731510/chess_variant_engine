// Với mỗi ứng viên X và mỗi ô trong 18 ô xếp quân: X đặt ở đó có an toàn không (Trắng và Đen).
// Ô khác: quân chắn đứng yên; Tốt (P, T) đi thật; Đen kín 3 hàng bằng quân đứng yên (ngoài Tốt).
const S = require('./betza_sim.js'); const U = require('./setup.js'); const fs = require('fs');
const [part, nparts] = process.argv.slice(2).map(Number);
const pool = require('./pool_eg.json').filter(x => Math.max(...x.r) <= 1.10);
const P = S.parse('mfWcfFimfnD'), T = S.parse('fKifmnDifmnA');
function test(comps, sq, side) {
  // side 'w': X trắng ở sq; 'b': X đen ở ảnh trục của sq, bên Đen đi 2 nước
  const b = new Array(100).fill(null);
  const own = side, opp = side === 'w' ? 'b' : 'w';
  const place = (i, c) => { if (c === 'w') return i; const x = i % 10, y = Math.floor(i / 10); return (9 - y) * 10 + x; };
  for (const [i, t] of Object.entries(U.FIXED)) { b[place(+i, own)] = { c: own, t, moved: false }; b[place(+i, opp)] = { c: opp, t: 'X', moved: false }; }
  for (const f of U.FREE) { b[place(f, own)] = { c: own, t: 'X', moved: false }; b[place(f, opp)] = { c: opp, t: 'X', moved: false }; }
  b[place(sq, own)] = { c: own, t: 'Z', moved: false };
  const comp = t => t === 'Z' ? comps : t === 'P' ? P : t === 'T' ? T : null;
  const gen = (bb, c) => { const a = new Int8Array(100); for (let i = 0; i < 100; i++) if (bb[i]) a[i] = bb[i].c === c ? 1 : 2; const out = [];
    for (let i = 0; i < 100; i++) { const p = bb[i]; if (!p || p.c !== c) continue; const cc = comp(p.t); if (!cc) continue;
      for (const m of S.genMoves(a, cc, i % 10, Math.floor(i / 10), c === 'w' ? 1 : -1, p.moved)) out.push({ from: i, to: m.to, caps: m.caps }); } return out; };
  for (const m1 of gen(b, own)) {
    if (m1.caps.length) return false;
    const b1 = U.apply(b, m1);
    for (const m2 of gen(b1, own)) if (m2.caps.length) return false;
  }
  return true;
}
const out = {};
const seen = new Set();
pool.forEach((x, k) => {
  if (k % nparts !== part || seen.has(x.p)) return; seen.add(x.p);
  const comps = S.parse(x.p);
  out[x.p] = U.FREE.filter(sq => test(comps, sq, 'w') && test(comps, sq, 'b')).map(U.nm);
});
fs.writeFileSync(`safe_${part}.json`, JSON.stringify(out));
console.log('part', part, Object.keys(out).length);
