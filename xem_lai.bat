@echo off
rem Xem lai mot van da luu (CHI xem: khong choi, khong tim kiem). Doc nhat ky tu_dau_log\*.txt cua che do tu dau.
rem   xem_lai.bat                              -> van moi nhat trong tu_dau_log
rem   xem_lai.bat tu_dau_log\tu_dau_XXXX.txt  -> mot van cu the (duong dan khong duoc co khoang trang)
rem Space = tu chay (1 giay/nuoc), phim mui ten / lan chuot / bam nuoc o thanh duoi = xem tung nuoc,
rem Home / End = ve dau / ve cuoi, PageUp / PageDown = lui / tien 10 nuoc.
setlocal
set "F=%~1"
if not "%F%"=="" goto go
for /f "delims=" %%i in ('dir /b /o-d "%~dp0tu_dau_log\tu_dau_*.txt"') do (
  set "F=%~dp0tu_dau_log\%%i"
  goto go
)
echo Khong tim thay nhat ky trong "%~dp0tu_dau_log". Cach dung: xem_lai.bat duong_dan_tep
pause
exit /b 1
:go
echo Xem lai: %F%
start "" "%~dp0gui\build\windows\x64\runner\Release\fairyzero_gui.exe" --engine "%~dp0custom_engine\build-dml\custom_engine.exe" --model "%~dp0models\gen92.onnx" --provider cpu --replay "%F%"
