"""Tình trạng dự án cờ vua (lệnh `cvt xem` / `cvc xem`): đời hiện tại, ngân sách, máy đang chạy, log gần nhất.

    python xem.py <GOC>
"""
import glob
import json
import os
import sys
import time


def main():
    goc = sys.argv[1]
    p = lambda *a: os.path.join(goc, *a)
    try:
        ch = json.load(open(p("cau_hinh.json")))
    except OSError:
        print("Chưa có cau_hinh.json (chưa chạy lần nào)."); return
    try:
        G = int(open(p("trang_thai", "doi_hien_tai.txt")).read())
    except OSError:
        G = 0
    lan_thu = [json.load(open(f)) for f in glob.glob(p("van", "doi*", "*.json"))]
    da_thu = sum(j.get("evals", 0) for j in lan_thu)
    truoc = sum(j.get("evals", 0) for j in lan_thu if j.get("doi", 0) < G)
    song = []
    for f in glob.glob(p("trang_thai", "song_*.json")):
        try:
            s = json.load(open(f))
        except (OSError, ValueError):
            continue
        s["cua_so"] = os.path.basename(f)[5:-5]
        s["cu"] = time.time() - s.get("cap_nhat", 0)
        song.append(s)
    dang = sum(s["evals"] for s in song if s["cu"] < 600)
    # Cùng quy tắc với truyen_thong.py (muc_tieu): cộng dồn, nhưng mỗi đời tự sinh ít nhất nửa ngân sách.
    muc = max(ch["ngan_sach_moi_doi"] * (G + 1), truoc + ch["ngan_sach_moi_doi"] // 2)
    print(f"Đời hiện tại: {G}   (mạng có sẵn: {sorted(int(os.path.basename(f)[3:-6]) for f in glob.glob(p('mang', 'doi*.pb.gz')))})")
    print(f"Lần chạy mạng cộng dồn: {da_thu + dang:,} / mục tiêu đời {G}: {muc:,} ({100 * (da_thu + dang) / muc:.1f}%)")
    if os.path.exists(p("trang_thai", "dung")):
        print("CÓ LỆNH DỪNG MỀM (cvt dung).")
    for s in song:
        print(f"  máy đang sinh: cửa sổ {s['cua_so']}, đời {s['doi']}, lần {s['lan']}: {s['evals']:,} lần chạy mạng, "
              f"{s.get('van_xong', 0)} ván xong, cập nhật {s['cu']:.0f} giây trước")
    for k in sorted(glob.glob(p("trang_thai", "khoa_*"))):
        try:
            c = json.load(open(os.path.join(k, "chu.json")))
            print(f"  khoá {os.path.basename(k)[5:]}: cửa sổ {c['cua_so']}, nhịp {time.time() - c['nhip']:.0f} giây trước")
        except (OSError, ValueError):
            print(f"  khoá {os.path.basename(k)[5:]}")
    tt = sorted(glob.glob(p("tom_tat", "doi*.json")), key=lambda f: int(os.path.basename(f)[3:-5]))
    for f in tt[-3:]:
        t = json.load(open(f))
        hl = t.get("huan_luyen", {})
        print(f"  đời {t['doi']}: {t['van_doi']} ván, {t['evals_doi']:,} lần chạy mạng, huấn luyện {hl.get('so_buoc')} bước "
              f"(mất mát policy {hl.get('mat_policy_hoc', 0):.3f}, value {hl.get('mat_value_hoc', 0):.3f}), xong {t['xong_luc']}")
    for f in sorted(glob.glob(p("log", "dieu_phoi_*.log"))):
        dong = open(f, encoding="utf-8", errors="replace").read().splitlines()[-4:]
        print(f"--- {os.path.basename(f)}")
        for d in dong:
            print("   " + d)


if __name__ == "__main__":
    main()
