# Arena đời mới đấu đời cũ (mục 6)
# Mục 6 của sổ tay: arena đời mới (NEXT) đấu đời cũ (CURRENT).
# 48 ván vẫn sai số lớn (hàng trăm Elo); phát hiện chênh ~50 Elo cần 400-1000 ván.
# --search-opt max-prefetch=0: như ô 04 -- bỏ đánh giá mạng "đoán trước" (đo trên T4: +37% nps).
# --parallel 4: 4 ván cùng lúc (như ô 04) -> GPU nhận lô đầy hơn. Cần binary có arena song song
# (từ 2026-09-25): log in "[arena] 4 games in parallel". Không thấy dòng đó = binary cũ (vẫn chạy,
# nhưng từng ván một) -> chạy ô 02b một lần rồi đưa binary mới lên Release.
# fz: hoi GAMES Số ván arena (hai bên đổi màu mỗi ván)
GAMES = 100

cmd = f"""bash {E}/run.sh --arena \
    --model-a {NEXT_ONNX} \
    --model-b {CURRENT_ONNX} \
    --games {GAMES} --visits 400 --temp-cutoff 32 \
    --provider cuda --fixed-batch 16 --max-moves 400 --show-nps \
    --search-opt max-prefetch=0 --parallel 4"""

print(cmd)
!{cmd}
