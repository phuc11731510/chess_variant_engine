// Kiểm tra nhanh hai điều kiện thế đầu, cho đúng cùng kết quả với cách cũ (random_setup.js).
// Tăng tốc: "vua có bị đánh không" chỉ sinh nước cho quân có độ lệch tới ô vua thuộc tập độ lệch có thể ăn của nó.
const S = require('./betza_sim.js');
const MAP = { A: 'F2t[WFF]', B: 'vWFFmWWcpWW', C: 'CHmFF[cj1]FF', D: 'NmF4cpF4', E: 'FZgF3', F: 'DHfrClfCblCrbC', G: 'WGgW3', H: 'sDt[WnA]', J: 'ZnD', L: 'nGsWWvW', M: 'nNfrNlfNblNrbN', N: 'nN[cj]nN', K: 'WFmnDmnAmnN', P: 'mfWcfFimfnD', T: 'fKifmnDifmnA' };
const comps = {}; for (const k in MAP) comps[k] = S.parse(MAP[k]);
// tập độ lệch (trong hệ của quân) mà quân có thể ăn tới, ở mọi thế cờ
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
const DISP = {}; for (const k in comps) DISP[k] = capDisp(comps[k]);
const opp = c => c === 'w' ? 'b' : 'w';
function sideArr(bb, c) { const a = new Int8Array(100); for (let i = 0; i < 100; i++) if (bb[i]) a[i] = bb[i].c === c ? 1 : 2; return a; }
function gen(bb, c) { const a = sideArr(bb, c); const o = [];
  for (let i = 0; i < 100; i++) { const p = bb[i]; if (!p || p.c !== c) continue; for (const m of S.genMoves(a, comps[p.t], i % 10, Math.floor(i / 10), c === 'w' ? 1 : -1, p.moved)) o.push({ from: i, to: m.to, caps: m.caps }); } return o; }
function apply(bb, m) { const nb = bb.slice(); const p = nb[m.from]; for (const c of m.caps) nb[c] = null; nb[m.from] = null; nb[m.to] = { c: p.c, t: p.t, moved: true }; return nb; }
// bên c có đang đánh vào quân hoàng gia của đối phương không
function attacked(bb, c) {
  const k = bb.findIndex(p => p && p.c === opp(c) && p.t === 'K'); if (k < 0) return false;
  const kx = k % 10, ky = Math.floor(k / 10), sd = c === 'w' ? 1 : -1; let a = null;
  for (let i = 0; i < 100; i++) {
    const p = bb[i]; if (!p || p.c !== c) continue;
    const dx = (kx - i % 10) * sd, dy = (ky - Math.floor(i / 10)) * sd;
    if (!DISP[p.t].has(dx * 100 + dy)) continue;
    if (!a) a = sideArr(bb, c);
    for (const m of S.genMoves(a, comps[p.t], i % 10, Math.floor(i / 10), sd, p.moved)) if (m.caps.includes(k)) return true;
  }
  return false;
}
function cond1(b) { for (const c of ['w', 'b']) for (const m1 of gen(b, c)) { if (m1.caps.length) return false; if (gen(apply(b, m1), c).some(m => m.caps.length)) return false; } return true; }
const legal = (bb, c) => gen(bb, c).filter(m => !attacked(apply(bb, m), opp(c)));
function cond2(b) {
  for (const c of ['w', 'b']) { const o = opp(c);
    for (const m1 of legal(b, c)) { const b1 = apply(b, m1); if (attacked(b1, c)) return false;
      if (!gen(b1, c).some(m3 => attacked(apply(b1, m3), c))) continue;
      let ref = false; for (const r of legal(b1, o)) { const b2 = apply(b1, r); if (!legal(b2, c).some(m3 => attacked(apply(b2, m3), c))) { ref = true; break; } }
      if (!ref) return false; } }
  return true;
}
module.exports = { cond1, cond2, attacked, DISP };
