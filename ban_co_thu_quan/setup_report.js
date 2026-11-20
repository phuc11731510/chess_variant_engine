const U = require('./setup.js');
function parse(code) { const a = new Map(); code.split('/').forEach((r, k) => { const y = 9 - k; let x = 0; for (const m of r.match(/\d+|[A-Za-z]/g)) { if (/\d/.test(m)) { x += +m; continue; } const i = y * 10 + x; if (m === m.toUpperCase() && U.FREE.includes(i)) a.set(i, m); x++; } }); return a; }
// bàn với quân Đen đặt theo từng cặp: swap[i] = true nghĩa là quân Đen của ô trắng i đặt ở ảnh qua tâm
function board2(a, central) {
  const b = new Array(100).fill(null);
  const all = new Map([...Object.entries(U.FIXED).map(([i, t]) => [Number(i), t]), ...a]);
  for (const [i, t] of all) {
    b[i] = { c: 'w', t, moved: false };
    const x = i % 10, y = Math.floor(i / 10);
    const j = (9 - y) * 10 + (central ? 9 - x : x);
    b[j] = { c: 'b', t, moved: false };
  }
  return b;
}
const pretty = b => { const out = []; for (let y = 9; y >= 0; y--) { let r = (y + 1).toString().padStart(2) + ' '; for (let x = 0; x < 10; x++) { const p = b[y * 10 + x]; r += ' ' + (p ? (p.c === 'w' ? p.t : p.t.toLowerCase()) : '.'); } out.push(r); } out.push('    a b c d e f g h i j'); return out.join('\n'); };
for (const f of process.argv.slice(2)) {
  const a = parse(require('./' + f).code);
  const types = [...new Set([...a.values()].filter(t => t !== 'K'))].sort();
  const cnt = {}; for (const t of a.values()) cnt[t] = (cnt[t] || 0) + 1;
  let val = [0, 0, 0]; for (const t of a.values()) if (U.VAL[t]) U.VAL[t].forEach((v, k) => val[k] += v);
  console.log('=====', f, '| loại:', types.join(''), '(' + types.length + ')', '| số lượng:', JSON.stringify(cnt), '| tổng giá trị quân (không tính Tốt):', val.map(v => v.toFixed(2)).join(' / '));
  for (const central of [false, true]) {
    const b = board2(a, central);
    const w = U.threats(b, 'w'), bl = U.threats(b, 'b');
    const t0 = Date.now(); const ckW = U.checkIn2(b, 'w'), ckB = U.checkIn2(b, 'b');
    console.log(` Đen ${central ? 'đối xứng tâm' : 'đối xứng trục'}: chuỗi 2 nước ăn được quân: Trắng ${w.n}, Đen ${bl.n} | chiếu trong 2 nước: Trắng ${ckW ? ckW.map(m => U.nm(m.from) + '-' + U.nm(m.to)).join(',') : 'không'}, Đen ${ckB ? ckB.map(m => U.nm(m.from) + '-' + U.nm(m.to)).join(',') : 'không'} | nước đi đầu: ${U.allMoves(b, 'w').length}/${U.allMoves(b, 'b').length} | mã: ${U.code(b)}`);
    if (!central) console.log(pretty(b));
  }
}
