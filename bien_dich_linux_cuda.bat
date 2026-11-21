@echo off
rem Bien dich binary Linux CO bo chay mang CUDA rieng (fzcuda) tren may nay bang Docker (image fz-build-cuda:24.04: co nvcc 12.6).
rem Can: Docker Desktop dang chay, image fz-build-cuda:24.04 (docker build -f custom_engine/scripts/docker/fz-build-cuda.Dockerfile ...)
rem va C:\fz_build\ort-gpu-1.20.1.tgz. Chi dich ma DA COMMIT (git HEAD). Ket qua: ban_linux\custom_engine_fzcuda
rem (khong de len ban custom_engine thuong). Cay bien dich o volume rieng fz_build_cuda.
cd /d "%~dp0"
docker run --rm -e FZ_CUDA=1 -v "%CD%:/src" -v C:\fz_build:/ortsrc:ro -v fz_build_cuda:/content fz-build-cuda:24.04 ^
  bash -c "tr -d '\r' < /src/custom_engine/scripts/docker_bien_dich.sh | bash"
if errorlevel 1 (echo [!] Bien dich loi) else (echo Xong.)
pause
