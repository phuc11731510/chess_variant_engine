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
 fz  → chọn  04   (colab exec)       ──────────▶   khởi động ô 04 chạy NỀN, log /content/fz_log/04.log
      màn hình log trực tiếp (ssh) ◀──────────────  tail -F log: từng dòng hiện ngay khi in
      Ctrl+C → về menu                                ô 04 VẪN chạy tiếp
 fz  → chọn  l    (ssh)              ◀──────────────  xem tiếp log ô đang chạy
 fz  → chọn  d                    ◀──────────────  tải games_gen0.zip về điện thoại
 fz  → chọn  t                       ──────────▶   trả máy (xoá sạch /content)
```

- **Mỗi ô của sổ tay là một tệp** trong thư mục chung **`Download/FairyZero/o_lenh/`** của điện thoại
  — mở, đọc, sửa bằng **MT Manager** (hay trình quản lý tệp bất kỳ) — (`02_khoi_dong.py`,
  `04_sinh_du_lieu.py`, …), viết đúng cú pháp ô Colab (`!lệnh`, `%cd`, biến Python).
- Gõ **`fz`** trong Termux → hiện **menu** liệt kê các ô kèm tên; gõ số ô (vd `04`) → ô đó được gửi
  lên máy Colab và chạy. Trước mỗi ô, menu **ghép ô cấu hình `00_cau_hinh.py` vào đầu**, nên mọi ô
  đều biết `GEN_CURRENT`, `E`, `CURRENT_ONNX`, … — giống sổ tay chạy ô cấu hình trước.
- **Mọi ô** (trừ 3 ô ngắn 01, 05, 09) chạy **nền** trên máy Colab, và menu **hiện log của ô đó
  trực tiếp** như ô sổ tay trên web. **Ctrl+C** chỉ đóng màn hình log, **ô vẫn chạy tiếp**; mất sóng
  hay đóng Termux cũng vậy. Xem lại: menu `l`. Chi tiết cơ chế: mục 6.1.
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

### 3.1. Đổi sang tài khoản Google khác (vd tài khoản này sắp hết quota GPU)

Colab CLI không có lệnh `logout` riêng. "Đăng xuất" = xoá tệp chứa thông tin đăng nhập; lần gọi
tiếp theo nó không thấy thì hỏi đăng nhập lại (mục 3) — lúc đó chọn tài khoản khác.

**Cách nhanh: menu `fz` → `a` (Đổi tài khoản Colab).** Nó hỏi lần lượt:

1. Trả máy `fz` của tài khoản hiện tại không (gõ `co` để trả — nên trả, sau khi đổi thì không điều
   khiển máy đó được nữa).
2. Cất tài khoản hiện tại không: gõ một tên (vd `A`) → token được cất vào
   `~/.config/colab-cli/luu/A/`, lần sau chọn lại được mà không phải đăng nhập; Enter = không cất.
3. Chọn: `0` = đăng nhập tài khoản **mới** (in link, chọn tài khoản trong trình duyệt); `1`, `2`, … =
   dùng lại tài khoản đã cất; Enter = huỷ, giữ nguyên tài khoản hiện tại.

Làm tay thì như sau:

1. **Trả hết máy của tài khoản cũ trước** (sau khi đổi tài khoản thì không điều khiển chúng được nữa):

   ```bash
   colab sessions
   colab stop -s fz
   ```

2. Xoá token đăng nhập — Colab CLI lưu nó ở **`~/.config/colab-cli/token.json`**:

   ```bash
   rm -f ~/.config/colab-cli/token.json ~/.config/colab-cli/sessions.json
   ```

   Các tệp khác trong thư mục đó (`settings.json`, `colab.log`, `history/` — lịch sử lệnh từng phiên)
   không chứa đăng nhập, để nguyên được.

3. Đăng nhập tài khoản mới: menu `fz` → `m` (hoặc `colab sessions`) → nó in link đăng nhập →
   làm như mục 3, **chọn tài khoản khác** trong trình duyệt.

Token đã cất mà hết hạn thì CLI hỏi đăng nhập lại như bình thường.

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

**Còn bao lâu nữa bị ngắt?** Menu **`h`**. `colab usage` chỉ in số dư đơn vị **mua** (tài khoản
miễn phí: 0) — nên menu chạy thêm `~/fz_han_muc.py`, đọc đúng API mà trang web và tiện ích Colab cho
VS Code của Google dùng (`colab.pa.googleapis.com/v1/user-info`, trường `freeCcuQuotaInfo`):

```
Hạn mức miễn phí còn: 1.60 đơn vị tính toán
=> Với mức tiêu hiện tại: còn khoảng 1 giờ 30 phút      <- = 1,60 / 1,07 (T4 tiêu ~1,07/giờ)
   Gợi ý SECS cho ô 04 (trừ 20 phút để gom zip + tải về): 4200
Nạp lại hạn mức lúc: 08:33 25/09
```

Chưa giữ máy nào thì nó tính theo mức T4 ~1,07/giờ. `python ~/fz_han_muc.py --raw` in nguyên dữ
liệu API trả về để tự kiểm. Đây là API nội bộ của Google (không có tài liệu chính thức), có thể đổi.

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
   Ô nào **đã có thì giữ nguyên** (không ghi đè ô bạn đã sửa). Muốn lấy bản mới nhất:
   - riêng vài ô (ghi đè đúng các ô đó): `bash lay_ve.sh 05 07`;
   - tất cả (ghi đè mọi ô đã sửa): `bash lay_ve.sh -f`.

   **Xoá một tệp ô** trong `o_lenh` thì ô đó biến khỏi menu và không chạy được nữa — menu đọc thẳng
   các tệp này mỗi lần. Lấy lại: `bash lay_ve.sh` (chỉ tải ô còn thiếu). Riêng `00_cau_hinh.py` mà
   mất thì **mọi ô** đều hỏng (chúng cần biến của nó).
2. Tải menu về `~/fz_menu.sh` và phần chạy trên máy Colab về `~/fz_may.py` (luôn lấy bản mới —
   đây không phải thứ bạn sửa).
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
| 05 | `05_xem_log.py` | — | tình trạng ô chạy nền gần nhất: còn chạy hay xong, log cuối |
| 06 | `06_dong_goi.py` | 4 | gom ván thành zip |
| 07 | `07_huan_luyen.py` | 5 | huấn luyện đời sau |
| 08 | `08_arena.py` | 6 | arena |
| 09 | `09_dung_viec_nen.py` | — | dừng ngay ô đang chạy nền |

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
    05   Tình trạng ô chạy nền gần nhất
    06   Gom ván thành zip (mục 4)
    07   Huấn luyện đời sau (mục 5)
    08   Arena đời mới đấu đời cũ (mục 6)
    09   Dừng NGAY ô đang chạy nền
   --------------------------------------
    m    Xin máy T4
    l    Log trực tiếp ô đang chạy nền
    k    Xem máy đang giữ
    h    Hạn mức GPU (colab usage)
    d    Tải tệp Colab -> điện thoại
    u    Tải tệp điện thoại -> Colab
    t    Trả máy (XOÁ /content)
    a    Đổi tài khoản Colab
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
| `l` | Log trực tiếp ô chạy nền gần nhất (từ đầu), Ctrl+C để về menu | `ssh … tail -F` |
| `k` | Xem máy đang giữ, có GPU gì | `colab sessions` + `colab status -s fz` |
| `h` | **Hạn mức GPU miễn phí còn lại** (≈ bao nhiêu giờ T4), giờ nạp lại, gợi ý `SECS` cho ô 04 | `colab usage` + `~/fz_han_muc.py` (mục 4) |
| `d` | **Duyệt thư mục trên Colab** (bắt đầu ở `/content`): gõ số để vào thư mục / tải tệp về `Download/FairyZero/`, `0` lên thư mục cha, `/đường/dẫn` để nhảy tới, `q` về menu | `ssh … find` + `colab download` |
| `u` | Liệt kê tệp trong `Download/FairyZero/`, chọn số → tải lên `/content/`; `c` = mở **trình chọn tệp của Android** (cần Termux:API, xem dưới) | `colab upload` |
| `t` | Trả máy — hỏi lại, phải gõ `co` | `colab stop -s fz` |
| `a` | Đổi tài khoản Colab (trả máy, cất token, đăng nhập mới / dùng lại tài khoản đã cất) | mục 3.1 |

**Tải lên bằng trình chọn tệp của Android (`u` → `c`).** Cần app **Termux:API** (cài cùng nguồn với
Termux — F-Droid hoặc GitHub, không trộn với bản Google Play) và gói `pkg install termux-api`.
Android không cho biết tên gốc của tệp đã chọn, nên menu hỏi tên để đặt trên Colab.

**Tải lên bằng "Chia sẻ" (giữ tên tệp).** Trong MT Manager / Files: chọn tệp → **Chia sẻ** →
**Termux** → **Edit**. Termux chép tệp vào `~/downloads` rồi gọi `~/bin/termux-file-editor`;
`lay_ve.sh` đặt ở đó một móc nhỏ hỏi "Enter = tải" rồi `colab upload` lên `/content/<tên gốc>`.
(Nếu bạn đã có `termux-file-editor` riêng thì `lay_ve.sh` không ghi đè.)

**Tải tệp về chạy thế nào mà không cần trình duyệt?** Máy Colab chạy một máy chủ Jupyter; Colab CLI
nói chuyện với nó qua HTTPS bằng token đăng nhập của bạn. `colab download` gọi API "contents" của
Jupyter: máy chủ đọc tệp, gửi về dạng base64 trong JSON, CLI giải mã và ghi ra tệp trên điện thoại
(`colab upload` làm ngược lại). Trình duyệt trên web cũng chỉ gọi đúng API đó.

**Lệnh `o` — gõ tắt, không qua menu.** `o 04` = chọn `04` trong menu; `o 04 05` = chọn `04 05`.
Nó gọi đúng menu (`bash ~/fz_menu.sh 04 05`), chỉ không vẽ menu ra. Dùng menu là đủ; `o` chỉ để ai
quen gõ lệnh.

### 6.1. Menu chạy một ô như thế nào

1. **Ghép:** lấy `00_cau_hinh.py` và tệp ô trong `Download/FairyZero/o_lenh`, nối thành một khối
   (bỏ ký tự lạ BOM, `\r` mà trình sửa tệp trên điện thoại có thể thêm vào). Nhờ vậy mỗi ô biết
   `GEN_CURRENT`, `E`, … — không có biến nào được "truyền" giữa các ô, mã của ô 00 chạy lại ở đầu
   mỗi ô.
2. **Ô ngắn** — có dòng `# fz: nhanh` (01, 05, 09): gửi khối cho `colab exec`, máy Colab chạy nó
   như một ô sổ tay, chữ hiện ngay về Termux. Xong là xong.
3. **Ô còn lại:** `colab exec` chỉ chạy một đoạn khởi động ngắn (vài giây) trên máy Colab: lưu khối
   thành `/content/fz_log/<ô>.ipy`, chạy nó **nền** bằng IPython riêng (hiểu `!lệnh`, `%cd` như ô
   sổ tay), mọi chữ in ra ghi vào `/content/fz_log/<ô>.log`, và ghi "ô nào đang chạy" vào
   `/content/fz_log/dang_chay`.
4. **Xem:** menu mở `ssh` tới máy Colab và chạy `fz_may.py theo_doi`: in log từ đầu rồi in tiếp
   mỗi dòng **ngay lúc ô in ra**. Ô kết thúc thì log in `[fz] o 04 xong …, ma thoat 0` và màn hình
   tự dừng. **Ctrl+C** đóng `ssh`; `theo_doi` trên Colab thấy đầu bên kia đã đóng và tự thoát —
   **ô không bị ảnh hưởng**.

**Ô xong hay chưa — xác định thế nào.** Toàn bộ phần chạy trên máy Colab nằm trong một tệp đọc được:
`~/fz_may.py` (menu gửi lên `/content/fz_log/fz_may.py` mỗi lần khởi động ô). Hàm `trang_thai` của
nó cho mỗi ô một trong ba trạng thái, không đoán theo thời gian hay nội dung log:

| Trạng thái | Khi nào |
|---|---|
| **xong** (kèm mã thoát) | có tệp `/content/fz_log/<ô>.rc`. Vỏ `bash` bọc ngoài ô ghi mã thoát vào đó **ngay khi IPython chạy ô kết thúc** (ghi qua tệp tạm rồi đổi tên, nên không bao giờ đọc phải tệp ghi dở) |
| **chạy** | chưa có `.rc`, **và** số PID của ô còn sống (không phải zombie), **và** dòng lệnh của PID đó có `fz_log/<ô>.ipy` — nếu Linux đã cấp lại số PID đó cho tiến trình khác thì dòng lệnh không khớp, không bị nhầm |
| **bị dừng** | không có `.rc` và tiến trình không còn: bị ô 09 dừng, hoặc máy giết giữa chừng |

Ô 05 và 09 cũng dùng đúng hàm đó. Ô 09 chỉ giết khi trạng thái là **chạy** (đã khớp dòng lệnh), nên
không bao giờ giết nhầm tiến trình lạ.

Vì sao hai đường (`colab exec` để khởi động, `ssh` để xem)? Máy Colab chỉ có **một kernel**, chạy mỗi
lần một khối mã; Ctrl+C trên `colab exec` **không** dừng được khối đang chạy trên kernel (đã thử),
nên nếu xem log bằng `colab exec` thì thoát ra xong mọi lệnh sau phải xếp hàng chờ. `ssh` chạy
trong shell riêng, tách hẳn khỏi kernel.

`ssh` cần gói `openssh` và khoá cá nhân `~/.ssh/id_ed25519` — `lay_ve.sh` tự cài / tự tạo nếu thiếu.
Menu gọi `ssh` qua `colab ssh --proxy-mode`, không cần `~/.ssh/config`.

Đang có ô chạy nền mà chọn thêm một ô chạy nền khác → menu hỏi lại (`co` = vẫn chạy song song).
Hai ô cùng dùng GPU thì chậm cả hai — thường là không nên.

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

**Ô chạy một lệnh lẻ** không cần tệp:

```bash
echo '!ls -la /content' | colab exec -s fz
echo '!nvidia-smi' | colab exec -s fz
```

**Shell thật** trên máy Colab (gõ lệnh Linux trực tiếp, xem log chạy liên tục):

```bash
colab console -s fz
# trong đó:  ls /content/fz_log ; nvidia-smi ; …    (exit để thoát)
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

Màn hình log hiện lệnh đầy đủ rồi log của engine chạy ra liên tục. Ctrl+C để về menu (selfplay vẫn
chạy), có thể thoát Termux; xem lại: menu `l`.

> `--max-seconds` dừng mềm: hết giờ thì không nhận ván mới, ván đang chạy vẫn chơi nốt —
> thường vượt 2-3 phút.

### Theo dõi: `l` (trực tiếp) và ô 05 (tóm tắt)

- Menu **`l`**: mở lại log trực tiếp của ô chạy nền gần nhất, từ đầu log; Ctrl+C để về.
- Ô **`05`**: tóm tắt nhanh — **`[DANG CHAY: ô 04]`**, **`[DA XONG, ma thoat 0: ô 04]`** hoặc
  **`[BI DUNG giua chung: ô 04]`**, 15 dòng log cuối,
  số tệp ván, mức dùng GPU. Nhiều dòng hơn: sửa `SO_DONG` trong ô.

Khi selfplay xong, cuối log có khối `--- Throughput ---` — so cấu hình bằng `NN eval/giay`, đừng bằng
`Van/gio`.

Lỡ sai tham số, muốn dừng ngay: ô **`09`** (dừng ô chạy nền gần nhất cùng engine / train.py của nó).

### Ô 06 — đóng gói · vài phút

Đợi ô 04 chạy xong (log in `[fz] o 04 xong …`; hoặc ô 05 báo `DA XONG`), rồi:

Menu `fz` → chọn **`06`** (gõ tắt: `o 06`).

Rồi tải về điện thoại: menu **`d`** → gõ `/content/games_gen0.zip` → tệp về `Download/FairyZero/`.

Đây là bản gốc dữ liệu của bạn — giữ cẩn thận.

### Ô 07 — huấn luyện · 10-40 phút

Kiểm `/content/gen0.pt` có trên máy (`echo '!ls -la /content' | colab exec -s fz`). Sửa tham số
trong `07_huan_luyen.py` nếu muốn (`--epochs`, `--lr`, `DATA`, …), rồi:

Menu `fz` → chọn **`07`** (gõ tắt: `o 07`).

Log huấn luyện hiện trực tiếp. Xong thì tải mạng mới về: menu **`d`** → `/content/gen1.onnx`, rồi
lại **`d`** → `/content/gen1.pt`.

### Ô 08 — arena · ~30 phút (tuỳ chọn)

Menu `fz` → chọn **`08`** (gõ tắt: `o 08`).

48 ván vẫn sai số lớn (hàng trăm Elo); phát hiện chênh
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

Termux lỡ bị giết: mở lại, `colab sessions` xem máy còn không. Còn thì menu `l` xem tiếp; mất rồi thì dữ
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

**Ô chạy nền xong ngay (`ma thoat` khác 0)** — lỗi khi khởi động; đọc log bằng menu `l` (in từ đầu). Hay gặp: thiếu mạng (`/content/genN.onnx` không có — kiểm `GEN_CURRENT`),
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
