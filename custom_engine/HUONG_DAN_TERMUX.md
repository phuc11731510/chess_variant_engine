# FairyZero trên điện thoại — chạy Colab GPU từ Termux

Tệp này hướng dẫn chạy **toàn bộ vòng một đời** (sinh dữ liệu → huấn luyện → arena) trên máy
Colab **có GPU T4**, điều khiển hoàn toàn từ **Termux** trên Android, **không mở Chrome/Colab web**.
Nó làm đúng những việc của sổ tay `FairyZero_1.ipynb`, chỉ khác cách bấm.

Công cụ dùng: **Google Colab CLI** (`google-colab-cli`, Google phát hành 6/2026) — xin máy Colab,
gửi lệnh, tải tệp lên/xuống, trả máy, tất cả bằng dòng lệnh. Script bọc sẵn mọi bước:
`scripts/colab_termux.sh`.

> ⚠ Script mới kiểm cú pháp, **chưa chạy thật trên điện thoại**. Lần đầu hãy chạy **từng lệnh một**
> và đọc kết quả trước khi sang lệnh sau.

---

## Mục lục

1. [Bức tranh chung](#1-bức-tranh-chung)
2. [Cài đặt một lần](#2-cài-đặt-một-lần)
3. [Đăng nhập Google một lần](#3-đăng-nhập-google-một-lần)
4. [Lấy script về điện thoại](#4-lấy-script-về-điện-thoại)
5. [Chắc chắn máy có GPU T4, không phải CPU](#5-chắc-chắn-máy-có-gpu-t4-không-phải-cpu)
6. [Chạy một đời, từng bước](#6-chạy-một-đời-từng-bước)
7. [Sang đời tiếp theo](#7-sang-đời-tiếp-theo)
8. [Giữ Termux sống khi tắt màn hình](#8-giữ-termux-sống-khi-tắt-màn-hình)
9. [Lệnh Colab CLI dùng tay](#9-lệnh-colab-cli-dùng-tay)
10. [Sự cố thường gặp](#10-sự-cố-thường-gặp)

---

## 1. Bức tranh chung

```
 Điện thoại (Termux)                         Máy Colab (Linux + GPU T4)
 ───────────────────                         ──────────────────────────
 bash colab_termux.sh start   ── colab new ──▶  xin VM có T4, tải engine + ONNX Runtime
 bash colab_termux.sh selfplay ─ colab exec ─▶  nohup run.sh --selfplay … &   (chạy NỀN ~4,3 giờ)
 bash colab_termux.sh status   ─ colab exec ─▶  tail log                       (xem tiến độ)
 bash colab_termux.sh fetch  ◀─ colab download ─ games_genN.zip
 bash colab_termux.sh train    ─ colab exec ─▶  nohup train.py … &             (chạy NỀN)
 bash colab_termux.sh getnet ◀─ colab download ─ gen(N+1).onnx / .pt
 bash colab_termux.sh arena    ─ colab exec ─▶  nohup run.sh --arena … &
 bash colab_termux.sh stop     ─ colab stop ──▶  trả VM (xoá sạch /content)
```

Điểm mấu chốt: việc dài (selfplay, train, arena) được khởi chạy bằng `nohup … &` **trên máy Colab**.
Điện thoại chỉ ra lệnh rồi thoát ngay; mất sóng hay đóng Termux thì engine trên Colab **vẫn chạy**.
Muốn xem thì gõ `status` bất cứ lúc nào.

**Vì sao không chạy thẳng tệp `.ipynb`?** `colab exec -f FairyZero_1.ipynb` có tồn tại nhưng:
`files.download` cần trình duyệt nên sẽ lỗi; và ô sinh dữ liệu chạy ~4,3 giờ, lệnh sẽ treo cả chừng đó,
Android giết Termux giữa chừng là hỏng.

---

## 2. Cài đặt một lần

### 2.1. Termux

Cài Termux từ **F-Droid** hoặc **GitHub** (bản trên Google Play đã cũ, không dùng được). Mở Termux.

### 2.2. Gói hệ thống

```bash
pkg update && pkg upgrade        # hỏi [Y/n] thì bấm Enter
pkg install python python-pip clang git openssh
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
ls ~/storage/downloads   # phải thấy thư mục Download của điện thoại
```

Script lưu mọi tệp tải về vào **`Download/FairyZero/`** trên điện thoại
(tức `~/storage/downloads/FairyZero` trong Termux) — mở được bằng trình quản lý tệp, chép sang máy tính.

---

## 3. Đăng nhập Google một lần

Lần đầu gọi lệnh cần máy Colab, CLI in ra một **đường link** rồi chờ:

```
Go to the following link in your browser: https://accounts.google.com/o/oauth2/...
Enter the authorization code:
```

1. Nhấn giữ link → **Sao chép**, mở bằng **bất kỳ trình duyệt nào** (chỉ lần này thôi).
2. Chọn đúng tài khoản Google dùng Colab → **Cho phép**. Trang ghi "gcloud CLI" là bình thường
   (Colab CLI mượn ứng dụng OAuth của gcloud).
3. Sao chép **mã** hiện ra, quay lại Termux, dán vào sau `Enter the authorization code:`, Enter.

Thông tin đăng nhập được lưu lại; các lần sau không hỏi nữa.

Để đăng nhập ngay mà không tốn quota GPU, dùng một máy **CPU** thử rồi trả luôn:

```bash
colab new -s thu            # KHÔNG có --gpu => máy CPU (xem mục 5)
echo 'print(1+1)' | colab exec -s thu      # in 2
colab stop -s thu           # NHỚ trả, nếu không nó chiếm chỗ
```

---

## 4. Lấy script về điện thoại

**Cách A — tải từ GitHub** (sau khi `scripts/colab_termux.sh` đã được push lên nhánh `main`):

```bash
cd ~
curl -LO https://raw.githubusercontent.com/phuc11731510/chess_variant_engine/main/custom_engine/scripts/colab_termux.sh
```

**Cách B — chép từ máy tính:** chép `custom_engine/scripts/colab_termux.sh` vào thư mục **Download**
của điện thoại (cáp USB, Drive, Zalo…), rồi:

```bash
cp ~/storage/downloads/colab_termux.sh ~/
```

Kiểm tra: `bash ~/colab_termux.sh` (không đối số) in ra bảng cách dùng.

> Nếu chép qua Windows mà báo lỗi `$'\r': command not found` thì tệp bị đổi xuống dòng kiểu Windows,
> sửa bằng `sed -i 's/\r$//' ~/colab_termux.sh`.

---

## 5. Chắc chắn máy có GPU T4, không phải CPU

**Đây là lý do hay gặp nhất khiến bạn nhận máy CPU:** `colab new` **không có `--gpu`** thì Colab
cấp **máy CPU** (mặc định). Lệnh thử ở mục 3 (`colab new -s thu`) và ví dụ trong hướng dẫn cài đặt
của Colab CLI đều là máy CPU. Muốn T4 phải xin rõ:

```bash
colab new -s fz --gpu T4
```

Script `start` đã làm việc này, **và kiểm lại ngay** bằng `nvidia-smi` trên máy vừa xin:

```
[fz] GPU cua VM: Tesla T4, 15360 MiB          <- đúng, đi tiếp
```

Nếu máy chỉ có CPU, script in `LOI: VM KHONG co GPU`, **tự trả máy** và dừng, không chạy tiếp.

Các lý do khác có thể khiến không có GPU:

| Hiện tượng | Nguyên nhân | Cách xử lý |
|---|---|---|
| `start` báo `phien 'fz' da ton tai` rồi `VM KHONG co GPU` | Còn phiên `fz` cũ là máy CPU | Script đã tự trả máy đó; chạy lại `start` để xin máy T4 mới (phiên `fz` cũ có GPU thì `start` dùng lại luôn) |
| `colab new --gpu T4` báo lỗi hết tài nguyên / quota | Tài khoản miễn phí đã dùng hết GPU trong ngày | Đợi vài giờ đến một ngày; hoặc Colab Pro |
| Lỡ `colab new` tay không `--gpu` | Mặc định là CPU | `colab stop -s <tên>` rồi xin lại có `--gpu T4` |
| Có nhiều phiên cùng lúc | `colab exec` không `-s` chỉ tự chọn khi có đúng 1 phiên | Luôn dùng `-s fz` (script đã làm) |

Kiểm bất cứ lúc nào:

```bash
bash colab_termux.sh gpu      # = colab sessions + colab status -s fz + nvidia-smi trên VM
```

`selfplay` và `train` cũng kiểm GPU trước khi chạy, nên không thể vô tình chạy trên CPU.

GPU khác: `GPU=L4 bash colab_termux.sh start` (L4, A100, H100, G4 cần Colab Pro / đơn vị tính toán).

---

## 6. Chạy một đời, từng bước

Ví dụ đời 0 → đời 1. Mọi lệnh gõ trong Termux, ở thư mục chứa script (`cd ~`).

### Bước 0 — chọn đời

```bash
export GEN=0          # giống GEN_CURRENT = 0 trong sổ tay
termux-wake-lock      # giữ Termux không bị ngủ (mục 8)
```

`export` chỉ sống trong phiên Termux hiện tại; mở cửa sổ Termux mới thì gõ lại.

### Bước 1 — `start` (mục 0, 1, 2 của sổ tay) · ~2-3 phút

```bash
bash colab_termux.sh start
```

Nó làm lần lượt:

1. `colab new -s fz --gpu T4` — xin máy; **kiểm GPU** (mục 5).
2. Clone mã nguồn nhánh `main`, tải **binary dựng sẵn** + ONNX Runtime qua `colab_quickstart.sh`.
   Phải thấy dòng `[quick] OK -- engine chay duoc tren Colab image nay.`
3. `pip install onnx onnxscript onnxruntime` (cho huấn luyện).
4. Nạp mạng đời `GEN` lên `/content/genN.onnx` và `.pt`, theo thứ tự ưu tiên:
   - có sẵn `Download/FairyZero/genN.onnx` / `.pt` trên điện thoại → **tải lên**;
   - không có và `GEN=0` → **tạo mạng đời 0** (`make_seed.py`, 144×12 SE-8) rồi tải về điện thoại;
   - không có và `GEN>0` → lấy từ **GitHub Release v3.0.0**.

Nếu `[quick]` báo lỗi (Colab đổi image, hoặc Release chưa có binary) → xem mục 10, "biên dịch lại".

### Bước 2 — `selfplay` (mục 3) · ~4,3 giờ

```bash
bash colab_termux.sh selfplay                 # mặc định --max-seconds 15480
SECS=3600 bash colab_termux.sh selfplay       # hoặc 1 giờ
```

Chạy với đúng cấu hình đã đo tốt nhất trên T4: `--visits 800 --max-moves 400 --temp-cutoff 32
--parallel 4 --fixed-batch 16 --noise-alpha 0.15 --search-opt max-prefetch=0`. Log ghi vào
`/content/selfplay.log` trên máy Colab. Lệnh trả về ngay; **có thể thoát Termux**.

> `--max-seconds` dừng mềm: hết giờ thì không nhận ván mới, ván đang chạy vẫn chơi nốt —
> thường vượt 2-3 phút. Đợi `status` báo **KHONG con tien trinh** rồi mới `fetch`.

### Bước 3 — `status` (theo dõi)

```bash
bash colab_termux.sh status          # log selfplay
N=40 bash colab_termux.sh status     # 40 dòng cuối thay vì 15
```

In: dòng log cuối, số tệp ván đã sinh, mức dùng GPU, và **DANG CHAY** hoặc **KHONG con tien trinh**.
Khi xong, cuối log có khối `--- Throughput ---` — so cấu hình bằng `NN eval/giay`, đừng bằng `Van/gio`.

### Bước 4 — `fetch` (mục 4) · vài phút

```bash
bash colab_termux.sh fetch
```

Gom hàng nghìn tệp `.gz` thành `/content/games_gen0.zip` (`archive.py pack`), rồi tải về
`Download/FairyZero/games_gen0.zip`. Đây là **bản gốc dữ liệu** của bạn — giữ cẩn thận.

### Bước 5 — `train` (mục 5) · 10-40 phút

```bash
bash colab_termux.sh train
bash colab_termux.sh status train     # theo dõi /content/train.log
```

Warm-start từ `/content/gen0.pt`, xuất `/content/gen1.onnx` và `gen1.pt`
(`--epochs 2 --batch 1024 --lr 1e-3 --amp --q-ratio 0.2 --weight-decay 1e-4 --channels 144 --blocks 12`).

**Cửa sổ trượt nhiều đời** — tải các zip cũ lên trước rồi truyền `DATA` (ngăn bằng dấu phẩy):

```bash
colab upload -s fz ~/storage/downloads/FairyZero/games_gen0.zip /content/games_gen0.zip
DATA="/content/games_gen0.zip,/content/games_gen1.zip" bash colab_termux.sh train
```

### Bước 6 — `getnet` · vài giây

```bash
bash colab_termux.sh getnet
```

Tải `gen1.onnx` và `gen1.pt` về `Download/FairyZero/`. **Làm trước khi `stop`.**

### Bước 7 — `arena` (mục 6) · ~30 phút

```bash
bash colab_termux.sh arena
bash colab_termux.sh status arena
```

48 ván gen1 đấu gen0, 400 visits. Nhớ: 48 ván vẫn sai số lớn (hàng trăm Elo); muốn phát hiện
chênh ~50 Elo cần 400-1000 ván.

### Bước 8 — `stop`

```bash
bash colab_termux.sh stop
termux-wake-unlock
```

⚠ `stop` **xoá sạch `/content`**. Kiểm chắc đã có `games_gen0.zip`, `gen1.onnx`, `gen1.pt` trong
`Download/FairyZero/` rồi mới trả máy. Không trả thì máy vẫn chiếm quota GPU của bạn.

### Tóm tắt một đời

```bash
export GEN=0; termux-wake-lock
bash colab_termux.sh start
bash colab_termux.sh selfplay
bash colab_termux.sh status            # lặp lại đến khi KHONG con tien trinh
bash colab_termux.sh fetch
bash colab_termux.sh train
bash colab_termux.sh status train      # lặp lại đến khi xong
bash colab_termux.sh getnet
bash colab_termux.sh arena             # tuỳ chọn
bash colab_termux.sh stop; termux-wake-unlock
```

---

## 7. Sang đời tiếp theo

```bash
export GEN=1
bash colab_termux.sh start     # thấy gen1.onnx/.pt trong Download/FairyZero -> tự tải lên
bash colab_termux.sh selfplay
…
```

Không cần đưa mạng lên GitHub Release: `start` ưu tiên tệp có sẵn trên điện thoại. Kiến trúc
`144 × 12` SE-8 phải giữ nguyên suốt chuỗi warm-start.

**Làm tiếp trên cùng máy (không `stop`):** nếu máy còn sống, chỉ cần `export GEN=1` rồi
`selfplay` — `gen1.onnx` vẫn nằm ở `/content`. Colab miễn phí tự ngắt sau tối đa khoảng 12 giờ,
nên một phiên thường chỉ đủ một đời với selfplay 4,3 giờ.

---

## 8. Giữ Termux sống khi tắt màn hình

Engine chạy trên Colab nên không phụ thuộc điện thoại. Nhưng Colab CLI có tiến trình **giữ máy khỏi bị
thu hồi vì "idle"**; chưa rõ tiến trình đó chạy ở điện thoại hay ở máy Colab. Để an toàn, trong suốt
lúc selfplay/train hãy giữ Termux sống:

- `termux-wake-lock` (hoặc kéo thanh thông báo Termux → **Acquire wakelock**).
- **Cài đặt → Ứng dụng → Termux → Pin → Không hạn chế** (tắt tối ưu pin). Trên Samsung còn phải bỏ
  Termux khỏi "Ứng dụng ngủ" / "Ứng dụng ngủ sâu".
- Đừng vuốt tắt Termux khỏi danh sách đa nhiệm.

Nếu Termux lỡ bị giết: mở lại, `bash colab_termux.sh gpu` xem máy còn không. Còn thì cứ `status`
tiếp; mất rồi thì dữ liệu trên máy đó mất theo (vì vậy nên selfplay theo lượt ngắn hơn nếu máy hay chết,
ví dụ `SECS=7200`, `fetch` sau mỗi lượt).

---

## 9. Lệnh Colab CLI dùng tay

Script chỉ là lớp bọc; lúc cần bạn gõ thẳng:

| Lệnh | Việc |
|---|---|
| `colab sessions` | Liệt kê các máy đang giữ |
| `colab status -s fz` | Phần cứng, cấu hình máy, trạng thái |
| `colab new -s fz --gpu T4` | Xin máy T4 (thiếu `--gpu` = CPU) |
| `echo '!nvidia-smi' \| colab exec -s fz` | Chạy một lệnh (cú pháp ô Colab: `!lệnh`, `%cd`) |
| `colab exec -s fz -f tep.py` | Chạy tệp Python trên máy |
| `colab console -s fz` | **Shell thật** (tmux) trên máy Colab — xem log trực tiếp: `tail -f /content/selfplay.log` (thoát tail: Ctrl+C) |
| `colab ls -s fz /content` | Liệt kê tệp trên máy |
| `colab upload -s fz <điện thoại> <máy>` | Tải lên |
| `colab download -s fz <máy> <điện thoại>` | Tải về |
| `colab log -s fz -o log.md` | Lưu lịch sử các lệnh đã chạy |
| `colab stop -s fz` | Trả máy |

Biến tuỳ chỉnh của script: `GEN` (đời), `SECS` (giây selfplay), `DATA` (dữ liệu train),
`N` (số dòng log), `GPU` (loại GPU, mặc định `T4`), `S` (tên phiên, mặc định `fz`),
`LOCAL` (thư mục trên điện thoại, mặc định `~/storage/downloads/FairyZero`).

---

## 10. Sự cố thường gặp

**Nhận máy CPU thay vì T4** → mục 5.

**`[quick]` báo lỗi ở `start`** — Release chưa có binary hoặc Colab đổi image, phải biên dịch lại
(8-12 phút). Máy vẫn giữ, làm tay:

```bash
colab console -s fz
# trong console:
bash /content/chess_variant_engine/custom_engine/scripts/colab_setup.sh 2>&1 | tail -4
bash /content/chess_variant_engine/custom_engine/scripts/colab_prebuilt.sh wrap
exit
# về Termux, lấy binary mới để đưa lên GitHub Release (tên đúng: custom_engine):
colab download -s fz /content/chess_variant_engine/custom_engine/build-linux/custom_engine ~/storage/downloads/FairyZero/custom_engine
```

Sau đó tiếp tục từ bước 4 của `start` bằng tay (tải mạng lên), hoặc `stop` rồi `start` lại sau khi đã
đưa binary lên Release.

**`status` báo KHONG con tien trinh quá sớm** — engine lỗi khi khởi động. Xem cả log:
`N=80 bash colab_termux.sh status`. Hay gặp: sai đường dẫn mạng (`/content/genN.onnx` không có —
kiểm `GEN`), hoặc máy không có GPU.

**`colab: command not found`** — `pip install` chưa xong hoặc lỗi; chạy lại mục 2.4.

**Đăng nhập hết hạn / báo lỗi quyền** — chạy lệnh bất kỳ cần máy (vd `colab sessions`) để nó in lại
link đăng nhập, làm lại mục 3.

**`$'\r': command not found`** — tệp script mang xuống dòng kiểu Windows: `sed -i 's/\r$//' ~/colab_termux.sh`.

---

Tham khảo: [google-colab-cli](https://github.com/googlecolab/google-colab-cli) ·
[Hướng dẫn cài trên Termux (issue #131)](https://github.com/googlecolab/google-colab-cli/issues/131) ·
tham số engine đầy đủ: `HUONG_DAN.md` mục D.
