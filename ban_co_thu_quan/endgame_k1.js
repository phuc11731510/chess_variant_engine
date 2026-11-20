// Tàn cuộc chặt chẽ: bên tấn công có Hoàng gia Ka + 1 quân X; bên phòng thủ chỉ có Hoàng gia trơ R.
// Thế = (R, Ka, X), phân tích ngược trên mọi thế, cả hai lượt đi.
// Luật dùng:
//  - Bên tấn công thắng khi ép được một lần chiếu (R bị tấn công khi đến lượt R), hoặc R hết nước đi hợp lệ.
//  - Hoàng gia không được đi vào ô bị đối phương tấn công. Hoàng gia chỉ ăn được ở 8 ô liền kề (W, F).
//  - R được ăn X nếu sau khi ăn, ô đó không bị Ka tấn công (X được Ka bảo vệ thì không ăn được).
//    Nếu R ăn được X thì bên tấn công chỉ còn Hoàng gia: coi như R thoát (không ép được chiếu nữa).
//  - Ka và X cản đường nhau và cản đường của R; Ka có thể đi các nước của Hoàng gia (kể cả nhảy N, D, A).
//  - Bên tấn công không được ăn Hoàng gia (chiếu là đủ). Bên tấn công đi lên (hướng +y), R đối xứng nên không phụ thuộc hướng.
'use strict';
const S = require('./betza_sim.js');
const ROYAL = 'WFmnDmnAmnN';
const nm = q => 'abcdefghij'[q % 10] + (Math.floor(q / 10) + 1);
const cheb = (p, q) => Math.max(Math.abs(p % 10 - q % 10), Math.abs(Math.floor(p / 10) - Math.floor(q / 10)));

// tập độ lệch (hệ của quân) mà quân có thể ăn tới, ở mọi thế cờ (dùng để bỏ qua phép sinh nước thừa)
function capDisp(cs) {
  const set = new Set(); const add = (x, y) => { if (Math.abs(x) <= 9 && Math.abs(y) <= 9) set.add(x * 100 + y); };
  for (const c of cs) {
    if (c.kind === 'step') { if (!c.modality.includes('c')) continue; for (const v of c.vecs) for (let k = 1; k <= Math.min(c.amax, 9); k++) add(v[0] * k, v[1] * k); }
    else if (c.kind === 'hop') { if (!c.modality.includes('c')) continue; const bm = c.hop === 'g' ? 1 : Math.min(c.amax, 9);
      for (const v of c.vecs) for (let a = 1; a <= Math.min(c.amax, 9); a++) for (let b = 1; b <= bm; b++) add(v[0] * (a + b), v[1] * (a + b)); }
    else if (c.kind === 'cj') { for (const v of c.vecs) for (let a = 1; a <= Math.min(c.amax, 9); a++) add(v[0] * a, v[1] * a); }
    else if (c.kind === 't') { for (const u of c.A.vecs) { add(u[0], u[1]); const dirs = c.B.cluster ? c.B.vecs : c.B.vecs.filter(d => u[0] * d[0] + u[1] * d[1] > 0);
      for (const d of dirs) for (let k = 1; k <= Math.min(c.B.amax, 9); k++) add(u[0] + d[0] * k, u[1] + d[1] * k); } }
  }
  return set;
}

class Csr { // danh sách kề dạng mảng phẳng
  constructor(n) { this.off = new Int32Array(n + 1); this.d = new Int32Array(1 << 24); this.n = 0; }
  push(v) { if (this.n === this.d.length) { const nd = new Int32Array(this.d.length * 2); nd.set(this.d); this.d = nd; } this.d[this.n++] = v; }
}

function solve(xBetza) {
  const X = S.parse(xBetza), K = S.parse(ROYAL), dX = capDisp(X);
  const NS = 1000000, sid = (d, k, a) => (d * 100 + k) * 100 + a;
  const board = new Int8Array(100);
  const valid = new Uint8Array(NS), inCheck = new Uint8Array(NS);
  for (let d = 0; d < 100; d++) for (let k = 0; k < 100; k++) { if (k === d) continue;
    for (let a = 0; a < 100; a++) { if (a === d || a === k) continue;
      const s = sid(d, k, a); valid[s] = 1;
      if (cheb(k, d) <= 1) { inCheck[s] = 1; continue; } // Ka tấn công R
      if (!dX.has((d % 10 - a % 10) * 100 + (Math.floor(d / 10) - Math.floor(a / 10)))) continue;
      board.fill(0); board[k] = 1; board[a] = 1; board[d] = 2;
      if (S.genMoves(board, X, a % 10, Math.floor(a / 10), 1).some(m => m.caps.includes(d))) inCheck[s] = 1;
    } }
  // nước của R (lượt R)
  const D = new Csr(NS), esc = new Uint8Array(NS);
  for (let s = 0; s < NS; s++) { D.off[s] = D.n; if (!valid[s] || inCheck[s]) continue;
    const d = Math.floor(s / 10000), k = Math.floor(s / 100) % 100, a = s % 100;
    board.fill(0); board[d] = 1; board[k] = 2; board[a] = 2;
    for (const m of S.genMoves(board, K, d % 10, Math.floor(d / 10), -1)) {
      if (m.caps.length) { if (m.caps.length === 1 && m.caps[0] === a && cheb(k, a) > 1) esc[s] = 1; continue; } // ăn X khi X không được Ka bảo vệ
      const s2 = sid(m.to, k, a); if (!inCheck[s2]) D.push(s2);
    } }
  D.off[NS] = D.n;
  // nước của bên tấn công (lượt Ka/X)
  const A = new Csr(NS);
  for (let s = 0; s < NS; s++) { A.off[s] = A.n; if (!valid[s] || inCheck[s]) continue;
    const d = Math.floor(s / 10000), k = Math.floor(s / 100) % 100, a = s % 100;
    board.fill(0); board[k] = 1; board[a] = 1; board[d] = 2;
    for (const m of S.genMoves(board, X, a % 10, Math.floor(a / 10), 1)) { if (m.caps.length) continue; A.push(sid(d, k, m.to)); }
    for (const m of S.genMoves(board, K, k % 10, Math.floor(k / 10), 1)) { if (m.caps.length) continue; if (cheb(m.to, d) <= 1) continue; A.push(sid(d, m.to, a)); }
  }
  A.off[NS] = A.n;
  const winD = new Uint8Array(NS), winA = new Uint8Array(NS), dep = new Int16Array(NS).fill(-1);
  for (let s = 0; s < NS; s++) if (valid[s] && (inCheck[s] || (!esc[s] && D.off[s + 1] === D.off[s]))) { winD[s] = 1; dep[s] = 0; }
  let changed = true, rounds = 0; const tmp = [];
  while (changed) {
    changed = false; rounds++; tmp.length = 0;
    for (let s = 0; s < NS; s++) { if (!valid[s] || inCheck[s] || winA[s]) continue;
      for (let i = A.off[s]; i < A.off[s + 1]; i++) if (winD[A.d[i]]) { tmp.push(s); break; } }
    for (const s of tmp) { winA[s] = 1; dep[s] = 2 * rounds - 1; changed = true; }
    tmp.length = 0;
    for (let s = 0; s < NS; s++) { if (!valid[s] || inCheck[s] || winD[s] || esc[s]) continue;
      let all = true; for (let i = D.off[s]; i < D.off[s + 1]; i++) if (!winA[D.d[i]]) { all = false; break; }
      if (all) tmp.push(s); }
    for (const s of tmp) { winD[s] = 1; dep[s] = 2 * rounds; changed = true; }
  }
  let nA = 0, wA = 0, nD = 0, wD = 0, maxA = 0, exA = -1, exD = -1;
  for (let s = 0; s < NS; s++) { if (!valid[s]) continue;
    if (!inCheck[s]) { nA++; if (winA[s]) { wA++; if (dep[s] > maxA) maxA = dep[s]; } else if (exA < 0) exA = s; }
    nD++; if (winD[s]) wD++; else if (exD < 0) exD = s; }
  const failList = []; if (process.env.LIST) for (let s = 0; s < NS; s++) if (valid[s] && !inCheck[s] && !winA[s]) failList.push(s);
  const show = s => s < 0 ? null : `R ${nm(Math.floor(s / 10000))}, Ka ${nm(Math.floor(s / 100) % 100)}, X ${nm(s % 100)}`;
  return { piece: xBetza, attToMove: `${wA}/${nA}`, attPct: +(100 * wA / nA).toFixed(2), defToMove: `${wD}/${nD}`, defPct: +(100 * wD / nD).toFixed(2),
    pass: wA === nA && wD === nD, maxHalfMoves: wA === nA ? maxA : null, failA: show(exA), failD: show(exD), rounds, failList };
}
module.exports = { solve };
if (require.main === module) {
  for (const p of process.argv.slice(2)) { const t = Date.now(); const r = solve(p); r.sec = ((Date.now() - t) / 1000).toFixed(1); console.log(JSON.stringify(r)); }
}
