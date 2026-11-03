@echo off
rem Bien dich engine co vua (co_vua/engine) thanh binary Linux cho Colab, bang Docker Ubuntu 24.04 (giong Colab).
rem Can: Docker Desktop dang chay, image fz-build:24.04 va C:\fz_build\ort-gpu-1.20.1.tgz.
rem Ket qua: co_vua\ban_linux\lc0 + co_vua\ban_linux\lib\
cd /d "%~dp0.."
docker run --rm -v "%CD%:/src" -v C:\fz_build:/ortsrc:ro -v cv_build:/content fz-build:24.04 ^
  bash -c "tr -d '\r' < /src/co_vua/scripts/bien_dich_linux.sh | bash"
if errorlevel 1 (echo [!] Bien dich loi) else (echo Xong.)
