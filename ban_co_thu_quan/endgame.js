// Tàn cuộc: 2 quân X (bên tấn công) đấu Hoàng gia trơ R (bên phòng thủ).
// Bên tấn công thắng khi ép được một lần chiếu, hoặc R hết nước đi hợp lệ.
// Phân tích ngược trên mọi thế cờ (R, X1, X2), cả hai lượt đi.
// Tùy chọn: royalAttacker = true thêm Hoàng gia của bên tấn công (chậm hơn nhiều).
'use strict';
const S = require('./betza_sim.js');
const ROYAL = 'WFmnDmnAmnN';

function solve(xBetza, opts = {}) {
  const allowCapture = !!opts.allowCapture;
  const X = S.parse(xBetza), R = S.parse(ROYAL);
  // chỉ số cặp không thứ tự (a<b)
  const pairIdx = new Int32Array(100 * 100).fill(-1); const pairs = [];
  for (let a = 0; a < 100; a++) for (let b = a + 1; b < 100; b++) { pairIdx[a * 100 + b] = pairIdx[b * 100 + a] = pairs.length; pairs.push([a, b]); }
  const NP = pairs.length, NS = 100 * NP;
  const sid = (d, a, b) => d * NP + pairIdx[a * 100 + b];
  const board = new Int8Array(100);
  // bàn nhìn từ bên tấn công: X = FRIEND(1), R = ENEMY(2)
  function setAtt(d, a, b) { board.fill(0); board[a] = 1; board[b] = 1; board[d] = 2; }
  function setDef(d, a, b) { board.fill(0); board[a] = 2; board[b] = 2; board[d] = 1; }
  // X ở ô s có tấn công ô d không (với bàn hiện tại)
  function attacks(s, d) {
    const mv = S.genMoves(board, X, s % 10, Math.floor(s / 10), 1);
    for (const m of mv) if (m.caps.includes(d)) return true;
    return false;
  }
  const valid = new Uint8Array(NS), inCheck = new Uint8Array(NS);
  for (let d = 0; d < 100; d++) for (let p = 0; p < NP; p++) {
    const [a, b] = pairs[p]; if (a === d || b === d) continue;
    const s = d * NP + p; valid[s] = 1;
    setAtt(d, a, b);
    if (attacks(a, d) || attacks(b, d)) inCheck[s] = 1;
  }
  // nước đi của bên phòng thủ từ thế s (lượt R): danh sách thế lượt bên tấn công; escape = có nước ăn thoát
  const defSucc = new Array(NS), defEscape = new Uint8Array(NS);
  for (let s = 0; s < NS; s++) {
    if (!valid[s] || inCheck[s]) continue;
    const d = Math.floor(s / NP), [a, b] = pairs[s % NP];
    setDef(d, a, b);
    const mv = S.genMoves(board, R, d % 10, Math.floor(d / 10), -1);
    const list = [];
    for (const m of mv) {
      const t = m.to;
      if (m.caps.length) {
        // ăn X ở ô t: hợp lệ nếu X còn lại không tấn công t
        if (!allowCapture) continue;
        const other = t === a ? b : a;
        board.fill(0); board[other] = 1; board[t] = 2;
        if (!attacks(other, t)) defEscape[s] = 1;
        setDef(d, a, b);
        continue;
      }
      const s2 = sid(t, a, b);
      if (!inCheck[s2]) list.push(s2);
    }
    defSucc[s] = list;
  }
  // nước đi của bên tấn công từ thế s (lượt X): danh sách thế lượt R
  const attSucc = new Array(NS);
  for (let s = 0; s < NS; s++) {
    if (!valid[s] || inCheck[s]) continue; // lượt X mà R đang bị chiếu: không hợp lệ (R vừa đi vào ô bị chiếu)
    const d = Math.floor(s / NP), [a, b] = pairs[s % NP];
    setAtt(d, a, b);
    const list = [];
    for (const [me, other] of [[a, b], [b, a]]) {
      for (const m of S.genMoves(board, X, me % 10, Math.floor(me / 10), 1)) {
        if (m.caps.length) continue; // không ăn Hoàng gia
        list.push(sid(d, m.to, other));
      }
    }
    attSucc[s] = list;
  }
  // điểm bất động: winD[s] (lượt R), winA[s] (lượt X)
  const winD = new Uint8Array(NS), winA = new Uint8Array(NS);
  for (let s = 0; s < NS; s++) if (valid[s] && (inCheck[s] || (defSucc[s] && defSucc[s].length === 0 && !defEscape[s]))) winD[s] = 1;
  let changed = true, rounds = 0;
  while (changed) {
    changed = false; rounds++;
    for (let s = 0; s < NS; s++) {
      if (!attSucc[s] || winA[s]) continue;
      for (const t of attSucc[s]) if (winD[t]) { winA[s] = 1; changed = true; break; }
    }
    for (let s = 0; s < NS; s++) {
      if (winD[s] || !defSucc[s] || defEscape[s]) continue;
      let all = true; for (const t of defSucc[s]) if (!winA[t]) { all = false; break; }
      if (all) { winD[s] = 1; changed = true; }
    }
  }
  let nA = 0, wA = 0, nD = 0, wD = 0, exA = null, exD = null;
  for (let s = 0; s < NS; s++) {
    if (!valid[s]) continue;
    if (!inCheck[s]) { nA++; if (winA[s]) wA++; else if (!exA) exA = s; }
    nD++; if (winD[s]) wD++; else if (!exD) exD = s;
  }
  const show = s => { if (s === null) return null; const d = Math.floor(s / NP), [a, b] = pairs[s % NP]; const n = q => 'abcdefghij'[q % 10] + (Math.floor(q / 10) + 1); return `R ${n(d)}, X ${n(a)} ${n(b)}`; };
  return { piece: xBetza, rounds, attToMove: `${wA}/${nA}`, defToMove: `${wD}/${nD}`, pass: wA === nA && wD === nD, failA: show(exA), failD: show(exD) };
}

module.exports = { solve };
if (require.main === module) {
  const cap = process.env.CAP === '1';
  for (const p of process.argv.slice(2)) { const t = Date.now(); const r = solve(p, { allowCapture: cap }); r.sec = ((Date.now() - t) / 1000).toFixed(1); console.log(JSON.stringify(r)); }
}
