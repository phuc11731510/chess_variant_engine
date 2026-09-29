# Arena đời mới đấu đời cũ (mục 6)
# Mục 6 của sổ tay: arena đời mới (NEXT) đấu đời cũ (CURRENT).
# 48 ván vẫn sai số lớn (hàng trăm Elo); phát hiện chênh ~50 Elo cần 400-1000 ván.
# --search-opt max-prefetch=0: như ô 04 -- bỏ đánh giá mạng "đoán trước" (đo trên T4: +37% nps).
# Gom batch như ô 04 (engine từ 4501740, 2026-09-29): 16 ván cùng lúc, mỗi mạng gom lá của mọi ván
# đang đến lượt nó vào một lần chạy GPU (--batch-aggregate, --fixed-batch 64, minibatch 32,
# task-workers 0). Đo T4 gen11 vs gen10: 2.164 -> 2.400 nps (+11%), ván/giờ +19%. Binary cũ không có
# arena gom batch: log thiếu dòng "[arena] batch-aggregate ON" -> lấy binary mới (ô 02).
# fz: hoi GAMES Số ván arena (hai bên đổi màu mỗi ván)
GAMES = 100

cmd = f"""bash {E}/run.sh --arena \
    --model-a {NEXT_ONNX} \
    --model-b {CURRENT_ONNX} \
    --games {GAMES} --visits 400 --temp-cutoff 32 \
    --provider cuda --fixed-batch 64 --max-moves 400 --show-nps \
    --search-opt max-prefetch=0 --parallel 16 --batch-aggregate \
    --search-opt minibatch-size=32 --search-opt task-workers=0"""

print(cmd)
!{cmd}
