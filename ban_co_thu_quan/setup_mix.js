const U = require('./setup.js');
function parse(code) { const a = new Map(); code.split('/').forEach((r, k) => { const y = 9 - k; let x = 0; for (const m of r.match(/\d+|[A-Za-z]/g)) { if (/\d/.test(m)) { x += +m; continue; } const i = y * 10 + x; if (m === m.toUpperCase() && U.FREE.includes(i)) a.set(i, m); x++; } }); return a; }
// 9 cặp ô tự do theo hàng: (a,j) hàng 3; (a,j),(c,h),(e,f) hàng 2; (a,j),(b,i),(c,h),(d,g),(e,f) hàng 1
const PAIRS = [['a3', 'j3'], ['a2', 'j2'], ['c2', 'h2'], ['e2', 'f2'], ['a1', 'j1'], ['b1', 'i1'], ['c1', 'h1'], ['d1', 'g1'], ['e1', 'f1']].map(p => p.map(U.idx));
for (const f of process.argv.slice(2)) {
  const a = parse(require('./' + f).code);
  const all = new Map([...Object.entries(U.FIXED).map(([i, t]) => [Number(i), t]), ...a]);
  let bad = 0, worst = null;
  for (let mask = 0; mask < 512; mask++) {
    const b = new Array(100).fill(null);
    for (const [i, t] of all) b[i] = { c: 'w', t, moved: false };
    for (const [i, t] of all) {
      const x = i % 10, y = Math.floor(i / 10);
      const k = PAIRS.findIndex(p => p.includes(i));
      const central = k >= 0 && (mask >> k) & 1;
      b[(9 - y) * 10 + (central ? 9 - x : x)] = { c: 'b', t, moved: false };
    }
    const w = U.threats(b, 'w', 1), bl = U.threats(b, 'b', 1);
    if (w.n || bl.n) { bad++; if (!worst) worst = mask; }
  }
  console.log(f, 'số phương án trộn không an toàn:', bad, '/ 512', worst !== null ? 'ví dụ mask ' + worst : '');
}
