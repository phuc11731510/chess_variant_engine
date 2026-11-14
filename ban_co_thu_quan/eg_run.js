const { solve } = require('./endgame.js'); const fs = require('fs');
const [inp, out] = process.argv.slice(2);
const list = fs.readFileSync(inp, 'utf8').split('\n').filter(Boolean);
const res = {};
for (const p of list) { try { const r = solve(p); res[p] = { pass: r.pass, a: r.attToMove, d: r.defToMove }; } catch (e) { res[p] = { err: String(e) }; } fs.writeFileSync(out, JSON.stringify(res)); }
