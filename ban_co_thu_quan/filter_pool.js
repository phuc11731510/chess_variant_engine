const S = require('./betza_sim.js'); const fs = require('fs');
const pool = require('./pool.json');
const ok = []; let bad = 0, checked = 0;
for (const x of pool) {
  // chỉ quân có thể ăn ở khoảng cách >= 4 mới cần kiểm tra
  const b = new Int8Array(100); const geo = new Set();
  const comps = S.parse(x.p);
  let far = false;
  for (let s of [0, 44, 99, 9, 90]) {
    // thử bàn có địch rải để thấy nước ăn xa
    for (let t = 0; t < 3 && !far; t++) {
      const r = S.rng(s * 7 + t); const bd = S.randomBoard(r, 0.15, s);
      for (const m of S.genMoves(bd, comps, s % 10, Math.floor(s / 10))) for (const c of m.caps) {
        if (Math.max(Math.abs(c % 10 - s % 10), Math.abs(Math.floor(c / 10) - Math.floor(s / 10))) >= 4) far = true;
      }
    }
  }
  if (/t\[|\d|[WFDAHGNCZ]{2}|p|g/.test(x.p.replace(/\[cj\d*\]/g, '')) || far) {
    checked++;
    const r = S.checkCaptureRule(x.p, 500, 5);
    if (r.problems.length) { bad++; continue; }
  }
  ok.push(x);
}
fs.writeFileSync('pool_ok.json', JSON.stringify(ok));
console.log('pool', pool.length, 'checked', checked, 'removed', bad, 'kept', ok.length);
