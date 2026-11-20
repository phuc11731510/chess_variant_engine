"""Bộ sinh thế cờ khởi đầu (sinh_the_khoi_dau.py): hai bảng khớp bộ kiểm hai nước, số cách xếp, thế sinh ra đạt tiêu chí
cho cả hai bên. Chạy: python test_sinh_the_khoi_dau.py  (khoảng 40 giây, phần lớn là tính lại hai bảng)."""
import random

import luat_py as orc
import sinh_the_khoi_dau as g


def test_hai_bang_khop_bo_kiem():
    cam, cap = g.tinh_bang()
    assert cam == {s: set(g.CAM_DON[s]) for s in g.FREE_SQ}
    assert cap == g.CAP_VI_PHAM


def test_so_cach_xep():
    assert g.so_cach_xep() == 3345753600


def test_bang_dung_voi_bo_kiem_tren_mau_tuy_y():
    # xếp tuỳ ý (đa số vi phạm) và xếp theo miền đơn (còn cặp vi phạm): bảng và bộ kiểm trực tiếp phải trùng nhau
    rng = random.Random(3)
    n_bad = n_ok = 0
    for it in range(300):
        if it % 2:
            arr = g.POOL[:]
            rng.shuffle(arr)
        else:
            while True:
                free, asg, ok = list(g.FREE_SQ), {}, True
                for t in sorted(g.POOL, key=lambda t: (sum(1 for s in g.FREE_SQ if t not in g.CAM_DON[s]), rng.random())):
                    c = [s for s in free if t not in g.CAM_DON[s]]
                    if not c:
                        ok = False
                        break
                    s = rng.choice(c)
                    free.remove(s)
                    asg[s] = t
                if ok:
                    arr = [asg[s] for s in g.FREE_SQ]
                    break
        b = g.make_board(arr, arr)
        truc_tiep = g.vi_pham(b, orc.W)
        assert truc_tiep == (not g.hop_le_theo_bang(arr))
        n_bad += truc_tiep
        n_ok += not truc_tiep
    assert n_bad > 0 and n_ok > 0     # cả hai loại đều được thử


def test_mau_dat_tieu_chi_ca_hai_ben():
    rng = random.Random(4)
    for _ in range(200):
        fen, aw, ab = g.lay_the(rng)
        assert g.kiem_the(aw, ab)
        assert orc.from_fen(fen) == g.make_board(aw, ab)
    for _ in range(10):                                   # nước hợp lệ thật (Hoàng gia không đứng ở ô bị tấn công)
        _, aw, ab = g.lay_the(rng)
        assert g.kiem_the(aw, ab, hop_le=True)


def test_dung_bo_quan():
    rng = random.Random(5)
    for _ in range(100):
        arr = g.lay_mau(rng)
        assert sorted(arr) == sorted(g.POOL)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
