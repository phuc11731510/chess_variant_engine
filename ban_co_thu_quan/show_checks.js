const S = require('./betza_sim.js'); const U = require('./setup.js');
const f = process.argv[2]; const setup = require('./' + f).setup;
const comps = { P: S.parse('mfWcfFimfnD'), T: S.parse('fKifmnDifmnA'), K: S.parse('WFmnDmnAmnN') };
const b = new Array(100).fill(null);
const put = (i, t) => { if (!comps[t]) comps[t] = S.parse(t); b[i] = { c: 'w', t, moved: false }; const x = i % 10, y = Math.floor(i / 10); b[(9 - y) * 10 + x] = { c: 'b', t, moved: false }; };
for (const [i, t] of Object.entries(U.FIXED)) put(+i, t);
for (const [sq, p] of Object.entries(setup)) put(U.idx(sq), p);
const gen = (bb, c) => { const a = new Int8Array(100); for (let i = 0; i < 100; i++) if (bb[i]) a[i] = bb[i].c === c ? 1 : 2; const o = [];
  for (let i = 0; i < 100; i++) { const p = bb[i]; if (!p || p.c !== c) continue; for (const m of S.genMoves(a, comps[p.t], i % 10, Math.floor(i / 10), c === 'w' ? 1 : -1, p.moved)) o.push({ from: i, to: m.to, caps: m.caps }); } return o; };
for (const c of ['w', 'b']) {
  const o = c === 'w' ? 'b' : 'w';
  const attacker = bb => { const k = bb.findIndex(p => p && p.c === o && p.t === 'K'); const m = gen(bb, c).find(m => m.caps.includes(k)); return m ? bb[m.from].t + '@' + U.nm(m.from) : null; };
  for (const m1 of gen(b, c)) {
    const b1 = U.apply(b, m1); const a1 = attacker(b1);
    if (a1) { console.log(c, b[m1.from].t + ' ' + U.nm(m1.from) + '-' + U.nm(m1.to), '=> chiếu bởi', a1); continue; }
    for (const m2 of gen(b1, c)) { const b2 = U.apply(b1, m2); const a2 = attacker(b2); if (a2) console.log(c, b[m1.from].t + ' ' + U.nm(m1.from) + '-' + U.nm(m1.to), ';', b1[m2.from].t + ' ' + U.nm(m2.from) + '-' + U.nm(m2.to), '=> chiếu bởi', a2); }
  }
}
