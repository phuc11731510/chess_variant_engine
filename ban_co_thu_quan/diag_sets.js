// Với mỗi cách chọn 5 loại có 2 quân: đếm chính xác số thế thỏa điều kiện cần, rồi lấy mẫu để ước lượng số thế hợp lệ.
// Dùng: node per_set.js <phần> <số phần> <số mẫu mỗi bộ>
const S = require('./betza_sim.js'); const U = require('./setup.js');
const safe = require('./safe_all.json');
const TYPES = ['F2t[WFF]', 'vWFFmWWcpWW', 'CHmFF[cj1]FF', 'NmF4cpF4', 'FZgF3', 'DHfrClfCblCrbC', 'WGgW3', 'sDt[WnA]', 'ZnD', 'nGsWWvW', 'nNfrNlfNblNrbN', 'nN[cj]nN'];
const LET = 'ABCDEFGHJLMN';
const VAL = [[1.09, 1.08, 1.04], [1.04, 0.98, 0.95], [1.03, 0.93, 0.79], [0.92, 0.77, 0.62], [0.96, 0.69, 0.45], [0.83, 0.63, 0.44], [0.82, 0.58, 0.36], [0.57, 0.50, 0.42], [0.56, 0.47, 0.36], [0.48, 0.46, 0.45], [0.39, 0.34, 0.27], [0.24, 0.28, 0.26]];
const NSAMP = 150; const WANT = process.argv.slice(2);
const FREE = U.FREE, NSQ = FREE.length, NT = 12;
const allowed = FREE.map(sq => TYPES.map(t => safe[t].includes(U.nm(sq))));
const kAllowed = FREE.map(sq => Math.floor(sq / 10) === 0);
function combos(n, k, start = 0, acc = [], out = []) { if (acc.length === k) { out.push(acc.slice()); return out; } for (let i = start; i < n; i++) { acc.push(i); combos(n, k, i + 1, acc, out); acc.pop(); } return out; }
const comps = { P: S.parse('mfWcfFimfnD'), T: S.parse('fKifmnDifmnA'), K: S.parse('WFmnDmnAmnN') };
for (const t of TYPES) comps[t] = S.parse(t);
const gen = (bb, c) => { const a = new Int8Array(100); for (let i = 0; i < 100; i++) if (bb[i]) a[i] = bb[i].c === c ? 1 : 2; const o = [];
  for (let i = 0; i < 100; i++) { const p = bb[i]; if (!p || p.c !== c) continue; for (const m of S.genMoves(a, comps[p.t], i % 10, Math.floor(i / 10), c === 'w' ? 1 : -1, p.moved)) o.push({ from: i, to: m.to, caps: m.caps }); } return o; };
const opp = c => c === 'w' ? 'b' : 'w';
const why = {};
function cond1(b) { for (const c of ['w', 'b']) for (const m1 of gen(b, c)) { if (m1.caps.length) return false; const b1 = U.apply(b, m1); const m2 = gen(b1, c).find(m => m.caps.length);
  if (m2) { const k = LETTER(b[m1.from].t) + '@' + U.nm(m1.from) + ' mở đường cho ' + LETTER(b1[m2.from].t) + '@' + U.nm(m2.from); why[k] = (why[k] || 0) + 1; return false; } } return true; }
const LETTER = t => ({ P: 'P', T: 'T', K: 'K' })[t] || LET[TYPES.indexOf(t)];
const attacked = (bb, c) => { const k = bb.findIndex(p => p && p.c === opp(c) && p.t === 'K'); return k >= 0 && gen(bb, c).some(m => m.caps.includes(k)); };
const legal = (bb, c) => gen(bb, c).filter(m => !attacked(U.apply(bb, m), opp(c)));
function cond2(b) {
  for (const c of ['w', 'b']) { const o = opp(c);
    for (const m1 of legal(b, c)) { const b1 = U.apply(b, m1); if (attacked(b1, c)) return false;
      if (!gen(b1, c).some(m3 => attacked(U.apply(b1, m3), c))) continue;
      let ref = false; for (const r of legal(b1, o)) { const b2 = U.apply(b1, r); if (!legal(b2, c).some(m3 => attacked(U.apply(b2, m3), c))) { ref = true; break; } }
      if (!ref) return false; } }
  return true;
}
function board(arr) { const b = new Array(100).fill(null);
  const put = (i, t) => { b[i] = { c: 'w', t, moved: false }; const x = i % 10, y = Math.floor(i / 10); b[(9 - y) * 10 + x] = { c: 'b', t, moved: false }; };
  for (const [i, t] of Object.entries(U.FIXED)) put(+i, t); FREE.forEach((sq, k) => put(sq, arr[k])); return b; }
let rs = 987;
const rnd = () => (rs = (rs * 1103515245 + 12345) % 2147483648) / 2147483648;
const results = [];
combos(NT, 5).forEach((D, idx) => {
  if (!WANT.includes(D.map(t => LET[t]).join(''))) return;
  const cap = TYPES.map((_, t) => D.includes(t) ? 2 : 1);
  // trạng thái: số đã dùng của mỗi loại (0..cap) + bit vua; mã hóa hỗn hợp cơ số
  const base = []; let m = 1; for (let t = 0; t < NT; t++) { base.push(m); m *= cap[t] + 1; } const KB = m; const NS = m * 2;
  const used = (st, t) => Math.floor((st % KB) / base[t]) % (cap[t] + 1);
  const g = Array.from({ length: NSQ + 1 }, () => new Float64Array(NS));
  for (let st = 0; st < NS; st++) { let ok = st >= KB; for (let t = 0; ok && t < NT; t++) if (used(st, t) !== cap[t]) ok = false; g[NSQ][st] = ok ? 1 : 0; }
  for (let k = NSQ - 1; k >= 0; k--) for (let st = 0; st < NS; st++) { let s = 0; if (st < KB && kAllowed[k]) s += g[k + 1][st + KB];
    for (let t = 0; t < NT; t++) if (allowed[k][t] && used(st, t) < cap[t]) s += g[k + 1][st + base[t]]; g[k][st] = s; }
  const total = g[0][0];
  const name = D.map(t => LET[t]).join('');
  const val = [0, 1, 2].map(j => TYPES.reduce((s, _, t) => s + cap[t] * VAL[t][j], 0));
  if (total === 0) { results.push({ D: name, total: 0, val }); return; }
  let n12 = 0, n1 = 0;
  for (let i = 0; i < NSAMP; i++) {
    let st = 0; const arr = [];
    for (let k = 0; k < NSQ; k++) { const opts = []; if (st < KB && kAllowed[k]) opts.push(['K', st + KB]);
      for (let t = 0; t < NT; t++) if (allowed[k][t] && used(st, t) < cap[t]) opts.push([TYPES[t], st + base[t]]);
      const w = opts.map(o => g[k + 1][o[1]]); let r = rnd() * w.reduce((a, b) => a + b, 0), j = 0; while (r >= w[j]) { r -= w[j]; j++; } arr.push(opts[j][0]); st = opts[j][1]; }
    const b = board(arr); if (!cond1(b)) continue; n1++; if (cond2(b)) n12++;
  }
  results.push({ D: name, total, n1, n12, NSAMP, est: total * n12 / NSAMP, val });
});
console.log(JSON.stringify(results.map(r => [r.D, r.n1, r.NSAMP])));
console.log(Object.entries(why).sort((a, b) => b[1] - a[1]).slice(0, 12).map(([k, v]) => v + ' × ' + k).join(String.fromCharCode(10)));
