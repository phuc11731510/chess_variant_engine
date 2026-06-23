# Walkthrough T8.2 + T8.5 — Thông tin tìm kiếm UCI (info/score/pv/ponder) + Đường Colab một-lệnh

> Phạm vi: triển khai **T8.2** (engine UCI phát `info` đầy đủ: score cp/wdl, pv, multipv, time-control
> `wtime/btime`, `searchmoves`, ponder) và **T8.5** (hoàn thiện đường Colab GPU từ chính bundle, thêm
> `colab_loop.sh` chạy trọn vòng lặp bằng một lệnh).
> Ngày: 2026-06-20. Thay đổi: `src/main.cc` (T8.2), `scripts/colab_loop.sh` + `package.ps1` + `HUONG_DAN.md` (T8.5).

---

## PHẦN A — T8.2: Thông tin tìm kiếm UCI

### A.0. Bối cảnh
Sau T8.1, engine chỉ phát `bestmove`. GUI tự viết của bạn cần thấy **đánh giá (score), biến chính (pv),
tiến độ (nodes/nps)** và chơi **có đồng hồ**. T8.2 bổ sung toàn bộ phần `info` + quản lý thời gian + ponder.

### A.1. Hai nguồn `info` — an toàn đa luồng
Khó khăn: search chạy trên **luồng worker**; đọc cây trong lúc đó (để lấy pv) là **không an toàn**.
Giải pháp dùng **hai nguồn**:

1. **Info ĐỊNH KỲ (live)** — qua một `UciResponder` thật (`UciInfoResponder`):
   - lc0 tự gọi `OutputThinkingInfo(...)` định kỳ (dưới khóa nội bộ của nó), đưa cho ta một `ThinkingInfo`
     đã tính sẵn: `depth, seldepth, score (cp), wdl, nodes, nps, time, hashfull`.
   - Ta chỉ **đọc các trường vô hướng** này và format thành dòng `info` — **không đụng cây** → an toàn.
   - KHÔNG kèm `pv` ở đây (pv cần duyệt cây).
2. **Info CUỐI (đầy đủ pv)** — tự tính trong `EmitBestMove`, chạy **sau khi search xong** (worker đã join,
   cây ổn định) → an toàn để duyệt cây và dựng pv.

```cpp
class UciInfoResponder : public lczero::UciResponder {
  void OutputThinkingInfo(std::vector<ThinkingInfo>* infos) override {
    for (auto& ti : *infos) {
      // format: info depth .. seldepth .. multipv .. score cp .. wdl w d l .. nodes .. nps .. time ..
      send_(formatted);   // send_ = engine's mutex-guarded Send()
    }
  }
};
```

### A.2. PV + score + WDL (info cuối, tự tính)
- **PV** (`ComputePvUci`): đi theo chuỗi **con nhiều-visit-nhất** từ root; mỗi ply **lật canonical xen kẽ**
  (`black` đảo mỗi nước) để ra tọa độ thật. Vd `pv d3d5 d8d6 e2f4 f9g7 c2a4` — nước Trắng (d3d5,e2f4,c2a4)
  và nước Đen (d8d6, f9g7, ở hàng 8/9) đều đúng tọa độ thật.
- **score cp** (`QToCp`): quy đổi `q∈[-1,1]` (win-loss, góc nhìn bên-đang-đi) sang centipawn bằng công thức
  logistic của lc0: `cp = 111.7·tan(1.562·q)`, kẹp ±12000.
- **score wdl** (`WdlPermille`): từ `q,d` → `(W,D,L)` phần nghìn, tổng = 1000.
- **MultiPV**: lấy top-K cạnh root (theo visits), mỗi cạnh in một dòng `info multipv k ... pv ...`; option
  `MultiPV` được set vào OptionsDict (`kMultiPvId`) mỗi `go` (không cần dựng lại backend).
- **bestmove + ponder**: `bestmove <nước tốt nhất> ponder <nước đối thủ dự đoán = pv[1]>`.

### A.3. Quản lý thời gian (`go wtime/btime/...`)
`HandleGo` nay parse `wtime btime winc binc movestogo movetime nodes infinite ponder searchmoves`:
```
budget_ms = mytime / max(movestogo, 30) + 0.8 * myinc - MoveOverheadMs   // bên-đang-đi
```
Ưu tiên stopper: `infinite|ponder` → InfiniteStopper · `movetime|wtime/btime` → TimeStopper(budget) ·
`nodes` → PlayoutCountStopper · còn lại → PlayoutCountStopper(Visits mặc định).

### A.4. searchmoves & ponder
- **searchmoves**: các nước sau từ khóa được parse qua `UciToCanonicalMove` (cùng phép lật T8.1) thành
  `MoveList`, truyền vào `Search` → root chỉ xét các nước đó. (Test: `go ... searchmoves b3b4` → `bestmove b3b4`.)
- **ponder (cơ bản)**: `go ponder` chạy kiểu infinite (không tự dừng, **chưa** phát bestmove); `ponderhit`
  (hoặc `stop`) → `StopSearch()` → phát bestmove. (Nghĩ trên thời gian đối thủ; bản đầy đủ thêm ngân sách
  sau ponderhit → T8.x.)

### A.5. Stopper mới
- `PlayoutCountStopper` (dùng `nodes_since_movestart` — **giống hệt PlayoutStopper của self-play**, vốn đã
  được chứng minh điều khiển một search nhiều-playout thật).
- `TimeStopper` (đồng hồ treo), `InfiniteStopper` (không bao giờ dừng).

### A.6. ⚠️ BÀI HỌC GỠ LỖI QUAN TRỌNG: "search chỉ 1 node" là lỗi TEST, không phải engine
Khi test bằng pipe `{ echo "go nodes 400"; echo "quit"; }`, debug cho `rootN=1, sumN=0` — tưởng search
không chạy. Đã loại trừ lần lượt: loại stopper, số luồng (1/2/4), nhiễu Dirichlet, loại responder — **đều
1 node**. Cuối cùng kiểm tra self-play (cùng `Search` class) thì nó search **120 visits/nước bình thường**.

**Nguyên nhân thật:** trong pipe, `quit` nằm **ngay sau** `go`. Engine bất đồng bộ (T8.1): `go` spawn luồng
search rồi **trả về ngay**; main thread đọc dòng kế (`quit`) → `Abort()` **giết search trước khi nó kịp chạy
playout nào**. GUI thật **chờ `bestmove`** rồi mới gửi lệnh tiếp, nên không bao giờ gặp.

**Kiểm chứng đúng** (giữ stdin mở bằng `sleep`):
```
{ echo "...go nodes 400"; sleep 8; echo "quit"; } | engine --uci-nn
→ rootN=181 sumN=180 ... pv d3d5 d8d6 e2f4 f9g7 c2a4   bestmove d3d5 ponder d8d6
```
→ Engine **luôn đúng**; các test pipe trước (kể cả T8.1) chỉ vô tình *under-search* vì `quit` tức thì.
Đây là điểm cần nhớ khi test engine UCI bất đồng bộ: **đừng gửi lệnh sau `go` cho tới khi nhận `bestmove`**.

### A.7. Kết quả test (giữ stdin mở)
```
# info định kỳ + cuối:
info depth 1 seldepth 2 score cp -1 wdl 338 321 341 nodes 17 nps 28 time 634
info depth 2 seldepth 3 score cp 0 wdl 340 320 340 nodes 33 ...
info depth 5 multipv 1 score cp 0 wdl 340 319 341 nodes 272 ... pv d3d5 d8d6 e2f4 f9g7 c2a4
bestmove d3d5 ponder d8d6
# MultiPV 3: ba dòng pv khác nhau (d3d5 / h2h4 / g3g5)
# time control go wtime 3000 btime 3000 -> tự dừng -> bestmove
# searchmoves b3b4 -> bestmove b3b4 (đúng nước bị giới hạn)
# go ponder -> ponderhit -> bestmove (không phát trước ponderhit)
```
`--test-uci` và `--test-encoder` vẫn **PASS** (không phá gì).

---

## PHẦN B — T8.5: Đường Colab GPU từ bundle

### B.0. Trạng thái
Hạ tầng Colab đã có từ trước: build đa nền tảng (T6.5), `colab_setup.sh` **tự dò layout** (sửa ở đợt
trước — chạy được cả repo lẫn bundle), và bundle (T8.4) đã kèm `engine_src/` + `python/` + scripts. T8.5
hoàn thiện thành một đường **một-lệnh** và bổ sung test.

### B.1. `scripts/colab_loop.sh` (MỚI) — chạy trọn vòng lặp bằng một lệnh
```
!bash /content/FairyZero/scripts/colab_loop.sh
```
- **Tự dò** `ENGINE_DIR` (repo hay `engine_src/`) và `PY_DIR` (giống `colab_setup.sh`), tìm binary đã build
  ở `engine_src/build-linux/custom_engine` (báo lỗi gọn nếu chưa build → chạy `colab_setup.sh` trước).
- **Tự set `LD_LIBRARY_PATH`** cho onnxruntime GPU + thư viện CUDA (nvidia-* trong torch + /usr/local/cuda)
  để CUDA EP nạp được.
- Chạy `loop.py --provider cuda` với mặc định GPU; **chỉnh qua biến môi trường**:
  `GENS GAMES VISITS WINDOW EPOCHS BATCH PARALLEL FIXED_BATCH EVAL WORKDIR EXTRA`.
- **`SAVE_DIR`**: nếu đặt, tự copy `*.onnx` kết quả về Drive sau khi xong.
```
!GENS=4 GAMES=400 VISITS=128 bash .../colab_loop.sh
!SAVE_DIR=/content/drive/MyDrive/FairyZero/models bash .../colab_loop.sh
```

### B.2. `colab_setup.sh` (đã hoàn thiện)
- Tự dò layout (repo/bundle), tải onnxruntime GPU đúng CUDA, `meson+ninja` build, chạy **toàn bộ bộ test**
  gồm `--test-uci` và `--test-encoder` (mới thêm), sinh seed, smoke self-play GPU. Mẹo: build ở `/content`
  (ổ local) thay vì Drive cho nhanh/đỡ lỗi FUSE.

### B.3. Đóng gói + tài liệu
- `package.ps1` nay copy **cả** `colab_setup.sh` và `colab_loop.sh` vào `scripts/` của bundle.
- `HUONG_DAN.md` mục C.3 cập nhật: copy sang ổ local → `colab_setup.sh` (build) → `colab_loop.sh` (train) →
  copy model về Drive.

### B.4. Quy trình Colab hoàn chỉnh (đã được người dùng xác nhận build chạy)
```
!cp -r /content/drive/MyDrive/FairyZero /content/FairyZero      # 1. sang ổ local
!bash /content/FairyZero/scripts/colab_setup.sh                 # 2. build + test + smoke
!SAVE_DIR=/content/drive/MyDrive/FairyZero/models \
    bash /content/FairyZero/scripts/colab_loop.sh               # 3. train GPU + lưu Drive
```
(Engine Linux build ra cũng hỗ trợ `--uci-nn` để chơi/đo Elo nếu muốn; chơi thường làm trên Windows.)

---

## C. Tổng hợp file đã đổi

| File | Thay đổi |
|------|----------|
| `src/main.cc` | `UciInfoResponder`; `QToCp`/`WdlPermille`; `HandleGo` parse time-control/searchmoves/ponder/multipv; `ComputePvUci`; `EmitBestMove` phát info+multipv+pv+ponder; `ponderhit`→finalize; stopper `PlayoutCountStopper`; options MultiPV/Ponder |
| `scripts/colab_loop.sh` | **MỚI** — chạy trọn vòng lặp GPU một-lệnh (auto-detect + LD_LIBRARY_PATH + env-tunable + SAVE_DIR) |
| `scripts/package.ps1` | bundle thêm `colab_loop.sh` |
| `HUONG_DAN.md` | mục C.3: lệnh `colab_loop.sh` + lưu model về Drive |

---

## D. Kết luận & bước kế tiếp

**T8.2 hoàn tất**: engine UCI nay phát `info` đầy đủ (score cp/wdl, pv, multipv, nodes/nps/time/seldepth),
chơi có đồng hồ (`wtime/btime`), giới hạn nước (`searchmoves`), và ponder cơ bản — đủ để GUI tự viết hiển
thị eval/biến chính và chơi có thời gian. **T8.5 hoàn tất**: đường Colab GPU một-lệnh từ bundle (build →
train → lưu Drive), test phủ cả UCI + encoder.

Đã ghi nhớ bài học: **engine UCI bất đồng bộ — khi test bằng pipe phải giữ stdin mở (sleep) tới khi có
`bestmove`**, nếu không `quit`/lệnh kế sẽ Abort search và gây ngộ nhận "search nông".

Còn lại (T8.x, tùy chọn): `--play` ASCII trong terminal, combo `Skill`, **tái dùng cây giữa các nước**
(tăng tốc), ponder đầy đủ (cấp ngân sách sau ponderhit), và **T8.3** (mở khóa toàn bộ ~75 siêu tham số
search của lc0 qua passthrough `setoption`/`--search-opt`).

Thứ tự đã đi: **T8.1 ✓ → T8.4 ✓ → T8.6 ✓ → (encoder test ✓) → T8.2 ✓ → T8.5 ✓**.
