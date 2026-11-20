// Đọc thế đầu (JSON: {ô: betza hoặc 'K'}) từ stdin; kiểm tra bằng nước đi thật cho cả hai bên (Đen đối xứng trục).
// Tùy chọn: biến môi trường CENTRAL = danh sách ô trắng (cách nhau dấu phẩy) mà quân Đen tương ứng đặt theo đối xứng tâm.
const S = require('./betza_sim.js'); const U = require('./setup.js');
const inp = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const central = new Set((process.env.CENTRAL || '').split(',').filter(Boolean).map(U.idx));
const comps = { P: S.parse('mfWcfFimfnD'), T: S.parse('fKifmnDifmnA'), K: S.parse('WFmnDmnAmnN') };
const b = new Array(100).fill(null);
const put = (i, t) => {
  b[i] = { c: 'w', t, moved: false };
  const x = i % 10, y = Math.floor(i / 10);
  b[(9 - y) * 10 + (central.has(i) ? 9 - x : x)] = { c: 'b', t, moved: false };
};
for (const [i, t] of Object.entries(U.FIXED)) put(+i, t);
for (const [sq, p] of Object.entries(inp)) { if (!comps[p]) comps[p] = S.parse(p); put(U.idx(sq), p); }
const gen = (bb, c) => {
  const a = new Int8Array(100); for (let i = 0; i < 100; i++) if (bb[i]) a[i] = bb[i].c === c ? 1 : 2;
  const out = [];
  for (let i = 0; i < 100; i++) {
    const p = bb[i]; if (!p || p.c !== c) continue;
    for (const m of S.genMoves(a, comps[p.t], i % 10, Math.floor(i / 10), c === 'w' ? 1 : -1, p.moved)) out.push({ from: i, to: m.to, caps: m.caps });
  }
  return out;
};
const bad = [];
// quy về ô trắng tương ứng (Đen: lật trục, hoặc qua tâm nếu ô đó dùng đối xứng tâm)
const whiteSq = (i, c) => { if (c === 'w') return i; const x = i % 10, y = Math.floor(i / 10); const w1 = (9 - y) * 10 + x, w2 = (9 - y) * 10 + (9 - x); return central.has(w2) ? w2 : w1; };
const pairs = new Set();
for (const c of ['w', 'b']) for (const m1 of gen(b, c)) {
  if (m1.caps.length) { bad.push([c, U.nm(m1.from) + '-' + U.nm(m1.to)]); pairs.add(U.nm(whiteSq(m1.from, c))); continue; }
  const b1 = U.apply(b, m1);
  for (const m2 of gen(b1, c)) if (m2.caps.length) {
    bad.push([c, U.nm(m1.from) + '-' + U.nm(m1.to), U.nm(m2.from) + '-' + U.nm(m2.to)]);
    const s1 = whiteSq(m1.from, c), s2 = whiteSq(m1.to === m2.from ? m1.from : m2.from, c);
    pairs.add(s1 === s2 ? U.nm(s1) : [U.nm(s1), U.nm(s2)].sort().join('+'));
  }
}
const first = { w: gen(b, 'w').length, b: gen(b, 'b').length };
console.log(JSON.stringify({ ok: bad.length === 0, bad: bad.slice(0, 6), nbad: bad.length, pairs: [...pairs], first, code: U.code(b) }));
