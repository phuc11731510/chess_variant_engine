// Ván thật: bên c đi nửa nước 1, bên kia đáp nửa nước 2, bên c đi nửa nước 3.
// Có tồn tại nước 1 sao cho với mọi nước đáp, bên c chiếu được (sau nửa nước 1 hoặc 3)?
// Nước đi phải hợp lệ: không được để quân hoàng gia của chính mình bị chiếu sau nước đi.
const S = require('./betza_sim.js'); const U = require('./setup.js');
const f = process.argv[2]; const setup = require('./' + f).setup;
const comps = { P: S.parse('mfWcfFimfnD'), T: S.parse('fKifmnDifmnA'), K: S.parse('WFmnDmnAmnN') };
const b = new Array(100).fill(null);
const put = (i, t) => { if (!comps[t]) comps[t] = S.parse(t); b[i] = { c: 'w', t, moved: false }; const x = i % 10, y = Math.floor(i / 10); b[(9 - y) * 10 + x] = { c: 'b', t, moved: false }; };
for (const [i, t] of Object.entries(U.FIXED)) put(+i, t);
for (const [sq, p] of Object.entries(setup)) put(U.idx(sq), p);
const gen = (bb, c) => { const a = new Int8Array(100); for (let i = 0; i < 100; i++) if (bb[i]) a[i] = bb[i].c === c ? 1 : 2; const o = [];
  for (let i = 0; i < 100; i++) { const p = bb[i]; if (!p || p.c !== c) continue; for (const m of S.genMoves(a, comps[p.t], i % 10, Math.floor(i / 10), c === 'w' ? 1 : -1, p.moved)) o.push({ from: i, to: m.to, caps: m.caps }); } return o; };
const opp = c => c === 'w' ? 'b' : 'w';
const attacked = (bb, c) => { const k = bb.findIndex(p => p && p.c === opp(c) && p.t === 'K'); return k >= 0 && gen(bb, c).some(m => m.caps.includes(k)); }; // c đang chiếu đối phương
const legal = (bb, c) => gen(bb, c).filter(m => !attacked(U.apply(bb, m), opp(c)));
const nm = (bb, m) => bb[m.from].t.replace(/\[.*?\]/g, '') + ' ' + U.nm(m.from) + '-' + U.nm(m.to);
function analyse(c) {
  const o = opp(c); const winners = [];
  let threats = 0;
  for (const m1 of legal(b, c)) {
    const b1 = U.apply(b, m1);
    if (attacked(b1, c)) { winners.push(nm(b, m1) + ' (chiếu ngay)'); continue; }
    let refuted = null;
    for (const r of legal(b1, o)) {
      const b2 = U.apply(b1, r);
      if (!legal(b2, c).some(m3 => attacked(U.apply(b2, m3), c))) { refuted = nm(b1, r); break; }
    }
    if (!refuted) winners.push(nm(b, m1));
    else if (legal(b1, c).some(m3 => attacked(U.apply(b1, m3), c))) { threats++; if (threats <= 4) console.log(`  ${c}: ${nm(b, m1)} dọa chiếu, Đen/Trắng chặn được bằng ${refuted}`); }
  }
  return { winners, threats };
}
for (const c of ['w', 'b']) { const r = analyse(c); console.log(f, c === 'w' ? 'Trắng đi trước' : 'Đen đi trước (giả định)', '| nước 1 ép được chiếu ở nửa nước 3:', r.winners.length ? r.winners.join('; ') : 'KHÔNG CÓ', '| số nước 1 có đe dọa chiếu nhưng bị chặn:', r.threats); }
