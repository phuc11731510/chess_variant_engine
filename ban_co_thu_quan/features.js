// Đếm các kiểu cú pháp một quân dùng (theo cách đếm của người dùng)
function features(str) {
  const f = new Set();
  // bỏ phần trong ngoặc [cj...] (số và chữ trong ngoặc không tính), nhưng ghi nhận cj
  let s = str.replace(/\[cj(mc|m|c)?\d*\]/g, () => { f.add('cj'); return '#'; });
  s = s.replace(/n\[[oda]\]/g, 'n');
  if (s.includes('t[')) f.add('t');
  s = s.replace(/t\[|\]/g, ' ');
  for (const ch of 'WFDAHGNCZ') if (s.includes(ch)) f.add(ch);
  if (/([WFDAHGNCZ])\1/.test(s)) f.add('rider');
  if (/[WFDAHGNCZ)]\d/.test(s)) f.add('num');
  for (const ch of 'mcfbsvlrpgi') if (s.includes(ch)) f.add(ch);
  if (s.includes('n')) f.add('n');
  return f;
}
const ORDER = ['W','F','D','A','H','G','N','C','Z','rider','num','m','c','f','b','s','v','l','r','n','p','g','i','t','cj'];
const RULE = { W:[6],F:[6],H:[2],G:[2],C:[2],Z:[2],rider:[4,6],p:[2],g:[2],i:[0],t:[2],cj:[2],
  N:[2,4],A:[2,4],D:[2,4], num:[2,4,6], m:[2,4,6], c:[2,4,6], f:[2,4,6], b:[2,4,6], s:[2,4,6], v:[2,4,6], l:[2,4,6], r:[2,4,6], n:[2,4,6] };
function tally(list) {
  const cnt = Object.fromEntries(ORDER.map(k => [k, 0]));
  for (const p of list) for (const k of features(p)) cnt[k]++;
  const bad = ORDER.filter(k => !RULE[k].includes(cnt[k]));
  return { cnt, bad };
}
module.exports = { features, tally, ORDER, RULE };
