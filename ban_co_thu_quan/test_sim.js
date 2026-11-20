const S = require('./betza_sim.js');
const fmt = a => a.map(v => '(' + v + ')').join(' ');
for (const [c, at] of [['fs',[0,1]],['fs',[1,1]],['fs',[1,2]],['sf',[1,2]],['fb',[1,2]],['vv',[1,2]],['lf',[1,1]],['llff',[1,1]],['llff',[1,2]],['lf',[1,2]],['fr',[1,2]],['bl',[1,2]],['rb',[1,2]]])
  console.log(c, at, fmt(S.filterDirs(c, S.baseVectors(...at))));
for (const v of [[2,1],[3,1],[3,2],[4,1],[4,3],[1,2]]) console.log('n', v, JSON.stringify(S.nPaths('o',...v)), JSON.stringify(S.nPaths('d',...v)), S.nPaths('a',...v).length);
// empty board queen at d4 (3,3)
const b = new Int8Array(100); b[33]=1;
console.log('Q empty d4', S.genMoves(b, S.parse('WWFF'), 3, 3).length, 'expect', 9+9+ (3+6)+ (3+6)); 
console.log('Gryphon t[FWW] empty d4', S.genMoves(b, S.parse('t[FWW]'), 3, 3).length);
