// Tìm vài thế cờ cụ thể (X = WW) để minh họa cách phân tích ngược
const S = require('./betza_sim.js');
const X = S.parse('WW'), R = S.parse('WFmnDmnAmnN');
const n = q => 'abcdefghij'[q % 10] + (Math.floor(q / 10) + 1);
const sq = s => 'abcdefghij'.indexOf(s[0]) + 10 * (Number(s.slice(1)) - 1);
function attacked(d, a, b) { const bd = new Int8Array(100); bd[a] = 1; bd[b] = 1; bd[d] = 2; for (const s of [a, b]) for (const m of S.genMoves(bd, X, s % 10, Math.floor(s / 10), 1)) if (m.caps.includes(d)) return true; return false; }
function defMoves(d, a, b) { const bd = new Int8Array(100); bd[a] = 2; bd[b] = 2; bd[d] = 1; const out = [];
  for (const m of S.genMoves(bd, R, d % 10, Math.floor(d / 10), -1)) { if (m.caps.length) continue; out.push([m.to, attacked(m.to, a, b)]); } return out; }
const pos = process.argv.slice(2);
for (const p of pos) { const [d, a, b] = p.split(' ').map(sq);
  console.log(`R ${n(d)}, X ${n(a)} ${n(b)}: chiếu=${attacked(d, a, b)}; nước của R:`, defMoves(d, a, b).map(([t, c]) => n(t) + (c ? '(bị chiếu)' : '')).join(' ')); }
