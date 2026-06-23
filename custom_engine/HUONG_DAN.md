# FairyZero — Sách hướng dẫn sử dụng

FairyZero là một engine cờ AlphaZero cho **biến thể cờ 10×10** của bạn: nó tự học bằng cách
tự chơi (self-play) → huấn luyện mạng nơ-ron → mạnh dần qua từng đời. Bản portable này cho
phép bạn **chơi với AI**, **tự sinh dữ liệu huấn luyện**, và **huấn luyện** — trên **Windows
(CPU)** lẫn **Google Colab (GPU)**.

> Bạn **không cần biết lập trình** để dùng. Cứ làm theo từng bước, copy-paste lệnh.

---

## 0. Trong bản portable có gì?

```
FairyZero/
├─ custom_engine.exe         ← engine (chơi + sinh dữ liệu) cho Windows
├─ onnxruntime.dll, *.dll    ← thư viện đi kèm (đừng xóa)
├─ play.bat                  ← bấm đúp để chơi nhanh
├─ models/seed.onnx          ← mạng khởi đầu (đời 0) để chơi/huấn luyện
├─ python/                   ← bộ huấn luyện (train.py, archive.py, make_seed.py, …)
│   └─ requirements.txt
├─ engine_src/               ← mã nguồn engine (để build bản GPU trên Colab)
├─ scripts/colab_setup.sh    ← script dựng engine trên Colab (build lần đầu)
├─ scripts/colab_prebuilt.sh ← lưu/khôi phục engine đã build (phiên sau khỏi build lại)
├─ VERSION.txt
└─ HUONG_DAN.md              ← tệp này
```

**3 việc bạn làm được:** (A) Chơi với AI · (B) Sinh dữ liệu tự chơi · (C) Huấn luyện đời mạnh hơn.

---

## 0b. Tự dựng bản portable từ mã nguồn + tạo mạng 0-ELO (cho người build)

> Nếu bạn đã có sẵn thư mục `FairyZero` thì **bỏ qua mục này** — nó chỉ dành cho người dựng lại từ mã nguồn.

**Chuẩn bị (Windows):** cài **MSYS2**, mở *MSYS2 UCRT64*, cài công cụ build:
```
pacman -S mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-meson mingw-w64-ucrt-x86_64-ninja mingw-w64-ucrt-x86_64-zlib
```
Engine cần `third_party/onnxruntime-win-x64-1.18.0/` (SDK ONNX Runtime) — đừng xóa thư mục này.

**Bước 1 — Build engine** (trong shell có `C:\msys64\ucrt64\bin` trên PATH):
```
meson setup build          # chỉ lần đầu (cấu hình)
ninja -C build             # build lại mỗi khi sửa mã nguồn
```
→ ra `build\custom_engine.exe` + `build\onnxruntime.dll`. Kiểm tra: `build\custom_engine.exe --test-uci` phải `[PASS]`.

> **(Tùy chọn) Build hỗ trợ iGPU/GPU bằng DirectML** — để chơi nhanh hơn CPU-only trên card Intel/AMD/NVIDIA
> bất kỳ của Windows. Tải gói **ONNX Runtime DirectML** (`onnxruntime-win-x64-directml-1.18.0`, có
> `DirectML.dll` + `dml_provider_factory.h`) vào `third_party\`, rồi cấu hình lại:
> ```
> meson setup build-dml -Duse_dml=true     # (hoặc: meson configure build -Duse_dml=true)
> ninja -C build-dml
> ```
> ⚠️ **Tùy chọn meson bám theo TỪNG thư mục build.** Phải cấu hình `build-dml` với `-Duse_dml=true` **và
> chạy đúng `build-dml\custom_engine.exe`** — nếu `ninja -C build` (thư mục CPU cũ) hoặc chạy nhầm exe cũ thì
> `-DUSE_DML` không có → engine in cảnh báo "EP not compiled" rồi fallback CPU. Khi đúng, log phải là
> `DirectML Execution Provider appended` + `GPU profile activated (dml)`.
> Khi chơi, bật bằng `setoption name Provider value dml` (hoặc `--play --provider dml`). Bản CPU thường
> **không bị ảnh hưởng** (mã DirectML nằm trong `#ifdef USE_DML`).
>
> 📊 **Số liệu thực đo (Iris Xe, mạng 10×128, sau warm-up):** DirectML **~140–200 NPS** so với **CPU
> `BackendThreads=4` ~60–106 NPS** → **DML NHANH HƠN ~2× cho việc chơi.** **Khuyến nghị: dùng `Provider=dml`
> để chơi** nếu đã có bản `build-dml`; CPU + `BackendThreads`/`Threads` (A.4) là phương án dự phòng chắc ăn.
> ⚠️ **Warm-up:** lần chạy DirectML ĐẦU TIÊN sau khi khởi động chậm bất thường (~32 NPS) do driver phải
> biên dịch shader **một lần**; sau vài chục giây / sau nước đầu mới đạt tốc độ thật. Đừng đánh giá DML qua nước đầu.

**Bước 2 — Tạo mạng khởi đầu "0-ELO"** (mạng khởi tạo ngẫu nhiên, chưa học gì):
```
python python\make_seed.py --out models\seed.onnx
```
→ ra `models\seed.onnx` (cho engine chơi) **và** `models\seed.pt` (để warm-start huấn luyện đời 1).
(Tự tạo thư mục `models\` nếu chưa có.)

**Các núm khởi tạo mạng (chỉ `make_seed.py`):** mạng `FairyNet` có đúng **3 núm KIẾN TRÚC** —
`--channels` (độ rộng, mặc định 128) · `--blocks` (độ sâu, 10) · `--se-ratio` (nén SE block, 8). Cả ba
**phải khớp y hệt giữa seed ↔ MỌI đời `train.py`**, nếu khác thì không nạp được trọng số cũ (vỡ warm-start).
Ngoài ra `--seed` (mặc định 0) chỉ để **tái lập** kết quả ngẫu nhiên, **không** phải kiến trúc.
`--dropout` **không** thuộc nhóm này — nó là loại "hàm" (không sinh tham số, tắt khi chơi), nên an toàn
warm-start và không cần đặt ở seed. Đó là **toàn bộ** núm khởi tạo; phần còn lại của mạng (value head,
policy head, số plane đầu vào…) **cố định cứng** trong `model.py`.

**Chọn kích thước thân mạng (b×f) — đừng để bị "tê liệt".** Ký hiệu `block × filter` là **chuẩn** của
AlphaZero/lc0. Thang cỡ quen thuộc:

| Hạng | b×f điển hình |
|---|---|
| Nhỏ / CPU | `6×64` · `8×96` · **`10×128`** · `16×128` |
| Vừa | `20×256` · `24×320` |
| Lớn (siêu nhân) | `30×384` · `40×512`  (AlphaZero gốc: `20×256`) |

- **Nguyên tắc nhỏ-nhanh** (cho dự án một mình + Colab + mục tiêu ~2000 + search 30s/nước): **chọn thân
  đủ NHỎ để vòng lặp chạy nhanh.** Sức mạnh đến từ *số ván × số đời*, **không** từ kích thước net; thân
  nhỏ → NPS cao hơn + self-play nhanh hơn + cần ít data hơn. → **Khuyến nghị mặc định: `10×128` SE-8.**
  Sâu/rộng hơn (vd `15×128`) đều hợp lệ nhưng **làm chậm** sinh-dữ-liệu/huấn-luyện; đừng nhắm cỡ "siêu nhân".
- **Không cần chọn đúng ngay — chốt bằng SỐ LIỆU về sau.** Dữ liệu `.gz` **độc lập với kích thước thân**
  (chỉ phụ thuộc định dạng I/O cố định). Khi đã có pool ván kha khá: train vài ứng viên (`8×96` / `10×128`
  / `15×128`) trên **CÙNG pool** rồi cho `--arena` đấu nhau → giữ con thắng. Đổi thân = **một lần train
  (vài giờ)**, không phải sinh lại data (hàng ngày).
- **Lưu ý SE:** mức nén = `filter ÷ ratio` phải **chia hết**. `128/8 = 16` (đẹp). Muốn "SE rộng kiểu lc0"
  (lc0 nén 192→32) thì ở 128 filter dùng `--se-ratio 4` (→32), **đừng** dùng 6 (`128/6` lẻ → bị làm tròn).

**Bước 3 — Đóng gói bản portable** (gom exe + DLL + Python + mã nguồn + seed + sách thành 1 thư mục chạy được trên máy Windows sạch):
```
powershell -ExecutionPolicy Bypass -File scripts\package.ps1
```
→ ra `dist\FairyZero\`. Mặc định bundle bản **CPU** (lấy từ `build\`). Tham số hữu ích:
- `-Dml` — đóng gói bản **DirectML** (lấy từ `build-dml\`) thay cho CPU. **Một bundle phục vụ CẢ `Provider=cpu`
  lẫn `Provider=dml`** (vì `onnxruntime.dll` bản DirectML chứa cả hai EP), có kèm `DirectML.dll`. Cần build
  `build-dml` trước (`meson setup build-dml -Duse_dml=true; ninja -C build-dml`).
- `-Model models\model_gen5.onnx` — đóng gói một mạng đã train làm `seed.onnx` (mặc định: tự sinh seed 0-ELO qua `make_seed.py`).
- `-Zip` — tạo thêm `dist\FairyZero.zip` để chép đi.
- `-OutDir <đường dẫn>` — đổi nơi xuất. `-Ucrt64Bin <...>` — chỉ chỗ DLL nếu MSYS2 không ở `C:\msys64`.

> **Về "1 bản portable cuda+dml+cpu":** CPU+DML gộp được vào một bundle (`-Dml`). **CUDA thì KHÔNG** đặt
> vào bản Windows portable (cần `onnxruntime.dll` bản CUDA + CUDA toolkit cài sẵn) — CUDA là đường **Colab/Linux**,
> dùng `engine_src/` kèm trong bundle để build lại bằng `colab_setup.sh`.

> **Lưu ý về biến thể:** luật cờ (10×10, bắt tốt qua đường, **7 lần chiếu = thắng**, các quân tùy biến…)
> được **nhúng thẳng trong engine** ở `src/app/variant_setup.cc` (một chuỗi `ini` đăng ký biến thể
> `custom_10x10_variant`), **không** đọc từ tệp `variants.ini` ngoài. Muốn đổi luật thì sửa chuỗi đó rồi
> build lại — sửa `variants.ini` bên ngoài sẽ KHÔNG có tác dụng. (Xem mục A để hiểu vì sao FEN có trường `7+7`.)

---

## A. CHƠI VỚI AI

### A.1. Cách nhanh nhất (Windows)
Mở thư mục `FairyZero`, **bấm đúp `play.bat`** (hoặc mở PowerShell tại đó và gõ `.\play.bat`).
Engine khởi động ở chế độ **UCI** và chờ lệnh. Gõ thử:
```
uci
isready
position startpos
go nodes 800
```
Engine trả về dòng `bestmove <nước đi>` — đó là nước AI chọn. Để AI đi mạnh hơn, tăng `go nodes`
(vd `go nodes 5000`); chậm hơn nhưng giỏi hơn. Gõ `quit` để thoát.

### A.2. Quy ước nước đi (QUAN TRỌNG cho GUI bạn tự viết)
- Ô cờ: **cột `a`–`j`** (10 cột) + **hàng `1`–`10`** (10 hàng). **Hàng 10 có HAI chữ số.**
- Nước đi = ô xuất phát + ô đích, vd `e2e4`, `a1a10`, `j9j10`.
- Phong cấp: thêm ký tự quân ở cuối, vd `a9a10v` (phong thành quân `v`).
- Trắng ở phía dưới (hàng 1,2,3…), Đen ở trên (hàng 8,9,10).

GUI của bạn chỉ cần **gửi/nhận đúng các chuỗi này** qua UCI là điều khiển được engine. Engine
tự xử lý việc lật bàn cho quân Đen — bạn luôn nói chuyện bằng tọa độ thật.

### A.2b. Chơi ngay trong terminal không cần GUI (`--play`)
Muốn thử nhanh, chạy bàn cờ ASCII trong terminal:
```
custom_engine.exe --play --weights models\seed.onnx --visits 800   (bạn cầm Trắng)
custom_engine.exe --play-black --weights models\seed.onnx           (bạn cầm Đen)
```
Engine in bàn cờ (chữ HOA = Trắng, thường = Đen), hỏi `Your move:`, bạn gõ nước (vd `b3b4`), AI đáp.
Gõ `quit` để thoát. Đây là tiện ích thử nhanh; đường chính để cắm GUI vẫn là `--uci-nn`.

### A.3. Một ván qua lệnh UCI (mẫu)
```
uci
isready
ucinewgame
position startpos
go nodes 1500           → engine: bestmove b3b4   (bạn cho AI cầm Trắng)
position startpos moves b3b4 <nước-của-bạn>
go nodes 1500           → engine: bestmove ...
... lặp lại ...
quit
```
Mỗi lượt: bạn cập nhật `position startpos moves <toàn bộ nước đã đi>` rồi `go` để AI nghĩ nước tiếp.

### A.4. Tinh chỉnh khi chơi (lệnh `setoption`)
Gõ trước khi `go`. Cú pháp: `setoption name <Tên> value <Giá trị>`.

| Tên | Mặc định | Ý nghĩa |
|-----|----------|---------|
| `WeightsFile` | seed.onnx | Đổi mạng nơ-ron engine đang dùng → chọn đời mạnh/yếu khác nhau (đời cao thường mạnh hơn). Vd: `setoption name WeightsFile value models\model_gen5.onnx`. |
| `Visits` | 800 | **Núm chỉnh sức cờ chính.** Số lần MCTS "nghĩ" (playout) mỗi lượt khi `go` không kèm `nodes`. Càng cao càng mạnh nhưng càng chậm. |
| `Threads` | 1 | Số luồng tìm kiếm chạy song song. Máy nhiều nhân → đặt cao hơn để nghĩ nhanh hơn (không làm yếu đi). |
| `Provider` | cpu | Thiết bị tính mạng: `cpu` (bản thường) · `cuda` (bản build GPU NVIDIA, Colab) · `dml` (DirectML — iGPU/GPU bất kỳ trên Windows, **chỉ khi build `-Duse_dml`**). Provider không được biên dịch vào bản này sẽ **tự cảnh báo + lùi về CPU**. |
| `FixedBatch` | 16 | Số thế gom lại đẩy GPU tính một lần (chỉ khi `cuda`). Lớn → GPU hiệu quả hơn. Bản CPU bỏ qua. |
| `BackendThreads` | 1 | Số luồng tính toán mạng nơ-ron trên CPU. Tăng nếu CPU còn nhân rảnh và muốn eval mạng nhanh hơn. |
| `PolicySoftmaxTemp` | 1.359 (khớp lc0) | Làm "mềm" gợi ý nước đi của mạng (chia logit policy). >1 (mặc định) cho các nước phụ thêm cơ hội được xét; <1 dồn niềm tin vào vài nước top. |
| `MoveOverheadMs` | 30 | Thời gian (ms) trừ hao mỗi nước để bù độ trễ truyền lệnh, tránh vượt giờ khi đánh cờ có đồng hồ (`go movetime`/`wtime`). |
| `Temperature` | 0 | **Núm hạ độ khó.** 0 = luôn đi nước tốt nhất (mạnh nhất). >0 (đơn vị phần nghìn ‰) → đôi khi đi nước hạng 2/3 → đa dạng và yếu đi. Vd 500 = khá ngẫu nhiên. |
| `TempCutoffPly` | 0 | Chỉ áp `Temperature` trong N nước đầu ván, sau đó đánh hết sức. 0 = áp suốt ván. Dùng để đầu ván đa dạng mà cuối ván vẫn chuẩn. |
| `MultiPV` | 1 | Số biến chính (PV) engine báo cáo trong `info`. Đặt 3 → in 3 nước hay nhất kèm phân tích. **Không** làm engine nghĩ lâu hơn (chỉ là báo cáo). |
| `ReuseTree` | true | Giữ lại cây MCTS đã dựng để tái dùng cho nước sau (đỡ tính lại từ đầu → nhanh hơn). Nên để bật. |

Điều khiển thời gian: `go nodes N` · `go movetime 3000` (3 giây) · `go wtime W btime B` (cờ có đồng hồ) ·
`go infinite` rồi `stop`. Engine phát `info ... score cp ... wdl ... pv ...` để GUI hiển thị đánh giá/biến chính.

> **Lệnh `d` (debug, kiểu Fairy-Stockfish):** gõ `d` để in bàn cờ ASCII + `Fen:` (tọa độ thật) của thế cờ
> hiện tại — tiện để kiểm tra/sao chép FEN. (Phải gửi `position ...` trước.)

#### Trường nhập thành trong FEN (khi tự nạp `position fen ...`)
Biến thể này chấp nhận **hai cách viết tương đương** cho trường nhập thành — chúng cho **cùng một thế cờ**
(đã kiểm chứng: cùng Zobrist key):

| Cách viết | Ý nghĩa | Ví dụ (đủ 4 quyền) |
|---|---|---|
| **Chuẩn `KQkq`** | gọi theo **cánh**: K/Q = cánh vua/cánh hậu (Trắng), k/q = (Đen) | `KQkq` |
| **Chữ-cái-cột `BIbi`** (X-FEN, giống variants.ini) | gọi thẳng theo **cột xe**: `I`=cột i (cánh vua), `B`=cột b (cánh hậu); HOA=Trắng, thường=Đen | `BIbi` |

Lý do tương đương: Fairy-Stockfish phiên dịch `K`/`Q` sang **cột xe** dựa trên định nghĩa biến thể
(`castlingRookKingsideFile = i` → `K`, `castlingRookQueensideFile = b` → `Q`). Bên trong nó luôn lưu theo
ô xe; lúc in (`d`/FEN) thì **chuẩn hóa về `KQkq`**.

- **Nên dùng `KQkq`** (hoặc quyền lẻ `K`/`Q`/`k`/`q`) cho thế bình thường — gọn, dễ tương thích GUI khác.
- Kiểu `BIbi` chỉ cần khi dựng thế **bất thường kiểu Chess960** (xe nằm cột lạ), vì nó nêu đích danh cột xe.
- **Không nhập thành: `-`**.
- ⚠️ Quyền chỉ "dính" nếu **vua + xe đang ở ô gốc**; ghi quyền mà quân không đúng chỗ thì engine tự bỏ.
  Cách chắc ăn: nạp xong gõ `d` để engine in lại FEN hợp lệ rồi copy dùng.

> **Độ khó gợi ý:** Dễ = `Visits 80` + `Temperature 500` · Vừa = `go nodes 400` · Khó = `go nodes 5000` + `Temperature 0`.

**Chỉnh sâu kiểu lc0 (tùy chọn):** đặt thẳng tham số tìm kiếm của lc0 bằng tên gốc, vd:
`setoption name cpuct value 2.5` · `setoption name draw-score value -0.2` · `setoption name fpu-value value 0.4`.

### A.5. Cắm vào GUI tự viết
GUI chỉ cần chạy tiến trình: `custom_engine.exe --uci-nn --weights models\seed.onnx` rồi nói
UCI qua stdin/stdout (uci → uciok; isready → readyok; position …; go …; nhận bestmove). Engine
tuân thủ giao thức UCI chuẩn, nên mọi GUI nói đúng UCI đều dùng được.

---

## B. SINH DỮ LIỆU TỰ CHƠI

Engine tự đánh với chính nó hàng trăm/ngàn ván và ghi lại để huấn luyện. **Phần này do engine
C++ làm (nhanh), không phải Python.**

### B.1. Trên Windows (CPU)
Mở PowerShell tại thư mục `FairyZero`:
```
.\custom_engine.exe --selfplay --games 200 --visits 200 --parallel 6 `
    --weights models\seed.onnx --out games_gen0
```
- `--games` số ván · `--visits` độ sâu mỗi nước · `--parallel` số ván chạy song song
  (đặt ≈ số nhân CPU) · `--out` thư mục lưu (mỗi ván 1 tệp `.gz`).
- Đời đầu nên để `--visits 200` cho nhanh; đời sau tăng `400`/`800`.

### B.2. Trên Google Colab (GPU — nhanh hơn nhiều)
Đã dựng engine Linux theo **Mục C.4 bước 1–3** (chạy `colab_setup.sh`). Sinh dữ liệu **vào ổ local
`/content`** (ĐỪNG sinh thẳng lên Drive vì FUSE rất chậm với nhiều tệp nhỏ):
```
!/content/FairyZero/engine_src/build-linux/custom_engine --selfplay \
    --games 1000 --visits 200 --parallel 2 --provider cuda --fixed-batch 32 \
    --weights /content/FairyZero/models/seed.onnx --out /content/games_gen0
```
- Khác bản Windows ở chỗ thêm `--provider cuda --fixed-batch 32` (chạy mạng trên GPU).
- GPU mạnh hơn nên đặt `--games` lớn (1000+); `--parallel` để nhỏ (2) vì GPU là nút cổ chai, không phải CPU.
- Muốn giữ dữ liệu lên Drive thì gói 1 zip trước (xem B.4) rồi mới chép.

### B.3. Tự xin thua sớm (resign) — tăng tốc (cả Windows lẫn Colab)
Mặc định TẮT. Bật để bỏ qua các ván đã thua rõ (nhanh hơn), vẫn giữ ~10% ván đánh tới cùng — thêm
vào lệnh `--selfplay` ở B.1/B.2:
```
... --resign-threshold -0.90 --resign-consecutive 3 --no-resign-frac 0.10
```

### B.4. Đóng gói dữ liệu thành 1 tệp `.zip` (để tải lên Drive / cho gọn)
Hàng ngàn tệp `.gz` nhỏ tải lên Drive rất chậm. Gom thành **1 tệp** (`archive.py` chạy được trên cả
Windows lẫn Colab):
```
# Windows:
python python\archive.py pack games_gen0 --out games_gen0.zip
# Colab:
!python /content/FairyZero/python/archive.py pack /content/games_gen0 --out /content/games_gen0.zip
```
Khi huấn luyện, `train.py --data games_gen0.zip` **đọc thẳng tệp `.zip`** (KHÔNG cần giải nén).

---

## C. HUẤN LUYỆN ĐỜI MẠNH HƠN

### C.0. Cài thư viện Python (làm 1 lần)
```
pip install -r python\requirements.txt
```

### C.1. Toàn cảnh: vòng đời 2 bước (làm TAY, tách bạch)
Bản portable **không** gộp sinh dữ liệu và huấn luyện vào một lệnh tự động — bạn điều khiển từng
bước cho dễ quan sát:
1. **Sinh dữ liệu** bằng mạng đời N (Mục B) → thư mục `games_genN` (hoặc gói `.zip`).
2. **Huấn luyện** trên dữ liệu đó, warm-start từ `.pt` đời N → ra mạng **đời N+1**.
3. Lặp lại: bước 1 dùng mạng đời N+1, bước 2 dùng cửa sổ vài đời gần nhất.

> **`.onnx` vs `.pt`:** `.onnx` = mạng engine C++ chạy (chơi / sinh dữ liệu). `.pt` = bản lưu để
> huấn luyện tiếp (warm-start). Mỗi lần train sinh ra **cả hai** cùng tên.

### C.2. Huấn luyện một đời (`train.py`)
```
python python\train.py --data games_gen0 --epochs 10 --batch 256 `
    --init-from models\seed.pt --out models\model_gen1.onnx
```
- `--data` = một thư mục, **nhiều thư mục** ngăn bằng dấu phẩy (chính là cách làm cửa sổ trượt),
  hoặc một tệp `.zip` (đọc **thẳng**, KHÔNG cần giải nén).
- `--init-from <.pt>` = học tiếp từ đời trước (warm-start). Bỏ đi nếu train từ đầu.
- Kết quả: `model_gen1.onnx` (cho engine chơi) **và** `model_gen1.pt` (để train đời sau).

### C.3. Chuỗi nhiều đời bằng TAY (Windows, CPU — để thử nhanh)
Mỗi đời = 1 lần sinh (Mục B) + 1 lần train. Ví dụ đi từ `seed` → đời 1 → đời 2:
```
# --- Đời 1: sinh bằng seed, train warm-start từ seed.pt ---
.\custom_engine.exe --selfplay --games 40 --visits 64 --parallel 6 `
    --weights models\seed.onnx --out games_gen0
python python\train.py --data games_gen0 --epochs 8 --batch 256 `
    --init-from models\seed.pt --out models\model_gen1.onnx

# --- Đời 2: sinh bằng mạng đời 1, train trên CỬA SỔ 2 đời gần nhất ---
.\custom_engine.exe --selfplay --games 40 --visits 64 --parallel 6 `
    --weights models\model_gen1.onnx --out games_gen1
python python\train.py --data games_gen0,games_gen1 --epochs 8 --batch 256 `
    --init-from models\model_gen1.pt --out models\model_gen2.onnx
```
- **Warm-start:** luôn `--init-from` bằng tệp `.pt` của đời **vừa dùng để sinh** dữ liệu.
- **Cửa sổ trượt:** truyền vài thư mục `games_gen*` gần nhất vào `--data` (ngăn bằng phẩy); đời quá cũ thì bỏ bớt.
- **(Tùy chọn) đấu thử** đời mới có mạnh hơn đời cũ không — xem **D.4**:
  `.\custom_engine.exe --arena --model-a models\model_gen2.onnx --model-b models\model_gen1.onnx --games 20 --visits 200`

### C.4. Trên Google Colab (GPU — KHUYẾN NGHỊ để huấn luyện thật)
Windows của bạn không có GPU nên huấn luyện chậm; Colab có GPU miễn phí. Vẫn là **2 bước tách bạch** như trên.
1. Tải cả thư mục `FairyZero` lên Google Drive (hoặc đẩy mã nguồn lên GitHub rồi `git clone`).
2. Mở Colab notebook mới, chọn **Runtime → Change runtime type → GPU**.
3. **Chép sang ổ local của Colab rồi build** (build trên Drive RẤT chậm + hay lỗi do FUSE):
   ```
   !cp -r /content/drive/MyDrive/FairyZero /content/FairyZero
   !bash /content/FairyZero/scripts/colab_setup.sh
   ```
   Script tự dò mã nguồn, tải onnxruntime GPU, build, chạy test. Engine Linux nằm ở
   `/content/FairyZero/engine_src/build-linux/custom_engine`. Khi xong, script in sẵn 2 lệnh mẫu (bước 4 và 5).
   - Nếu Colab dùng CUDA 11.x: `!ORT_VER=1.18.0 bash /content/FairyZero/scripts/colab_setup.sh`

   **3b. Phiên sau KHỎI build lại** (đỡ vài phút biên dịch + tải ORT). Có **2 cách tương đương**, chọn 1:

   **Cách 1 — cache riêng trên Drive** (giữ bundle gọn, chỉ chứa mã nguồn):
   ```
   # CHẠY MỘT LẦN, ngay sau khi colab_setup.sh build xong:
   !bash /content/FairyZero/scripts/colab_prebuilt.sh save        # -> MyDrive/FairyZero_prebuilt
   # Các phiên SAU (vài giây, KHÔNG build):
   !cp -r /content/drive/MyDrive/FairyZero /content/FairyZero
   !bash /content/FairyZero/scripts/colab_prebuilt.sh restore
   ```

   **Cách 2 — build THẲNG vào bundle** (binary nằm luôn trong bundle, không cần thư mục cache riêng):
   ```
   # CHẠY MỘT LẦN: build trên ổ local rồi chép binary + libs NGƯỢC vào bundle trên Drive
   !bash /content/FairyZero/scripts/colab_setup.sh
   !cp -r /content/FairyZero/engine_src/build-linux /content/drive/MyDrive/FairyZero/engine_src/
   !cp -r /content/FairyZero/engine_src/third_party /content/drive/MyDrive/FairyZero/engine_src/
   # Các phiên SAU: copy bundle (đã kèm binary) về local, rồi chỉ cần tạo wrapper + kiểm tra:
   !cp -r /content/drive/MyDrive/FairyZero /content/FairyZero
   !bash /content/FairyZero/scripts/colab_prebuilt.sh wrap
   ```
   > Lưu ý: **đừng build trực tiếp trên Drive** (FUSE rất chậm + hay lỗi) — luôn build ở `/content` local rồi
   > mới chép artefact ngược vào bundle trên Drive. Bù lại, bundle sẽ nặng thêm (~vài trăm MB do libs ORT).

   **CẢ HAI cách** đều sinh **wrapper `run.sh`** (tự đặt `LD_LIBRARY_PATH` + lib CUDA) và tự chạy `--test-uci`.
   Sau đó **luôn chạy engine qua wrapper** (vì mỗi ô `!` của Colab là shell mới, biến môi trường không sống sót
   qua ô khác):
   ```
   !bash /content/FairyZero/engine_src/run.sh --selfplay --games 1000 --visits 400 --provider cuda --fixed-batch 32 \
       --weights /content/FairyZero/models/seed.onnx --out /content/games_gen0
   !bash /content/FairyZero/engine_src/run.sh --arena --model-a ... --model-b ... --provider cuda
   ```
   > **Khi nào vẫn phải build lại** (hiếm — script tự báo và thoát lỗi): Colab đổi ảnh nền (glibc/Ubuntu) ⇒
   > binary không chạy; hoặc Colab đổi **CUDA major** ⇒ EP CUDA không nạp được (CPU vẫn chạy). Khi đó chạy
   > `colab_setup.sh` một lần rồi lưu lại (cách 1: `save`; cách 2: chép artefact vào bundle). Đổi nơi cache bằng
   > `FZ_CACHE=...`; đổi ORT bằng `ORT_VER=1.18.0 bash ... save`.

4. **Bước 1 — sinh dữ liệu trên GPU** (sinh vào ổ local `/content`, ĐỪNG sinh thẳng lên Drive):
   ```
   !/content/FairyZero/engine_src/build-linux/custom_engine --selfplay \
       --games 1000 --visits 200 --parallel 2 --provider cuda --fixed-batch 32 \
       --weights /content/FairyZero/models/seed.onnx --out /content/games_gen0
   ```
5. **Bước 2 — huấn luyện đời mới** (warm-start từ `.pt` đời trước, `--amp` bật FP16 cho nhanh):
   ```
   !python /content/FairyZero/python/train.py --data /content/games_gen0 \
       --epochs 20 --batch 1024 --amp \
       --init-from /content/FairyZero/models/seed.pt --out /content/model_gen1.onnx
   ```
6. **Lưu mạng về Drive** để giữ, rồi tải về máy đặt vào `FairyZero\models\` mà chơi (Mục A):
   ```
   !cp /content/model_gen1.onnx /content/model_gen1.pt /content/drive/MyDrive/FairyZero/models/
   ```
7. Lặp lại bước 4–6 cho đời sau: đổi `--weights` → `model_gen1.onnx`, `--init-from` → `model_gen1.pt`,
   `--out` → `model_gen2`, và `--data` thành cửa sổ `/content/games_gen0,/content/games_gen1`.

> **Gọn dữ liệu để giữ trên Drive (tùy chọn):** gói nghìn tệp `.gz` thành **1 zip** trước khi chép —
> `!python /content/FairyZero/python/archive.py pack /content/games_gen0 --out /content/games_gen0.zip` —
> rồi train đọc thẳng zip đó (`--data /content/games_gen0.zip`), KHÔNG cần giải nén.

---

## D. DANH MỤC SIÊU THAM SỐ (tra cứu nhanh)

> Mỗi phần ghi rõ **DÙNG ĐƯỢC** (chỉnh được ngay) và **CHƯA DÙNG ĐƯỢC** (chưa có nút, chạy ở
> giá trị mặc định) để bạn biết giới hạn hiện tại.

#### D.0. Windows hay Colab đều dùng được TẤT CẢ các cờ — chỉ nhóm cờ GPU là khác

**CÓ — gần như toàn bộ cờ giống hệt trên cả hai**, vì **cùng một mã nguồn**:
- Engine trên Windows và engine Linux trên Colab build từ **cùng `engine_src/`** → bộ phân tích cờ CLI
  y hệt → mọi cờ `--selfplay` ở **D.2** (gồm `--search-opt`, `--resign-*`, `--noise-*`, `--cpuct`,
  `--policy-temp`, `--start-fen`…) đều tồn tại và xử lý **như nhau** trên cả hai.
- `train.py` là **cùng một tệp Python** được chép vào bundle → mọi cờ ở **D.3** (`--optimizer`,
  `--lr-values/boundaries`, `--se-ratio`, `--dropout`, `--accum-steps`, `--diff-focus`,
  `--swa-start-frac`, `--grad-clip`…) đều có **y hệt** trên cả Windows lẫn Colab.

→ Tất cả các cờ "thuật toán thuần" (tinh chỉnh sức cờ, độ ngẫu nhiên, resign, optimizer, lịch LR,
regularization…) chạy **giống nhau** dù CPU hay GPU.

**Ngoại lệ duy nhất: nhóm cờ GPU** — được chấp nhận ở cả hai nhưng chỉ **"có tác dụng" trên Colab**:

| Cờ | Windows (bản CPU trong bundle) | Colab (bản build GPU) |
|----|-------------------------------|----------------------|
| `--provider cuda` / `--fixed-batch` (sinh dữ liệu) | Nhận cờ nhưng **không dùng GPU** (bản Windows không có CUDA EP) → thực chất chạy CPU | Dùng GPU thật |
| `--amp` (train) | **Tự bỏ qua an toàn**: `use_amp = amp AND device==cuda` (`train.py:150`) → no-op, không lỗi | Bật FP16 thật |
| `--device cuda` (train) | Tự **cảnh báo + lùi về cpu** (`train.py:147-149`), không crash | Chạy trên cuda |
| `--pin-memory` (train) | Vô hại / không lợi (chỉ giúp chuyển dữ liệu lên GPU) | Có lợi |

> Tóm lại: bạn **gõ được mọi cờ trên cả hai môi trường mà không lỗi cú pháp**; chỉ 4 cờ GPU ở trên là
> chỉ thật sự phát huy khi chạy bản GPU (Colab). Muốn dùng GPU trên Windows phải tự build bản `-Duse_cuda`.

### D.1. Khi CHƠI (`--uci-nn`, lệnh `setoption name <X> value <Y>`)

**DÙNG ĐƯỢC — option thân thiện:**
| Option | Mặc định | Ý nghĩa |
|--------|----------|---------|
| `WeightsFile` | seed.onnx | Đổi mạng nơ-ron đang dùng (chọn đời mạnh/yếu); đời cao thường mạnh hơn. |
| `Visits` | 800 | Số playout MCTS mỗi nước khi `go` không kèm `nodes`. **Núm chỉnh sức cờ chính** — cao = mạnh + chậm. |
| `Threads` | 1 | Số luồng MCTS chạy song song; máy nhiều nhân đặt cao → nghĩ nhanh hơn (không yếu đi). |
| `Provider` | cpu | `cpu` / `cuda` (bản build GPU NVIDIA) / `dml` (DirectML iGPU/GPU Windows, chỉ khi build `-Duse_dml`). |
| `FixedBatch` | 16 | Số thế gom đẩy GPU tính một lần (chỉ khi `cuda`); lớn → GPU hiệu quả hơn. |
| `BackendThreads` | 1 | Số luồng tính mạng nơ-ron trên CPU; tăng nếu còn nhân rảnh. |
| `PolicySoftmaxTemp` | **1.359** (khớp lc0) | Làm "mềm" gợi ý mạng: >1 cho nước phụ thêm cơ hội, <1 dồn vào vài nước top. |
| `MoveOverheadMs` | 30 | Thời gian (ms) trừ hao mỗi nước để bù độ trễ, tránh vượt giờ khi đánh có đồng hồ. |
| `Temperature` | 0 | **Núm hạ độ khó** (đơn vị ‰): 0 = đi nước tốt nhất; >0 → đôi khi đi nước hạng 2/3, đa dạng + yếu đi. |
| `TempCutoffPly` | 0 | Chỉ áp `Temperature` trong N nước đầu rồi đánh hết sức; 0 = áp suốt ván. |
| `MultiPV` | 1 | Số biến chính (PV) báo cáo trong `info`; **không** làm engine nghĩ lâu hơn (chỉ là báo cáo). |
| `ReuseTree` | true | Giữ cây MCTS để tái dùng cho nước sau → nhanh hơn. Nên để bật. |
| `Ponder` | false | Cho engine suy nghĩ sẵn trong lúc chờ đối thủ đi (tận dụng thời gian, mạnh hơn chút khi cờ có đồng hồ). |

**DÙNG ĐƯỢC — chỉnh sâu kiểu lc0** (đặt bằng tên gốc, vd `setoption name cpuct value 2.5`) — ~35 tham số.
Mặc định = đúng default `lc0-master`.

*PUCT — điều khiển cách MCTS cân bằng giữa **thăm dò** (thử nước mới) và **đào sâu** (bám nước tốt):*
| Tham số | Mặc định | Ý nghĩa |
|---------|----------|---------|
| `cpuct` | 1.745 | Núm chính điều tiết thăm dò. **Tăng** (vd 3.0) → engine thử nhiều nước lạ, ít tin gợi ý mạng → hợp khi mạng còn yếu hoặc tự-chơi cần đa dạng. **Giảm** (vd 1.0) → bám nước mạng cho điểm cao, đào sâu một biến → chơi "sắc" hơn khi mạng đã mạnh. |
| `cpuct-base` | 38739 | Quy mô cây (số visit) mà tại đó `cpuct` bắt đầu tự nhích tăng. **Lớn** → `cpuct` gần như không đổi trong một lần nghĩ bình thường; **nhỏ** → cây càng phình thì thăm dò càng được nới. Hiếm khi cần đụng. |
| `cpuct-factor` | 3.894 | Cường độ của việc `cpuct` tăng theo cây (theo công thức log cùng `cpuct-base`). Đặt 0 = tắt phần tăng (cpuct cố định). Để mặc định trừ khi tinh chỉnh rất sâu. |
| `cpuct-at-root` / `-base-at-root` / `-factor-at-root` | =bản thường | Ba bản sao dành riêng cho **nút gốc** (thế cờ hiện tại), cho phép gốc thăm dò khác phần còn lại của cây. Chỉ có hiệu lực khi bật cờ ngay dưới. |
| `root-has-own-cpuct-params` | false | Công tắc bật/tắt nhóm `*-at-root`. Mặc định tắt → cả cây (kể cả gốc) dùng chung một bộ cpuct. Bật khi muốn gốc thăm dò rộng/hẹp khác các tầng sâu. |
| `fpu-value` | 0.330 | "First Play Urgency" — điểm giả định gán cho nước **chưa thử lần nào**, để engine quyết thử sớm hay muộn. **Cao** → coi nước mới đáng giá → thử rộng; **thấp/âm** → e dè nước mới → đào sâu nước đã biết. |
| `fpu-value-at-root` | 1.0 | Như `fpu-value` nhưng cho các nước **ngay tại gốc**. Chỉ có tác dụng khi `fpu-strategy-at-root` khác `same`. |
| `fpu-strategy` | reduction | Cách dùng `fpu-value`: `reduction` = lấy đánh giá thế cha **trừ đi** `fpu-value` (nước mới hơi kém cha); `absolute` = gán **thẳng** `fpu-value` làm điểm nước mới (bỏ qua điểm cha). |
| `fpu-strategy-at-root` | same | Như `fpu-strategy` nhưng tại gốc. `same` = không đối xử riêng cho gốc (giữ y phần còn lại của cây). |

*Hòa / khinh địch (contempt) — lái cách engine đánh giá thế hòa và giả định mạnh/yếu so với đối thủ:*
| Tham số | Mặc định | Ý nghĩa |
|---------|----------|---------|
| `draw-score` | 0 | Điểm engine gán cho thế **hòa**, theo phía Trắng. 0 = trung lập. Đặt **âm** (vd −0.1) → engine "ghét hòa", chịu mạo hiểm để thắng; −1 = kiểu Armageddon (hòa coi như thua). |
| `two-fold-draws` | true | Trong lúc nghĩ, nếu một thế lặp lại lần 2 **ngay trong cây search** thì coi nhánh đó là hòa (vì bên muốn hòa luôn ép được lần lặp thứ 3). Chỉ là mẹo tăng tốc/chính xác — **không** rút ngắn luật hòa-3-lần của ván thật. Nên để `true`. |
| `contempt-mode` | play | Chế độ áp khinh địch: `play` cho đấu thật; `white_side_analysis`/`black_side_analysis` cho phân tích một phía; `disable` tắt hẳn. |
| `contempt-max-value` | 420 | Trần (đơn vị Elo) của mức khinh địch, để giá trị quá lớn không làm đánh giá WDL méo mó. |
| `wdl-calibration-elo` | 0 | Elo ước lượng của phía đang đi, dùng để "mài sắc / làm dịu" phân bố Thắng-Hòa-Thua cho khớp trình độ đó. 0 = không hiệu chỉnh, dùng WDL thô của mạng. |
| `wdl-contempt-attenuation` | 1.0 | Mức chuyển lợi thế Elo thành khinh địch. 1.0 cho phân tích thực tế; 0.5–0.6 thường cho thành tích đấu giải tốt hơn. |
| `wdl-max-s` | 1.4 | Giới hạn độ "sắc" (s) của đường cong WDL, tránh engine phản ứng thất thường khi contempt cao. Tăng cho thế biến động mạnh. |
| `wdl-eval-objectivity` | 1.0 | Điểm centipawn hiển thị nên "khách quan" tới đâu: 0 = phản ánh đúng WDL nội bộ (đã ngấm contempt); 1 = cố cho ra con số khách quan. |
| `wdl-draw-rate-target` / `-reference` | 0 / 0.5 | `target` = tỉ lệ hòa mong muốn ở thế cân bằng (proxy cho độ chính xác lối đánh; 0 = giữ WDL thô). `reference` = tỉ lệ hòa mạng dự đoán ở thiết lập mặc định, làm mốc hiệu chỉnh. |
| `wdl-book-exit-bias` | 0.65 | Độ lệch cán cân của thế khai cuộc khi đo Elo (≈0.2 cho thế đầu bàn, 1 nếu Trắng thắng 50%). Chỉ quan trọng khi tỉ lệ hòa mục tiêu > 80%. |
| `score-type` | WDL_mu | Dạng điểm in trong `info score`: `centipawn` (kiểu cờ vua quen thuộc), `win_percentage` (% thắng), `Q` (điểm nội bộ ×100), `WDL_mu` (suy từ phân bố Thắng-Hòa-Thua). |

*Nhiệt độ — thêm tính ngẫu nhiên vào việc chọn nước (chủ yếu cho tự-chơi/đa dạng, ít dùng khi đấu nghiêm túc):*
| Tham số | Mặc định | Ý nghĩa |
|---------|----------|---------|
| `tempdecay-moves` | 0 | Số nước để hạ dần độ ngẫu nhiên (`Temperature`) một cách tuyến tính về 0. 0 = không hạ (giữ ngẫu nhiên suốt ván). Dùng để đầu ván đa dạng, càng về sau càng đánh chuẩn. |
| `tempdecay-delay-moves` | 0 | Hoãn việc bắt đầu hạ nhiệt thêm N nước — giữ độ ngẫu nhiên cao trọn vẹn N nước đầu rồi mới giảm. |
| `temp-cutoff-move` | 0 | Từ nước thứ N trở đi, đổi sang dùng `temp-endgame` thay cho temperature ban đầu. 0 = không có mốc cắt. |
| `temp-endgame` | 0 | Độ ngẫu nhiên dùng cho giai đoạn sau `temp-cutoff-move`, và **không** giảm dần nữa. Thường để 0 (tàn cuộc đánh chính xác). |
| `temp-value-cutoff` | 100 | Khi bốc nước theo độ ngẫu nhiên, loại bỏ nước có xác suất thắng kém nước tốt nhất quá X%. 100 = không loại nước nào; giảm xuống để cấm engine lỡ bốc trúng nước quá tệ. |
| `temp-visit-offset` | 0 | Cộng/trừ vào số lần thăm của mỗi nước trước khi bốc theo độ ngẫu nhiên. Âm → nước ít được thăm dễ bị loại; tinh chỉnh độ "liều" của việc bốc. |
| `policy-softmax-temp` | 1.359 | Làm "mềm" gợi ý của mạng (chia logit policy cho giá trị này). **>1** (mặc định) → san bằng bớt, cho nước phụ cơ hội được thăm; **=1** → dùng nguyên gợi ý mạng; **<1** → dồn niềm tin vào vài nước top. |

*Hiệu năng / nội bộ MCTS — ảnh hưởng tốc độ và đa luồng, thường để mặc định:*
| Tham số | Mặc định | Ý nghĩa |
|---------|----------|---------|
| `minibatch-size` | 0 | Số thế cờ engine gom lại để đẩy mạng tính một lần. Lớn → tận dụng GPU tốt hơn nhưng mỗi "nhịp" chậm; 0 = để backend tự chọn. |
| `max-collision-events` | 917 | Khi nhiều luồng đụng cùng một node thì gọi là "va chạm"; đây là trần số sự kiện va chạm mỗi batch trước khi buộc đẩy đi tính. Để mặc định trừ khi tinh chỉnh đa luồng. |
| `max-collision-visits` | 80000 | Tổng số lượt-thăm-va-chạm cho phép mỗi batch (trần rộng hơn `events`). Để mặc định. |
| `out-of-order-eval` | true | Nếu một node đã có sẵn kết quả (trong cache hoặc là thế kết thúc), cho xử lý ngay không chờ đủ batch → search trôi nhanh hơn. Nên để bật. |
| `max-out-of-order-evals-factor` | 2.4 | Trần số lần eval "vượt thứ tự" nói trên = cỡ batch × hệ số này. Để mặc định. |
| `cache-history-length` | 0 | Bao nhiêu nửa-nước lịch sử được đưa vào khóa của cache. 0 = chỉ dùng thế hiện tại làm khóa (cache trúng nhiều hơn nhưng có thể lẫn thế cùng vị trí khác lịch sử). |
| `sticky-endgames` | true | Khi tìm thấy thế kết thúc chắc chắn (chiếu hết/hòa) trong cây, cho kết quả đó "dính" ngược lên thế cha để đánh giá chuẩn hơn. Nên để bật. |
| `nps-limit` | 0 | Giới hạn trên số node/giây (để cố tình giảm sức hoặc đồng đều tốc độ). 0 = không giới hạn. |
| `max-concurrent-searchers` | 1 | Số luồng được phép cùng lúc đi gom batch. Tăng cùng `Threads` khi chạy đa luồng mạnh. |
| `task-workers` | -1 | Số luồng phụ giúp một luồng search chính chạy nhanh hơn. -1 = engine tự chọn theo máy. |
| `search-spin-backoff` | false | Khi luồng phải chờ để giành quyền search, có "lùi dần" (đỡ tốn CPU quay vòng vô ích) hay không. Bật giúp giảm tải CPU khi nhiều luồng tranh nhau. |
| `garbage-collection-delay` | 10 | Engine chờ bao nhiêu % thời gian của nước đi rồi mới bắt đầu dọn các nhánh cây bỏ đi — hoãn để kịp tận dụng chuyển vị (transposition). |
| `per-pv-counters` | false | Trong `info`, đếm node theo từng biến chính (PV) riêng thay vì in tổng. Chủ yếu để phân tích. |
| `verbose-move-stats` | false | In chi tiết Q (điểm), V (giá trị mạng), N (số thăm), U (phần thăm dò), P (xác suất policy) của mọi nước ứng viên. Hữu ích để gỡ lỗi / hiểu engine. |

**Điều khiển `go`:** `nodes N` · `movetime ms` · `wtime W btime B winc Wi binc Bi movestogo M` ·
`infinite` (+`stop`) · `searchmoves m1 m2…` · `ponder` (+`ponderhit`). Engine phát `info ... score cp ...
wdl ... multipv ... pv ...`.

**CHƯA DÙNG ĐƯỢC:** vài tham số search hiếm/nội bộ chưa đưa vào (`max-prefetch`, `solid-tree-threshold`,
`minimum-*-work`…); `go depth N`/`go mate N` (nhận nhưng chưa giới hạn); `score mate N` (chưa phát);
ponder mới ở mức cơ bản (kết thúc khi `ponderhit`, chưa cấp thêm ngân sách thời gian).

### D.2. Khi SINH DỮ LIỆU (`custom_engine.exe --selfplay`)

**DÙNG ĐƯỢC — cờ CLI:**
| Cờ | Mặc định | Ý nghĩa |
|----|----------|---------|
| `--games N` | 100 | Tổng số ván engine tự đánh với chính nó và ghi lại. Càng nhiều → dữ liệu huấn luyện càng phong phú nhưng càng lâu. |
| `--visits N` | 200 | Số playout MCTS mỗi nước trong lúc tự chơi. Cao → nước đi chất lượng hơn (dữ liệu tốt hơn) nhưng chậm. Đời đầu để 200, đời sau tăng 400/800. |
| `--parallel K` | 1 | Số ván chạy **song song** cùng lúc. Đặt ≈ số nhân CPU để tận dụng hết máy → sinh nhanh hơn nhiều. |
| `--threads-per-game T` | 1 | Số luồng MCTS dùng cho **mỗi** ván. Thường để 1 và tăng `--parallel` thay vì cái này. |
| `--max-moves N` | 200 | Trần số nước mỗi ván; tới hạn thì xử hòa để khỏi kẹt ván dài vô tận. |
| `--temp-cutoff N` | 30 | Trong N nước đầu, chọn nước **lấy mẫu theo số visit** (ngẫu nhiên có trọng số) để dữ liệu đa dạng; sau đó đi nước tốt nhất. |
| `--backend-threads N` | 1 | Số luồng tính mạng nơ-ron trên CPU (dùng khi `--provider cpu`). |
| `--provider cpu\|cuda` | cpu | Thiết bị chạy mạng: CPU (Windows) hoặc GPU (Colab). |
| `--fixed-batch N` | 16 | Cỡ batch đẩy GPU mỗi lần (khi `cuda`); lớn → GPU hiệu quả hơn. |
| `--weights FILE` | — | Mạng `.onnx` engine dùng để tự chơi (thường là đời mới nhất). |
| `--out DIR` | selfplay_data | Thư mục lưu dữ liệu — mỗi ván một tệp `.gz`. |
| `--noise-epsilon F` | 0.25 | Lượng nhiễu Dirichlet trộn vào gợi ý ở **nút gốc** để engine thử nước mới (cốt lõi của tự học AlphaZero). 0 = không nhiễu. |
| `--noise-alpha F` | 0.3 | Độ "tù" của nhiễu Dirichlet: lớn → nhiễu trải đều các nước; nhỏ → dồn vào ít nước. |
| `--policy-temp F` | 1.0 | Làm "mềm" gợi ý mạng khi tự chơi (xem `policy-softmax-temp` ở D.1). |
| `--cpuct F` | auto(1.745) | Hệ số thăm dò MCTS khi tự chơi (xem `cpuct` ở D.1). |
| `--start-fen FEN\|FILE` | startpos | Thế cờ bắt đầu mỗi ván; truyền một tệp để xoay vòng nhiều thế (đa dạng khai cuộc). |
| `--resign-threshold F` | tắt | Tự xin thua khi điểm tốt nhất `best_q ≤ F` để bỏ ván thua rõ (nhanh hơn). Bật bằng vd `-0.90`; mặc định tắt = đánh tới cùng. |
| `--resign-consecutive N` | 3 | Cần N **lượt liên tiếp** dưới ngưỡng mới xin thua (tránh thua nhầm vì một nước tụt điểm). |
| `--resign-earliest-move N` | 0 | Không cho xin thua trước nước thứ N (để không bỏ ván quá sớm). |
| `--no-resign-frac F` | 0.10 | Tỉ lệ ván **tắt** resign, đánh tới cùng — để mạng vẫn học cách kết liễu/phòng thủ thế thua. |
| `--search-opt name=value` (lặp) | — | Đặt **bất kỳ** search-param lc0 nào cho self-play (xem danh sách ~35 ở D.1). Lặp nhiều lần, vd `--search-opt cpuct-base=20000 --search-opt two-fold-draws=true`. |
| `--show-nps` | tắt | Hiện **NPS tổng** (cộng dồn mọi worker = throughput tìm kiếm của engine) trong log mỗi ván + dòng tổng kết. Mặc định TẮT; thêm cờ để bật. Với `--parallel 1` thì NPS này = NPS một ván; parallel>1 thì chia cho số parallel để ra NPS/ván. |

**CHƯA DÙNG ĐƯỢC từ CLI self-play:** `--resign-wdlstyle` (resign theo ngưỡng WDL) chưa viết.
*Lưu ý: self-play VỐN đã tái dùng cây trong một ván (không cần cờ riêng).*

### D.3. Khi HUẤN LUYỆN (`python train.py`)

**DÙNG ĐƯỢC — cờ CLI:**
| Cờ | Mặc định | Ý nghĩa |
|----|----------|---------|
| `--data X` | — | Nguồn dữ liệu: một thư mục, nhiều thư mục (ngăn bằng dấu phẩy — dùng cho cửa sổ trượt nhiều đời), hoặc một tệp `.zip` đã gói. |
| `--epochs N` | 20 | Số vòng quét hết toàn bộ dữ liệu. Nhiều quá → dễ quá khớp; ít quá → học chưa tới. |
| `--batch N` | 32 | Số thế cờ học mỗi bước. Trên GPU đặt lớn (512–2048) cho nhanh + ổn định; CPU để nhỏ. |
| `--lr F` | 1e-3 | Tốc độ học (bước cập nhật trọng số) khi **không** dùng lịch LR. Cao → học nhanh nhưng dễ phân kỳ; thấp → chậm mà chắc. |
| `--q-ratio F` | 0.2 | Tỉ lệ trộn mục tiêu value giữa **q của search** và **kết quả ván thật**. 0 = chỉ dùng kết quả ván; tăng → tin thêm vào đánh giá search. |
| `--downsample F` | 1.0 | Giữ ngẫu nhiên tỉ lệ F số thế cờ (vd 0.5 = bỏ nửa). Giảm trùng lặp giữa các thế gần nhau trong cùng ván. |
| `--channels N` / `--blocks N` | 128 / 10 | Độ rộng (số kênh) và độ sâu (số block) của mạng. Lớn hơn → mạnh hơn nhưng chậm + nặng. **Phải cố định suốt chuỗi warm-start.** |
| `--init-from FILE.pt` | — | Học tiếp từ trọng số đời trước (warm-start) thay vì từ số 0 — cốt lõi để mạng mạnh dần qua các đời. |
| `--out FILE.onnx` | model_gen1.onnx | Tệp mạng xuất ra cho engine chơi (kèm theo một tệp `.pt` cùng tên để train đời sau). |
| `--device auto\|cuda\|cpu` | auto | Thiết bị huấn luyện; `auto` tự chọn GPU nếu có. |
| `--amp` | tắt | Bật tính toán nửa độ chính xác (FP16) — nhanh hơn nhiều và tốn ít VRAM trên GPU. Chỉ có lợi trên GPU (cuda tự bật). |
| `--value-weight F` / `--policy-weight F` | 1.0 / 1.0 | Trọng số của hai phần loss (đánh giá thế ↔ gợi ý nước). Tăng cái nào → mạng ưu tiên học giỏi phần đó. |
| `--weight-decay F` | 1e-4 | Phạt L2 lên trọng số để chống quá khớp (giữ mạng "đơn giản"). Đây cũng là L2 của AdamW. |
| `--swa-start-frac F` | 0.75 | Từ mốc 75% quá trình train, bật **SWA** (trung bình hóa trọng số nhiều bước cuối) → mạng tổng quát tốt và ổn định hơn. |
| `--optimizer adamw\|sgd\|nadam` | adamw | Thuật toán tối ưu. `adamw` (mặc định) bền, chạy ngon với LR hằng; `sgd`+momentum = recipe chuẩn lc0 (mạnh nhất nhưng cần lịch LR đúng); `nadam` = Adam + Nesterov. |
| `--momentum M` | 0.9 | Quán tính cho `--optimizer sgd` (bật luôn Nesterov). Chỉ dùng khi chọn sgd. |
| `--grad-clip G` | 0 (tắt) | Cắt độ lớn (norm) của gradient xuống ≤ G để tránh "nổ" gradient làm train phân kỳ. 0 = tắt. |
| `--seed S` | 0 | Hạt giống ngẫu nhiên để chạy lại cho ra kết quả y hệt (tái lập thí nghiệm). |
| `--warmup-steps N` | 0 | Tăng LR tuyến tính từ 0 lên trong N bước đầu cho ổn định, rồi mới theo lịch. |
| `--lr-values a,b` + `--lr-boundaries i` | — | **Lịch LR bậc thang** kiểu lc0: đặt LR theo từng chặng bước (ghi đè `--lr`). Vd values `0.02,0.002,0.0005` + boundaries `100000,130000`. |
| `--accum-steps K` | 1 | **Tích lũy gradient** K lô nhỏ rồi mới cập nhật một lần → batch hiệu dụng = batch × K, mà bộ nhớ chỉ tốn bằng một lô. Cứu cánh cho GPU nhỏ (Colab). |
| `--max-steps N` | 0 | Dừng sau N bước tối ưu (thay cho hoặc cùng với `--epochs`). 0 = chỉ theo epochs. |
| `--max-records N` | 0 | Chỉ nạp tối đa N thế cờ (chạy thử nhanh / hạn chế RAM). 0 = nạp tất cả. |
| `--report-every N` | 0 | In loss mỗi N bước để theo dõi tiến độ trong epoch. 0 = chỉ báo cáo theo từng epoch. |
| `--save-every N` | 0 | Lưu checkpoint `.pt` mỗi N bước (đề phòng mất điện/đứt Colab). 0 = chỉ lưu khi xong. |
| `--se-ratio R` | 8 | Mức nén của SE block trong mạng (xem giải thích ở mục B câu hỏi se-ratio). **CHỈ đổi khi train từ đầu** — đổi giữa chừng sẽ không nạp được trọng số cũ. |
| `--dropout R` | 0 | Tỉ lệ dropout ở value head để chống quá khớp khi dữ liệu ít. 0 = tắt (giống lc0); bật vd 0.1 nếu thấy `train_loss ≪ val_loss`. An toàn warm-start. |
| `--diff-focus` (+ `--df-slope/--df-kld-w/--df-min`) | tắt | Ưu tiên học các thế cờ "khó" (mạng đoán sai nhiều) thay vì học đều; các cờ `--df-*` tinh chỉnh cường độ. |
| `--workers N` / `--pin-memory` | auto | Tăng tốc khâu **nạp dữ liệu** (nhiều tiến trình đọc + dựng plane song song; ghim bộ nhớ để chuyển lên GPU nhanh hơn). **Mặc định tự bật trên GPU** (`workers = số nhân CPU`, `pin_memory` bật) vì khi đó GPU hay phải chờ CPU dựng plane; trên CPU mặc định `workers=0` (tránh Windows pickle cache vào từng tiến trình). Truyền tay để ghi đè. |
| `--sparse-cache` / `--dense-cache` | sparse | Cách lưu cache dữ liệu: `sparse` tốn ít RAM (chống tràn bộ nhớ trên Colab); `dense` nhanh hơn nhưng ngốn RAM. |

> **Để giống lc0-training:** mặc định của ta là **AdamW + LR hằng** (dễ/ổn cho quy mô nhỏ). Muốn khớp
> lc0 (SGD + lịch LR), dùng: `--optimizer sgd --momentum 0.9 --warmup-steps 250
> --lr-values 0.02,0.002,0.0005 --lr-boundaries 100000,130000` (theo `example.yaml`).

**CHƯA DÙNG ĐƯỢC (chưa có cờ):** `--loss-scale`, `--batch-renorm`, `--ema`, `--swa-max-n/--swa-every`,
`--val-split/--test-every`, `--shuffle-size`.

### D.4. Đấu thử giữa hai đời (`custom_engine.exe --arena`)
So tài hai mạng để biết đời mới có thật sự mạnh hơn không (engine tự đánh A vs B nhiều ván,
luân phiên cầm Trắng/Đen). Arena **chia sẻ một phần** bộ cờ với phần sinh dữ liệu (Mục B/D.0) —
nó dùng các cờ thiết bị/độ sâu/tìm kiếm dưới đây, nhưng **bỏ qua** các cờ chỉ thuộc self-play.

| Cờ | Mặc định | Ý nghĩa |
|----|----------|---------|
| `--model-a FILE` | — | Mạng `.onnx` thứ nhất (thường là đời mới). |
| `--model-b FILE` | — | Mạng `.onnx` thứ hai (thường là đời cũ để so). |
| `--games N` | 100 | Số ván đấu (chia đôi mỗi bên cầm Trắng/Đen cho công bằng). |
| `--visits N` | 200 | Độ sâu MCTS mỗi nước khi đấu. |
| `--max-moves N` | 200 | Trần số nước mỗi ván (chạm trần ⇒ tính hòa). |
| `--temp-cutoff N` | 30 | Số nước đầu lấy mẫu theo visit (để hai ván không giống hệt nhau); đấu nghiêm ngặt có thể đặt nhỏ (vd 6) hoặc 0 để hai mạng đánh "tốt nhất" hoàn toàn. |
| `--provider cpu\|cuda\|dml` | cpu | Thiết bị suy luận. `cuda` cho Colab (bản `-Duse_cuda`); `dml` cho GPU Windows — kể cả NVIDIA (bản `-Duse_dml`). |
| `--backend-threads N` | 1 | Số luồng intra-op cho ONNX khi `cpu`/`dml` (nên đặt = số nhân, vd 4). |
| `--fixed-batch N` | 16 | Kích thước batch cố định khi `--provider cuda`. |
| `--cpuct F` | (mặc định search) | Hằng số thám hiểm MCTS; đặt giống nhau cho cả hai mạng để công bằng. |
| `--policy-temp F` | 1.0 | Nhiệt độ làm mềm policy của mạng (giữ 1.0 cho đánh giá trung tính). |
| `--show-nps` | tắt | In NPS (playout/giây) gộp sau mỗi ván + tổng kết, để đo tốc độ. |

> **Cờ self-play KHÔNG có tác dụng trong arena:** `--threads-per-game`, `--parallel`, `--noise-*`,
> `--resign-*`, `--start-fen`, `--out`, `--policy-temp` của self-play... Arena đánh **tuần tự từng ván**
> (mỗi lúc một tìm kiếm) nên không có pool worker — muốn nhanh hơn thì tăng `--backend-threads`
> hoặc dùng `--provider dml/cuda`, chứ `--threads-per-game` sẽ bị **bỏ qua**.

> ⚠️ **GPU trong arena:** trước đây arena bỏ qua mọi provider ≠ `cuda` nên `--provider dml` âm thầm
> chạy CPU. Nay đã sửa — bản dựng `-Duse_dml` sẽ kích hoạt đúng iGPU. Kiểm tra dòng in
> `[arena] backend: provider=dml,threads=N` (chứ không phải `threads=N` đơn thuần) là biết GPU đã bật.

**Windows — tận dụng iGPU (Iris Xe) qua DirectML** (cần bản đóng gói `-Dml`, xem Mục 0b):
```powershell
.\custom_engine.exe --arena `
  --model-a models\model_gen2.onnx --model-b models\model_gen1.onnx `
  --games 20 --visits 400 --temp-cutoff 6 `
  --provider dml --backend-threads 4
```

**Windows — CPU thuần** (bản thường):
```powershell
.\custom_engine.exe --arena --model-a models\model_gen2.onnx --model-b models\model_gen1.onnx `
  --games 20 --visits 200 --backend-threads 4
```

**Colab — GPU T4 qua CUDA** (bản Linux `-Duse_cuda` do `colab_setup.sh` dựng):
```bash
!/content/FairyZero/.../custom_engine --arena \
  --model-a models/model_gen2.onnx --model-b models/model_gen1.onnx \
  --games 40 --visits 400 --temp-cutoff 6 \
  --provider cuda --fixed-batch 32
```

Kết thúc, engine in số thắng/hòa/thua của A và `A score` (>0.5 ⇒ A mạnh hơn B). Theo chuẩn AlphaZero,
chỉ **giữ đời mới làm mốc** nếu nó đạt ngưỡng thắng rõ rệt (vd score ≥ 0.55 qua ≥ 40 ván).

> **Lưu ý:** bản portable này **không còn** lệnh vòng lặp tự động (`loop.py`/`colab_loop.sh` đã gỡ bỏ).
> Sinh dữ liệu (Mục B) và huấn luyện (Mục C) là hai bước **tách bạch**, bạn tự nối chuỗi theo C.3/C.4.

---

## E. KHẮC PHỤC SỰ CỐ

- **`custom_engine.exe` không chạy / thiếu DLL:** đảm bảo các tệp `.dll` nằm **cùng thư mục**
  với `.exe` (đừng tách ra). Đây là bản đã đóng gói đủ DLL cho Windows.
- **`bestmove 0000`:** thế cờ đã hết (chiếu hết/hòa) hoặc nạp mạng thất bại — kiểm tra đường
  dẫn `--weights`.
- **Engine "đứng im" sau `go infinite`:** đúng vậy — nó nghĩ vô hạn; gõ `stop` để lấy nước.
- **Python báo thiếu thư viện:** chạy `pip install -r python\requirements.txt`.
- **Colab: meson báo `ERROR: Clock skew detected ... time stamp ...s in the future`:** do `cp` từ Google
  Drive làm mtime tệp lệch về tương lai so với đồng hồ máy Colab. Sửa: chuẩn hóa timestamp rồi cấu hình lại —
  `!find /content/FairyZero -exec touch {} +` → `!rm -rf .../engine_src/build-linux` → chạy lại `colab_setup.sh`.
  (Bản `colab_setup.sh` mới đã tự `touch` trước khi `meson setup` nên sẽ không gặp lại.)
- **Test engine còn nguyên vẹn:** `custom_engine.exe --test-uci` (kiểm tra I/O nước) phải in
  `[PASS]`.

---

Chúc bạn chơi vui và huấn luyện ra những đời mạng ngày càng mạnh! 🦊♟️
