// Tàn cuộc: 1 quân X (bên tấn công) đấu Hoàng gia trơ R (bên phòng thủ).
// Cùng quy ước với endgame.js (2 quân): bên tấn công thắng khi ép được một lần chiếu,
// hoặc R hết nước đi hợp lệ (bên bị hết nước thua). Hoàng gia của bên tấn công không có trên bàn.
// Phân tích ngược trên mọi thế (R, X), cả hai lượt đi. CAP=1: R được phép ăn X (X không có quân bảo vệ).
'use strict';
const S = require('./betza_sim.js');
const ROYAL = 'WFmnDmnAmnN';
const nm = q => 'abcdefghij'[q % 10] + (Math.floor(q / 10) + 1);

function solve(xBetza, opts = {}) {
  const allowCapture = !!opts.allowCapture;
  const X = S.parse(xBetza), R = S.parse(ROYAL);
  const sid = (d, a) => d * 100 + a, NS = 10000;
  const board = new Int8Array(100);
  const setAtt = (d, a) => { board.fill(0); board[a] = 1; board[d] = 2; };   // nhìn từ bên tấn công
  const setDef = (d, a) => { board.fill(0); board[a] = 2; board[d] = 1; };   // nhìn từ R
  const attacks = (a, d) => S.genMoves(board, X, a % 10, Math.floor(a / 10), 1).some(m => m.caps.includes(d));
  const valid = new Uint8Array(NS), inCheck = new Uint8Array(NS);
  for (let d = 0; d < 100; d++) for (let a = 0; a < 100; a++) { if (a === d) continue; valid[sid(d, a)] = 1; setAtt(d, a); if (attacks(a, d)) inCheck[sid(d, a)] = 1; }
  const defSucc = new Array(NS), defEscape = new Uint8Array(NS);
  for (let s = 0; s < NS; s++) {
    if (!valid[s] || inCheck[s]) continue;
    const d = Math.floor(s / 100), a = s % 100;
    setDef(d, a);
    const list = [];
    for (const m of S.genMoves(board, R, d % 10, Math.floor(d / 10), -1)) {
      if (m.caps.length) { if (allowCapture) defEscape[s] = 1; continue; } // R ăn X: không còn quân nào để chiếu
      const s2 = sid(m.to, a);
      if (!inCheck[s2]) list.push(s2);
    }
    defSucc[s] = list;
  }
  const attSucc = new Array(NS);
  for (let s = 0; s < NS; s++) {
    if (!valid[s] || inCheck[s]) continue;
    const d = Math.floor(s / 100), a = s % 100;
    setAtt(d, a);
    const list = [];
    for (const m of S.genMoves(board, X, a % 10, Math.floor(a / 10), 1)) { if (m.caps.length) continue; list.push(sid(d, m.to)); }
    attSucc[s] = list;
  }
  // điểm bất động; depthD/depthA = số nửa nước tới khi thắng (để báo cáo)
  const winD = new Uint8Array(NS), winA = new Uint8Array(NS), dep = new Int16Array(NS).fill(-1);
  for (let s = 0; s < NS; s++) if (valid[s] && (inCheck[s] || (defSucc[s] && defSucc[s].length === 0 && !defEscape[s]))) { winD[s] = 1; dep[s] = 0; }
  let changed = true, rounds = 0;
  while (changed) {
    changed = false; rounds++;
    const nA = [], nD = [];
    for (let s = 0; s < NS; s++) {
      if (!attSucc[s] || winA[s]) continue;
      for (const t of attSucc[s]) if (winD[t]) { nA.push(s); break; }
    }
    for (const s of nA) { winA[s] = 1; dep[s] = 2 * rounds - 1; changed = true; }
    for (let s = 0; s < NS; s++) {
      if (winD[s] || !defSucc[s] || defEscape[s]) continue;
      let all = true; for (const t of defSucc[s]) if (!winA[t]) { all = false; break; }
      if (all) nD.push(s);
    }
    for (const s of nD) { winD[s] = 1; dep[s] = 2 * rounds; changed = true; }
  }
  let nA = 0, wA = 0, nD = 0, wD = 0, maxA = 0, exA = null, exD = null;
  for (let s = 0; s < NS; s++) {
    if (!valid[s]) continue;
    if (!inCheck[s]) { nA++; if (winA[s]) { wA++; if (dep[s] > maxA) maxA = dep[s]; } else if (exA === null) exA = s; }
    nD++; if (winD[s]) wD++; else if (exD === null) exD = s;
  }
  const show = s => s === null ? null : `R ${nm(Math.floor(s / 100))}, X ${nm(s % 100)}`;
  return { piece: xBetza, attToMove: `${wA}/${nA}`, attPct: +(100 * wA / nA).toFixed(1), defToMove: `${wD}/${nD}`, defPct: +(100 * wD / nD).toFixed(1),
    pass: wA === nA && wD === nD, maxHalfMoves: wA === nA ? maxA : null, failA: show(exA), failD: show(exD) };
}
module.exports = { solve };
if (require.main === module) {
  const cap = process.env.CAP === '1';
  for (const p of process.argv.slice(2)) { const t = Date.now(); const r = solve(p, { allowCapture: cap }); r.sec = ((Date.now() - t) / 1000).toFixed(1); console.log(JSON.stringify(r)); }
}
