@echo off
REM ============================================================================
REM FairyZero - launch the UCI engine (MCTS + neural net) for the 10x10 variant.
REM Usage:   play.bat [path-to-model.onnx]   (default: models\seed.onnx)
REM Point your own UCI GUI at:  custom_engine.exe --uci-nn --weights <model>
REM ============================================================================
setlocal
cd /d "%~dp0"

set "MODEL=%~1"
if "%MODEL%"=="" set "MODEL=models\seed.onnx"

if not exist "custom_engine.exe" (
  echo [FairyZero] ERROR: custom_engine.exe not found next to this script.
  pause
  exit /b 1
)
if not exist "%MODEL%" (
  echo [FairyZero] ERROR: model not found: %MODEL%
  echo Put a .onnx model in models\ or pass one:  play.bat models\model_gen5.onnx
  pause
  exit /b 1
)

echo [FairyZero] Starting UCI engine with model: %MODEL%
echo [FairyZero] Type UCI commands (uci, isready, position startpos, go nodes 800, quit)
echo            or point your GUI at: custom_engine.exe --uci-nn --weights "%MODEL%"
echo.
custom_engine.exe --uci-nn --weights "%MODEL%"
