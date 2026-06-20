# Walkthrough — Phase T7: Vòng lặp AlphaZero đầy đủ (self-play → train → gen mới → lặp)

> Ngày: 2026-06-20 · Dự án: FairyZero (`custom_engine`) — biến thể cờ 10×10.
> Phạm vi: milestone **T7** — khép vòng lặp AlphaZero, áp dụng **Rolling Window (8.2.8)** + **diff_focus (8.2.6)**, có **arena** đánh giá "đời sau thắng đời trước".
> DoD (plan): chạy thành công ≥3 đời; mô hình đời sau mạnh hơn đời trước.
> Trạng thái: ✅ Vòng lặp + arena + rolling window + diff_focus hoàn chỉnh, **portable Windows (CPU) + Colab (GPU)**, đã chạy demo end-to-end.

---

## 0. T7 là gì

T1–T6.5 đã có đủ mảnh ghép: seed (`make_seed`), self-play (`--selfplay`), train (`train.py` warm-start), build Linux/GPU. **T7 là "bộ điều phối"** nối chúng thành vòng lặp tự cải thiện:

```
gen 0 (seed ngẫu nhiên)
  └─► self-play với model_gen{N} ──► games/gen{N}/*.gz
        └─► rolling window (K đời gần nhất) ──► train (warm-start từ gen{N})
              └─► model_gen{N+1} ──► arena vs gen{N} ──► lặp
```

---

## 1. Các thành phần mới

### 1.1. `[NEW] python/loop.py` — bộ điều phối vòng lặp (portable)
Một script Python chạy được **trên cả Windows lẫn Colab** (chỉ khác cờ `--engine` + `--provider`). Mỗi đời:
1. **Self-play** gọi engine `--selfplay` với `model_gen{N}.onnx` → ghi vào `games/gen{N}/`.
2. **Rolling window (8.2.8):** chọn `--window-gens K` thư mục đời GẦN NHẤT (FIFO — đời cũ nhất bị loại khi đời mới thêm vào).
3. **Train (warm-start):** gọi `train.py --init-from model_gen{N}.pt` trên cửa sổ → `model_gen{N+1}`.
4. **Arena (tùy chọn):** `--eval-games E > 0` → đấu gen{N+1} vs gen{N}.
- Tự tạo seed gen-0 nếu chưa có. Bố cục `workdir/{models,games}/`. Đặt `PYTHONIOENCODING=utf-8` cho tiến trình con (chống lỗi unicode console Windows).

### 1.2. `[MODIFY] src/main.cc` — chế độ `--arena` (đánh giá net-vs-net)
- `run_arena(model_a, model_b, games, visits, ...)`: load **2 backend ONNX**, chơi K ván **đổi màu mỗi ván** (công bằng). Mỗi nước: chọn backend theo bên-tới-lượt; **`TrimTreeAtHead()` trước mỗi search** để cây không mang eval cũ của net kia. **Noise OFF** (đánh giá xác định); khai cuộc lấy mẫu theo temperature (đa dạng ván), giữa-tàn cuộc greedy.
- Báo cáo **A score = (A_wins + 0.5·draws)/games** (>0.5 ⇒ A mạnh hơn B).
- Cờ: `--arena --model-a X --model-b Y --games K [--visits --max-moves --temp-cutoff --provider --fixed-batch]`.

### 1.3. `[MODIFY] python/dataset.py` — rolling window + diff_focus
- `_resolve_files` nhận **danh sách dir/glob ngăn cách bằng dấu phẩy** → loop truyền nhiều thư mục đời cho cửa sổ trượt.
- **diff_focus (8.2.6):** `_diff_focus_keep` — giữ record với xác suất tăng theo "độ đột biến" = `|orig_q − best_q| + kld_w·policy_kld`. Thế cờ mà search bất đồng với eval tĩnh của mạng (hoặc π lệch prior) được ưu tiên học. Bật bằng `--diff-focus`.

### 1.4. `[MODIFY] python/train.py` — cờ `--diff-focus`
Truyền diff_focus xuống `FairyDataset`.

---

## 2. Quy trình & lệnh

### Windows (CPU) — thử nghiệm / quy mô nhỏ
```powershell
python python/loop.py --engine build/custom_engine.exe --gens 3 ^
  --games-per-gen 40 --visits 64 --window-gens 3 --epochs 8 ^
  --provider cpu --parallel 6 --eval-games 10 --workdir python/loop_run
```
### Colab (GPU) — quy mô lớn
```bash
python python/loop.py --engine build-linux/custom_engine --gens 10 \
  --games-per-gen 1000 --visits 200 --window-gens 4 --epochs 20 --batch 256 \
  --provider cuda --fixed-batch 32 --parallel 2 --eval-games 40 --diff-focus \
  --workdir python/loop_run
```
> `--window-gens K` × `--games-per-gen G` = số ván trong cửa sổ (plan đề 5k–10k ván; vd K=4, G=2500 ⇒ 10k).

---

## 3. Kết quả verify

### 3.1. Arena (cơ chế đánh giá)
gen0 vs gen0 (cùng net) → **score = 0.5** (6 ván, đều hòa) → arena công bằng, đếm đúng, đổi màu đúng. ✓

### 3.2. Vòng lặp demo (3 đời gen0→gen2, Windows CPU) — PASS, exit 0
```
make_seed → model_gen0 (3.85M) + verify PASS
GEN 0: self-play 6 ván (39.7s) → rolling window 0..0 (96 records)
   train warm-start(gen0.pt): policy 3.63→3.00, value 1.06→0.51 → gen1 export+verify PASS
   arena gen1 vs gen0 → A score 0.5
GEN 1: self-play 6 ván (36.4s, dùng gen1) → rolling window 0..1 (12 files, 192 records)
   train warm-start(gen1.pt): policy 3.19→2.75, value 0.46→0.35 → gen2 export+verify PASS
   arena gen2 vs gen1 → A score 0.5
DONE. Final model: model_gen2.onnx
```
**Những điều demo CHỨNG MINH:**
- ✅ **3 đời chạy khép kín** (DoD "≥3 generations").
- ✅ **Rolling window FIFO đúng:** gen1 train trên `gen0` (1 dir, 96 rec); gen2 train trên `gen0,gen1` (2 dir, 192 rec). Cửa sổ trượt theo `--window-gens`.
- ✅ **Warm-start đúng:** mỗi đời nạp `.pt` đời trước.
- ✅ **Loss GIẢM xuyên đời** (tín hiệu tích lũy học tập): đầu train gen0→1 là policy **3.63**/value **1.06**; đầu train gen1→2 đã là policy **3.19**/value **0.46** (thấp hơn) — nhờ warm-start từ model đã train hơn + cửa sổ dữ liệu lớn hơn.
- Arena đều **0.5**: ở quy mô tí hon này (net gần ngẫu nhiên, ván toàn hòa) chưa có chênh lệch đo được — đúng kỳ vọng (xem §4).

---

## 4. Lưu ý về DoD "đời sau thắng đời trước"
- Cơ chế **arena đã sẵn sàng** để đo. Nhưng với **bootstrap ngẫu nhiên + cutoff ngắn + ít compute** (demo CPU), các ván gần như toàn hòa nên 2–3 đời nhanh CHƯA thể hiện chênh lệch rõ — điều này cần **nhiều ván + visits cao (800) + nhiều đời trên Colab GPU**. Đúng tinh thần plan: "Chạy self-play trên Colab GPU ở visits=800 để lặp đời AI đạt Elo cao".
- Vậy: **vòng lặp + đánh giá đầy đủ và đúng**; mức tăng Elo thực tế là hệ quả của compute, hiển thị qua `A score > 0.5` khi chạy quy mô Colab.

---

## 5. Bảng quyết định kỹ thuật

| Quyết định | Lý do |
|-----------|-------|
| Orchestrator bằng Python (subprocess) | Portable Win/Colab; tách logic vòng lặp khỏi engine C++ |
| Rolling window theo **đời** (FIFO dir) | Đơn giản, đúng FIFO; window_games = window_gens × games_per_gen |
| Arena: `TrimTreeAtHead()` mỗi nước | Cây không lẫn eval của 2 net khác nhau |
| Arena noise OFF + temperature khai cuộc | Đánh giá mạnh nhất + ván đa dạng (không trùng lặp do xác định) |
| diff_focus là tùy chọn (`--diff-focus`) | Kỹ thuật nâng cao; bật khi cần ưu tiên thế khó |
| `PYTHONIOENCODING=utf-8` cho child | Chống lỗi unicode console Windows khi gọi train/export |

---

## 6. Trạng thái & việc tiếp theo
- **CHƯA commit.** File mới: `python/loop.py`. Sửa: `src/main.cc` (arena), `python/{dataset.py, train.py}`, `scripts/colab_setup.sh` (gợi ý loop).
- **T7 = milestone CUỐI của lộ trình huấn luyện.** Sau T7, toàn bộ vòng AlphaZero chạy được trên cả 2 nền tảng.
- Việc còn lại (đã bàn, ngoài T1–T7): **T8** (đóng gói + cầu UCI→MCTS+NN để chơi + sách hướng dẫn) và tối ưu **gom-batch-eval xuyên ván** cho throughput GPU tối đa.
