// Tìm thế khởi đầu: Trắng ở hàng 1-3, Đen đối xứng qua trục ngang.
// Điều kiện: một bên đi 2 nước liên tiếp (bên kia không đi) không ăn được quân nào.
'use strict';
const S = require('./betza_sim.js');
const PIECES = {
  K: 'WFmnDmnAmnN', A: 'F2t[WFF]', B: 'sWFFmWWcpWW', C: 'CHmFF[cj1]FF', D: 'DHmFFcpFF', E: 'NGfrClfCblCrbC',
  F: 'FZgF3', G: 'WGgWW', H: 'vDt[WA]', J: 'ZnD', L: 'sWWvW', M: 'nNfrNlfNblNrbN', N: 'nN[cj]nN',
  P: 'mfWcfFimfnD', T: 'fKifmnDifmnA',
};
const VAL = { A: [1.09, 1.08, 1.04], B: [1.04, 0.98, 0.95], C: [1.03, 0.93, 0.79], D: [0.95, 0.80, 0.67], E: [0.99, 0.75, 0.53], F: [0.96, 0.69, 0.45],
  G: [0.83, 0.60, 0.38], H: [0.68, 0.58, 0.45], J: [0.56, 0.47, 0.36], L: [0.44, 0.41, 0.38], M: [0.39, 0.34, 0.27], N: [0.24, 0.28, 0.26] };
const COMPS = Object.fromEntries(Object.entries(PIECES).map(([k, v]) => [k, S.parse(v)]));
const TYPES = 'ABCDEFGHJLMN'.split('');
const idx = s => 'abcdefghij'.indexOf(s[0]) + 10 * (Number(s.slice(1)) - 1);
const nm = i => 'abcdefghij'[i % 10] + (Math.floor(i / 10) + 1);
const FIXED = {};
for (const f of 'bcdefghi') FIXED[idx(f + '3')] = 'P';
for (const f of 'bdgi') FIXED[idx(f + '2')] = 'T';
const FREE = ['a3', 'j3', 'a2', 'c2', 'e2', 'f2', 'h2', 'j2', 'a1', 'b1', 'c1', 'd1', 'e1', 'f1', 'g1', 'h1', 'i1', 'j1'].map(idx);

function makeBoard(assign) { // assign: Map square -> type (trắng); trả về mảng 100 phần tử {c,t,moved}
  const b = new Array(100).fill(null);
  const put = (i, t) => { b[i] = { c: 'w', t, moved: false }; const x = i % 10, y = Math.floor(i / 10); b[(9 - y) * 10 + x] = { c: 'b', t, moved: false }; };
  for (const [i, t] of Object.entries(FIXED)) put(Number(i), t);
  for (const [i, t] of assign) put(i, t);
  return b;
}
function sideBoard(b, c) { const a = new Int8Array(100); for (let i = 0; i < 100; i++) if (b[i]) a[i] = b[i].c === c ? 1 : 2; return a; }
function allMoves(b, c) {
  const a = sideBoard(b, c), out = [];
  for (let i = 0; i < 100; i++) {
    const p = b[i]; if (!p || p.c !== c) continue;
    for (const m of S.genMoves(a, COMPS[p.t], i % 10, Math.floor(i / 10), c === 'w' ? 1 : -1, p.moved)) out.push({ from: i, to: m.to, caps: m.caps });
  }
  return out;
}
function apply(b, m) { const nb = b.slice(); const p = nb[m.from]; for (const c of m.caps) nb[c] = null; nb[m.from] = null; nb[m.to] = { ...p, moved: true }; return nb; }
// số chuỗi 2 nước của bên c có ăn quân; trả về ví dụ đầu tiên
function threats(b, c, limit = Infinity) {
  let n = 0, ex = null;
  for (const m1 of allMoves(b, c)) {
    if (m1.caps.length) { n++; if (!ex) ex = [m1]; if (n >= limit) return { n, ex }; continue; }
    const b1 = apply(b, m1);
    for (const m2 of allMoves(b1, c)) if (m2.caps.length) { n++; if (!ex) ex = [m1, m2]; if (n >= limit) return { n, ex }; break; }
  }
  return { n, ex };
}
// bên c có chiếu được sau tối đa 2 nước liên tiếp không (chiếu = sau nước đó, một nước tiếp theo của c ăn được quân hoàng gia đối phương)
function checkIn2(b, c) {
  const o = c === 'w' ? 'b' : 'w';
  const kOf = bb => bb.findIndex(p => p && p.c === o && p.t === 'K');
  const attacks = bb => { const k = kOf(bb); return allMoves(bb, c).some(m => m.caps.includes(k)); };
  for (const m1 of allMoves(b, c)) {
    const b1 = apply(b, m1); if (attacks(b1)) return [m1];
    for (const m2 of allMoves(b1, c)) { const b2 = apply(b1, m2); if (attacks(b2)) return [m1, m2]; }
  }
  return null;
}
function code(b) {
  const rows = [];
  for (let y = 9; y >= 0; y--) { let r = '', e = 0; for (let x = 0; x < 10; x++) { const p = b[y * 10 + x]; if (!p) { e++; continue; } if (e) { r += e; e = 0; } r += p.c === 'w' ? p.t : p.t.toLowerCase(); } if (e) r += e; rows.push(r); }
  return rows.join('/');
}
module.exports = { PIECES, VAL, TYPES, FREE, FIXED, idx, nm, makeBoard, allMoves, apply, threats, checkIn2, code };
