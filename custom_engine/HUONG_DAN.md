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
Ngoài ra `--seed` chỉ để **tái lập** kết quả ngẫu nhiên, **không** phải kiến trúc: mặc định mỗi lần chạy
tự rút một seed 10 chữ số (dòng `[make_seed] seed …` trong log); truyền lại số đó để ra đúng mạng cũ.
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

**Bước 3 — Đóng gói bản portable** (gom thành 1 thư mục/bundle để chạy trên Windows sạch hoặc đưa lên Colab):
```
powershell -ExecutionPolicy Bypass -File scripts\package.ps1
```
→ mặc định ra `dist\FairyZero\` (target **both**: Windows CPU + mã nguồn Colab). **Hai siêu tham số chính:**

- **`-Target both|colab|windows`** — chọn loại bundle:
  - **`both`** (mặc định) — bản Windows chạy được (CHƠI + SINH DỮ LIỆU) **kèm** `engine_src/` + script Colab
    để build lại binary GPU. Ra `dist\FairyZero\`. (Cần `build\` đã `ninja` xong.)
  - **`colab`** — **CHỈ Colab, tối giản (~2MB)**: chỉ `engine_src/` + `python/` + script Colab; **KHÔNG** exe/DLL
    Windows, **KHÔNG** ONNX Runtime, **KHÔNG** binary (không build Linux trên Windows được). Trên Colab chạy
    `bash scripts/colab_setup.sh` **MỘT LẦN** (build binary GPU + tải ONNX Runtime), các phiên sau
    `bash scripts/colab_prebuilt.sh wrap`. Đủ để **sinh dữ liệu, huấn luyện và arena**. Ra `dist\FairyZero_colab\`.
  - **`windows`** — chỉ bản Windows (exe + DLL + python + play.bat), **không** kèm mã nguồn/script Colab.
    Ra `dist\FairyZero_win\`.
- **`-NoModel`** — **không** xuất seed model (vd khi bạn tải mạng từ GitHub release riêng). Mặc định (không có cờ
  này) thì tự sinh seed 0-ELO qua `make_seed.py`; hoặc `-Model models\model_gen7.onnx` để đóng gói một mạng đã
  train làm `seed.onnx`.

Tham số khác:
- `-Dml` — đóng gói bản **DirectML** (lấy từ `build-dml\`) thay cho CPU. **Một bundle phục vụ CẢ `Provider=cpu`
  lẫn `Provider=dml`** (vì `onnxruntime.dll` bản DirectML chứa cả hai EP), có kèm `DirectML.dll`. Chỉ áp dụng
  target `both`/`windows`. Cần build `build-dml` trước (`meson setup build-dml -Duse_dml=true; ninja -C build-dml`).
- `-Zip` — tạo thêm `<OutDir>.zip` để chép đi (dùng `Compress-Archive`; muốn nhỏ hơn thì nén lại bằng
  WinRAR/7-Zip). *Lưu ý: bundle do `package.ps1` tạo (kể cả `both`) chỉ có DLL Windows, KHÔNG chứa thư
  viện ORT GPU của Linux — cái đó chỉ xuất hiện sau khi build trên Colab.*
- `-OutDir <đường dẫn>` — đổi nơi xuất. `-Ucrt64Bin <...>` — chỉ chỗ DLL nếu MSYS2 không ở `C:\msys64`.

> **Ví dụ bản colab tối giản để đẩy lên GitHub release:** `... package.ps1 -Target colab -NoModel`
> → `dist\FairyZero_colab\` (~2MB, source-only). Đưa lên Colab, `colab_setup.sh` một lần, rồi `wrap` mỗi phiên.

> **Về "1 bản portable cuda+dml+cpu":** CPU+DML gộp được vào một bundle (`-Dml`). **CUDA thì KHÔNG** đặt
> vào bản Windows portable (cần `onnxruntime.dll` bản CUDA + CUDA toolkit cài sẵn) — CUDA là đường **Colab/Linux**,
> dùng `engine_src/` kèm trong bundle để build lại bằng `colab_setup.sh`.

> **Lưu ý về biến thể:** luật cờ (10×10, bắt tốt qua đường, **8 lần chiếu = thắng**, các quân tùy biến…)
> được **nhúng thẳng trong engine** ở `src/app/variant_setup.cc` (một chuỗi `ini` đăng ký biến thể
> `custom_10x10_variant`), **không** đọc từ tệp `variants.ini` ngoài. Muốn đổi luật thì sửa chuỗi đó rồi
> build lại — sửa `variants.ini` bên ngoài sẽ KHÔNG có tác dụng. (Xem mục A để hiểu vì sao FEN có trường `8+8`.)
>
> **CẬP NHẬT LUẬT — 2026-09-21.** Hai thay đổi, và chúng **phá vỡ tính tương thích của mọi
> đời mạng cũ** (gen 0-12) — phải huấn luyện lại từ đời 0:
> 1. **Amazon → Hậu** ở thế cờ bắt đầu: ô `e1` và `e10` giờ là `Q`/`q` thay vì `A`/`a`.
>    Quân Amazon vẫn còn trong định nghĩa biến thể (giữ nguyên bố cục 13 plane của mạng)
>    nhưng không còn xuất hiện trong ván đấu.
> 2. **7-checks → 8-checks**: trường check trong FEN đổi từ `7+7` thành `8+8`.
>
> FEN bắt đầu mới:
> `vrhbqkberv/msysnnsysm/yppppppppy/10/10/10/10/YPPPPPPPPY/MSYSNNSYSM/VRHBQKBERV w BIbi - 8+8 0 1`

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
Bên trong, Fairy-Stockfish lưu mỗi quyền nhập thành là **một cặp ô**: ô Hoàng gia + ô Xe. Chữ cái
trong FEN chỉ là cách *viết* cặp đó. Có hai cách viết, và chúng **không** tương đương trong mọi thế cờ:

| Cách viết | FSF đọc như thế nào | Ví dụ (đủ 4 quyền, thế cờ bắt đầu) |
|---|---|---|
| **Chữ-cái-cột `BIbi`** (Shredder-FEN) | lấy **đúng Xe ở cột đó**: `I` = Xe cột i, `B` = Xe cột b; HOA = Trắng, thường = Đen | `BIbi` |
| **`KQkq`** | *dò tìm*: `K` = Xe **đầu tiên** gặp khi đi từ cột i về phía cột a; `Q` = Xe đầu tiên đi từ cột b về phía cột j | `KQkq` |

Nhập thành được trên **mọi hàng** (từ 2026-09-24): Hoàng gia và Xe chưa đi, đứng cùng một hàng, nhập
thành trên chính hàng đó (Hoàng gia tới cột h/d, Xe tới cột g/e). Vì vậy mỗi chữ (cả `K`/`Q` lẫn chữ
cột) đều tìm Xe **trên hàng của Hoàng gia bên đó**: `…/1R3K2R1/10 w BI` = Hoàng gia f2, Xe b2 và i2.

- Ở **thế cờ bắt đầu** (Xe ở b và i) hai cách cho **cùng một thế cờ** (cùng Zobrist key), vì phép dò
  tìm gặp đúng Xe b/i. FSF in FEN ra (lệnh `d`, lệnh `fen`) ở dạng `K`/`Q` **khi đọc lại ra đúng Xe
  đó**, còn không thì in chữ cột (ví dụ Xe a1 và b1, quyền với Xe a1 được in là `A`, vì `Q` sẽ gặp b1).
  Nên FEN do engine in ra luôn đọc lại đúng như cũ.
- Khi Xe **không** ở cột b/i (thế tự dựng, hay sau này xáo trộn kiểu Chess960), `KQkq` có thể sai
  **nghĩa** mà không báo gì: ví dụ `4k5/.../R4K3R w K - 8+8 0 1` (Xe ở a1 và j1), phép dò cho `K` đi
  từ i1 về phía a, bỏ qua j1, gặp a1 → thành quyền nhập thành **cánh Hậu** với Xe a1. Viết `J` thì
  đúng ý (Xe j1, cánh Vua).
- **Nên dùng chữ-cái-cột (`BIbi`)** cho mọi FEN tự viết. Nó nêu đích danh Xe nên không bao giờ nhập
  nhằng; đây cũng là cách mọi FEN khởi đầu trong mã nguồn đang viết.
- **Không nhập thành: `-`**.
- ⚠️ Quyền chỉ "dính" nếu **Hoàng gia + Xe đang ở ô gốc**; ghi quyền mà quân không đúng chỗ thì FSF
  **tự bỏ, không báo**. Với self-play (`--start-fen`, sách khai cuộc) engine kiểm việc này: mỗi chữ phải
  cho đúng quyền nó ghi (`K`/`Q` đúng cánh, chữ cột đúng Xe cột đó) và không có quyền thừa, sai là
  dừng và báo dòng nào.
- Nếu sau này dùng **thế cờ khởi đầu xáo trộn** kiểu Chess960: viết sách khai cuộc bằng chữ-cái-cột và
  xem mục "Nếu sau này xáo trộn thế cờ khởi đầu" trong `LUAT_BIEN_THE.md` (phần engine đã sẵn sàng:
  nhập thành mọi hàng, khoá Zobrist có ô Xe, bản ghi lưu ô Xe).

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
- `--max-seconds <giây>` — **giới hạn thời gian** (0 = tắt, mặc định): ngoài dừng khi đủ `--games`, còn
  tự dừng khi chạy quá `<giây>` kể từ ván đầu. Dừng "mềm": ngừng nhận ván MỚI, để ván đang chạy hoàn tất
  (không có `.gz` cụt), thống kê cuối tính theo số ván THỰC SỰ xong. Chi phí ≈ 0 (so sánh 1 lần/ván, ngoài
  vòng lặp MCTS). Công dụng chính là khớp **quota Colab** — xem cách đặt ở **B.2**.

### B.2. Trên Google Colab (GPU — nhanh hơn nhiều)
Đã dựng engine Linux theo **Mục C.4 bước 1–3** (chạy `colab_setup.sh`). Sinh dữ liệu **vào ổ local
`/content`** (ĐỪNG sinh thẳng lên Drive vì FUSE rất chậm với nhiều tệp nhỏ):
```
!/content/FairyZero/engine_src/build-linux/custom_engine --selfplay \
    --games 1000 --visits 200 --parallel 2 --provider cuda --fixed-batch 32 \
    --weights /content/FairyZero/models/seed.onnx --out /content/games_gen0
```
- Khác bản Windows ở chỗ thêm `--provider cuda --fixed-batch ...` (chạy mạng trên GPU).

> ### ⚠ CẬP NHẬT 2026-09-22 — cấu hình khuyến nghị đã ĐỔI (dựa trên đo đạc)
>
> Lời khuyên cũ ngay dưới đây (`--parallel 2 --fixed-batch 32`, "GPU là nút cổ chai nên để parallel
> nhỏ") là **suy đoán và đã bị đo đạc bác bỏ**. Cấu hình tốt nhất đo được trên Colab T4:
>
> ```
> --parallel 4 --provider cuda --fixed-batch 16
> ```
>
> **Vì sao 16 chứ không phải 32/64:** MCTS gom trung bình ~15 lá mỗi lượt, nên `fixed-batch 16` lấp
> đầy **94%** mỗi batch (chỉ 5,7% phí padding). Đặt 64 thì chỉ lấp được 62% → **38% thời gian GPU
> tính ô rỗng**, và tổng lại **chậm hơn** dù mỗi lần gọi mạng hiệu quả hơn.
>
> **Vì sao parallel 4:** quét 1→32 ván song song cho throughput gần như phẳng; 4 cho `eval/giây` cao
> nhất. Tăng parallel còn làm `--max-seconds` vượt giờ nặng hơn (dừng mềm chờ mọi ván đang chạy xong:
> parallel 4 vượt ~2-3 phút, parallel 32 vượt tới **10 lần**).
>
> **`--batch-aggregate`: không dùng.** Đo được là ngang hoặc tệ hơn khi tắt.
>
> Trần phần cứng đo được cho mạng 12×144 trên T4 (fp32): **~3.170 vị trí/giây ≈ 3,2 TFLOP/s**, và
> self-play đạt ~91% mức đó. Không còn đòn bẩy phần mềm đáng kể.

- GPU mạnh hơn nên đặt `--games` lớn (1000+).
- Muốn giữ dữ liệu lên Drive thì gói 1 zip trước (xem B.4) rồi mới chép.
- **Khớp quota Colab bằng `--max-seconds`:** đặt `--games` thật lớn (vd `100000`) để **thời gian là ràng
  buộc** thay vì số ván, rồi đặt `--max-seconds` = hạn quota **trừ vài phút** đệm (vì dừng "mềm" có thể
  vượt ~một ván mỗi worker). Ví dụ chạy tối đa ~3 giờ (10800s, để đệm còn 10500):
```
!/content/FairyZero/engine_src/build-linux/custom_engine --selfplay \
    --games 100000 --max-seconds 10500 --visits 200 --parallel 2 --provider cuda --fixed-batch 32 \
    --weights /content/FairyZero/models/seed.onnx --out /content/games_gen0
```

### B.3. Tự xin thua sớm (resign) — tăng tốc (cả Windows lẫn Colab)
Mặc định TẮT. Bật để bỏ qua các ván đã thua rõ (nhanh hơn), vẫn giữ ~10% ván đánh tới cùng — thêm
vào lệnh `--selfplay` ở B.1/B.2:
```
... --resign-threshold -0.90 --resign-consecutive 3 --no-resign-frac 0.10
```
> ⚠ **Engine trước 2026-09-23:** `best_q` (giá trị resign dựa vào) bị lưu NGƯỢC dấu, nên bật resign
> khi đó sẽ khiến bên đang **thắng** xin thua. Dữ liệu sinh với resign bật bằng engine cũ có nhãn ván
> sai — đừng dùng. Từ bản sửa, resign hoạt động đúng.

> **Thay đổi 2026-09-23 (engine mới):** mỗi nước self-play là một lượt tìm kiếm **cây mới** (như lc0
> và AlphaZero), nên **nhiễu Dirichlet có ở gốc của MỌI nước** (trước đây chỉ nước đầu mỗi ván). Bản
> ghi dữ liệu mới mang `version = 2` (giá trị tìm kiếm đúng góc nhìn bên-tới-lượt); `train.py` tự đảo
> dấu cho dữ liệu cũ `version = 1`, nên trộn dữ liệu cũ và mới trong cửa sổ trượt vẫn đúng.

> **Sửa lỗi lặp thế (2026-09-23, phiên 2) — bản ghi mới mang `version = 3`:** engine cũ so khoá
> Zobrist có trộn bộ đếm luật 50 nước, nên từ rule50 ≥ 14 **không nhận ra thế cờ lặp**: ván không kết
> thúc khi lặp 3 lần, và plane "lặp thế" của mạng bị tắt. Đo trên `games_gen0.zip` (engine cũ): 25% số
> ván đi tiếp sau khi đã lặp 3 lần, 12% bản ghi nằm sau điểm lẽ ra đã hoà, 35% thế cờ lặp thiếu cờ lặp.
> Cũng từ `version = 3`: **chiếu đôi tính 2 lần chiếu** (mỗi quân đang chiếu tính 1; trước đây mỗi nước
> chiếu chỉ tính 1). Luật đầy đủ và các trường hợp biên: `LUAT_BIEN_THE.md`.
> Bố cục bản ghi không đổi, `train.py` đọc `version = 3` như `version = 2`. Không cần sinh lại gen0: mỗi
> đời chỉ học dữ liệu của đời trước, nên chỉ cần sinh dữ liệu từ nay bằng engine mới. Kiểm dữ liệu:
> `python audit_generation.py <zip>` giờ kiểm cả lặp thế trong từng ván (với dữ liệu `version < 3` chỉ
> báo con số, không tính là lỗi).
>
> File ván giờ được ghi vào `game_N.gz.tmp` rồi mới đổi tên thành `game_N.gz` khi ghi trọn vẹn: đĩa
> đầy hay tiến trình bị dừng giữa chừng không còn để lại `.gz` hỏng lọt vào `archive.py`/`train.py`
> (engine in `[TrainingDataWriter] FAILED ...` và bỏ ván đó).

> **Bản ghi `version = 4` (2026-09-24):** `orig_q`/`orig_d`/`policy_kld` (đánh giá thô của mạng ở gốc,
> chỉ `--diff-focus` dùng) giờ **luôn** là đánh giá thật. Trước đây, khi mục cache của gốc đã bị ghi đè
> (8,6% bản ghi gen0), chúng bị chép từ `best_q` và `policy_kld = 0`, và `--diff-focus` coi những bản ghi
> đó là "thế cờ dễ" nên loại bớt; nay `dataset.py` giữ chúng với tỉ lệ trung bình. Engine đánh giá lại gốc
> trong các trường hợp đó (khoảng 0,2% lượt GPU). Bố cục không đổi; `train.py` đọc được mọi version 1–4,
> và **từ chối** version lạ thay vì đọc bừa. `audit_generation.py` kiểm thêm: kết quả ván nhất quán trong
> từng ván, lượt đi xen kẽ, nước tốt nhất / nước đã đi hợp lệ và nước tốt nhất là nước nhiều lượt thăm
> nhất, và (từ version 4) không còn bản ghi chép `best_q`.

> **Bản ghi `version = 5` (2026-09-24):** vì nhập thành được trên mọi hàng, 4 byte nhập thành giờ lưu
> **ô** của Xe (hàng × 10 + cột, theo góc nhìn bên tới lượt như mọi plane; 255 = hết quyền) thay vì chỉ
> cột. Bố cục không đổi. `train.py` đọc được version 1–5: với bản ghi cũ (Xe luôn ở hàng đầu của mỗi
> bên) nó tự đổi cột thành ô, nên plane mạng dựng ra y hệt trước; trộn dữ liệu cũ và mới vẫn đúng.

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

### B.5. Đọc log self-play: số quân còn lại + điểm tấn công
Khi sinh dữ liệu, engine in **mỗi ván một dòng** và một khối **tổng kết** ở cuối. Ngoài kết quả, nó
còn in **2 chỉ số thống kê** (cả hai **luôn bật**, không cần thêm cờ) giúp bạn quan sát luật N-checks
ảnh hưởng thế nào tới lối chơi:
```
[selfplay] 1/200  (game 0 -> result=1, pieces=41, cong W=108 B=50 -> W)
[selfplay] 2/200  (game 1 -> result=1, pieces=53, cong W=58 B=71 -> B)
...
[selfplay] Finished 200/200 games in 1423.5s.
  White wins: 96 | Black wins: 99 | Draws: 5
  So quan con lai trung binh luc ket thuc: 47.8
  Diem tan cong tich luy trung binh moi van: Trang=83  Den=60.5
  So van moi ben choi the cong nhieu hon: Trang=104 | Den=91
  Ben cong nhieu hon THANG: 118/195 van (60.5%)
  Output dir: games_gen0
```
- `result=` là mã kết quả nội bộ: **1 = Đen thắng · 2 = hòa · 3 = Trắng thắng · 0 = chưa phân định**.
- `Finished X/Y` = **số ván THỰC SỰ xong / mục tiêu `--games`**. Bình thường X=Y; nếu dừng sớm do
  `--max-seconds` thì X < Y (vd `143/100000`) và có thêm ghi chú `(dung som...)`. Mọi trung bình bên
  dưới tính theo **X** (số ván xong).

**① Số quân còn lại — `pieces=N`** (đếm **cả Trắng + Đen, kể cả quân royal**):
- `pieces=N` (mỗi ván): số quân còn trên bàn ở thế cuối cùng của ván.
- `So quan con lai trung binh...` (tổng kết): trung bình của `pieces` trên mọi ván.
- **Dùng để đo độ "sắc" của ván.** Thế bắt đầu có **60 quân**, nên trung bình **cao** (gần 60) → ván
  kết thúc **sớm, còn nhiều quân** (thắng nhanh bằng đòn chiến thuật / dồn đủ N chiếu) = quyết liệt;
  trung bình **thấp** → ván hay **mài tới tàn cuộc thưa quân** mới phân thắng bại.

**② Điểm hệ số tấn công — `cong W=<wa> B=<ba> -> <bên>`** (đo bên nào "đóng quân trên sân địch" nhiều/lâu hơn):
- Cách tính: ở **MỖI thế cờ** trong ván, đếm số quân của một bên đang ở **nửa bàn đối phương** rồi
  **cộng dồn qua cả ván**. Trắng tấn công = quân Trắng ở **hạng 6-10** (nửa sân Đen); Đen tấn công =
  quân Đen ở **hạng 1-5** (nửa sân Trắng). Điểm càng cao = quân ở sân địch **càng nhiều và càng lâu**.
- `cong W=<wa> B=<ba> -> <W|B|=>` (mỗi ván): điểm tích luỹ của hai bên + bên nào công nhiều hơn ván đó.
- `Diem tan cong tich luy trung binh moi van` (tổng kết): trung bình điểm công mỗi bên trên mọi ván.
- `So van moi ben choi the cong nhieu hon` (tổng kết): trong tổng số ván, mỗi bên là bên-công-nhiều-hơn
  bao nhiêu ván (cho biết có **MỘT MÀU bị buộc tấn công hệ thống** không — cân bằng thì nên ~50/50).
- `Ben cong nhieu hon THANG: X/Y (Z%)` (tổng kết): **CON SỐ QUAN TRỌNG NHẤT để chỉnh N.** Trong **Y**
  ván có **phân thắng-bại VÀ có bên-công-rõ-ràng** (bỏ ván hòa + ván hai bên công ngang nhau), bên-công-
  nhiều-hơn thắng **X** ván → **`Z%` = xác suất "công nhiều hơn thì thắng"**.

**Dùng để minh bạch khi chỉnh N:** con số `Z%` trả lời thẳng câu *"tấn công có đáng không"* ở mỗi N:
- `Z%` **cao** (vd 70%) → tấn công **được tưởng thưởng** (thế công mạnh; bên lép vế khó phản công).
- `Z%` **thấp** (vd 40% — tức bên phòng-thủ/phản-công thắng nhiều hơn) → tấn công **bị trừng phạt**
  (phơi royal ra để công thì dễ ăn đòn phản công).
- Dò N sao cho `Z%` về mức bạn thấy "đẹp" (vd ~50-60%: công đáng giá nhưng không bất khả chiến bại),
  kết hợp với **"số quân còn lại trung bình"** để vừa cân bằng vừa đúng độ-dài/độ-sắc bạn muốn.

> **Vì sao cần dòng `... THANG: X/Y` riêng (không tự suy từ các dòng kia)?** "White/Black wins" và "số
> ván mỗi bên công nhiều hơn" là hai thống kê **RỜI NHAU (biên)** — từ chúng KHÔNG suy ra được bên-công-
> có-trùng-bên-thắng không (cùng một bộ "biên" có thể ứng với P=0% **hoặc** P=100%). Phải đếm **khớp**
> từng ván; dòng `... THANG: X/Y (Z%)` chính là phép đếm khớp đó (engine tính sẵn).
>
> **Lưu ý điểm tuyệt đối:** `Diem tan cong ... trung binh` là **tổng tích luỹ** nên ván dài điểm lớn hơn
> ván ngắn — **đừng so con số tuyệt đối giữa các N** (bị độ-dài-ván làm nhiễu). So `W` vs `B` trong cùng
> một ván thì công bằng; giữa các N hãy nhìn **`Z%`** và cột "số ván mỗi bên công nhiều hơn".

---

## C. HUẤN LUYỆN ĐỜI MẠNH HƠN

### C.0. Cài thư viện Python (làm 1 lần)
```
pip install -r python\requirements.txt
```
> **Colab:** mỗi phiên Colab là một máy mới, nên gói nào không có sẵn trong ảnh Colab phải cài lại mỗi
> phiên. Ảnh Colab hiện tại (Python 3.13) **không có `onnx`**, mà `torch.onnx.export` cần nó → thêm vào
> ô cài đặt đầu notebook: `!pip install -q onnx onnxscript onnxruntime`. Cảnh báo xung đột `protobuf`
> của các gói Google khác là vô hại.

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

   **3b. CÁCH ĐỂ PHIÊN SAU KHỎI BUILD LẠI** (đỡ vài phút biên dịch + tải ORT mỗi lần mở Colab).

   *Hiểu 3 "nơi" này là HẾT rối:*
   - **Drive** (`/content/drive/MyDrive/`) — kho **BỀN**, sống mãi. Thư mục `FairyZero` của bạn (gọi là
     **"bundle"**) nằm ở đây.
   - **Ổ local của Colab** (`/content/`) — **NHANH** nhưng **bị xoá sạch mỗi phiên**. Bắt buộc build ở đây.
   - **"Engine đã build"** = file `build-linux/custom_engine` + thư viện ORT trong `third_party/` — thứ tốn
     công biên dịch; ta muốn **cất nó lên Drive** để phiên sau lấy lại, KHỎI build.

   👉 **Bạn chỉ phải quyết 1 điều: cất "engine đã build" Ở ĐÂU trên Drive?** Có 2 cách, chọn 1:
   - **Cách 2 — NHÉT VÀO BUNDLE** *(khuyến nghị, đơn giản):* để engine **ngay trong thư mục `FairyZero`**.
     → Chỉ 1 thư mục, khỏi nhớ cache riêng. Đổi lại bundle nặng thêm ~vài trăm MB.
   - **Cách 1 — CACHE RIÊNG:** để engine ở một thư mục Drive **riêng** tên `FairyZero_prebuilt`, **tách**
     khỏi bundle. → Bundle gọn (chỉ mã nguồn) nhưng phải quản 2 thư mục.

   **➤ Cách 2 (khuyến nghị):**
   ```bash
   # ===== LÀM MỘT LẦN (ngay sau khi bước 3 build xong) — chép engine NGƯỢC vào bundle trên Drive:
   !cp -r /content/FairyZero/engine_src/build-linux  /content/drive/MyDrive/FairyZero/engine_src/
   !cp -r /content/FairyZero/engine_src/third_party  /content/drive/MyDrive/FairyZero/engine_src/

   # ===== MỖI PHIÊN SAU (vài giây, KHÔNG build):
   !cp -r /content/drive/MyDrive/FairyZero /content/FairyZero   # bundle đã kèm sẵn engine
   !bash /content/FairyZero/scripts/colab_prebuilt.sh wrap      # chỉ tạo run.sh + tự kiểm tra
   ```

   **➤ Cách 1 (nếu muốn giữ bundle gọn):**
   ```bash
   # ===== LÀM MỘT LẦN (ngay sau khi bước 3 build xong):
   !bash /content/FairyZero/scripts/colab_prebuilt.sh save      # cất engine -> MyDrive/FairyZero_prebuilt

   # ===== MỖI PHIÊN SAU (vài giây, KHÔNG build):
   !cp -r /content/drive/MyDrive/FairyZero /content/FairyZero   # bundle (chỉ mã nguồn)
   !bash /content/FairyZero/scripts/colab_prebuilt.sh restore   # kéo engine từ cache về bundle + tạo run.sh
   ```

   **Sau đó LUÔN chạy engine qua `run.sh`** (mọi lệnh selfplay/arena/train ở bước 4–6 đều thay đường dẫn
   binary bằng `bash .../engine_src/run.sh`):
   ```bash
   !bash /content/FairyZero/engine_src/run.sh --selfplay --games 1000 --visits 400 \
       --provider cuda --fixed-batch 32 --weights /content/FairyZero/models/seed.onnx --out /content/games_gen0
   ```

   > **Vì sao cần `run.sh`?** Mỗi ô `!` của Colab là một shell mới, nên `LD_LIBRARY_PATH` (đường dẫn tới
   > lib ORT + CUDA) **không sống sót** sang ô khác. `run.sh` (script tự sinh khi `wrap`/`restore`) set lại
   > giúp bạn mỗi lần chạy. Sau `wrap`/`restore`, script tự chạy `--test-uci`; thấy `[PASS]` là OK.
   >
   > **Đừng build trên Drive** (FUSE rất chậm/hay lỗi) — luôn build ở `/content` local rồi mới cất lên Drive.
   >
   > **Khi nào VẪN phải build lại** (hiếm — script tự báo lỗi & thoát): Colab đổi ảnh nền (glibc/Ubuntu) ⇒
   > binary không khởi động; hoặc đổi **CUDA major** ⇒ EP CUDA không nạp (CPU vẫn chạy). Khi đó chạy lại
   > `colab_setup.sh` rồi lưu lại (Cách 2: chép artefact vào bundle; Cách 1: `save`). Đổi nơi cache:
   > `FZ_CACHE=...`; đổi phiên bản ORT: `ORT_VER=1.18.0 bash ... save`.

4. **Bước 1 — sinh dữ liệu trên GPU** (sinh vào ổ local `/content`, ĐỪNG sinh thẳng lên Drive):
   ```
   !/content/FairyZero/engine_src/build-linux/custom_engine --selfplay \
       --games 1000 --visits 200 --parallel 2 --provider cuda --fixed-batch 32 \
       --weights /content/FairyZero/models/seed.onnx --out /content/games_gen0
   ```
   > Lệnh gọi binary trực tiếp ở trên dùng được ngay sau khi build (bước 3). Nếu báo lỗi thiếu thư viện
   > ORT (`error while loading shared libraries`), hoặc bạn đã dùng 3b (`wrap`/`restore`), hãy chạy qua
   > wrapper: `!bash /content/FairyZero/engine_src/run.sh --selfplay ...` (xem 3b).
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

> **Từ 2026-09-24 engine kiểm TOÀN BỘ dòng lệnh trước khi chạy.** Cờ lạ (gõ nhầm), cờ thiếu giá trị,
> số sai định dạng hay ngoài khoảng (`--visits 8OO`, `--visits 0`, `--noise-alpha abc`, `--fixed-batch 65`),
> hay một từ thừa → engine in `custom_engine: ...` cho từng lỗi, **không chạy gì** và thoát mã 2.
> Trước đây những thứ này bị bỏ qua không một lời: gõ `--visit 800` là sinh dữ liệu ở 200 visits mặc
> định, gõ `--max-move 400` là xử hoà mọi ván ở 200 ply. (`train.py` vốn đã báo lỗi cờ lạ nhờ argparse.)

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

**CHƯA DÙNG ĐƯỢC:** vài tham số search hiếm/nội bộ chưa đưa vào (`solid-tree-threshold`,
`minimum-*-work`…); `go depth N`/`go mate N` (nhận nhưng chưa giới hạn); `score mate N` (chưa phát);
ponder mới ở mức cơ bản (kết thúc khi `ponderhit`, chưa cấp thêm ngân sách thời gian).

### D.2. Khi SINH DỮ LIỆU (`custom_engine.exe --selfplay`)

**DÙNG ĐƯỢC — cờ CLI:**
| Cờ | Mặc định | Ý nghĩa |
|----|----------|---------|
| `--games N` | 100 | Tổng số ván engine tự đánh với chính nó và ghi lại. Càng nhiều → dữ liệu huấn luyện càng phong phú nhưng càng lâu. |
| `--max-seconds S` | 0 (tắt) | Giới hạn thời gian: dừng khi chạy quá S giây kể từ ván đầu (song song với trần `--games`, dừng khi CÁI NÀO đến trước). Dừng "mềm" — ngừng nhận ván mới, ván đang chạy vẫn hoàn tất. Dùng khớp **quota Colab**: đặt `--games` thật lớn rồi để S là ràng buộc (xem B.2). |
| `--visits N` | 200 | Số playout MCTS mỗi nước trong lúc tự chơi. Cao → nước đi chất lượng hơn (dữ liệu tốt hơn) nhưng chậm. Đời đầu để 200, đời sau tăng 400/800. |
| `--parallel K` | 1 | Số ván chạy **song song** cùng lúc. Đặt ≈ số nhân CPU để tận dụng hết máy → sinh nhanh hơn nhiều. |
| `--threads-per-game T` | 1 | Số luồng MCTS dùng cho **mỗi** ván. Thường để 1 và tăng `--parallel` thay vì cái này. |
| `--max-moves N` | 200 | Trần số **ply** (nửa nước: mỗi nước của một bên tính 1; 400 ply = 200 nước đầy đủ) mỗi ván; tới hạn thì xử hòa để khỏi kẹt ván dài vô tận. |
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
| `--zobrist-seed N` | ngẫu nhiên | Seed 10 chữ số (10^9 … 10^10−1) của **khoá Zobrist** ("dấu vân tay" thế cờ dùng cho lặp thế và cache mạng). Mặc định mỗi lần chạy chương trình một seed mới, rút từ nguồn ngẫu nhiên của hệ điều hành, in ở dòng đầu log: `Zobrist seed … (random for this run; --zobrist-seed … repeats it)`. Chỉ ảnh hưởng dấu vân tay, **không** ảnh hưởng nước đi, nhiễu hay nhiệt độ. Có ở mọi chế độ (self-play, arena, UCI, test). |
| `--start-fen FEN\|FILE` | startpos | Thế cờ bắt đầu mỗi ván; truyền một tệp để xoay vòng nhiều thế (đa dạng khai cuộc; một FEN mỗi dòng, `#` là chú thích). Mỗi FEN được **kiểm trước ván đầu**: đủ trường `N+N` (thiếu thì FSF chơi 1+1), bàn 10×10, đúng một Hoàng gia mỗi bên, bên không tới lượt không bị chiếu, quyền nhập thành ra đúng như viết (xem A.4). Sai là dừng và báo số dòng. |
| `--resign-threshold F` | tắt | Tự xin thua khi điểm tốt nhất `best_q ≤ F` để bỏ ván thua rõ (nhanh hơn). Bật bằng vd `-0.90`; mặc định tắt = đánh tới cùng. |
| `--resign-consecutive N` | 3 | Cần N **lượt liên tiếp** dưới ngưỡng mới xin thua (tránh thua nhầm vì một nước tụt điểm). |
| `--resign-earliest-move N` | 0 | Không cho xin thua trước nước thứ N (để không bỏ ván quá sớm). |
| `--no-resign-frac F` | 0.10 | Tỉ lệ ván **tắt** resign, đánh tới cùng — để mạng vẫn học cách kết liễu/phòng thủ thế thua. |
| `--search-opt name=value` (lặp) | — | Đặt **bất kỳ** search-param lc0 nào cho self-play (xem danh sách ~35 ở D.1). Lặp nhiều lần, vd `--search-opt cpuct-base=20000 --search-opt two-fold-draws=true`. Tên lạ, giá trị sai kiểu hay ngoài khoảng của lc0 (vd `draw-score` ∈ [-1, 1], `fpu-strategy` ∈ {reduction, absolute}, `minibatch-size`/`max-prefetch` ≤ 64) → **dừng** kèm lý do. Trước 2026-09-24 tên lạ chỉ in một dòng cảnh báo, còn giá trị hỏng âm thầm thành một mặc định cứng (`max-prefetch=x` → 32). |
| `--search-opt max-prefetch=N` | **0** (self-play) | Số vị trí tối đa search "nạp trước vào cache" khi batch chưa đầy (lc0 mặc định 32). Prefetch chỉ đoán trước để lấp cache, **không đổi giá trị đánh giá** nên không ảnh hưởng chất lượng dữ liệu. Đo trên Colab T4 (`--parallel 4 --fixed-batch 16 --visits 800`): tắt prefetch cho **+37% playout/giây** (2.488 → 3.401), vì GPU bão hoà ở cả hai cấu hình và prefetch tốn ~27% ô batch cho phần đoán + pad. **Từ 2026-09-23 self-play mặc định 0**; đặt `max-prefetch=32` nếu muốn hành vi lc0 gốc. |
| `--show-nps` | tắt | Hiện **NPS tổng** (cộng dồn mọi worker) trong log mỗi ván + dòng tổng kết, **cộng một khối `--- Throughput ---`** ở cuối. Mặc định TẮT. **Từ 2026-09-22 nps đếm playout MỚI** — trước đó nó cộng `root->GetN()` mỗi nước, mà giá trị này đã bao gồm cây tái sử dụng từ nước trước nên **phóng đại ~2×**; số cũ và mới KHÔNG so thẳng được. |
| `--batch-aggregate` | tắt | **(A4 — chỉ GPU)** Gom thế cờ cần eval từ NHIỀU ván song song vào **một batch NN** chạy một lần → GPU no hơn, ít lệnh inference hơn. Mặc định TẮT. |
| `--batch-timeout-us N` | 2000 | Cửa sổ gộp batch (micro-giây) khi dùng `--batch-aggregate`: chờ tối đa N µs cho các ván khác kịp nộp rồi mới chạy (cũng là chốt chống treo). |

> **`--batch-aggregate` dùng khi nào?** CHỈ với **GPU** (`--provider cuda` hoặc `dml`) **và `--parallel ≥ 2`**.
> - Trên **DML (Windows)**: self-play `--parallel ≥ 2` mà KHÔNG bật cờ này sẽ **crash** (EP DirectML không cho nhiều luồng `Run` đồng thời). Bật `--batch-aggregate` vừa **hết crash** vừa nhanh hơn (đo trên Iris Xe: 50 vs 39 nps so với `--parallel 1`).
> - Trên **CUDA (Colab T4)**: tăng throughput sinh dữ liệu khi chạy nhiều ván song song (GPU mạnh, batch lớn càng lợi).
> - **ĐỪNG bật trên `--provider cpu`**: nó dồn inference vào một luồng → **CHẬM hơn** nhiều (engine sẽ tự in cảnh báo). CPU cứ để TẮT và dùng `--parallel = số nhân`.

**Khối `--- Throughput ---` (mới 2026-09-22, in khi bật `--show-nps`):**

| Dòng | Nghĩa |
|---|---|
| `Van/gio`, `Giay/van` | mục tiêu thật sự. **Cảnh báo:** với mẫu dưới ~50 ván, độ dài ván dao động áp đảo — đừng so cấu hình bằng con số này |
| `NN eval/giay` | công việc GPU thật sự. Nhân ~1,0 GFLOP ra TFLOP/s (T4 đỉnh fp32 = 8,1) |
| `NN eval/playout` | >1 nghĩa là nhiều lượt gọi mạng cho một playout (collision, cache miss) |
| `Batch TB moi Run()` | batch trung bình mỗi lần gọi GPU. Thấp hơn `--fixed-batch` nhiều = lãng phí |
| `Phi do pad` | % thời gian GPU tính ô rỗng do `--fixed-batch` pad. Nên dưới 10% |

> **So sánh cấu hình thì dùng `NN eval/giay` hoặc `playout/giây`, KHÔNG dùng `Van/gio`.**

**Chế độ `--bench-nn` (mới 2026-09-22) — đo suy luận THUẦN TUÝ, không MCTS:**

```
custom_engine --bench-nn --weights net.onnx --provider cuda --fixed-batch 16
```

Nạp mạng rồi gọi `ComputeBlocking()` lặp lại, **không cây, không cache**, dựng một ORT session riêng
cho từng cỡ batch (1…64) và chạy đầy. Cho biết **trần tuyệt đối** của mạng trên máy đó, tách khỏi mọi
thứ khác trong engine — dùng để trả lời "engine chậm, hay phần cứng chỉ được vậy?".

In thêm một phép khớp tuyến tính `ms/Run ≈ a + b×batch`: `a` là chi phí cố định mỗi lần gọi (batch lớn
sẽ pha loãng), `b` là chi phí mỗi vị trí (nghịch đảo ra trần TFLOP/s).

**`--cuda-graph` (mới 2026-09-22, THỰC NGHIỆM — CHƯA kiểm chứng trên phần cứng thật):**

```
custom_engine --bench-nn --weights net.onnx --provider cuda --fixed-batch 16 --cuda-graph
```

Bật CUDA Graph capture của ONNX Runtime (`enable_cuda_graph`) cho session CUDA. Ý tưởng: phép
khớp tuyến tính ở trên tách được một khoản "chi phí cố định mỗi lần gọi" khá lớn ở batch sản xuất
(16) — hình dạng đặc trưng của overhead khởi chạy kernel CUDA qua ~12 block ResNet, KHÔNG phải
FLOPs (FLOPs/vị trí không đổi theo batch). CUDA Graph ghi lại chuỗi kernel một lần rồi phát lại
bằng một lệnh gọi duy nhất, nhắm thẳng vào khoản chi phí đó. Đòi hỏi `--fixed-batch` (không hỗ trợ
batch động).

Khi bật cờ này, `--bench-nn` tự dựng **hai** session ở cùng `fixed_batch` (một có graph, một
không) và in ra:
1. **Sai lệch đầu ra** (`q`, `d`, toàn bộ policy hợp lệ) giữa hai session trên CÙNG một thế cờ —
   `[FAIL]` nếu lệch quá 1e-3. Đây là bước bắt buộc: che giấu đúng-sai ở đây sẽ âm thầm làm hỏng
   dữ liệu huấn luyện, không chỉ là crash.
2. **Tốc độ** hai bên, % chênh lệch.

**Chỉ tin dùng cho self-play/arena thật sau khi cả hai mục trên đều tốt trên Colab.** Cờ này CHƯA
được nối vào `--selfplay`/`--arena`/`--uci-nn` — muốn dùng sản xuất phải thêm `cuda_graph=1` vào
backend_opts tương ứng (xem `onnx_backend.cc`) sau khi đã xác minh.

**CHƯA DÙNG ĐƯỢC từ CLI self-play:** `--resign-wdlstyle` (resign theo ngưỡng WDL) chưa viết.
*Lưu ý: self-play VỐN đã tái dùng cây trong một ván (không cần cờ riêng).*

### D.3. Khi HUẤN LUYỆN (`python train.py`)

**DÙNG ĐƯỢC — cờ CLI:**
| Cờ | Mặc định | Ý nghĩa |
|----|----------|---------|
| `--data X` | — | Nguồn dữ liệu: một thư mục, nhiều thư mục (ngăn bằng dấu phẩy — dùng cho cửa sổ trượt nhiều đời), hoặc một tệp `.zip` đã gói. **Mỗi phần phải khớp ít nhất một tệp**, không thì dừng (trước 2026-09-24 phần gõ sai bị bỏ qua, nên có thể huấn luyện thiếu cả một đời mà không biết). |
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
| `--swa-start-frac F` | 0.75 | **SWA**: mạng xuất ra là trung bình trọng số ở cuối các epoch **bắt đầu sau** mốc F của quá trình train (20 epoch, 0.75 → epoch 16–20). `train.py` in ra `swa: averages the end of epochs a..b`. Với `--epochs 2` chỉ còn epoch 2 (tức không trung bình); `--swa-start-frac 0` trung bình mọi epoch — đây là cách gen1 đã được train, vì trước 2026-09-24 mốc bị tính sớm một epoch. |
| `--optimizer adamw\|sgd\|nadam` | adamw | Thuật toán tối ưu. `adamw` (mặc định) bền, chạy ngon với LR hằng; `sgd`+momentum = recipe chuẩn lc0 (mạnh nhất nhưng cần lịch LR đúng); `nadam` = Adam + Nesterov. |
| `--momentum M` | 0.9 | Quán tính cho `--optimizer sgd` (bật luôn Nesterov). Chỉ dùng khi chọn sgd. |
| `--grad-clip G` | 0 (tắt) | Cắt độ lớn (norm) của gradient xuống ≤ G để tránh "nổ" gradient làm train phân kỳ. 0 = tắt. |
| `--seed S` | ngẫu nhiên | Seed của lần train: thứ tự xáo trộn thế cờ, down-sampling, chọn ván kiểm định. Mặc định **mỗi lần chạy một seed 10 chữ số mới** (10^9 … 10^10−1), rút từ bộ sinh số ngẫu nhiên an toàn của hệ điều hành (`secrets`), in ở log: `[train] seed … (random for this run; --seed … repeats it)`. Truyền lại số đó để train lại y hệt từng trọng số (trên CPU; GPU có thể lệch rất nhỏ). |
| `--warmup-steps N` | 0 | Tăng LR tuyến tính từ 0 lên trong N bước đầu cho ổn định, rồi mới theo lịch. |
| `--lr-values a,b` + `--lr-boundaries i` | — | **Lịch LR bậc thang** kiểu lc0: đặt LR theo từng chặng bước (ghi đè `--lr`). Vd values `0.02,0.002,0.0005` + boundaries `100000,130000`. |
| `--accum-steps K` | 1 | **Tích lũy gradient** K lô nhỏ rồi mới cập nhật một lần → batch hiệu dụng = batch × K, mà bộ nhớ chỉ tốn bằng một lô. Cứu cánh cho GPU nhỏ (Colab). |
| `--max-steps N` | 0 | Dừng sau N bước tối ưu (thay cho hoặc cùng với `--epochs`). 0 = chỉ theo epochs. Dừng trước khi SWA lấy mẫu nào thì xuất trọng số đã học như hiện có (trước 2026-09-24 xuất nhầm **trọng số ban đầu chưa học**). |
| `--max-records N` | 0 | Chỉ nạp tối đa N thế cờ (chạy thử nhanh / hạn chế RAM). 0 = nạp tất cả. |
| `--val-frac F` | 0.04 | **Tập kiểm định:** giữ riêng tỉ lệ F số **ván** (nguyên ván: mọi thế cờ của ván đó; mỗi tệp `game_*.gz` hay mỗi ván trong `.zip` là một ván), chọn là các ván có **thời gian sửa (date modified) mới nhất** — tức self-play mới nhất, mạng đời trước chưa học — không đem train (đổi tên tệp bằng Explorer không đổi thời gian này; `.zip` giữ thời gian của từng tệp). Log in `[val] validation games modified … ; training games up to …` để kiểm là ván đời mới nhất. In `[val]` 4 lần với `--epochs 2`: trọng số ban đầu, sau epoch 1, sau epoch 2, mạng xuất ra (sau SWA). Mỗi dòng có 2 cặp số: `train:` (một phần tập train, cùng số thế cờ với tập kiểm định) và `validation:`; cả hai tính như nhau (trọng số cố định, trung bình loss trên từng thế cờ). `validation` cao hơn `train` nhiều và ngày càng xa = mạng học thuộc ván. Ít ván quá (F × số ván làm tròn ra 0) thì bỏ qua và báo. 0 = tắt. |
| `--report-every N` | 0 | In loss mỗi N bước để theo dõi tiến độ trong epoch. 0 = chỉ báo cáo theo từng epoch. |
| `--save-every N` | 0 | Lưu checkpoint `.pt` mỗi N bước (đề phòng mất điện/đứt Colab). 0 = chỉ lưu khi xong. |
| `--se-ratio R` | 8 | Mức nén của SE block trong mạng (xem giải thích ở mục B câu hỏi se-ratio). **CHỈ đổi khi train từ đầu** — đổi giữa chừng sẽ không nạp được trọng số cũ. |
| `--dropout R` | 0 | Tỉ lệ dropout ở value head để chống quá khớp khi dữ liệu ít. 0 = tắt (giống lc0); bật vd 0.1 nếu dòng `[val]` cho thấy `validation` value cao hơn hẳn `train` (xem `--val-frac`). An toàn warm-start. |
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
| `--max-moves N` | 200 | Trần số **ply** (nửa nước) mỗi ván (chạm trần ⇒ tính hòa). |
| `--temp-cutoff N` | 30 | Số nước đầu lấy mẫu theo visit (để hai ván không giống hệt nhau); đấu nghiêm ngặt có thể đặt nhỏ (vd 6) hoặc 0 để hai mạng đánh "tốt nhất" hoàn toàn. |
| `--provider cpu\|cuda\|dml` | cpu | Thiết bị suy luận. `cuda` cho Colab (bản `-Duse_cuda`); `dml` cho GPU Windows — kể cả NVIDIA (bản `-Duse_dml`). |
| `--backend-threads N` | 1 | Số luồng intra-op cho ONNX khi `cpu`/`dml` (nên đặt = số nhân, vd 4). |
| `--fixed-batch N` | 16 | Kích thước batch cố định khi `--provider cuda`. |
| `--cpuct F` | (mặc định search) | Hằng số thám hiểm MCTS; đặt giống nhau cho cả hai mạng để công bằng. |
| `--policy-temp F` | 1.0 | Nhiệt độ làm mềm policy của mạng (giữ 1.0 cho đánh giá trung tính). |
| `--show-nps` | tắt | In NPS (playout/giây) gộp sau mỗi ván + tổng kết, để đo tốc độ. |
| `--arena-moves` | tắt | In **danh sách nước đi (UCI)** của mỗi ván (`moves: 1.e2e4 ...`) để bạn theo dõi/xem lại ván — vd kiểm tra mạng có thí quân bậy không. |

> **`--search-opt name=value` có tác dụng trong arena** (cho cả hai mạng; trước 2026-09-24 bị bỏ qua).
>
> **Cờ self-play KHÔNG có tác dụng trong arena:** `--threads-per-game`, `--parallel`, `--noise-*`,
> `--resign-*`, `--start-fen`, `--out`, `--max-seconds`... Arena đánh **tuần tự từng ván**
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
  `[PASS]`. Bộ test đầy đủ (mỗi cờ một mảng, danh mục ở `src/tests/README.md`): quan trọng nhất là
  `--test-search-logic --weights <mạng.onnx>` (dấu giá trị trong dữ liệu, nhiễu Dirichlet mọi nước,
  sổ sách cây MCTS đa luồng, `AddInput` an toàn đa luồng, `ReuseTree`, stress vòng đời search) và
  `--test-history` (cắt lịch sử 200 nước, khoá Zobrist/e.p., khoá cache, thứ tự luật kết thúc ván,
  lặp thế ở mọi mức rule50) và `--audit-rules` (so engine với **một bộ luật viết lại độc lập** trên
  ván ngẫu nhiên: nước hợp lệ, kết quả từng nước, chiếu, ep, nhập thành, kết thúc ván, plane mạng;
  chạy sâu: `--audit-rules --games 1000 --max-moves 300`, ~70 s).
- **Đo chi phí CPU của self-play:** `custom_engine.exe --bench-cpu` in ns/lần cho sinh nước, lịch sử,
  mã hoá đầu vào mạng, ghi bản ghi + gzip (không cần mạng). Dùng để quyết có đáng tối ưu phần CPU không.

---

Chúc bạn chơi vui và huấn luyện ra những đời mạng ngày càng mạnh! 🦊♟️
