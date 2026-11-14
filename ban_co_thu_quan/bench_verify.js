const OLD = require('./random_setup_ef.js'); const NEW = require('./verify_fast.js');
const N = Number(process.argv[2] || 400);
const props = []; for (let i = 0; i < N; i++) props.push(OLD.propose());
let t = Date.now(); let c1o = 0, c2o = 0, tC1 = 0, tC2 = 0; const resOld = [];
for (const b of props) { const a = Date.now(); const r1 = OLD.cond1(b); tC1 += Date.now() - a; let r2 = false; if (r1) { c1o++; const a2 = Date.now(); r2 = OLD.cond2(b); tC2 += Date.now() - a2; if (r2) c2o++; } resOld.push(r1 && r2); }
const tOld = Date.now() - t;
t = Date.now(); const resNew = []; for (const b of props) resNew.push(NEW.cond1(b) && NEW.cond2(b)); const tNew = Date.now() - t;
const diff = resOld.filter((x, i) => x !== resNew[i]).length;
console.log(`${N} thế đề xuất: qua đk1 ${c1o}, qua cả hai ${c2o}`);
console.log(`cách cũ: ${tOld} ms (đk1 ${tC1} ms, đk2 ${tC2} ms) | cách mới: ${tNew} ms | khác kết quả: ${diff}`);
