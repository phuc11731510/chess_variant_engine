// Đếm và lấy mẫu đều các thế khởi đầu.
// Điều kiện cần (đếm chính xác bằng quy hoạch động): mỗi quân đứng ở ô an toàn của riêng nó, vua ở hàng 1,
// đủ 12 loại, mỗi loại 1 hoặc 2 quân. Sau đó lấy mẫu đều và kiểm tra đầy đủ:
//   (1) một bên đi 2 nước liên tiếp không ăn được quân (cả hai bên);
//   (2) bên đi trước không ép được chiếu tới nửa nước 3 khi bên kia đáp lại (cả hai chiều).
const S = require('./betza_sim.js'); const U = require('./setup.js');
const safe = require('./safe_all.json');
const TYPES = ['F2t[WFF]', 'vWFFmWWcpWW', 'CHmFF[cj1]FF', 'NmF4cpF4', 'FZgF3', 'DHfrClfCblCrbC', 'WGgW3', 'sDt[WnA]', 'ZnD', 'nGsWWvW', 'nNfrNlfNblNrbN', 'nN[cj]nN'];
const FREE = U.FREE; const NSQ = FREE.length; const NT = TYPES.length;
const allowed = FREE.map(sq => { const s = U.nm(sq); return TYPES.map(t => safe[t].includes(s)); });
const kAllowed = FREE.map(sq => Math.floor(sq / 10) === 0);
const P3 = Array.from({ length: NT + 1 }, (_, i) => 3 ** i);
const NS = P3[NT] * 2; // trạng thái: chữ số cơ số 3 cho mỗi loại (đã dùng 0..2) + 1 bit vua
const digit = (st, t) => Math.floor((st % P3[NT]) / P3[t]) % 3;
// g[k][st] = số cách lấp các ô k..NSQ-1 từ trạng thái st tới trạng thái hợp lệ cuối
const g = Array.from({ length: NSQ + 1 }, () => new Float64Array(NS));
for (let st = 0; st < NS; st++) {
  const kb = st >= P3[NT] ? 1 : 0; let ok = kb === 1;
  for (let t = 0; ok && t < NT; t++) if (digit(st, t) === 0) ok = false;
  g[NSQ][st] = ok ? 1 : 0;
}
for (let k = NSQ - 1; k >= 0; k--) {
  const gk = g[k], gn = g[k + 1];
  for (let st = 0; st < NS; st++) {
    let s = 0;
    const kb = st >= P3[NT];
    if (!kb && kAllowed[k]) s += gn[st + P3[NT]];
    for (let t = 0; t < NT; t++) if (allowed[k][t] && digit(st, t) < 2) s += gn[st + P3[t]];
    gk[st] = s;
  }
}
const total = g[0][0];
console.log('Số thế thỏa điều kiện cần (đếm chính xác):', total.toExponential(4), '=', total);
// ---- lấy mẫu đều ----
let rs = Number(process.argv[2] || 7);
const rnd = () => (rs = (rs * 1103515245 + 12345) % 2147483648) / 2147483648;
function sample() {
  let st = 0; const arr = [];
  for (let k = 0; k < NSQ; k++) {
    const opts = [];
    if (st < P3[NT] && kAllowed[k]) opts.push(['K', st + P3[NT]]);
    for (let t = 0; t < NT; t++) if (allowed[k][t] && digit(st, t) < 2) opts.push([TYPES[t], st + P3[t]]);
    const w = opts.map(o => g[k + 1][o[1]]); const sum = w.reduce((a, b) => a + b, 0);
    let r = rnd() * sum, j = 0; while (r >= w[j]) { r -= w[j]; j++; }
    arr.push(opts[j][0]); st = opts[j][1];
  }
  return arr;
}
// ---- kiểm tra đầy đủ ----
const comps = { P: S.parse('mfWcfFimfnD'), T: S.parse('fKifmnDifmnA'), K: S.parse('WFmnDmnAmnN') };
for (const t of TYPES) comps[t] = S.parse(t);
function board(arr) {
  const b = new Array(100).fill(null);
  const put = (i, t) => { b[i] = { c: 'w', t, moved: false }; const x = i % 10, y = Math.floor(i / 10); b[(9 - y) * 10 + x] = { c: 'b', t, moved: false }; };
  for (const [i, t] of Object.entries(U.FIXED)) put(+i, t);
  FREE.forEach((sq, k) => put(sq, arr[k]));
  return b;
}
const gen = (bb, c) => { const a = new Int8Array(100); for (let i = 0; i < 100; i++) if (bb[i]) a[i] = bb[i].c === c ? 1 : 2; const o = [];
  for (let i = 0; i < 100; i++) { const p = bb[i]; if (!p || p.c !== c) continue; for (const m of S.genMoves(a, comps[p.t], i % 10, Math.floor(i / 10), c === 'w' ? 1 : -1, p.moved)) o.push({ from: i, to: m.to, caps: m.caps }); } return o; };
const opp = c => c === 'w' ? 'b' : 'w';
function cond1(b) { for (const c of ['w', 'b']) for (const m1 of gen(b, c)) { if (m1.caps.length) return false; if (gen(U.apply(b, m1), c).some(m => m.caps.length)) return false; } return true; }
const attacked = (bb, c) => { const k = bb.findIndex(p => p && p.c === opp(c) && p.t === 'K'); return k >= 0 && gen(bb, c).some(m => m.caps.includes(k)); };
const legal = (bb, c) => gen(bb, c).filter(m => !attacked(U.apply(bb, m), opp(c)));
function cond2(b) {
  for (const c of ['w', 'b']) {
    const o = opp(c);
    for (const m1 of legal(b, c)) {
      const b1 = U.apply(b, m1);
      if (attacked(b1, c)) return false;
      // chỉ cần xét kỹ khi có ít nhất một nước tiếp theo dọa chiếu
      if (!gen(b1, c).some(m3 => attacked(U.apply(b1, m3), c))) continue;
      let refuted = false;
      for (const r of legal(b1, o)) { const b2 = U.apply(b1, r); if (!legal(b2, c).some(m3 => attacked(U.apply(b2, m3), c))) { refuted = true; break; } }
      if (!refuted) return false;
    }
  }
  return true;
}
const NSAMP = Number(process.argv[3] || 200);
let n1 = 0, n12 = 0; const t0 = Date.now(); const examples = [];
for (let i = 0; i < NSAMP; i++) {
  const arr = sample(); const b = board(arr);
  if (!cond1(b)) continue; n1++;
  if (!cond2(b)) continue; n12++;
  if (examples.length < 3) examples.push(U.code(b));
}
const out = { seed: process.argv[2], total, NSAMP, n1, n12, sec: (Date.now() - t0) / 1000, examples };
require('fs').writeFileSync(`count_${process.argv[2]}.json`, JSON.stringify(out));
console.log(JSON.stringify(out));
