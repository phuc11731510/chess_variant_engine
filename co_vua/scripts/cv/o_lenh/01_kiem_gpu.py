# Kiểm GPU
# cv: nhanh
# Máy Colab có GPU gì. Phải thấy "Tesla T4"; không thấy gì = máy CPU.
!nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
