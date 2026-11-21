@echo off
rem Xem lai van co da luu (CHI xem: khong choi, khong tim kiem). Ba kieu dung:
rem
rem   xem_lai.bat                              -> van moi nhat trong tu_dau_log (nhat ky cua xem_tu_dau.bat)
rem   xem_lai.bat tu_dau_log\tu_dau_XXXX.txt   -> mot van cu the (nhat ky .txt)
rem   xem_lai.bat DU_LIEU [so]                 -> NHIEU van trong DU LIEU HUAN LUYEN, co bang chon van ben trai
rem
rem DU_LIEU la thu muc (vd "Du lieu huan luyen\games_gen1"), goi .zip hoac mot tep van .xz.
rem Lan dau bat doi du lieu sang nhat ky + bang chi muc (vai chuc giay) trong tu_dau_log\xem_TEN; cac lan sau mo ngay.
rem Keo tha thu muc / goi len tep .bat nay cung duoc. Thu muc da doi san (co chi_muc.tsv) mo thang.
rem [so] = mo san van co so thu tu do (cot "so" cua bang), khong co thi mo van dau bang.
rem
rem Bang chon van (ben trai cua so): loc theo ket qua (Trang thang / Den thang / Hoa), ly do ket thuc, so quan con lai
rem o cuoi van; sap xep theo so nua nuoc / so quan; bam mot dong de xem van do; [ va ] = van truoc / sau; G = an / hien bang.
rem De tim van "thang thua ma con ~60 quan": chon Trang thang hoac Den thang, keo thanh "con it nhat N quan" len cao,
rem sap xep "It nua nuoc nhat". Nuoc di co chieu co dau + (++ = chieu doi) va to mau do; dong tren cung ghi ly do ket thuc.
rem
rem Phim: Space = tu chay (1 giay/nuoc), phim mui ten / lan chuot / bam nuoc o thanh duoi = xem tung nuoc,
rem Home / End = ve dau / ve cuoi, PageUp / PageDown = lui / tien 10 nuoc,
rem L = bat / tat bang tim kiem ben phai (lan tim da chon nuoc dang xem; Q / cp theo phia Trang;
rem voi du lieu huan luyen: N = so luot tham cua 8 nuoc nhieu nhat, Q chi co cho nuoc da di va nuoc tot nhat).
rem Re chuot vao tieu de cot %%N cua bang do: chon %%N^2 (nhiet do 0.5), %%N^4... de them cot xac suat chon nuoc khi ap nhiet do.
rem Can: py -3 (Python 3 co numpy), engine build-dml (dung lai sau moi lan doi luat: ninja -C build-dml).
setlocal
set "ENG=%~dp0custom_engine\build-dml\custom_engine.exe"
set "MODEL=%~dp0models\gen1.onnx"
set "GUI=%~dp0gui\build\windows\x64\runner\Release\fairyzero_gui.exe"
set "A=%~1"
if "%A%"=="" goto newest
if "%A:~-1%"=="\" set "A=%A:~0,-1%"
if /i "%~x1"==".txt" goto one
if exist "%A%\chi_muc.tsv" ( set "LIB=%A%" & goto lib )
for %%I in ("%A%") do set "NAME=%%~nxI"
set "LIB=%~dp0tu_dau_log\xem_%NAME%"
echo Doi du lieu huan luyen "%A%" sang nhat ky xem lai: "%LIB%"
py -3 "%~dp0custom_engine\python\xem_du_lieu.py" "%A%" --xuat "%LIB%" --engine "%ENG%"
if errorlevel 1 (
  echo.
  echo [!] Doi du lieu loi hoac co van giai ma sai - xem thong bao tren. Van mo bang cac van doc duoc.
  if not exist "%LIB%\chi_muc.tsv" ( pause & exit /b 1 )
)
:lib
set "GAME="
if not "%~2"=="" set "GAME=--replay-game %~2"
start "" "%GUI%" --engine "%ENG%" --model "%MODEL%" --provider cpu --replay-dir "%LIB%" %GAME%
exit /b 0
:newest
for /f "delims=" %%i in ('dir /b /o-d "%~dp0tu_dau_log\tu_dau_*.txt"') do (
  set "A=%~dp0tu_dau_log\%%i"
  goto one
)
echo Khong tim thay nhat ky trong "%~dp0tu_dau_log". Cach dung: xem_lai.bat DU_LIEU  (xem phan dau tep)
pause
exit /b 1
:one
echo Xem lai: %A%
start "" "%GUI%" --engine "%ENG%" --model "%MODEL%" --provider cpu --replay "%A%"
exit /b 0
