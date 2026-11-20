// Bộ bốc thế khởi đầu ngẫu nhiên đều.
// Tập đề xuất S': hàng 2-3 (8 ô) là hoán vị của H,H,L,L,M,M,N,N với a3, j3 khác H (1350 cách);
// hàng 1 là hoán vị của K + A,B,C,D,E,F,G,J + một loại X nhân đôi (8 · 10!/2 cách). Mọi thế hợp lệ đều nằm trong S'.
// Bốc đều trong S', kiểm tra đầy đủ, hỏng thì bốc lại (lấy mẫu loại bỏ) => đều trên tập thế hợp lệ.
const S = require('./betza_sim.js'); const U = require('./setup.js');
const PIECE = { A: 'F2t[WFF]', B: 'vWFFmWWcpWW', C: 'CHmFF[cj1]FF', D: 'NmF4cpF4', E: 'FZgF3', F: 'DHfrClfCblCrbC', G: 'WGgW3', H: 'sDt[WnA]', J: 'ZnD', L: 'nGsWWvW', M: 'nNfrNlfNblNrbN', N: 'nN[cj]nN', K: 'WFmnDmnAmnN', P: 'mfWcfFimfnD', T: 'fKifmnDifmnA' };
const comps = Object.fromEntries(Object.entries(PIECE).map(([k, v]) => [k, S.parse(v)]));
const R23 = ['a3', 'j3', 'a2', 'c2', 'e2', 'f2', 'h2', 'j2'].map(U.idx);
const R1 = 'abcdefghij'.split('').map(f => U.idx(f + '1'));
const rand = Math.random;
const shuffle = a => { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
function propose() {
  let r23; do { r23 = shuffle('HHLLMMNN'.split('')); } while (r23[0] === 'H' || r23[1] === 'H'); // đều trên 1350 cách
  const X = 'ABCDEFGJ'[Math.floor(rand() * 8)];
  const r1 = shuffle(('KABCDEFGJ' + X).split(''));
  const b = new Array(100).fill(null);
  const put = (i, t) => { b[i] = { c: 'w', t, moved: false }; const x = i % 10, y = Math.floor(i / 10); b[(9 - y) * 10 + x] = { c: 'b', t, moved: false }; };
  for (const [i, t] of Object.entries(U.FIXED)) put(+i, t);
  R23.forEach((sq, k) => put(sq, r23[k])); R1.forEach((sq, k) => put(sq, r1[k]));
  return b;
}
const gen = (bb, c) => { const a = new Int8Array(100); for (let i = 0; i < 100; i++) if (bb[i]) a[i] = bb[i].c === c ? 1 : 2; const o = [];
  for (let i = 0; i < 100; i++) { const p = bb[i]; if (!p || p.c !== c) continue; for (const m of S.genMoves(a, comps[p.t], i % 10, Math.floor(i / 10), c === 'w' ? 1 : -1, p.moved)) o.push({ from: i, to: m.to, caps: m.caps }); } return o; };
const opp = c => c === 'w' ? 'b' : 'w';
function cond1(b) { for (const c of ['w', 'b']) for (const m1 of gen(b, c)) { if (m1.caps.length) return false; if (gen(U.apply(b, m1), c).some(m => m.caps.length)) return false; } return true; }
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
function randomSetup() { let tries = 0; for (;;) { tries++; const b = propose(); if (cond1(b) && cond2(b)) return { code: U.code(b), tries }; } }
module.exports = { randomSetup, propose, cond1, cond2 };
if (require.main === module) {
  const n = Number(process.argv[2] || 50); const t0 = Date.now(); let tries = 0; const X = {};
  for (let i = 0; i < n; i++) { const r = randomSetup(); tries += r.tries; const row1 = r.code.split('/')[9]; for (const c of 'ABCDEFGJ') if (row1.split(c).length - 1 === 2) X[c] = (X[c] || 0) + 1; if (i < 3) console.log(r.code); }
  const sec = (Date.now() - t0) / 1000;
  console.log(`${n} thế hợp lệ, trung bình ${(tries / n).toFixed(1)} lần bốc/thế (tỉ lệ đạt ${(100 * n / tries).toFixed(2)}%), ${(sec / n).toFixed(3)} giây/thế; loại nhân đôi:`, JSON.stringify(X));
}
