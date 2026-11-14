const S = require('./betza_sim.js');
const list = process.argv.slice(2);
const Q = [0.6,0.4,0.2].map(d => S.mobility('WWFF', d, 6000).score);
console.log('Q', Q.map(x=>x.toFixed(2)).join(' '));
for (const p of list) {
  const r = [0.6,0.4,0.2].map(d => S.mobility(p, d, 6000).score);
  console.log(p.padEnd(28), r.map((x,i)=>(x/Q[i]).toFixed(3)).join('  '), '  raw', r.map(x=>x.toFixed(2)).join(' '));
}
