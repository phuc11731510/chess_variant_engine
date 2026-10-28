#!/usr/bin/env bash
# Bien dich binary Linux cho Colab TREN MAY NAY, trong container Docker Ubuntu 24.04 (giong Colab: GCC 13.3,
# glibc 2.39). Goi tu bien_dich_linux.bat (thu muc goc du an); khong chay truc tiep tren Windows/WSL.
#
#   /src     = thu muc goc du an (D:\chess_variant), lay ma nguon tu git HEAD (DA COMMIT) -- giong Colab clone
#   /ortsrc  = C:\fz_build (goi ONNX Runtime 1.20.1 GPU day du: ort-gpu-1.20.1.tgz)
#   /content = volume Docker fz_build: cay ma + build-linux giu lai giua cac lan (bien dich lai chi tep doi)
#
# Ma nguon dat o /content/chess_variant_engine/custom_engine nhu tren Colab, nen RUNPATH ghi trong binary
# giong het ban dich tren Colab. Ket qua: /src/ban_linux/custom_engine (+ thong tin kiem tra).
set -euo pipefail
ORT=onnxruntime-linux-x64-gpu-1.20.1
ED=/content/chess_variant_engine/custom_engine
OUT=/src/ban_linux

git config --global --add safe.directory /src
REV=$(git -C /src rev-parse --short HEAD)
echo "[linux] ma nguon: commit $REV ($(git -C /src log -1 --format=%s HEAD | cut -c1-90))"
if [ -n "$(git -C /src status --porcelain -- custom_engine/src custom_engine/meson.build custom_engine/meson_options.txt)" ]; then
  echo "[linux] CHU Y: custom_engine co thay doi CHUA commit -- KHONG nam trong ban dich nay (chi dich HEAD)."
fi

# Ma nguon HEAD -> cay bien dich. rsync -c (so noi dung, khong giu mtime): chi tep thay doi duoc ghi lai
# va mang mtime moi, nen ninja chi bien dich lai nhung tep do.
rm -rf /tmp/moi && mkdir -p /tmp/moi "$ED"
git -C /src archive HEAD custom_engine | tar -x -C /tmp/moi
rsync -rlc --delete --exclude /build-linux/ --exclude "/third_party/$ORT/" /tmp/moi/custom_engine/ "$ED/"

if [ ! -f "$ED/third_party/$ORT/include/onnxruntime_cxx_api.h" ]; then
  echo "[linux] giai nen ONNX Runtime ($ORT) ..."
  mkdir -p "$ED/third_party"
  tar -xzf /ortsrc/ort-gpu-1.20.1.tgz -C "$ED/third_party"
fi

cd "$ED"
if [ ! -f build-linux/build.ninja ]; then
  meson setup build-linux --buildtype=release -Duse_cuda=true -Donnxruntime_dir="third_party/$ORT"
fi
ninja -C build-linux
BIN=$ED/build-linux/custom_engine

# Kiem tra: phien ban glibc / libstdc++ binary doi phai co tren Colab (Ubuntu 24.04: glibc 2.39, GLIBCXX 3.4.33).
gmax=$(objdump -T "$BIN" | grep -o 'GLIBC_[0-9.]*' | sort -uV | tail -1)
cmax=$(objdump -T "$BIN" | grep -o 'GLIBCXX_[0-9.]*' | sort -uV | tail -1)
echo "[linux] can toi da: $gmax, $cmax"
printf '%s\n%s\n' "$gmax" GLIBC_2.39 | sort -CV || { echo "[linux] LOI: can glibc moi hon Colab"; exit 1; }
printf '%s\n%s\n' "$cmax" GLIBCXX_3.4.33 | sort -CV || { echo "[linux] LOI: can libstdc++ moi hon Colab"; exit 1; }

# Chay thu tren CPU (may nay khong co GPU NVIDIA; phan CUDA chi kiem duoc tren Colab -- o 02 tu chay --test-uci).
export LD_LIBRARY_PATH="$ED/third_party/$ORT/lib"
"$BIN" --test-uci 2>&1 | grep -E '\[(PASS|FAIL)\]' | tail -3
"$BIN" --test-uci 2>&1 | grep -q '\[PASS\]' || { echo "[linux] LOI: --test-uci khong PASS"; exit 1; }
"$BIN" --test-adapter 2>&1 | tail -2

mkdir -p "$OUT"
cp -f "$BIN" "$OUT/custom_engine"
{ echo "commit=$REV"; echo "built=$(date '+%Y-%m-%d %H:%M:%S')"; echo "gcc=$(gcc -dumpfullversion)";
  echo "glibc_max=$gmax"; echo "glibcxx_max=$cmax"; echo "sha256=$(sha256sum "$BIN" | cut -d' ' -f1)"; } > "$OUT/thong_tin.txt"
cat "$OUT/thong_tin.txt"
echo "[linux] XONG: ban_linux\\custom_engine"
