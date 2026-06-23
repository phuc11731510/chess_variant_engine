# Walkthrough — GUI Mốc M1: Lệnh engine `legalmoves` / `result` / `fen`

> Đợt chỉnh sửa: **2026-06-23**. Mục tiêu M1 (theo `implementation_plan_GUI.md` §5.2/§6/§11):
> bổ sung cho engine các lệnh để **engine làm trọng tài luật**, GUI không phải code lại luật biến thể.
>
> **Kết quả: M1 ✅ HOÀN TẤT** — thêm 3 lệnh, build cả CPU lẫn DML, test tay ra đúng định dạng.

---

## 0. TL;DR

| Việc | Kết quả |
|---|---|
| File sửa | `custom_engine/src/app/uci_nn_engine.cc` (vòng `UciNnEngine::Loop()`, ngay sau lệnh `d`) |
| Lệnh thêm | `legalmoves`, `result`, `fen` |
| Build | `ninja -C build` (CPU) ✓ + `ninja -C build-dml` (DML) ✓ |
| Test tay | startpos → 34 nước hợp lệ, `result undecided`, `fen` sạch — đúng |

---

## 1. Vì sao cần M1

GUI (Kiểu A) sẽ nói chuyện với engine bằng UCI. `--uci-nn` đã có `position/go/d/setoption/...`
nhưng **thiếu** cách liệt kê **nước hợp lệ** và báo **kết quả ván**. Nếu GUI tự tính các thứ này
thì phải code lại toàn bộ luật biến thể (sergeant đôi bước, en passant đặc biệt, nhập thành, phong
`b h m n v y`) — nguồn lỗi lớn. Giải pháp: để **engine trả lời**, GUI chỉ vẽ + nhận thao tác.

---

## 2. Thay đổi mã (1 file)

Thêm 3 nhánh lệnh vào `UciNnEngine::Loop()` trong `src/app/uci_nn_engine.cc`:

### `legalmoves` — liệt kê nước hợp lệ (viết CHO HIỆU NĂNG)
```cpp
} else if (cmd == "legalmoves") {
    if (tree_) {
        const auto& board = tree_->GetPositionHistory().Last().GetBoard();
        const bool black = tree_->IsBlackToMove();
        const lczero::MoveList moves = board.GenerateLegalMoves();   // movegen native
        std::string line;
        line.reserve(moves.size() * 8 + 16);     // 1 buffer, tránh cấp phát lại
        line += "legalmoves";
        for (const lczero::Move& m : moves) {
            line += ' ';
            line += CanonicalMoveToUci(m, black); // -> UCI toạ-độ-thật
        }
        Send(line);                               // 1 lần ghi, không flush từng token
    } else {
        Send("legalmoves");
    }
}
```
**Lý do hiệu năng:** (1) dùng `ChessBoard::GenerateLegalMoves()` — movegen native của Stockfish,
KHÔNG brute-force; (2) gom vào **một `std::string` đã `reserve`**; (3) **một lần `Send`** (không
`std::endl`/flush mỗi token). movegen mới là chi phí chính, phần dựng chuỗi là không đáng kể.
Lệnh này chỉ chạy 1 lần/lượt nên không phải điểm nóng.

### `result` — kết quả ván
```cpp
} else if (cmd == "result") {
    const char* r = "undecided";
    if (tree_) {
        switch (tree_->GetPositionHistory().ComputeGameResult()) {
            case lczero::GameResult::WHITE_WON: r = "white"; break;
            case lczero::GameResult::BLACK_WON: r = "black"; break;
            case lczero::GameResult::DRAW:      r = "draw";  break;
            default: break;  // UNDECIDED
        }
    }
    Send(std::string("result ") + r);
}
```
Tận dụng `ComputeGameResult()` (đã dùng trong arena/self-play) → bao trọn luật thắng/hòa của biến thể.

### `fen` — FEN sạch một dòng
```cpp
} else if (cmd == "fen") {
    if (tree_) {
        Send("fen " + tree_->GetPositionHistory().Last()
                          .GetBoard().GetRawPosition().fen());
    } else {
        Send("info string no position set (send 'position ...' first)");
    }
}
```
Giúp GUI lấy FEN để vẽ bàn mà **khỏi parse tranh ASCII** của lệnh `d`.

---

## 3. Build

```bash
ninja -C build        # CPU   -> Linking target custom_engine.exe   (exit 0)
ninja -C build-dml    # DML   -> Linking target custom_engine.exe   (exit 0)
```
(Cảnh báo `-Wdeprecated-enum-enum-conversion` là của Stockfish có sẵn, không phải từ thay đổi này.)

---

## 4. Test tay & kết quả

Đầu vào (thế xuất phát):
```
position startpos
legalmoves
result
fen
quit
```
Đầu ra (đã rút gọn):
```
legalmoves b3b4 c3c4 d3d4 e3e4 f3f4 g3g4 h3h4 i3i4 b3b5 c3c5 d3d5 e3e5 f3f5 g3g5 h3h5 i3i5
           e2d4 e2f4 f2e4 f2g4 a2b4 j2i4 a1b4 j1i4 c2a4 c2c4 c2e4 h2f4 h2h4 h2j4 a3a5 a3c5 j3h5 j3j5
result undecided
fen vrhbakberv/msysnnsysm/yppppppppy/10/10/10/10/YPPPPPPPPY/MSYSNNSYSM/VRHBAKBERV w KQkq - 7+7 0 1
```
→ 34 nước hợp lệ ở toạ độ thật (a–j, 1–10), `result undecided`, FEN sạch. Bản DML cho kết quả y hệt.

---

## 5. Cạm bẫy gặp phải (lưu cho lần sau)

**Không đưa được stdin vào engine qua pipe:**
- Git Bash: `printf '...' | ./custom_engine.exe --uci-nn` → **exit 127** (Git Bash không exec/đưa
  stdin đúng cho .exe Windows trong pipe này).
- PowerShell: `"uci`nquit" | & exe` → engine chỉ in banner rồi thoát (stdin không tới `getline`).
- **Cách chạy đúng:** `Start-Process -FilePath exe -ArgumentList '--uci-nn'
  -RedirectStandardInput <file_lệnh> -RedirectStandardOutput <file_out> -NoNewWindow -Wait`.

**`fen` in castling `KQkq`** thay cho nhãn `BIbi` của biến thể — đây là biểu diễn nội bộ của
Fairy-Stockfish, **không ảnh hưởng GUI** (GUI chỉ dùng phần bố trí quân trong FEN để vẽ; còn để
ra lệnh cho engine thì dùng `position startpos moves ...`, không gửi FEN ngược lại).

---

## 6. Trạng thái & bước tiếp

- **M1 ✅ DONE.** Cả `build` (CPU) và `build-dml` (DML) đã có 3 lệnh.
- **Chưa commit** (người dùng tự commit).
- **Mốc kế — M2:** viết `UciProcessEngine` phía Flutter: spawn `custom_engine.exe --uci-nn`, làm
  trình tự khởi động (`uci`/`setoption`/`isready`/`ucinewgame`/`position startpos`), rồi gọi
  `legalmoves` + `fen` để lấy dữ liệu cho M3 vẽ bàn. Đọc output engine **bất đồng bộ** (Stream).

## Phụ lục — định dạng giao thức M1 (cho GUI parse)
```
legalmoves <m1> <m2> ...      # 1 dòng; chỉ "legalmoves" nếu hết nước
result     undecided|white|black|draw
fen        <FEN 1 dòng, toạ độ thật>
```
