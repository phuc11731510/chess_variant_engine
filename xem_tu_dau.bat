@echo off
rem Xem mang NN doi moi nhat tu dau (GPU tich hop DirectML, 800 luot tim (visits) moi nuoc, tham so nhu luc sinh du lieu).
rem Space = tam dung / tiep tuc. Doi mang: sua duong dan --model ben duoi.
rem --temperature 0.5 --temp-cutoff 0 = chon nuoc voi nhiet do 0.5 suot ca van, dung nhu sinh du lieu (day cung la mac dinh, bo hai co nay cung nhu vay).
rem Mang (--model) phai la mang cua luat hien tai (genN.onnx do custom_engine\python\lay_mang.py doi tu genN.pt); engine build-dml phai dung lai sau moi lan doi luat.
rem The xuat phat: NGAU NHIEN dung nhu luc sinh du lieu va arena (python\sinh_the_khoi_dau.py --n 1, moi lan bat mot the khac).
rem Khong co py -3 hoac bo sinh loi thi dung the tam cua engine (xoa 3 dong "the ngau nhien" ben duoi neu muon luon dung the tam).
rem Van moi ghi vao tu_dau_log\tu_dau_*.txt, xem lai bang xem_lai.bat.
setlocal
rem --- the ngau nhien ---
if not exist "%~dp0tu_dau_log" mkdir "%~dp0tu_dau_log"
set "THE=%~dp0tu_dau_log\the_khoi_dau.txt"
if exist "%THE%" del "%THE%"
py -3 "%~dp0custom_engine\python\sinh_the_khoi_dau.py" --n 1 --out "%THE%" >nul 2>&1
set "XP="
if exist "%THE%" set XP=--start-fen-file "%THE%"
if not defined XP echo [!] Khong sinh duoc the ngau nhien - dung the tam cua engine.
start "" "D:\chess_variant\gui\build\windows\x64\runner\Release\fairyzero_gui.exe" --engine "D:\chess_variant\custom_engine\build-dml\custom_engine.exe" --model "D:\chess_variant\models\gen1.onnx" --provider dml --visits 8000 --self-play --temperature 0.5 --temp-cutoff 0 %XP%
