# Moi truong bien dich binary Linux CO nhan CUDA (bo chay mang rieng "fzcuda"): image fz-build:24.04 (Ubuntu 24.04, GCC 13.3,
# meson, ninja, liblzma) + bo cong cu CUDA 12.6 (nvcc, cudart, cuBLAS: header + thu vien de lien ket). Khong can GPU de DICH
# (chay thu / do toc do phai tren T4 that: scripts/thu_fzcuda_t4.py).
#
# Dung:  docker build -t fz-build-cuda:24.04 -f custom_engine/scripts/docker/fz-build-cuda.Dockerfile custom_engine/scripts/docker
# Ban dich: bien_dich_linux_cuda.bat (cung cach voi bien_dich_linux.bat, image khac).
#
# Chi cai phan can: nvcc + cudart + cuBLAS (cublasLt.h). Khong cai driver, khong cai ca bo cuda-toolkit (nhieu GB).
FROM fz-build:24.04
ARG CUDA_VER=12-6
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends wget gnupg \
    && wget -q https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb \
    && dpkg -i cuda-keyring_1.1-1_all.deb && rm -f cuda-keyring_1.1-1_all.deb \
    && apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
         cuda-nvcc-${CUDA_VER} cuda-cudart-dev-${CUDA_VER} libcublas-dev-${CUDA_VER} \
    && rm -rf /var/lib/apt/lists/*
ENV CUDA_HOME=/usr/local/cuda-12.6 \
    PATH=/usr/local/cuda-12.6/bin:${PATH}
RUN nvcc --version && ls ${CUDA_HOME}/include/cublasLt.h ${CUDA_HOME}/lib64/libcudart_static.a
