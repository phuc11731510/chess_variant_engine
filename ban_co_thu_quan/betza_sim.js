// Trình mô phỏng ký hiệu Betza theo quy ước trong fairy_chess_betza.md
// (chữ hướng mục 4.1, [cj] mục 5.2, p/g mục 5.7, t[A B] mục 6, n / n[σ] / !n mục 7).
// Hệ tọa độ: quân ở (x,y), y tăng theo hướng tiến của quân, x tăng về bên phải.
'use strict';

const SIZE = 10;
const EMPTY = 0, FRIEND = 1, ENEMY = 2;

const ATOMS = {
  W: [0, 1], F: [1, 1], D: [0, 2], A: [2, 2], H: [0, 3], G: [3, 3],
  N: [1, 2], C: [1, 3], Z: [2, 3],
};

function baseVectors(a, b) {
  const set = new Map();
  for (const [x, y] of [[a, b], [b, a]])
    for (const sx of [1, -1]) for (const sy of [1, -1]) {
      const v = [x * sx, y * sy];
      set.set(v.join(','), v);
    }
  return [...set.values()];
}

// ---------- chữ hướng (mục 4.1) ----------
const WIDE = {
  f: ([x, y]) => y > 0, b: ([x, y]) => y < 0, l: ([x, y]) => x < 0, r: ([x, y]) => x > 0,
  s: ([x, y]) => x !== 0, v: ([x, y]) => y !== 0,
};
const NARROW = {
  f: ([x, y]) => y >= Math.abs(x), b: ([x, y]) => -y >= Math.abs(x),
  l: ([x, y]) => -x >= Math.abs(y), r: ([x, y]) => x >= Math.abs(y),
  s: ([x, y]) => Math.abs(x) >= Math.abs(y), v: ([x, y]) => Math.abs(y) >= Math.abs(x),
};
function filterDirs(cluster, vecs) {
  if (!cluster) return vecs;
  const c = cluster;
  if (c.length === 1) return vecs.filter(WIDE[c]);
  if (c.length === 2 && c[0] === c[1]) return vecs.filter(NARROW[c[0]]);
  if (c.length === 2) {
    const inter = vecs.filter(v => WIDE[c[0]](v) && NARROW[c[1]](v));
    if (inter.length) return inter;
    return vecs.filter(v => WIDE[c[0]](v) || NARROW[c[1]](v));
  }
  if (c.length === 4 && c[0] === c[1] && c[2] === c[3] && c[0] !== c[2])
    return vecs.filter(v => NARROW[c[0]](v) || NARROW[c[2]](v));
  throw new Error('Cụm chữ hướng không hợp lệ: ' + c);
}

// ---------- đường đi của n (mục 7.1, 7.5) ----------
const pathCache = new Map();
function inStrip(x, y, a, b) {
  const d = x * a + y * b;
  const e = x * b - y * a;
  return d >= 0 && d <= a * a + b * b && 4 * e * e <= a * a + b * b;
}
const KING = [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [1, -1], [-1, 1], [-1, -1]];
function stripPath(a, b, preferStraight) {
  const k = Math.max(Math.abs(a), Math.abs(b));
  // dist[x,y] = số nước Vua tối thiểu trong dải tới B
  const key = (x, y) => x + ',' + y;
  const dist = new Map();
  dist.set(key(a, b), 0);
  let frontier = [[a, b]];
  while (frontier.length) {
    const nxt = [];
    for (const [x, y] of frontier) for (const [dx, dy] of KING) {
      const nx = x + dx, ny = y + dy;
      if (!inStrip(nx, ny, a, b) || dist.has(key(nx, ny))) continue;
      dist.set(key(nx, ny), dist.get(key(x, y)) + 1);
      nxt.push([nx, ny]);
    }
    frontier = nxt;
  }
  if (dist.get(key(0, 0)) !== k) throw new Error('strip path length mismatch ' + a + ',' + b);
  const path = [];
  let [x, y] = [0, 0];
  for (let i = 0; i < k - 1; i++) {
    const cands = KING.map(([dx, dy]) => [x + dx, y + dy, dx, dy])
      .filter(([nx, ny]) => inStrip(nx, ny, a, b) && dist.get(key(nx, ny)) === k - i - 1);
    const straight = cands.filter(c => c[2] === 0 || c[3] === 0);
    const diag = cands.filter(c => c[2] !== 0 && c[3] !== 0);
    let pick = preferStraight ? (straight[0] || diag[0]) : (diag[0] || straight[0]);
    const same = preferStraight ? (straight.length ? straight : diag) : (diag.length ? diag : straight);
    if (same.length > 1) throw new Error('path not unique');
    [x, y] = pick;
    path.push([x, y]);
  }
  return [path];
}
function allMonotonePaths(a, b) {
  const k = Math.max(Math.abs(a), Math.abs(b));
  const sa = Math.sign(a), sb = Math.sign(b);
  const res = [];
  function rec(x, y, steps, acc) {
    if (steps === k) { if (x === a && y === b) res.push(acc.slice(0, -1)); return; }
    for (const [dx, dy] of KING) {
      if (dx * sa < 0 || dy * sb < 0) continue;
      if (a === 0 && dx !== 0) continue;
      if (b === 0 && dy !== 0) continue;
      const nx = x + dx, ny = y + dy;
      const rem = k - steps - 1;
      if (Math.max(Math.abs(a - nx), Math.abs(b - ny)) > rem) continue;
      acc.push([nx, ny]);
      rec(nx, ny, steps + 1, acc);
      acc.pop();
    }
  }
  rec(0, 0, 0, []);
  return res;
}
function nPaths(sel, a, b) {
  const key = sel + ':' + a + ',' + b;
  if (pathCache.has(key)) return pathCache.get(key);
  let r;
  if (sel === 'o') r = stripPath(a, b, true);
  else if (sel === 'd') r = stripPath(a, b, false);
  else if (sel === 'a') r = allMonotonePaths(a, b);
  else throw new Error('bad selector ' + sel);
  pathCache.set(key, r);
  return r;
}

// ---------- parser ----------
// component: { kind: 'step'|'hop'|'cj'|'t', ... }
function parseAtomSpec(str, i) {
  // returns {vecs (base), rider:boolean, limit:number|null, len}
  let a, b, j = i;
  if (str[j] === '(') {
    const close = str.indexOf(')', j);
    [a, b] = str.slice(j + 1, close).split(',').map(Number);
    j = close + 1;
  } else if (str[j] === 'K') {
    [a, b] = [0, 0];
    j++;
    return { a, b, king: true, rider: false, limit: null, len: j - i };
  } else if (ATOMS[str[j]]) {
    [a, b] = ATOMS[str[j]];
    j++;
  } else throw new Error('Atom lạ tại ' + j + ' trong ' + str);
  let rider = false, limit = null;
  if (str[j] === str[i] && str[i] !== '(') { rider = true; j++; }
  const m = /^\d+/.exec(str.slice(j));
  if (m) { limit = Number(m[0]); j += m[0].length; }
  return { a, b, rider, limit, len: j - i };
}

function parsePrefixed(str, i, ctx) {
  // đọc modifier + atom, trả về component
  let j = i;
  let modality = null, cluster = '', hop = null, n = null, negN = false, initial = false;
  while (j < str.length) {
    const ch = str[j];
    if (ch === 'm' || ch === 'c') {
      if (modality === 'c' && ch === 'm') throw new Error('cm');
      modality = modality ? modality + ch : ch; j++;
    } else if ('fbslrv'.includes(ch)) { cluster += ch; j++; }
    else if (ch === 'p' || ch === 'g') { hop = ch; j++; }
    else if (ch === 'i') { initial = true; j++; }
    else if (ch === '!' && str[j + 1] === 'n') { negN = true; j++; }
    else if (ch === 'n') {
      j++;
      if (str[j] === '[') { n = str[j + 1]; j += 3; } else n = 'o';
    } else break;
  }
  const at = parseAtomSpec(str, j);
  j += at.len;
  const base = at.king ? baseVectors(0, 1).concat(baseVectors(1, 1)) : baseVectors(Math.abs(at.a), Math.abs(at.b));
  const vecs = filterDirs(cluster, base);
  const amax = at.limit !== null ? at.limit : (at.rider ? Infinity : 1);
  return {
    comp: { kind: hop ? 'hop' : 'step', hop, modality: modality || 'mc', cluster, vecs, amax, n, negN, initial, atom: at },
    len: j - i,
  };
}

function parse(str) {
  const comps = [];
  let i = 0;
  while (i < str.length) {
    if (str.startsWith('t[', i)) {
      const close = matchBracket(str, i + 1);
      const inner = str.slice(i + 2, close);
      const A = parsePrefixed(inner, 0);
      const B = parsePrefixed(inner, A.len);
      if (A.len + B.len !== inner.length) throw new Error('t[...] thừa ký tự: ' + inner);
      comps.push({ kind: 't', A: A.comp, B: B.comp });
      i = close + 1;
    } else if (str.startsWith('[cj', i)) {
      const close = str.indexOf(']', i);
      const inner = str.slice(i + 3, close);
      const mm = /^(mc|m|c)?(\d+)?$/.exec(inner);
      if (!mm) throw new Error('[cj] lạ: ' + inner);
      const Y = parsePrefixed(str, close + 1);
      const c = Y.comp;
      c.kind = 'cj';
      c.landing = mm[1] || 'm';
      c.bmax = mm[2] ? Number(mm[2]) : c.amax;
      comps.push(c);
      i = close + 1 + Y.len;
    } else {
      const P = parsePrefixed(str, i);
      comps.push(P.comp);
      i += P.len;
    }
  }
  return comps;
}
function matchBracket(str, open) {
  let d = 0;
  for (let k = open; k < str.length; k++) {
    if (str[k] === '[') d++;
    else if (str[k] === ']') { d--; if (d === 0) return k; }
  }
  throw new Error('unbalanced');
}

// ---------- sinh nước đi ----------
// board: Int8Array(100), index = y*10+x ; side: +1 trắng, -1 đen (đen = xoay 180°, vì x tăng về bên phải của chính quân)
function onBoard(x, y) { return x >= 0 && x < SIZE && y >= 0 && y < SIZE; }

function nOk(board, comp, x, y, v, side) {
  // bước từ (x,y) theo vector v (hệ quân), kiểm tra ô giữa theo n
  if (!comp.n && !comp.negN) return true;
  const sel = comp.n || 'o';
  const paths = nPaths(sel, v[0], v[1]);
  let anyClear = false;
  for (const p of paths) {
    let clear = true;
    for (const [px, py] of p) {
      const X = x + px * side, Y = y + py * side;
      if (!onBoard(X, Y) || board[Y * SIZE + X] !== EMPTY) { clear = false; break; }
    }
    if (clear) { anyClear = true; break; }
  }
  return comp.negN ? !anyClear : anyClear;
}

function genComp(board, comp, sx, sy, side, out) {
  const at = (x, y) => board[y * SIZE + x];
  if (comp.kind === 'step') {
    for (const v of comp.vecs) {
      let x = sx, y = sy;
      for (let k = 1; k <= comp.amax; k++) {
        if (!nOk(board, comp, x, y, v, side)) break;
        x += v[0] * side; y += v[1] * side;
        if (!onBoard(x, y)) break;
        const o = at(x, y);
        if (o === EMPTY) { if (comp.modality.includes('m')) out.push([x, y, -1]); continue; }
        if (o === ENEMY && comp.modality.includes('c')) out.push([x, y, y * SIZE + x]);
        break;
      }
    }
  } else if (comp.kind === 'hop') {
    const bmax = comp.amax;
    for (const v of comp.vecs) {
      let x = sx, y = sy, found = false;
      for (let k = 1; k <= comp.amax; k++) {
        if (!nOk(board, comp, x, y, v, side)) break;
        x += v[0] * side; y += v[1] * side;
        if (!onBoard(x, y)) break;
        if (at(x, y) !== EMPTY) { found = true; break; }
      }
      if (!found) continue;
      const blim = comp.hop === 'g' ? 1 : bmax;
      for (let b = 1; b <= blim; b++) {
        if (!nOk(board, comp, x, y, v, side)) break;
        x += v[0] * side; y += v[1] * side;
        if (!onBoard(x, y)) break;
        const o = at(x, y);
        if (o === EMPTY) { if (comp.modality.includes('m')) out.push([x, y, -1]); continue; }
        if (o === ENEMY && comp.modality.includes('c')) out.push([x, y, y * SIZE + x]);
        break;
      }
    }
  } else if (comp.kind === 'cj') {
    for (const v of comp.vecs) {
      let x = sx, y = sy, found = false;
      for (let k = 1; k <= comp.amax; k++) {
        if (!nOk(board, comp, x, y, v, side)) break;
        x += v[0] * side; y += v[1] * side;
        if (!onBoard(x, y)) break;
        if (at(x, y) !== EMPTY) { found = at(x, y) === ENEMY; break; }
      }
      if (!found) continue;
      const h = y * SIZE + x;
      for (let b = 1; b <= comp.bmax; b++) {
        if (!nOk(board, comp, x, y, v, side)) break;
        x += v[0] * side; y += v[1] * side;
        if (!onBoard(x, y)) break;
        const o = at(x, y);
        if (o === EMPTY) { if (comp.landing.includes('m')) out.push([x, y, h]); continue; }
        if (o === ENEMY && comp.landing.includes('c')) out.push([x, y, h, y * SIZE + x]);
        break;
      }
    }
  } else if (comp.kind === 't') {
    const A = comp.A, B = comp.B;
    for (const u of A.vecs) {
      if (!nOk(board, A, sx, sy, u, side)) continue;
      const px = sx + u[0] * side, py = sy + u[1] * side;
      if (!onBoard(px, py)) continue;
      const o = at(px, py);
      if (o === FRIEND) continue;
      if (o === ENEMY) { out.push([px, py, py * SIZE + px]); continue; }
      out.push([px, py, -1]);
      const dirs = B.cluster ? B.vecs : B.vecs.filter(d => u[0] * d[0] + u[1] * d[1] > 0);
      for (const d of dirs) {
        let x = px, y = py;
        for (let k = 1; k <= B.amax; k++) {
          if (!nOk(board, B, x, y, d, side)) break;
          x += d[0] * side; y += d[1] * side;
          if (!onBoard(x, y)) break;
          const q = at(x, y);
          if (q === EMPTY) { if (B.modality.includes('m')) out.push([x, y, -1]); continue; }
          if (q === ENEMY && B.modality.includes('c')) out.push([x, y, y * SIZE + x]);
          break;
        }
      }
    }
  }
}

function genMoves(board, comps, sx, sy, side = 1, moved = false) {
  const raw = [];
  for (const c of comps) { if (c.initial && moved) continue; genComp(board, c, sx, sy, side, raw); }
  // gộp nước trùng (cùng ô đến, cùng tập quân bị bắt)
  const seen = new Map();
  for (const m of raw) {
    const caps = m.slice(2).filter(z => z >= 0).sort((a, b) => a - b);
    const key = (m[1] * SIZE + m[0]) + '|' + caps.join(',');
    if (!seen.has(key)) seen.set(key, { to: m[1] * SIZE + m[0], caps });
  }
  return [...seen.values()];
}

// ---------- mô phỏng độ cơ động ----------
function rng(seed) {
  let s = seed >>> 0;
  return () => { s = (s + 0x6D2B79F5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
function randomBoard(rand, density, pieceSq) {
  const total = Math.round(density * SIZE * SIZE);
  const others = total - 1;
  const friends = Math.floor(total / 2) - 1, enemies = others - friends;
  const sq = [];
  for (let i = 0; i < SIZE * SIZE; i++) if (i !== pieceSq) sq.push(i);
  for (let i = sq.length - 1; i > 0; i--) { const j = Math.floor(rand() * (i + 1)); [sq[i], sq[j]] = [sq[j], sq[i]]; }
  const board = new Int8Array(SIZE * SIZE);
  board[pieceSq] = FRIEND;
  for (let i = 0; i < friends; i++) board[sq[i]] = FRIEND;
  for (let i = friends; i < friends + enemies; i++) board[sq[i]] = ENEMY;
  return board;
}
function mobility(betza, density, trials = 20000, seed = 1) {
  const comps = parse(betza);
  const rand = rng(seed);
  let tot = 0, quiet = 0, caps = 0;
  for (let t = 0; t < trials; t++) {
    const s = t % (SIZE * SIZE);
    const board = randomBoard(rand, density, s);
    const mv = genMoves(board, comps, s % SIZE, Math.floor(s / SIZE));
    for (const m of mv) { if (m.caps.length) { tot += 2; caps++; } else { tot += 1; quiet++; } }
  }
  return { score: tot / trials, quiet: quiet / trials, caps: caps / trials };
}

// ---------- kiểm tra ràng buộc bắt quân ----------
function checkCaptureRule(betza, trials = 4000, seed = 7) {
  const comps = parse(betza);
  const rand = rng(seed);
  const problems = [];
  let checked = 0;
  for (let t = 0; t < trials; t++) {
    const density = [0.02, 0.05, 0.1, 0.2, 0.3, 0.45, 0.6][t % 7];
    const s = Math.floor(rand() * 100);
    const board = randomBoard(rand, density, s);
    const sx = s % SIZE, sy = Math.floor(s / SIZE);
    const mv = genMoves(board, comps, sx, sy);
    const capturable = new Set();
    for (const m of mv) {
      if (m.caps.length > 1) problems.push({ type: 'multi', board: [...board], s, m });
      for (const c of m.caps) capturable.add(c);
    }
    for (const X of capturable) {
      const hx = X % SIZE, hy = Math.floor(X / SIZE);
      if (Math.max(Math.abs(hx - sx), Math.abs(hy - sy)) < 4) continue;
      checked++;
      let good = 0;
      for (let e = 0; e < 100 && good < 2; e++) {
        if (board[e] !== EMPTY) continue;
        if (Math.max(Math.abs(e % SIZE - hx), Math.abs(Math.floor(e / SIZE) - hy)) > 3) continue; // vùng 7x7 quanh X
        board[e] = ENEMY;
        const mv2 = genMoves(board, comps, sx, sy);
        board[e] = EMPTY;
        if (!mv2.some(m => m.caps.includes(X))) good++;
      }
      if (good < 2) { problems.push({ type: 'far', s, X, good }); if (problems.length > 3) return { checked, problems }; }
    }
  }
  return { checked, problems };
}

// ---------- kiểm tra chạm mọi ô ----------
function reachability(betza) {
  // nước đi hình học: cho phép mọi tình huống thuận lợi.
  // Với mỗi ô s, xét nhiều bàn cờ "thuận lợi": dò bằng cách thử tất cả cấu hình cục bộ là quá nhiều,
  // nên dùng cách sinh trực tiếp: bàn trống (nước thường) + bàn có quân địch/bạn ở các ô cần thiết.
  const comps = parse(betza);
  const adj = [];
  for (let s = 0; s < 100; s++) {
    const sx = s % SIZE, sy = Math.floor(s / SIZE);
    const dest = new Set();
    for (const c of comps) for (const d of geomDests(c, sx, sy)) dest.add(d);
    adj.push([...dest]);
  }
  let worst = 100;
  for (let s = 0; s < 100; s++) {
    const seen = new Set([s]); const q = [s];
    while (q.length) { const u = q.pop(); for (const w of adj[u]) if (!seen.has(w)) { seen.add(w); q.push(w); } }
    worst = Math.min(worst, seen.size);
  }
  return worst;
}
function geomDests(comp, sx, sy) {
  // ô đến có thể đạt được trong một tình huống phù hợp (đường n trống, hurdle tồn tại...)
  const out = [];
  const ok = (x, y) => onBoard(x, y);
  const pathOnBoard = (c, x, y, v) => {
    if (!c.n && !c.negN) return true;
    // với !n cần ít nhất một ô giữa trên bàn (để đặt vật cản); với n cần đường trên bàn
    const paths = nPaths(c.n || 'o', v[0], v[1]);
    if (c.negN) return paths.every(p => p.some(([px, py]) => ok(x + px, y + py))) && paths.length > 0 && paths[0].length > 0;
    return paths.some(p => p.every(([px, py]) => ok(x + px, y + py)));
  };
  if (comp.kind === 'step') {
    for (const v of comp.vecs) {
      let x = sx, y = sy;
      for (let k = 1; k <= Math.min(comp.amax, 12); k++) {
        if (!pathOnBoard(comp, x, y, v)) break;
        x += v[0]; y += v[1]; if (!ok(x, y)) break; out.push(y * SIZE + x);
      }
    }
  } else if (comp.kind === 'hop' || comp.kind === 'cj') {
    const bmax = comp.kind === 'cj' ? comp.bmax : (comp.hop === 'g' ? 1 : comp.amax);
    for (const v of comp.vecs) for (let a = 1; a <= Math.min(comp.amax, 12); a++) {
      let hx = sx + a * v[0], hy = sy + a * v[1]; if (!ok(hx, hy)) break;
      for (let b = 1; b <= Math.min(bmax, 12); b++) {
        const lx = hx + b * v[0], ly = hy + b * v[1]; if (!ok(lx, ly)) break; out.push(ly * SIZE + lx);
      }
    }
  } else if (comp.kind === 't') {
    for (const u of comp.A.vecs) {
      const px = sx + u[0], py = sy + u[1]; if (!ok(px, py)) continue; out.push(py * SIZE + px);
      const dirs = comp.B.cluster ? comp.B.vecs : comp.B.vecs.filter(d => u[0] * d[0] + u[1] * d[1] > 0);
      for (const d of dirs) { let x = px, y = py; for (let k = 1; k <= Math.min(comp.B.amax, 12); k++) { x += d[0]; y += d[1]; if (!ok(x, y)) break; out.push(y * SIZE + x); } }
    }
  }
  return out;
}

module.exports = { parse, genMoves, mobility, checkCaptureRule, reachability, filterDirs, baseVectors, randomBoard, rng, nPaths };
