"""tu_quet.py -- cây nhỏ trên máy Colab cho cách cây trò chơi: khi hết việc mà còn ngân sách (chắc chắn ở đời 0, khi
cây trên điện thoại còn trống), máy tự quét các ván do chính nó chơi trong lần chạy này rồi rẽ tiếp, như 6.2 và 12.6
(bước 5) của THIET_KE_CO_VUA.md. Mỗi node được quét đúng một lần, bốc một nước theo (số lượt thăm)^(1/T), T = 0.5;
nước chưa ai chơi ở node đó thành một điểm rẽ. Danh sách điểm rẽ của mỗi lượt quét được xếp bằng cách bốc không lặp
theo m = số ván (của máy này) đã đi qua node, như cay.py trên điện thoại (6.3, sửa 11/11).

Đọc bản ghi treeplay dần dần từ van.bin (engine ghi trọn từng bản ghi khi một việc xong).
"""
import random
import struct

import numpy as np

MAGIC = b"CVG1"
_DAU = struct.Struct("<4sIQBbBBHH")
_LAN = struct.Struct("<HHIfffff")
_NUOC = 12          # u16 nước, u16 n, f16 q, f16 d, f16 prior nhiễu, f16 prior thô


def sang_uci(m):
    tu, den = (m >> 6) & 63, m & 63
    if (m >> 12) & 7 == 1:
        den = (tu & ~7) | (6 if (den & 7) > (tu & 7) else 2)
    s = "abcdefgh"[tu & 7] + str(tu // 8 + 1) + "abcdefgh"[den & 7] + str(den // 8 + 1)
    if m & 0x4000:
        s += "nqrb"[(m >> 12) & 3]
    return s


class CayCucBo:
    def __init__(self, T=0.5, seed=None):
        self.T = T
        self.rng = random.Random(seed)
        self.cha, self.nuoc = [-1], [0]
        self.tham = [None]          # (mảng nước, mảng n) của lần search đầu tại node
        self.con = {}               # (cha, nuoc) -> node
        self.da_quet = [False]
        self.het = [False]
        self.m = [0]                # số ván G của máy này đã đi qua node
        self.so_lan_g = 0           # số lần search trong các việc G đã xong
        self.so_viec_g = 0
        self.so_lan_s = 0           # số lần search của các việc search lại (S) đã xong
        self._du = b""
        self._vi_tri = 0

    def _node(self, cha, m):
        k = (cha, m)
        c = self.con.get(k)
        if c is None or c < 0:           # -1 = chỗ giữ của một điểm rẽ đã giao
            c = len(self.cha)
            self.cha.append(cha); self.nuoc.append(m); self.tham.append(None)
            self.da_quet.append(False); self.het.append(False); self.m.append(0)
            self.con[k] = c
        return c

    def doc_them(self, duong_dan):
        """Đọc các bản ghi mới của van.bin; gộp bản ghi G vào cây nhỏ. Trả về số bản ghi mới."""
        try:
            with open(duong_dan, "rb") as f:
                f.seek(self._vi_tri)
                them = f.read()
        except OSError:                      # engine chưa tạo tệp
            return 0
        self._vi_tri += len(them)
        b = self._du + them
        i, so = 0, 0
        while i + _DAU.size <= len(b):
            magic, co, _id, loai, _kq, _kt, _, so_dd, so_lan = _DAU.unpack_from(b, i)
            if magic != MAGIC:
                raise ValueError("sai magic")
            if i + co > len(b):
                break
            j = i + _DAU.size
            dd = struct.unpack_from(f"<{so_dd}H", b, j)
            j += 2 * so_dd
            so += 1
            if loai == 0:
                s = 0
                self.m[0] += 1
                for m in dd:
                    s = self._node(s, m)
                    self.m[s] += 1
                for _ in range(so_lan):
                    nuoc, so_tham, *_r = _LAN.unpack_from(b, j)
                    j += _LAN.size
                    x = np.frombuffer(b, np.uint16, so_tham * 6, j).reshape(so_tham, 6)
                    j += _NUOC * so_tham
                    if self.tham[s] is None:
                        self.tham[s] = (x[:, 0].copy(), x[:, 1].astype(np.float64))
                    s = self._node(s, nuoc)
                    self.m[s] += 1
                self.het[s] = True
                self.so_lan_g += so_lan
                self.so_viec_g += 1
            elif loai == 1:
                self.so_lan_s += so_lan
            i += co
        self._du = b[i:]
        return so

    def duong(self, s):
        ra = []
        while self.cha[s] >= 0:
            ra.append(self.nuoc[s])
            s = self.cha[s]
        return ra[::-1]

    def quet(self):
        """Quét các node chưa quét; trả về danh sách đường đi (danh sách nước UCI) của các ván rẽ, đã xáo trộn."""
        ra, khoa = [], []
        for s in range(len(self.cha)):
            if self.da_quet[s] or self.tham[s] is None or self.het[s]:
                continue
            self.da_quet[s] = True
            mv, n = self.tham[s]
            w = n ** (1 / self.T)
            if w.sum() <= 0:
                continue
            m = int(mv[np.searchsorted(np.cumsum(w), self.rng.random() * w.sum(), side="right").clip(0, len(mv) - 1)])
            if (s, m) not in self.con:
                ra.append([sang_uci(x) for x in self.duong(s) + [m]])
                khoa.append(self.rng.expovariate(1.0) / max(self.m[s], 1))
                self.con[(s, m)] = -1        # giữ chỗ: không rẽ lại cùng nước ở node này trong lần chạy
        return [ra[i] for i in sorted(range(len(ra)), key=khoa.__getitem__)]
