@echo off
rem Bien dich binary Linux (Colab, CUDA) tren may nay bang Docker Ubuntu 24.04 -- giong Colab.
rem Can: Docker Desktop dang chay, image fz-build:24.04 va C:\fz_build\ort-gpu-1.20.1.tgz.
rem Chi dich ma DA COMMIT (git HEAD). Ket qua: ban_linux\custom_engine
rem Dua len Release (ban tu chay):  gh release upload v3.0.0 ban_linux\custom_engine --clobber
cd /d "%~dp0"
docker run --rm -v "%CD%:/src" -v C:\fz_build:/ortsrc:ro -v fz_build:/content fz-build:24.04 ^
  bash -c "tr -d '\r' < /src/custom_engine/scripts/docker_bien_dich.sh | bash"
if errorlevel 1 (echo [!] Bien dich loi) else (echo Xong.)
pause
