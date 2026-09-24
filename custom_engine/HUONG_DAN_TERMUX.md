# FairyZero trên điện thoại — chạy Colab GPU từ Termux

Tệp này hướng dẫn chạy **một đời huấn luyện** (sinh dữ liệu → huấn luyện → arena) trên máy Colab
**có GPU T4**, điều khiển hoàn toàn từ **Termux** trên Android, **không mở Chrome/Colab web**.

Công cụ: **Google Colab CLI** (`google-colab-cli`, Google phát hành 6/2026) — xin máy Colab, gửi
lệnh, tải tệp lên/xuống, trả máy, tất cả bằng dòng lệnh.

Có hai cách dùng:

| Cách | Dành cho | Tệp |
|---|---|---|
| **A. Ô lệnh (khuyên dùng)** | Tự chạy từng ô như sổ tay, **xem và sửa** mọi lệnh, mọi siêu tham số | `scripts/colab_cells/*.py` |
| B. Script tự động | Chạy nhanh cả đời bằng vài lệnh, **không** sửa được tham số | `scripts/colab_termux.sh` (mục 11) |

---

## Mục lục

1. [Bức tranh chung](#1-bức-tranh-chung)
2. [Cài đặt một lần](#2-cài-đặt-một-lần)
3. [Đăng nhập Google một lần](#3-đăng-nhập-google-một-lần)
4. [Xin máy T4 (không phải CPU)](#4-xin-máy-t4-không-phải-cpu)
5. [Lấy các ô lệnh về điện thoại](#5-lấy-các-ô-lệnh-về-điện-thoại)
6. [Xem, sửa, chạy một ô](#6-xem-sửa-chạy-một-ô)
7. [Một đời, từng ô](#7-một-đời-từng-ô)
8. [Tải tệp lên / về](#8-tải-tệp-lên--về)
9. [Sang đời tiếp theo](#9-sang-đời-tiếp-theo)
10. [Giữ Termux sống khi tắt màn hình](#10-giữ-termux-sống-khi-tắt-màn-hình)
11. [Cách B: script tự động](#11-cách-b-script-tự-động)
12. [Lệnh Colab CLI dùng tay](#12-lệnh-colab-cli-dùng-tay)
13. [Sự cố thường gặp](#13-sự-cố-thường-gặp)

---

## 1. Bức tranh chung

```
 Điện thoại (Termux)                              Máy Colab (Linux + GPU T4)
 ───────────────────                              ──────────────────────────
 fz  → menu, chọn  m                 ──────────▶   xin máy T4
 fz  → chọn  02                      ──────────▶   chạy ô 02 như một ô sổ tay
 fz  → chọn  04                      ──────────▶   nohup run.sh --selfplay … &   (chạy NỀN)
 fz  → chọn  05                      ──────────▶   tail log                       (xem tiến độ)
 fz  → chọn  d                    ◀──────────────  tải games_gen0.zip về điện thoại
 fz  → chọn  t                       ──────────▶   trả máy (xoá sạch /content)
```

- **Mỗi ô của sổ tay là một tệp** trong thư mục chung **`Download/FairyZero/o_lenh/`** của điện thoại
  — mở, đọc, sửa bằng **MT Manager** (hay trình quản lý tệp bất kỳ) — (`02_khoi_dong.py`,
  `04_sinh_du_lieu.py`, …), viết đúng cú pháp ô Colab (`!lệnh`, `%cd`, biến Python).
- Gõ **`fz`** trong Termux → hiện **menu** liệt kê các ô kèm tên; gõ số ô (vd `04`) → ô đó được gửi
  lên máy Colab và chạy. Trước mỗi ô, menu **ghép ô cấu hình `00_cau_hinh.py` vào đầu**, nên mọi ô
  đều biết `GEN_CURRENT`, `E`, `CURRENT_ONNX`, … — giống sổ tay chạy ô cấu hình trước.
- Việc dài (selfplay, train, arena) mặc định chạy **nền** trên máy Colab (`CHAY_NEN = True`): lệnh
  trả về ngay, mất sóng hay đóng Termux thì engine **vẫn chạy**; xem tiến độ bằng ô `05`.
- Tải tệp giữa điện thoại và máy Colab: `colab upload` / `colab download` (thay cho `files.download`
  của sổ tay, vốn cần trình duyệt). Các ô in sẵn lệnh tải đúng đường dẫn.

---

## 2. Cài đặt một lần

### 2.1. Termux

Cài Termux từ **F-Droid** hoặc **GitHub** (bản trên Google Play đã cũ). Mở Termux.

### 2.2. Gói hệ thống

```bash
pkg update && pkg upgrade        # hỏi [Y/n] thì bấm Enter
pkg install python python-pip clang git openssh nano
```

### 2.3. Thư viện có mã máy (không tự biên dịch được trên điện thoại)

```bash
pkg install python-cryptography python-rpds-py python-pyarrow
pip install tornado
```

### 2.4. Colab CLI

```bash
pip install --only-binary=:all: \
  --extra-index-url https://termux-user-repository.github.io/pypi/ \
  "google-colab-cli==0.6.0"
```

Thay `jupyter-kernel-client` bằng bản sửa (bản gốc không chạy trên Termux):

```bash
pip install --no-deps --force-reinstall \
  "git+https://github.com/googlecolab/jupyter-kernel-client.git@f18e982c3265df5e923aa9def101ab3fd737e139"
```

### 2.5. Kiểm tra

```bash
pip check
python -c "import jupyter_kernel_client as j; print(hasattr(j,'KernelClient'))"   # phải in True
colab version
```

### 2.6. Cho Termux ghi vào bộ nhớ máy

```bash
termux-setup-storage     # Android hỏi quyền -> Cho phép
mkdir -p ~/storage/downloads/FairyZero
```

`~/storage/downloads/FairyZero` chính là thư mục **Download/FairyZero** của điện thoại — nơi để
dữ liệu và mạng tải về, mở được bằng trình quản lý tệp, chép sang máy tính được.

> Thư mục home của Termux (`~`, tức `/data/data/com.termux/files/home`) là bộ nhớ **riêng** của
> Termux: trình quản lý tệp không thấy. Vì vậy các ô lệnh và dữ liệu đều để ở `Download/FairyZero/`.

---

## 3. Đăng nhập Google một lần

Lần đầu gọi lệnh cần máy Colab, CLI in ra một **đường link** rồi chờ:

```
Go to the following link in your browser: https://accounts.google.com/o/oauth2/...
Enter the authorization code:
```

1. Nhấn giữ link → **Sao chép**, mở bằng **bất kỳ trình duyệt nào** (chỉ lần này).
2. Chọn đúng tài khoản Google dùng Colab → **Cho phép**. Trang ghi "gcloud CLI" là bình thường
   (Colab CLI mượn ứng dụng OAuth của gcloud).
3. Sao chép **mã** hiện ra, dán vào Termux sau `Enter the authorization code:`, Enter.

Thông tin đăng nhập được lưu lại; các lần sau không hỏi nữa.

---

## 4. Xin máy T4 (không phải CPU)

```bash
colab new -s fz --gpu T4
```

⚠ **Thiếu `--gpu T4` thì Colab cấp máy CPU** (mặc định). `fz` là tên phiên; mọi lệnh sau dùng `-s fz`.

Kiểm tra:

```bash
colab sessions               # các máy đang giữ
colab status -s fz           # phải có "Hardware: T4 ... Variant: GPU"
```

Nếu `colab sessions` đã có sẵn phiên `fz` từ trước thì **không cần `new` nữa** — dùng luôn (kiểm
bằng `colab status -s fz`). Phiên đó là CPU thì trả rồi xin lại:

```bash
colab stop -s fz
colab new -s fz --gpu T4
```

`colab new --gpu T4` báo lỗi hết tài nguyên = tài khoản miễn phí đã dùng hết GPU trong ngày; đợi vài
giờ đến một ngày, hoặc Colab Pro. GPU khác: `--gpu L4` / `A100` / `H100` (cần Pro / đơn vị tính toán).

---

## 5. Lấy các ô lệnh về điện thoại

```bash
cd ~
curl -fLO https://raw.githubusercontent.com/phuc11731510/chess_variant_engine/main/custom_engine/scripts/colab_cells/lay_ve.sh
bash lay_ve.sh
source ~/.bashrc
```

(`-f`: đường link lỗi thì `curl` báo lỗi, thay vì lưu trang `404: Not Found` vào tệp.)

`lay_ve.sh` làm ba việc:

1. Tải 11 ô về **`Download/FairyZero/o_lenh/`** (trong Termux: `~/storage/downloads/FairyZero/o_lenh`).
   Ô nào **đã có thì giữ nguyên** (không ghi đè ô bạn đã sửa). Muốn tải lại bản mới nhất, ghi đè
   hết: `bash lay_ve.sh -f`.
2. Tải menu về `~/fz_menu.sh` (luôn lấy bản mới — đây không phải thứ bạn sửa).
3. Thêm hai lệnh vào `~/.bashrc` (chạy lại thì thay dòng cũ, không nhân đôi): **`fz`** mở menu, và
   **`o`** — cách gõ tắt không qua menu (mục 6).

Sau `source ~/.bashrc` (hoặc mở lại Termux), gõ `fz` là vào menu.

Danh sách ô, đối chiếu với sổ tay `FairyZero_1.ipynb`:

| Ô | Tệp | Mục sổ tay | Việc |
|---|---|---|---|
| 00 | `00_cau_hinh.py` | Cấu hình | `GEN_CURRENT` và mọi đường dẫn — **tự ghép vào đầu mọi ô** |
| 01 | `01_kiem_gpu.py` | 0 | `nvidia-smi` |
| 02 | `02_khoi_dong.py` | 1 (+5a) | clone mã, binary từ Release, ONNX Runtime, `pip install onnx…`, tải mạng đời hiện tại từ Release |
| 02b | `02b_bien_dich.py` | 1b | biên dịch lại (chỉ khi cần) |
| 03 | `03_tao_gen0.py` | 2 | tạo mạng đời 0 mới (ghi đè gen0) |
| 04 | `04_sinh_du_lieu.py` | 3 | sinh dữ liệu |
| 05 | `05_xem_log.py` | — | xem log việc chạy nền, còn chạy hay không |
| 06 | `06_dong_goi.py` | 4 | gom ván thành zip |
| 07 | `07_huan_luyen.py` | 5 | huấn luyện đời sau |
| 08 | `08_arena.py` | 6 | arena |
| 09 | `09_dung_viec_nen.py` | — | dừng ngay việc chạy nền |

---

## 6. Xem, sửa, chạy một ô

1. **Xem / sửa** bằng **MT Manager**: vào bộ nhớ trong → `Download` → `FairyZero` → `o_lenh` →
   chạm `04_sinh_du_lieu.py` → mở bằng trình sửa văn bản của MT Manager → sửa → **Lưu**.
2. **Chạy**: trong Termux gõ `fz`, menu hiện ra:

   ```
   ======== FairyZero trên Colab ========
    Phiên: fz   ·   Đời hiện tại: 0
    Ô lệnh: Download/FairyZero/o_lenh
   --------------------------------------
    01   Kiểm GPU (mục 0)
    02   Khởi động: mã, binary, ONNX Runtime, mạng (mục 1)
    02b  Biên dịch lại, chỉ khi cần (mục 1b)
    03   Tạo mạng đời 0 MỚI, ghi đè gen0 (mục 2)
    04   Sinh dữ liệu (mục 3)
    05   Xem tiến độ việc chạy nền
    06   Gom ván thành zip (mục 4)
    07   Huấn luyện đời sau (mục 5)
    08   Arena đời mới đấu đời cũ (mục 6)
    09   Dừng NGAY việc chạy nền
   --------------------------------------
    m    Xin máy T4
    k    Xem máy đang giữ
    d    Tải tệp Colab -> điện thoại
    u    Tải tệp điện thoại -> Colab
    t    Trả máy (XOÁ /content)
    q    Thoát
   --------------------------------------
    Nhiều ô liền nhau: gõ cách nhau, vd: 01 02
   Chọn:
   ```

   Gõ `04`, Enter → ô 04 chạy, kết quả hiện ra; xong nhấn Enter để về menu. Gõ `01 02` → chạy ô 01
   rồi ô 02.

Menu đọc tệp **ngay lúc chạy**: sửa trong MT Manager, lưu, rồi chọn ô trong menu là dùng bản mới —
không cần tải lại gì. Tên mỗi ô trong menu là **dòng đầu tiên** của tệp (dòng `# …`); đổi dòng đó
thì tên trong menu đổi theo. Thêm ô mới: tạo tệp `10_ten_gi_do.py` trong `o_lenh`, menu tự hiện.

Các mục chữ của menu:

| Chọn | Việc | Tương đương lệnh |
|---|---|---|
| `m` | Xin máy T4 | `colab new -s fz --gpu T4` |
| `k` | Xem máy đang giữ, có GPU gì | `colab sessions` + `colab status -s fz` |
| `d` | Hỏi đường dẫn trên Colab (vd `/content/games_gen0.zip`), tải về `Download/FairyZero/` | `colab download` |
| `u` | Liệt kê tệp trong `Download/FairyZero/`, chọn số → tải lên `/content/` | `colab upload` |
| `t` | Trả máy — hỏi lại, phải gõ `co` | `colab stop -s fz` |

**Lệnh `o` — gõ tắt, không qua menu.** `o 04` chạy ô 04; `o 04 05` chạy ô 04 rồi 05. Nó làm đúng
việc menu làm khi chọn `04`:

1. lấy `00_cau_hinh.py` và `04_…py` trong `Download/FairyZero/o_lenh`, nối thành một khối;
2. bỏ ký tự lạ (BOM, `\r`) mà trình sửa tệp trên điện thoại có thể thêm vào — chúng làm Python báo lỗi;
3. gửi khối đó cho `colab exec -s fz`: máy Colab chạy nó như **một ô sổ tay**, in kết quả về Termux.

Dùng menu là đủ; `o` chỉ để ai quen gõ lệnh.

Sửa trong Termux cũng được: `nano ~/storage/downloads/FairyZero/o_lenh/04_sinh_du_lieu.py`
(lưu: Ctrl+O, Enter; thoát: Ctrl+X).

Lưu ý khi sửa: ô là mã Python — giữ nguyên thụt lề (dấu cách đầu dòng) của các dòng trong `if`/`for`,
và giữ dấu ngoặc kép `"""` bao quanh lệnh.

Ví dụ sửa siêu tham số sinh dữ liệu — mở `04_sinh_du_lieu.py`, đổi `SECS = 15480` thành
`SECS = 3600` (1 giờ) và `--visits 800` thành `--visits 400` ngay trong lệnh:

```python
SECS = 3600

cmd = f"""bash {E}/run.sh --selfplay \
    --games 1000 --max-seconds {SECS} \
    --visits 400 --max-moves 400 --temp-cutoff 32 \
    ...
```

Mỗi dòng của lệnh phải kết thúc bằng ` \` (trừ dòng cuối); đừng thêm chú thích `#` vào giữa lệnh.

Mỗi ô in lệnh đầy đủ (`print(cmd)`) trước khi chạy, nên bạn luôn thấy chính xác cái gì được chạy.

**Chạy nền hay chờ:** các ô 04, 07, 08 có `CHAY_NEN = True` (mặc định). Đặt `False` thì ô chạy như
ô sổ tay — Termux chờ đến khi xong; an toàn hơn cho việc ngắn, nhưng với selfplay ~4,3 giờ thì
Android mà tắt Termux giữa chừng là không biết kết quả.

**Ô chạy một lệnh lẻ** không cần tệp:

```bash
echo '!ls -la /content' | colab exec -s fz
echo '!nvidia-smi' | colab exec -s fz
```

**Shell thật** trên máy Colab (gõ lệnh Linux trực tiếp, xem log chạy liên tục):

```bash
colab console -s fz
# trong đó:  tail -f /content/selfplay.log    (Ctrl+C để dừng xem; exit để thoát)
```

---

## 7. Một đời, từng ô

Ví dụ đời 0 → đời 1. Trước khi bắt đầu:

1. MT Manager: `Download/FairyZero/o_lenh/00_cau_hinh.py` → `GEN_CURRENT = 0`, lưu.
2. Termux: `termux-wake-lock` (mục 10), rồi `fz` để mở menu.
3. Menu: `k` xem đã có máy `fz` T4 chưa; chưa có thì `m` để xin (mục 4).

### Ô 01 — kiểm GPU

Menu `fz` → chọn **`01`** (gõ tắt: `o 01`).

Phải thấy `Tesla T4, 15360 MiB`. Không thấy → máy CPU, xem mục 4.

### Ô 02 — khởi động · ~2-3 phút

Mở xem trước bằng MT Manager (`02_khoi_dong.py`). Cuối ô có:

```python
TAI_ONNX = True     # tải gen{GEN_CURRENT}.onnx từ GitHub Release v3.0.0
TAI_PT = True       # tải gen{GEN_CURRENT}.pt   từ GitHub Release v3.0.0
```

Đặt `False` cho tệp nào bạn định **tự tải lên từ điện thoại** (mục 8) hoặc **tự tạo** (ô 03).

Menu `fz` → chọn **`02`** (gõ tắt: `o 02`).

Phải thấy `[quick] OK -- engine chay duoc tren Colab image nay.` và cuối cùng danh sách
`/content/gen0.onnx`, `/content/gen0.pt`. Nếu một tệp không có trên Release, ô in
`[!] Release KHONG co …` và **không để lại tệp rỗng**.

> Lưu ý: Release v3.0.0 hiện có `gen0.onnx` nhưng **chưa có `gen0.pt`**. Huấn luyện (ô 07) cần
> `gen0.pt` → hoặc đưa `gen0.pt` lên Release, hoặc tải lên từ điện thoại:
> `colab upload -s fz ~/storage/downloads/FairyZero/gen0.pt /content/gen0.pt`

Cảnh báo `protobuf ... incompatible` khi `pip install` là của các gói khác của Colab, không ảnh hưởng
FairyZero.

### Ô 03 — tạo mạng đời 0 mới (tuỳ chọn)

Chỉ khi muốn mạng đời 0 **mới** (seed mới). Nó ghi đè `/content/gen0.onnx` và `gen0.pt`. Có mạng
đời 0 rồi (từ Release hay điện thoại) thì bỏ qua.

Menu `fz` → chọn **`03`** (gõ tắt: `o 03`).

### Ô 04 — sinh dữ liệu · theo `SECS`

Sửa tham số trong `04_sinh_du_lieu.py` nếu muốn, rồi:

Menu `fz` → chọn **`04`** (gõ tắt: `o 04`).

In lệnh đầy đủ rồi `[da chay nen] xem: o 05` (tức ô 05 trong menu). Có thể thoát Termux.

> `--max-seconds` dừng mềm: hết giờ thì không nhận ván mới, ván đang chạy vẫn chơi nốt —
> thường vượt 2-3 phút.

### Ô 05 — xem tiến độ

Menu `fz` → chọn **`05`** (gõ tắt: `o 05`).

In 15 dòng log cuối, số tệp ván, mức dùng GPU, và **`[DANG CHAY]`** hoặc
**`[KHONG con tien trinh -- xong hoac loi]`**. Khi xong, cuối log có khối `--- Throughput ---` —
so cấu hình bằng `NN eval/giay`, đừng bằng `Van/gio`.

Xem log train / arena: sửa `LOG = "train"` (hoặc `"arena"`) trong `05_xem_log.py`; nhiều dòng hơn:
sửa `SO_DONG`.

Lỡ sai tham số, muốn dừng ngay: `o 09`.

### Ô 06 — đóng gói · vài phút

Đợi `o 05` báo **KHONG con tien trinh**, rồi:

Menu `fz` → chọn **`06`** (gõ tắt: `o 06`).

Ô in sẵn lệnh tải về. **Chạy lệnh đó trong Termux** (không phải trong ô):

```bash
colab download -s fz /content/games_gen0.zip ~/storage/downloads/FairyZero/games_gen0.zip
```

Đây là bản gốc dữ liệu của bạn — giữ cẩn thận.

### Ô 07 — huấn luyện · 10-40 phút

Kiểm `/content/gen0.pt` có trên máy (`echo '!ls -la /content' | colab exec -s fz`). Sửa tham số
trong `07_huan_luyen.py` nếu muốn (`--epochs`, `--lr`, `DATA`, …), rồi:

Menu `fz` → chọn **`07`** (gõ tắt: `o 07`).

Theo dõi: `LOG = "train"` trong ô 05, rồi `o 05`. Xong thì tải mạng mới về (ô 07 in sẵn lệnh):

```bash
colab download -s fz /content/gen1.onnx ~/storage/downloads/FairyZero/gen1.onnx
colab download -s fz /content/gen1.pt   ~/storage/downloads/FairyZero/gen1.pt
```

### Ô 08 — arena · ~30 phút (tuỳ chọn)

Menu `fz` → chọn **`08`** (gõ tắt: `o 08`).

Theo dõi: `LOG = "arena"` trong ô 05. 48 ván vẫn sai số lớn (hàng trăm Elo); phát hiện chênh
~50 Elo cần 400-1000 ván — sửa `--games`, `--visits` trong ô.

### Trả máy

Kiểm chắc trong `Download/FairyZero/` đã có `games_gen0.zip`, `gen1.onnx`, `gen1.pt`, rồi:

```bash
colab stop -s fz
termux-wake-unlock
```

⚠ `stop` **xoá sạch `/content`**. Không trả thì máy vẫn chiếm quota GPU của bạn.

---

## 8. Tải tệp lên / về

```bash
# điện thoại -> máy Colab
colab upload   -s fz ~/storage/downloads/FairyZero/gen1.onnx /content/gen1.onnx
# máy Colab -> điện thoại
colab download -s fz /content/games_gen1.zip ~/storage/downloads/FairyZero/games_gen1.zip
# xem trên máy Colab có gì
colab ls -s fz /content
```

**Nguồn mạng đời hiện tại — bạn chọn, không có gì tự động:**

| Muốn | Làm |
|---|---|
| Lấy từ GitHub Release | `TAI_ONNX` / `TAI_PT = True` trong ô 02 (mặc định) |
| Lấy từ điện thoại | `TAI_… = False` trong ô 02, rồi `colab upload` như trên |
| Tạo mới (đời 0) | `TAI_… = False` trong ô 02, rồi `o 03` |

---

## 9. Sang đời tiếp theo

1. MT Manager: `00_cau_hinh.py` → `GEN_CURRENT = 1`, lưu.
2. Menu `fz`: `m` (nếu đã trả máy), rồi `01 02`.
3. Mạng đời 1: có trên Release thì ô 02 tự tải; không thì `TAI_… = False` và `colab upload` từ
   `Download/FairyZero/`.
4. Ô `04` → `05` → `06` → `07` → …

Kiến trúc `144 × 12` SE-8 phải giữ nguyên suốt chuỗi warm-start.

**Cửa sổ trượt nhiều đời** (ô 07): tải các zip cũ lên trước, rồi sửa `DATA`:

```bash
colab upload -s fz ~/storage/downloads/FairyZero/games_gen0.zip /content/games_gen0.zip
```
```python
DATA = "/content/games_gen0.zip,/content/games_gen1.zip"
```

Máy còn sống từ đời trước (chưa `stop`) thì chỉ cần đổi `GEN_CURRENT` rồi `o 04` — `gen1.onnx`
vẫn nằm ở `/content`. Colab miễn phí tự ngắt sau tối đa khoảng 12 giờ, nên một phiên thường chỉ đủ
một đời với selfplay 4,3 giờ.

---

## 10. Giữ Termux sống khi tắt màn hình

Engine chạy trên Colab nên không phụ thuộc điện thoại. Nhưng Colab CLI có tiến trình **giữ máy khỏi bị
thu hồi vì "idle"**; chưa rõ nó chạy ở điện thoại hay ở máy Colab. Để an toàn, suốt lúc
selfplay/train hãy giữ Termux sống:

- `termux-wake-lock` (hoặc kéo thanh thông báo Termux → **Acquire wakelock**).
- **Cài đặt → Ứng dụng → Termux → Pin → Không hạn chế**. Trên Samsung còn phải bỏ Termux khỏi
  "Ứng dụng ngủ" / "Ứng dụng ngủ sâu".
- Đừng vuốt tắt Termux khỏi danh sách đa nhiệm.

Termux lỡ bị giết: mở lại, `colab sessions` xem máy còn không. Còn thì `o 05` tiếp; mất rồi thì dữ
liệu trên máy đó mất theo — máy hay chết thì selfplay theo lượt ngắn hơn (`SECS = 7200`) và tải zip
về sau mỗi lượt.

---

## 11. Cách B: script tự động

`scripts/colab_termux.sh` gói cả đời thành vài lệnh, **tham số cố định** (giống ô sổ tay mặc định).
Chỉ nên dùng khi đã quen và không cần sửa gì.

```bash
curl -LO https://raw.githubusercontent.com/phuc11731510/chess_variant_engine/main/custom_engine/scripts/colab_termux.sh
export GEN=0
bash colab_termux.sh start      # colab new --gpu T4 (hoặc dùng lại phiên fz có sẵn), kiểm GPU, ô 02, nạp mạng
bash colab_termux.sh selfplay   # ô 04 (SECS=… để đổi thời gian)
bash colab_termux.sh status     # ô 05 (status train / status arena)
bash colab_termux.sh fetch      # ô 06 + colab download zip
bash colab_termux.sh train      # ô 07 (DATA=… để cửa sổ trượt)
bash colab_termux.sh getnet     # colab download gen{GEN+1}.onnx/.pt
bash colab_termux.sh arena      # ô 08
bash colab_termux.sh stop
```

**`start` chọn nguồn mạng đời `GEN` theo thứ tự** (khác ô 02!):

1. Có `Download/FairyZero/genN.onnx` / `.pt` trên điện thoại → **tải lên tệp đó**.
2. Không có, `GEN=0` → **tạo mạng đời 0 mới** rồi tải về điện thoại.
3. Không có, `GEN>0` → tải từ Release v3.0.0.

Muốn chắc chắn dùng mạng trên Release thì dùng cách A.

---

## 12. Lệnh Colab CLI dùng tay

| Lệnh | Việc |
|---|---|
| `colab sessions` | Liệt kê các máy đang giữ |
| `colab status -s fz` | Phần cứng, cấu hình máy, trạng thái |
| `colab new -s fz --gpu T4` | Xin máy T4 (thiếu `--gpu` = CPU) |
| `echo '!lệnh' \| colab exec -s fz` | Chạy một lệnh (cú pháp ô Colab) |
| `colab exec -s fz -f tệp.py` | Chạy một tệp (không ghép ô cấu hình — dùng `o` nếu ô cần biến của ô 00) |
| `colab console -s fz` | Shell thật (tmux) trên máy Colab |
| `colab ls -s fz /content` | Liệt kê tệp trên máy |
| `colab upload -s fz <điện thoại> <máy>` | Tải lên |
| `colab download -s fz <máy> <điện thoại>` | Tải về |
| `colab log -s fz -o log.md` | Lưu lịch sử các lệnh đã chạy |
| `colab stop -s fz` | Trả máy |

---

## 13. Sự cố thường gặp

**Nhận máy CPU thay vì T4** → mục 4.

**`o: command not found`** — chưa `source ~/.bashrc` sau khi chạy `lay_ve.sh`, hoặc mở Termux
mới trước khi `.bashrc` được sửa. Chạy `source ~/.bashrc`.

**`cat: …/o_lenh/04_*.py: No such file`** — sai số ô, hoặc chưa `bash lay_ve.sh`, hoặc đổi tên tệp
(tên phải bắt đầu bằng `<số>_`). Xem: `ls ~/storage/downloads/FairyZero/o_lenh`.

**`SyntaxError` / `IndentationError` sau khi sửa ô** — lỡ xoá dấu cách thụt lề, dấu ngoặc hay dấu
`\` cuối dòng của lệnh. So với bản gốc: `bash lay_ve.sh -f` tải lại (ghi đè) — sao lưu ô đã sửa trước.

**`NameError: name 'E' is not defined`** — chạy ô bằng `colab exec -f` thay vì `o`, nên thiếu ô
cấu hình. Dùng `o <số>`.

**Ô 02 báo `[quick]` lỗi** — Release chưa có binary hoặc Colab đổi image: `o 02b` (8-12 phút), rồi
tải binary về theo lệnh ô in ra và đưa lên GitHub Release (tên đúng: `custom_engine`).

**Ô 05 báo KHONG con tien trinh quá sớm** — engine lỗi khi khởi động. Tăng `SO_DONG = 80` trong ô 05
rồi `o 05` để đọc lỗi. Hay gặp: thiếu mạng (`/content/genN.onnx` không có — kiểm `GEN_CURRENT`),
hoặc máy không có GPU.

**Huấn luyện báo không thấy `.pt`** — `gen{GEN_CURRENT}.pt` chưa có trên máy (Release chưa có tệp đó):
`colab upload` từ điện thoại (mục 8).

**`colab: command not found`** — chạy lại mục 2.4.

**Đăng nhập hết hạn / lỗi quyền** — chạy `colab sessions` để nó in lại link đăng nhập, làm lại mục 3.

**`$'\r': command not found`** — tệp mang xuống dòng kiểu Windows: `sed -i 's/\r$//' <tệp>`.

---

Tham khảo: [google-colab-cli](https://github.com/googlecolab/google-colab-cli) ·
[Hướng dẫn cài trên Termux (issue #131)](https://github.com/googlecolab/google-colab-cli/issues/131) ·
tham số engine đầy đủ: `HUONG_DAN.md` mục D.
