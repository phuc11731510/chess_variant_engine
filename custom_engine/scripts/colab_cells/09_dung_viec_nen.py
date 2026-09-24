# Dừng NGAY việc chạy nền
# Dừng NGAY việc đang chạy nền (selfplay / train / arena), ví dụ khi lỡ sai tham số.
# Selfplay dừng giữa chừng: các ván ĐÃ XONG vẫn còn trong thư mục ván; ván đang dở bị mất.
!pkill -f '[c]ustom_engine' ; pkill -f '[t]rain\.py' ; sleep 2
!pgrep -af '[c]ustom_engine|[t]rain\.py' || echo '[da dung het]'
