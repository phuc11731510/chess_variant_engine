const S = require('./betza_sim.js'); const F = require('./features.js');
const set = process.argv.slice(2);
const T = 20000;
const Qr = [0.6,0.4,0.2].map(d => S.mobility('WWFF', d, T, 11).score);
console.log('Queen raw', Qr.map(x => x.toFixed(2)).join(' / '));
const t = F.tally(set); console.log('feature counts', JSON.stringify(t.cnt), 'bad:', t.bad);
for (const p of set) {
  const raw = [0.6,0.4,0.2].map(d => S.mobility(p, d, T, 11).score);
  const rel = raw.map((x, i) => x / Qr[i]);
  const b = new Int8Array(100); b[44] = 1; const empty = S.genMoves(b, S.parse(p), 4, 4).length;
  const cap = S.checkCaptureRule(p, 3000, 21);
  console.log(p.padEnd(22), 'rel', rel.map(x => x.toFixed(2)).join(' '), 'avg', ((rel[0]+rel[1]+rel[2])/3).toFixed(2),
    '| raw', raw.map(x => x.toFixed(1)).join(' '), '| e5-empty', empty, '| reach', S.reachability(p), '| far caps checked', cap.checked, 'problems', cap.problems.length, cap.problems.slice(0,1).map(x=>JSON.stringify(x)).join(''));
}
