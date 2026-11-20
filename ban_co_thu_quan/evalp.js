const S = require('./betza_sim.js');
const F = require('./features.js');
const T = Number(process.env.T || 4000);
const Q = [0.6,0.4,0.2].map(d => S.mobility('WWFF', d, T*2).score);
const rows = [];
for (const p of process.argv.slice(2)) {
  const r = [0.6,0.4,0.2].map((d,i) => S.mobility(p, d, T).score / Q[i]);
  const reach = S.reachability(p);
  const avg = (r[0]+r[1]+r[2])/3;
  rows.push([avg, p, r, reach]);
}
rows.sort((a,b)=>b[0]-a[0]);
for (const [avg,p,r,reach] of rows) console.log(p.padEnd(30), r.map(x=>x.toFixed(2)).join(' '), ' avg', avg.toFixed(2), ' reach', reach, ' ', [...F.features(p)].join(','));
