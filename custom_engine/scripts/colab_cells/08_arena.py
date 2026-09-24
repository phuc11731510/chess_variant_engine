# Arena đời mới đấu đời cũ (mục 6)
# Mục 6 của sổ tay: arena đời mới (NEXT) đấu đời cũ (CURRENT).
# 48 ván vẫn sai số lớn (hàng trăm Elo); phát hiện chênh ~50 Elo cần 400-1000 ván.
cmd = f"""bash {E}/run.sh --arena \
    --model-a {NEXT_ONNX} \
    --model-b {CURRENT_ONNX} \
    --games 48 --visits 400 --temp-cutoff 32 \
    --provider cuda --fixed-batch 16 --max-moves 400 --show-nps"""

CHAY_NEN = True   # False = chờ đến khi xong (~30 phút)

print(cmd)
if CHAY_NEN:
    !nohup {cmd} > /content/arena.log 2>&1 &
    print('[da chay nen] xem: sua LOG = "arena" trong o 05, roi: o 05')
else:
    !{cmd}
