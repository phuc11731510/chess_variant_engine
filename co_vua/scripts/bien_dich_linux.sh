#!/usr/bin/env bash
# Bien dich engine co vua (co_vua/engine, ban sao lc0) thanh binary Linux cho Colab, trong container Docker
# Ubuntu 24.04 (giong Colab: GCC 13.3, glibc 2.39). Goi tu co_vua/bien_dich_linux.bat; khong chay truc tiep.
#
#   /src     = thu muc goc du an (D:\chess_variant); dich THU MUC LAM VIEC cua co_vua/engine (ca phan chua
#              commit), thong tin git ghi vao thong_tin.txt de biet binary dich tu dau
#   /ortsrc  = C:\fz_build (goi ONNX Runtime 1.20.1 GPU: ort-gpu-1.20.1.tgz)
#   /content = volume Docker cv_build: cay ma + build-linux giu lai giua cac lan (chi dich lai tep doi)
#
# Ket qua: co_vua/ban_linux/lc0 + lib/ (thu vien ONNX Runtime) + thong_tin.txt
set -euo pipefail
ORT=onnxruntime-linux-x64-gpu-1.20.1
ED=/content/co_vua_engine
ORTD=/content/ort/$ORT   # ngoai cay ma nguon: meson cua lc0 khong cho include tuyet doi trong cay
OUT=/src/co_vua/ban_linux

git config --global --add safe.directory /src
REV=$(git -C /src rev-parse --short HEAD)
BAN=$(git -C /src status --porcelain -- co_vua/engine | wc -l)
echo "[linux] commit $REV; tep chua commit trong co_vua/engine: $BAN"

# rsync -c (so noi dung, khong giu mtime): chi tep thay doi mang mtime moi, nen ninja chi dich lai tep do.
mkdir -p "$ED"
rsync -rlc --delete --include "/subprojects/packagefiles/***" \
  --exclude /build-linux/ --exclude "/subprojects/*/" \
  /src/co_vua/engine/ "$ED/"

if [ ! -f "$ORTD/include/onnxruntime_cxx_api.h" ]; then
  echo "[linux] giai nen ONNX Runtime ($ORT) ..."
  mkdir -p /content/ort
  tar -xzf /ortsrc/ort-gpu-1.20.1.tgz -C /content/ort
fi

cd "$ED"
if [ ! -f build-linux/build.ninja ]; then
  rm -rf build-linux
  # Chi bat backend ONNX (onnx-cuda chay tren T4 qua ONNX Runtime; khong can CUDA toolkit luc dich).
  # native_arch=false: khong dich theo CPU cua may nay, vi binary chay tren CPU cua Colab.
  meson setup build-linux --buildtype=release \
    -Dnative_arch=false -Dgtest=false \
    -Dblas=false -Dopenblas=false -Dispc=false \
    -Dplain_cuda=false -Dcudnn=false -Dnvcc=false -Dcutlass=false \
    -Donnx=true -Donnx_libdir="$ORTD/lib" -Donnx_include="$ORTD/include" \
    '-Dcpp_link_args=-Wl,-rpath,$ORIGIN/lib'
fi
ninja -C build-linux lc0
BIN=$ED/build-linux/lc0

# Phien ban glibc / libstdc++ ma binary doi phai co tren Colab (Ubuntu 24.04: glibc 2.39, GLIBCXX 3.4.33).
gmax=$(objdump -T "$BIN" | grep -o 'GLIBC_[0-9.]*' | sort -uV | tail -1)
cmax=$(objdump -T "$BIN" | grep -o 'GLIBCXX_[0-9.]*' | sort -uV | tail -1)
echo "[linux] can toi da: $gmax, $cmax"
printf '%s\n%s\n' "$gmax" GLIBC_2.39 | sort -CV || { echo "[linux] LOI: can glibc moi hon Colab"; exit 1; }
printf '%s\n%s\n' "$cmax" GLIBCXX_3.4.33 | sort -CV || { echo "[linux] LOI: can libstdc++ moi hon Colab"; exit 1; }

mkdir -p "$OUT/lib"
cp -f "$BIN" "$OUT/lc0"
cp -f "$ORTD/lib/"libonnxruntime*.so* "$OUT/lib/"

# Chay thu tren CPU (may nay khong co GPU NVIDIA; onnx-cuda chi kiem duoc tren Colab).
"$OUT/lc0" --help > /dev/null && echo "[linux] binary chay duoc"

{ echo "commit=$REV"; echo "tep_chua_commit=$BAN"; echo "built=$(date '+%Y-%m-%d %H:%M:%S')";
  echo "gcc=$(gcc -dumpfullversion)"; echo "glibc_max=$gmax"; echo "glibcxx_max=$cmax";
  echo "sha256=$(sha256sum "$BIN" | cut -d' ' -f1)"; } > "$OUT/thong_tin.txt"
cat "$OUT/thong_tin.txt"
echo "[linux] XONG: co_vua/ban_linux/lc0"
