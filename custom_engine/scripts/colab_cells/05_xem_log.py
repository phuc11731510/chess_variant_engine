# Xem tiến độ việc chạy nền
# Xem tiến độ việc đang chạy nền. Đổi LOG thành "train" hoặc "arena" khi cần.
LOG = "selfplay"
SO_DONG = 15

!tail -n {SO_DONG} /content/{LOG}.log
!ls {OUT_GAMES_DIR} 2>/dev/null | wc -l | sed "s/^/[so tep van] /"
!nvidia-smi --query-gpu=name,utilization.gpu,memory.used --format=csv,noheader
!pgrep -af '[c]ustom_engine|[t]rain\.py' >/dev/null && echo '[DANG CHAY]' || echo '[KHONG con tien trinh -- xong hoac loi]'
