<#
================================================================================
 package.ps1  -  Build the FairyZero all-in-one portable bundle (T8.4).

 Produces a single self-contained folder that runs on a CLEAN Windows machine
 (no MSYS2 needed) for PLAY + DATA-GEN, ships the Python training stack, the
 engine source (so Colab can rebuild a GPU binary), a seed model, and the manual.

 Usage (from anywhere):
   powershell -ExecutionPolicy Bypass -File scripts\package.ps1
   powershell ... -File scripts\package.ps1 -Model models\model_gen5.onnx -Zip

 Params:
   -OutDir      output folder (default: dist\FairyZero)
   -Model       .onnx to bundle as models\seed.onnx (default: generate via make_seed.py)
   -Python      python.exe used to generate the seed (default: auto-detect)
   -Ucrt64Bin   MSYS2 ucrt64 bin holding the runtime DLLs (default: C:\msys64\ucrt64\bin)
   -Zip         also produce <OutDir>.zip (Store)
================================================================================
#>
param(
  [string]$OutDir   = "dist\FairyZero",
  [string]$Model    = "",
  [string]$Python   = "",
  [string]$Ucrt64Bin = "C:\msys64\ucrt64\bin",
  [switch]$Zip
)
$ErrorActionPreference = "Stop"

# --- Resolve repo root (this script lives in <root>\scripts) ---------------
$Root = Split-Path -Parent $PSScriptRoot
Write-Host "[package] repo root: $Root"
$Exe = Join-Path $Root "build\custom_engine.exe"
$OrtDll = Join-Path $Root "build\onnxruntime.dll"
if (-not (Test-Path $Exe))   { throw "Engine not built: $Exe  (run: ninja -C build)" }
if (-not (Test-Path $OrtDll)){ throw "onnxruntime.dll not found: $OrtDll" }

# --- Clean output dir ------------------------------------------------------
if (Test-Path $OutDir) { Remove-Item -Recurse -Force $OutDir }
$dirs = @("", "models", "python", "engine_src", "scripts")
foreach ($d in $dirs) { New-Item -ItemType Directory -Force -Path (Join-Path $OutDir $d) | Out-Null }

# --- 1. Engine exe + runtime DLLs (clean-Windows standalone) ---------------
Copy-Item $Exe (Join-Path $OutDir "custom_engine.exe")
Copy-Item $OrtDll (Join-Path $OutDir "onnxruntime.dll")
$ortShared = Join-Path $Root "third_party\onnxruntime-win-x64-1.18.0\lib\onnxruntime_providers_shared.dll"
if (Test-Path $ortShared) { Copy-Item $ortShared $OutDir }

$runtimeDlls = @("libstdc++-6.dll","libgcc_s_seh-1.dll","libwinpthread-1.dll","zlib1.dll")
$missing = @()
foreach ($dll in $runtimeDlls) {
  $src = Join-Path $Ucrt64Bin $dll
  if (Test-Path $src) { Copy-Item $src $OutDir }
  else { $missing += $dll }
}
if ($missing.Count) {
  Write-Warning "Missing runtime DLLs (engine may not run on a clean PC): $($missing -join ', '). Set -Ucrt64Bin to your MSYS2 ucrt64\bin."
}

# --- 2. Seed model ---------------------------------------------------------
$seedOut = Join-Path $OutDir "models\seed.onnx"
if ($Model -ne "") {
  Copy-Item (Resolve-Path $Model) $seedOut
  $pt = [IO.Path]::ChangeExtension((Resolve-Path $Model), ".pt")
  if (Test-Path $pt) { Copy-Item $pt (Join-Path $OutDir "models\seed.pt") }
  Write-Host "[package] bundled model: $Model -> models\seed.onnx"
} else {
  if ($Python -eq "") {
    $cand = @("$env:LOCALAPPDATA\Programs\Python\Python313\python.exe","python")
    foreach ($c in $cand) { if (Get-Command $c -ErrorAction SilentlyContinue) { $Python = $c; break } }
  }
  Write-Host "[package] generating seed model via make_seed.py ($Python) ..."
  & $Python (Join-Path $Root "python\make_seed.py") --out $seedOut
  if ($LASTEXITCODE -ne 0) { Write-Warning "make_seed.py failed; bundle has no model. Pass -Model <onnx>." }
}

# --- 3. Python training stack ---------------------------------------------
Copy-Item (Join-Path $Root "python\*.py") (Join-Path $OutDir "python")
Copy-Item (Join-Path $Root "python\requirements.txt") (Join-Path $OutDir "python")

# --- 4. Engine source (for rebuilding a GPU binary on Colab) ---------------
Copy-Item -Recurse (Join-Path $Root "src") (Join-Path $OutDir "engine_src\src")
Copy-Item (Join-Path $Root "meson.build") (Join-Path $OutDir "engine_src")
Copy-Item (Join-Path $Root "meson_options.txt") (Join-Path $OutDir "engine_src")
Copy-Item (Join-Path $Root "scripts\colab_setup.sh") (Join-Path $OutDir "scripts")
Copy-Item (Join-Path $Root "scripts\colab_loop.sh") (Join-Path $OutDir "scripts")

# --- 5. Launchers + manual -------------------------------------------------
Copy-Item (Join-Path $Root "scripts\play.bat") $OutDir
$manual = Join-Path $Root "HUONG_DAN.md"
if (Test-Path $manual) { Copy-Item $manual $OutDir }

# --- 6. VERSION.txt --------------------------------------------------------
$githash = (& git -C $Root rev-parse --short HEAD 2>$null)
$ver = @(
  "FairyZero portable bundle",
  "built: $(Get-Date -Format 'yyyy-MM-dd HH:mm')",
  "git:   $githash",
  "model: seed.onnx",
  "platform: Windows x64 (CPU). For Colab GPU: scripts\colab_setup.sh on the engine_src tree."
) -join "`r`n"
Set-Content -Path (Join-Path $OutDir "VERSION.txt") -Value $ver -Encoding utf8

# --- 7. Summary + optional zip --------------------------------------------
$size = (Get-ChildItem -Recurse $OutDir | Measure-Object -Property Length -Sum).Sum / 1MB
Write-Host ("[package] bundle ready: {0}  ({1:N1} MB)" -f $OutDir, $size)
if ($Zip) {
  $zipPath = "$OutDir.zip"
  if (Test-Path $zipPath) { Remove-Item -Force $zipPath }
  Compress-Archive -Path "$OutDir\*" -DestinationPath $zipPath
  Write-Host "[package] zipped: $zipPath"
}
