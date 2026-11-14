const S = require('./betza_sim.js');
const cases = require('./rand_cases.json');
let bad = 0; const perKey = {};
for (const c of cases) {
  const b = new Int8Array(100);
  const idx = ([x, y]) => (y - 1) * 10 + (x - 1);
  b[idx(c.Z)] = 1; for (const s of c.T) b[idx(s)] = 1; for (const s of c.D) b[idx(s)] = 2;
  const mv = S.genMoves(b, S.parse(c.betza), c.Z[0] - 1, c.Z[1] - 1);
  const normal = new Set(), cj = new Set();
  for (const m of mv) {
    const x = m.to % 10 + 1, y = Math.floor(m.to / 10) + 1;
    if (m.caps.length === 0 || (m.caps.length === 1 && m.caps[0] === m.to)) normal.add(x + ',' + y);
    else cj.add(x + ',' + y + ',' + (m.caps[0] % 10 + 1) + ',' + (Math.floor(m.caps[0] / 10) + 1));
  }
  const pn = new Set(c.normal.map(s => s.join(','))), pc = new Set(c.cj.map(s => s.join(',')));
  const same = (A, B) => A.size === B.size && [...A].every(x => B.has(x));
  perKey[c.key] = (perKey[c.key] || 0) + 1;
  if (!same(normal, pn) || !same(cj, pc)) { if (bad++ < 5) console.log('MISMATCH', c.key, c.betza, JSON.stringify(c.Z), [...normal].sort().join(' '), '| py', [...pn].sort().join(' ')); }
}
console.log('cases', cases.length, 'mismatches', bad, JSON.stringify(perKey));
