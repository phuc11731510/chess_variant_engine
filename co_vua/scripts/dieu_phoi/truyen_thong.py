"""Vòng lặp nhiều đời của cách truyền thống (mốc so sánh), chạy trên điện thoại (Termux) hoặc máy tính (WSL).

Mỗi cửa sổ Termux chạy một tiến trình này với một tài khoản Google; nhiều cửa sổ cùng làm một đời bằng cách
dùng chung thư mục gốc (GOC) và khoá thư mục (mkdir). Một đời G:
  1. Sinh ván: mỗi cửa sổ giữ một máy T4 chạy colab/sinh.py với mạng đời G. Bộ điều phối hỏi tiến độ mỗi
     phút; khi tổng số lần chạy mạng cộng dồn của mọi đời đạt ngan_sach_moi_doi * (G + 1) thì báo dừng mềm.
     Ván dở vẫn chơi nốt, nên ngân sách thường vượt một chút; phần vượt được trừ vào đời sau vì mốc là cộng dồn.
  2. Thu về: tải van.bin.gz và mọi log về GOC. Không xoá gì.
  3. Huấn luyện: một cửa sổ giữ khoá hl_doi<G>, tải các ván của cửa sổ 4 đời lên, chạy colab/huan_luyen_doi.sh,
     tải mạng đời G+1 về, ghi tom_tat/doi<G>.json, rồi chuyển sang đời G+1. Các cửa sổ khác trả máy và chờ.

Thư mục gốc (GOC):
  cau_hinh.json                    cấu hình (tạo mặc định nếu chưa có)
  goi.tar.gz                       gói chạy trên Colab (co_vua/scripts/dong_goi.py tạo)
  trang_thai/doi_hien_tai.txt      đời đang làm
  trang_thai/song_<cửa sổ>.json    tiến độ sống của lần sinh đang chạy (để cộng ngân sách)
  trang_thai/khoa_*/               khoá (thư mục), có tệp chu.json làm nhịp tim
  trang_thai/dung                  có tệp này = dừng mềm mọi cửa sổ (cv dung)
  mang/doi<G>.pt, doi<G>.pb.gz     mạng các đời
  van/doi<G>/<cửa sổ>_<lần>.bin.gz bản ghi ván (kèm .json: số lần chạy mạng, số ván, cấu hình)
  log/dieu_phoi_<cửa sổ>.log       log của bộ điều phối (chỉ ghi thêm)
  log/doi<G>/...                   log thô tải về từ Colab
  tom_tat/doi<G>.json              tóm tắt mỗi đời (máy đọc được)

Chạy:  python truyen_thong.py --goc <GOC> --tai-khoan <tên|chinh> [--ten-cua-so <tên>]
"""
import argparse
import glob
import json
import os
import random
import shutil
import signal
import socket
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from colab_may import May  # noqa: E402

MAC_DINH = {
    "ngan_sach_moi_doi": 80_000_000,   # số lần chạy mạng mỗi đời (khoảng 1000 ván 100 nửa nước, 800 lượt thăm)
    "so_doi": 1000,                    # dừng khi đạt đời này
    "cua_so_doi": 4,                   # số đời dữ liệu mỗi lần huấn luyện (như engine biến thể)
    "visits": 800,
    "temp_plies": 30,
    "max_ply": 450,
    "song_song": 128,                  # đo 2026-11-03 trên T4 (THIET_KE_CO_VUA.md 12.8)
    "luong_gom_lo": 1,
    "seed_doi0": 1,
    "gpu": "T4",
    "giay_hoi_tien_do": 60,
    "giay_tai_tam": 1200,              # tải bản ghi dở về mỗi chừng ấy giây (phòng mất máy)
}
CV = "/content/cv"


class DieuPhoi:
    def __init__(self, goc, tai_khoan, ten):
        self.goc, self.tk, self.ten = os.path.abspath(goc), tai_khoan, ten
        for d in ("trang_thai", "mang", "van", "log", "tom_tat"):
            os.makedirs(self.p(d), exist_ok=True)
        self.f_log = open(self.p("log", f"dieu_phoi_{ten}.log"), "a", buffering=1)
        if not os.path.exists(self.p("cau_hinh.json")):
            with open(self.p("cau_hinh.json"), "w") as f:
                json.dump(MAC_DINH, f, indent=1)
        self.ch = {**MAC_DINH, **json.load(open(self.p("cau_hinh.json")))}
        home = "~" if tai_khoan == "chinh" else f"~/.fz_tk/{tai_khoan}"
        self.may = May(f"cv_{ten}", home, self.log)
        self.co_may = False
        self.mang_tren_may = None
        self.khoa_giu = set()
        self.log(f"=== bat dau: cua so {ten}, tai khoan {tai_khoan}, may {socket.gethostname()}, "
                 f"cau hinh {json.dumps(self.ch, ensure_ascii=False)}")

    # --- tiện ích -----------------------------------------------------------------------------------
    def p(self, *phan):
        return os.path.join(self.goc, *phan)

    def log(self, s):
        dong = time.strftime("%Y-%m-%d %H:%M:%S ") + s
        self.f_log.write(dong + "\n")
        print(dong, flush=True)

    def ghi_json(self, duong_dan, du_lieu):
        tam = duong_dan + ".tam"
        with open(tam, "w") as f:
            json.dump(du_lieu, f, ensure_ascii=False, indent=1)
        os.replace(tam, duong_dan)

    def doi(self):
        try:
            return int(open(self.p("trang_thai", "doi_hien_tai.txt")).read())
        except OSError:
            return 0

    def dung_mem(self):
        return os.path.exists(self.p("trang_thai", "dung"))

    # --- khoá (thư mục) có nhịp tim -------------------------------------------------------------
    def lay_khoa(self, ten_khoa, het_han=1800):
        d = self.p("trang_thai", f"khoa_{ten_khoa}")
        try:
            os.mkdir(d)
        except FileExistsError:
            try:
                chu = json.load(open(os.path.join(d, "chu.json")))
                if chu.get("cua_so") == self.ten:
                    self.khoa_giu.add(ten_khoa)
                    return True
                if time.time() - chu.get("nhip", 0) < het_han:
                    return False
                self.log(f"pha khoa {ten_khoa} cu (cua so {chu.get('cua_so')}, im lang {time.time() - chu['nhip']:.0f} giay)")
            except (OSError, ValueError):
                if time.time() - os.path.getmtime(d) < 60:
                    return False
            shutil.rmtree(d, ignore_errors=True)
            try:
                os.mkdir(d)
            except FileExistsError:
                return False
        self.khoa_giu.add(ten_khoa)
        self.nhip_khoa()
        return True

    def nhip_khoa(self):
        for k in self.khoa_giu:
            try:
                self.ghi_json(self.p("trang_thai", f"khoa_{k}", "chu.json"),
                              {"cua_so": self.ten, "pid": os.getpid(), "nhip": time.time()})
            except OSError:
                pass

    def tha_khoa(self, ten_khoa):
        self.khoa_giu.discard(ten_khoa)
        shutil.rmtree(self.p("trang_thai", f"khoa_{ten_khoa}"), ignore_errors=True)

    # --- ngân sách -------------------------------------------------------------------------------
    def evals_cong_don(self):
        """Tổng số lần chạy mạng của mọi đời: lần sinh đã thu về + lần đang chạy (tiến độ sống, còn mới)."""
        tong = 0
        for f in glob.glob(self.p("van", "doi*", "*.json")):
            tong += json.load(open(f)).get("evals", 0)
        for f in glob.glob(self.p("trang_thai", "song_*.json")):
            try:
                s = json.load(open(f))
            except (OSError, ValueError):
                continue
            if time.time() - s.get("cap_nhat", 0) < 600:
                tong += s.get("evals", 0)
        return tong

    def muc_tieu(self, G):
        return self.ch["ngan_sach_moi_doi"] * (G + 1)

    def con_lan_sinh_khac(self, G):
        for f in glob.glob(self.p("trang_thai", "song_*.json")):
            if os.path.basename(f) == f"song_{self.ten}.json":
                continue
            try:
                s = json.load(open(f))
            except (OSError, ValueError):
                continue
            if s.get("doi") == G and time.time() - s.get("cap_nhat", 0) < 600:
                return True
        return False

    # --- máy -----------------------------------------------------------------------------------
    def dam_bao_may(self):
        if self.co_may and self.may.con_song():
            return
        self.co_may = False
        cho = 60
        while not self.may.xin(self.ch["gpu"]):
            if self.dung_mem():
                raise SystemExit("dung mem trong luc xin may")
            self.log(f"chua xin duoc may, thu lai sau {cho} giay")
            time.sleep(cho)
            cho = min(cho * 2, 1800)
        goi = self.p("goi.tar.gz")
        if not os.path.exists(goi):
            raise SystemExit(f"thieu {goi} (tao bang co_vua/scripts/dong_goi.py)")
        self.may.ssh(f"mkdir -p {CV}")
        if not self.may.tai_len(goi, f"{CV}/goi.tar.gz"):
            raise RuntimeError("khong tai duoc goi len may")
        rc, ra = self.may.ssh(f"cd {CV} && tar -xzf goi.tar.gz colab/chuan_bi.sh && bash colab/chuan_bi.sh", timeout=900)
        self.log(f"chuan bi may: ma {rc}; {ra.strip()[-600:]}")
        if rc != 0:
            raise RuntimeError("chuan bi may loi")
        self.co_may = True
        self.mang_tren_may = None

    def tra_may(self):
        if self.co_may:
            self.may.tra()
        self.co_may = False
        self.mang_tren_may = None

    def dam_bao_mang(self, G):
        if self.mang_tren_may == G:
            return
        for duoi in ("pb.gz", "pt"):
            if not self.may.tai_len(self.p("mang", f"doi{G}.{duoi}"), f"{CV}/mang/doi{G}.{duoi}"):
                raise RuntimeError(f"khong tai duoc mang doi {G} len may")
        self.mang_tren_may = G

    # --- các bước -----------------------------------------------------------------------------
    def tao_doi0(self):
        self.dam_bao_may()
        seed = self.ch["seed_doi0"]
        rc, ra = self.may.ssh(f"bash {CV}/colab/tao_doi0.sh {seed}; tail -5 {CV}/log/tao_doi0.log", timeout=900)
        self.log(f"tao doi 0 (seed {seed}): ma {rc}; {ra.strip()[-400:]}")
        if "XONG_DOI0" not in ra:
            raise RuntimeError("tao doi 0 loi")
        for duoi in ("pt", "pb.gz"):
            if not self.may.tai_ve(f"{CV}/mang/doi0.{duoi}", self.p("mang", f"doi0.{duoi}")):
                raise RuntimeError("khong tai duoc doi 0 ve")
        self.may.tai_ve(f"{CV}/log/tao_doi0.log", self.p("log", "doi0", "tao_doi0.log"))
        self.mang_tren_may = 0

    def sinh(self, G):
        self.dam_bao_may()
        self.dam_bao_mang(G)
        lan = time.strftime("%Y%m%d_%H%M%S")
        tm = f"{CV}/sinh/{lan}"
        ch = self.ch
        lenh = (f"source {CV}/moi_truong.sh && python3 {CV}/colab/sinh.py --mang {CV}/mang/doi{G}.pb.gz "
                f"--thu-muc {tm} --song-song {ch['song_song']} --luong-gom-lo {ch['luong_gom_lo']} "
                f"--visits {ch['visits']} --temp-plies {ch['temp_plies']} --max-ply {ch['max_ply']}")
        rc, ra = self.may.chay_nen(lenh)
        self.log(f"doi {G}: bat dau sinh, lan {lan} (ma {rc})")
        f_song = self.p("trang_thai", f"song_{self.ten}.json")
        da_bao_dung = False
        lan_tai_tam = time.time()
        loi_lien = 0
        tien_do = {}
        while True:
            time.sleep(self.ch["giay_hoi_tien_do"])
            self.nhip_khoa()
            # "; true" ở cuối: mã thoát của SSH chỉ báo lỗi kết nối, không bị `test -f` (chưa xong) làm thành 1.
            rc, ra = self.may.ssh(f"cat {tm}/tien_do.json 2>/dev/null; echo; test -f {tm}/xong.json && echo __XONG__; true")
            if rc != 0:
                loi_lien += 1
                self.log(f"doi {G} lan {lan}: hoi tien do loi (ma {rc}) lan {loi_lien}: {ra.strip()[-200:]}")
                if loi_lien >= 5 and not self.may.con_song():
                    self.log(f"doi {G} lan {lan}: MAT MAY; giu ban ghi tai tam (neu co) lam ket qua")
                    self.ket_thuc_lan_mat_may(G, lan, tien_do)
                    os.remove(f_song) if os.path.exists(f_song) else None
                    self.co_may = False
                    return
                continue
            loi_lien = 0
            try:
                tien_do = json.loads(ra.split("\n")[0])
            except ValueError:
                tien_do = tien_do or {}
            self.ghi_json(f_song, {"doi": G, "lan": lan, "evals": tien_do.get("evals", 0),
                                   "van_xong": tien_do.get("van_xong", 0), "cap_nhat": time.time()})
            tong = self.evals_cong_don()
            if not da_bao_dung and (tong >= self.muc_tieu(G) or self.dung_mem()):
                self.may.ssh(f"touch {tm}/dung")
                da_bao_dung = True
                self.log(f"doi {G} lan {lan}: bao dung mem (cong don {tong:,} / muc tieu {self.muc_tieu(G):,}"
                         f"{', lenh cv dung' if self.dung_mem() else ''}); van dang do se choi not")
            if "__XONG__" in ra:
                break
            if time.time() - lan_tai_tam >= self.ch["giay_tai_tam"]:
                self.may.ssh(f"cp {tm}/van.bin {tm}/van_tam.bin; cp {tm}/tien_do.json {tm}/tien_do_tam.json")
                self.may.tai_ve(f"{tm}/van_tam.bin", self.p("log", f"doi{G}", f"{self.ten}_{lan}", "van_tam.bin"))
                self.may.tai_ve(f"{tm}/tien_do_tam.json",
                                self.p("log", f"doi{G}", f"{self.ten}_{lan}", "tien_do_tam.json"))
                lan_tai_tam = time.time()
        # Thu về: bản ghi + mọi log của lần sinh.
        dich_log = self.p("log", f"doi{G}", f"{self.ten}_{lan}")
        for t in ("xong.json", "sinh.log", "engine_ra.log", "engine_loi.log", "gpu.log"):
            self.may.tai_ve(f"{tm}/{t}", os.path.join(dich_log, t))
        dich = self.p("van", f"doi{G}", f"{self.ten}_{lan}.bin.gz")
        if not self.may.tai_ve(f"{tm}/van.bin.gz", dich):
            raise RuntimeError("khong tai duoc ban ghi ve")
        xong = json.load(open(os.path.join(dich_log, "xong.json")))
        self.ghi_json(dich[:-len(".bin.gz")] + ".json",
                      {"doi": G, "lan": lan, "cua_so": self.ten, "tai_khoan": self.tk, "evals": xong["evals"],
                       "van_xong": xong["van_xong"], "giay": xong["giay"], "mang": f"doi{G}",
                       "cau_hinh": xong.get("cau_hinh"), "ma_thoat_engine": xong.get("ma_thoat_engine")})
        if os.path.exists(f_song):
            os.remove(f_song)
        self.log(f"doi {G} lan {lan}: XONG {xong['van_xong']} van, {xong['evals']:,} lan chay mang, "
                 f"{xong['giay']:.0f} giay ({xong['evals'] / max(xong['giay'], 1):.0f}/giay)")
        self.may.ssh(f"rm -f {tm}/van.bin {tm}/van_tam.bin")   # đã có bản .gz trên điện thoại

    def ket_thuc_lan_mat_may(self, G, lan, tien_do):
        """Máy mất giữa chừng: lấy bản ghi tải tạm gần nhất (nếu có) làm kết quả; số lần chạy mạng theo lúc tải."""
        d = self.p("log", f"doi{G}", f"{self.ten}_{lan}")
        tam, td = os.path.join(d, "van_tam.bin"), os.path.join(d, "tien_do_tam.json")
        if not os.path.exists(tam) or not os.path.exists(td):
            self.log(f"doi {G} lan {lan}: khong co ban ghi tai tam; mat {tien_do.get('evals', 0):,} lan chay mang")
            return
        import gzip
        dich = self.p("van", f"doi{G}", f"{self.ten}_{lan}.bin.gz")
        with open(tam, "rb") as a, gzip.open(dich, "wb") as b:
            shutil.copyfileobj(a, b)
        t = json.load(open(td))
        self.ghi_json(dich[:-len(".bin.gz")] + ".json",
                      {"doi": G, "lan": lan, "cua_so": self.ten, "tai_khoan": self.tk, "evals": t.get("evals", 0),
                       "van_xong": t.get("van_xong", 0), "mang": f"doi{G}", "mat_may": True,
                       "evals_mat": tien_do.get("evals", 0) - t.get("evals", 0)})

    def huan_luyen(self, G):
        self.dam_bao_may()
        self.dam_bao_mang(G)
        seed = random.randrange(1, 2**31)
        self.may.ssh(f"rm -rf {CV}/hl && mkdir -p {CV}/hl/van")
        dau = max(0, G - self.ch["cua_so_doi"] + 1)
        t0 = time.time()
        so_tep = 0
        for k in range(dau, G + 1):
            self.may.ssh(f"mkdir -p {CV}/hl/van/doi{k}")
            for f in sorted(glob.glob(self.p("van", f"doi{k}", "*.bin.gz"))):
                if not self.may.tai_len(f, f"{CV}/hl/van/doi{k}/{os.path.basename(f)}"):
                    raise RuntimeError(f"khong tai duoc {f} len")
                so_tep += 1
        t_tai_len = time.time() - t0
        self.may.chay_nen(f"bash {CV}/colab/huan_luyen_doi.sh {G} {seed}")
        self.log(f"doi {G}: bat dau huan luyen (doi {dau}..{G}, {so_tep} tep, tai len {t_tai_len:.0f} giay, seed {seed})")
        log_xa = f"{CV}/log/hl_doi{G}.log"
        t1 = time.time()
        while True:
            time.sleep(30)
            self.nhip_khoa()
            rc, ra = self.may.ssh(f"tail -3 {log_xa}; pgrep -f huan_luyen_doi.sh > /dev/null && echo __CHAY__; true")
            if "XONG_HUAN_LUYEN" in ra:
                break
            if rc != 0:
                self.log(f"doi {G}: hoi tien do huan luyen loi (ma {rc}): {ra.strip()[-200:]}")
                if not self.may.con_song():
                    raise RuntimeError(f"mat may trong luc huan luyen doi {G}")
                continue
            if "__CHAY__" not in ra:
                self.may.tai_ve(log_xa, self.p("log", "hl", f"hl_doi{G}_loi.log"))
                raise RuntimeError(f"huan luyen doi {G} loi; xem log/hl/hl_doi{G}_loi.log")
        t_hl = time.time() - t1
        G1 = G + 1
        for duoi in ("pt", "pb.gz"):
            if not self.may.tai_ve(f"{CV}/mang/doi{G1}.{duoi}", self.p("mang", f"doi{G1}.{duoi}")):
                raise RuntimeError(f"khong tai duoc doi {G1} ve")
        self.may.tai_ve(log_xa, self.p("log", "hl", f"hl_doi{G}.log"))
        self.may.tai_ve(f"{CV}/hl/tom_tat_doi{G}.json", self.p("log", "hl", f"tom_tat_doi{G}.json"))
        self.mang_tren_may = G1
        try:
            hl = json.loads(open(self.p("log", "hl", f"tom_tat_doi{G}.json")).read().strip().splitlines()[-1])
        except (OSError, ValueError, IndexError):
            hl = {}
        lan_sinh = [json.load(open(f)) for f in sorted(glob.glob(self.p("van", f"doi{G}", "*.json")))]
        tom = {"doi": G, "cach": "truyen_thong", "mang_ra": f"doi{G1}", "evals_doi": sum(x["evals"] for x in lan_sinh),
               "evals_cong_don": self.evals_cong_don(), "van_doi": sum(x["van_xong"] for x in lan_sinh),
               "lan_sinh": lan_sinh, "huan_luyen": hl, "seed_huan_luyen": seed, "cua_so_doi": [dau, G],
               "giay_tai_len": round(t_tai_len), "giay_huan_luyen": round(t_hl), "cua_so": self.ten,
               "tai_khoan": self.tk, "cau_hinh": self.ch, "xong_luc": time.strftime("%Y-%m-%d %H:%M:%S")}
        self.ghi_json(self.p("tom_tat", f"doi{G}.json"), tom)
        with open(self.p("trang_thai", "doi_hien_tai.txt"), "w") as f:
            f.write(str(G1))
        self.log(f"doi {G} -> doi {G1}: XONG huan luyen ({t_hl:.0f} giay); {tom['van_doi']} van, "
                 f"{tom['evals_doi']:,} lan chay mang trong doi, cong don {tom['evals_cong_don']:,}")

    # --- vòng lặp -------------------------------------------------------------------------------
    def chay(self):
        if not self.lay_khoa(f"tk_{self.tk}", het_han=900):
            raise SystemExit(f"tai khoan {self.tk} dang duoc mot cua so khac dung")
        lan_cho = 0
        try:
            while not self.dung_mem():
                try:
                    lan_cho = self.mot_buoc(lan_cho)
                except (RuntimeError, OSError) as e:
                    # Lỗi tạm thời (mất máy, lỗi tải, lỗi trên Colab): ghi log, trả máy, chờ rồi làm lại từ trạng thái
                    # trên đĩa. Khoá đang giữ (trừ khoá tài khoản) được thả để cửa sổ khác làm thay.
                    self.log(f"LOI: {type(e).__name__}: {e}; tra may, thu lai sau 5 phut")
                    self.tra_may()
                    for k in [k for k in self.khoa_giu if not k.startswith("tk_")]:
                        self.tha_khoa(k)
                    time.sleep(300)
                    lan_cho = 0
                if lan_cho < 0:
                    break
            self.log("dung: thoat")
        finally:
            self.tra_may()
            for k in list(self.khoa_giu):
                self.tha_khoa(k)

    def mot_buoc(self, lan_cho):
        """Một bước của vòng lặp theo trạng thái trên đĩa. Trả về số lần chờ liên tiếp (-1 = thoát)."""
        self.nhip_khoa()
        G = self.doi()
        if G >= self.ch["so_doi"]:
            self.log(f"da toi doi {G} (so_doi), dung")
            return -1
        if not os.path.exists(self.p("mang", f"doi{G}.pb.gz")):
            if G == 0 and self.lay_khoa("tao_doi0"):
                if not os.path.exists(self.p("mang", "doi0.pb.gz")):
                    self.tao_doi0()
                self.tha_khoa("tao_doi0")
                return 0
            self.cho(lan_cho, f"chua co mang doi {G}")
            return lan_cho + 1
        if self.evals_cong_don() < self.muc_tieu(G):
            self.sinh(G)
            return 0
        if self.con_lan_sinh_khac(G):
            self.cho(lan_cho, f"doi {G} du ngan sach, cho cac cua so khac thu ve")
            return lan_cho + 1
        if self.lay_khoa(f"hl_doi{G}"):
            if self.doi() == G:
                self.huan_luyen(G)
            self.tha_khoa(f"hl_doi{G}")
            return 0
        self.cho(lan_cho, f"cua so khac dang huan luyen doi {G}")
        return lan_cho + 1

    def cho(self, lan, ly_do):
        if lan == 0:
            self.log(f"cho: {ly_do}")
        if lan == 3:                       # chờ lâu thì trả máy, đỡ tiêu hạn mức
            self.log("cho lau: tra may")
            self.tra_may()
        time.sleep(60)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--goc", required=True)
    ap.add_argument("--tai-khoan", default="chinh")
    ap.add_argument("--ten-cua-so", default="")
    a = ap.parse_args()
    # SIGTERM (Termux bị tắt, kill) -> SystemExit, để khối finally trả máy và thả khoá.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    DieuPhoi(a.goc, a.tai_khoan, a.ten_cua_so or a.tai_khoan).chay()


if __name__ == "__main__":
    main()
