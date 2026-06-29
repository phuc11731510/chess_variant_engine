<#
================================================================================
 package.ps1  -  Build a FairyZero portable bundle.

 TARGETS (-Target):
   both    (default) Windows standalone (PLAY + DATA-GEN) PLUS the Colab source
           (engine_src + colab scripts) so a GPU binary can be rebuilt on Colab.
   colab             Colab-only, MINIMAL: engine source + python stack + colab
                     scripts. NO Windows binaries, NO ONNX Runtime, NO prebuilt
                     Linux binary (you can't build Linux on Windows). On Colab you
                     run `bash scripts/colab_setup.sh` ONCE — it builds the GPU
                     binary and downloads ONNX Runtime — then `bash
                     scripts/colab_prebuilt.sh wrap` each later session. This is
                     all you need to GENERATE self-play data, TRAIN, and run ARENA.
   windows           Windows standalone only (exe + DLLs + python + model + play.bat).
                     No engine_src / colab scripts. Smallest Windows-only bundle.

 SEED MODEL (-Model / -NoModel):
   (default)   generate a fresh 0-Elo seed via make_seed.py -> models\seed.onnx
   -Model X    bundle X (and its .pt sibling if present) as models\seed.onnx
   -NoModel    bundle NO model at all (e.g. you pull weights from a GitHub release)

 USAGE:
   powershell -ExecutionPolicy Bypass -File scripts\package.ps1
   powershell ... -File scripts\package.ps1 -Target colab -NoModel
   powershell ... -File scripts\package.ps1 -Target both -Model models\model_gen7.onnx -Dml -Zip

 PARAMS:
   -Target      both | colab | windows           (default: both)
   -OutDir      output folder (default: dist\FairyZero[_colab|_win] per target)
   -Model       .onnx to bundle as models\seed.onnx (default: generate via make_seed.py)
   -NoModel     do not bundle any seed model (overrides -Model)
   -Python      python.exe used to generate the seed (default: auto-detect)
   -Ucrt64Bin   MSYS2 ucrt64 bin holding the runtime DLLs (default: C:\msys64\ucrt64\bin)
   -Dml         bundle the DirectML build (build-dml): ONE Windows bundle serving BOTH
                Provider=cpu AND Provider=dml. Needs `meson setup build-dml
                -Duse_dml=true; ninja -C build-dml` first. (Windows targets only.)
   -Zip         also produce <OutDir>.zip (note: WinRAR compresses the .so far better)
================================================================================
#>
param(
  [ValidateSet('both','colab','windows')]
  [string]$Target   = 'both',
  [string]$OutDir   = "",
  [string]$Model    = "",
  [switch]$NoModel,
  [string]$Python   = "",
  [string]$Ucrt64Bin = "C:\msys64\ucrt64\bin",
  [switch]$Dml,
  [switch]$Zip
)
$ErrorActionPreference = "Stop"

# --- Resolve repo root (this script lives in <root>\scripts) ---------------
$Root = Split-Path -Parent $PSScriptRoot
Write-Host "[package] repo root: $Root"
Write-Host "[package] target:    $Target"

# What each target ships:
$wantWindows = ($Target -eq 'both' -or $Target -eq 'windows')   # exe + runtime DLLs + play.bat
$wantColab   = ($Target -eq 'both' -or $Target -eq 'colab')     # engine_src + colab scripts

# Default OutDir per target so the three modes don't clobber each other.
if ($OutDir -eq "") {
  $OutDir = switch ($Target) {
    'colab'   { "dist\FairyZero_colab" }
    'windows' { "dist\FairyZero_win" }
    default   { "dist\FairyZero" }
  }
}

# --- Windows engine build presence (only when shipping Windows) ------------
$BuildDir = if ($Dml) { "build-dml" } else { "build" }
if ($wantWindows) {
  $Exe = Join-Path $Root "$BuildDir\custom_engine.exe"
  $OrtDll = Join-Path $Root "$BuildDir\onnxruntime.dll"
  if (-not (Test-Path $Exe))   { throw "Engine not built: $Exe  (run: ninja -C $BuildDir$(if ($Dml) { '  - configure it with: meson setup build-dml -Duse_dml=true' }))" }
  if (-not (Test-Path $OrtDll)){ throw "onnxruntime.dll not found: $OrtDll" }
}

# --- Clean output dir + create only the subdirs this target needs ----------
if (Test-Path $OutDir) { Remove-Item -Recurse -Force $OutDir }
$dirs = @("", "python")
if (-not $NoModel) { $dirs += "models" }
if ($wantColab)    { $dirs += @("engine_src", "scripts") }
foreach ($d in $dirs) { New-Item -ItemType Directory -Force -Path (Join-Path $OutDir $d) | Out-Null }

# --- 1. Windows engine exe + runtime DLLs + launcher (windows/both) --------
if ($wantWindows) {
  Copy-Item $Exe (Join-Path $OutDir "custom_engine.exe")
  Copy-Item $OrtDll (Join-Path $OutDir "onnxruntime.dll")
  if ($Dml) {
    # DirectML build needs DirectML.dll alongside (CPU+DML in one bundle).
    $dmlDll = Join-Path $Root "$BuildDir\DirectML.dll"
    if (Test-Path $dmlDll) { Copy-Item $dmlDll $OutDir; Write-Host "[package] DirectML.dll bundled (Provider=dml available)" }
    else { Write-Warning "DirectML.dll not found in $BuildDir; Provider=dml will fall back to CPU." }
  } else {
    $ortShared = Join-Path $Root "third_party\onnxruntime-win-x64-1.18.0\lib\onnxruntime_providers_shared.dll"
    if (Test-Path $ortShared) { Copy-Item $ortShared $OutDir }
  }

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

  Copy-Item (Join-Path $Root "scripts\play.bat") $OutDir
} else {
  Write-Host "[package] target '$Target': skipping Windows exe/DLLs/play.bat."
}

# --- 2. Seed model (unless -NoModel) ---------------------------------------
if ($NoModel) {
  Write-Host "[package] -NoModel: no seed model bundled (supply weights at run time)."
} else {
  $seedOut = Join-Path $OutDir "models\seed.onnx"
  if ($Model -ne "") {
    $modelPath = (Resolve-Path $Model).Path
    Copy-Item $modelPath $seedOut
    $pt = [IO.Path]::ChangeExtension($modelPath, ".pt")
    if (Test-Path $pt) { Copy-Item $pt (Join-Path $OutDir "models\seed.pt") }
    Write-Host "[package] bundled model: $Model -> models\seed.onnx"
  } else {
    if ($Python -eq "") {
      $cand = @("$env:LOCALAPPDATA\Programs\Python\Python313\python.exe","python")
      foreach ($c in $cand) { if (Get-Command $c -ErrorAction SilentlyContinue) { $Python = $c; break } }
    }
    Write-Host "[package] generating seed model via make_seed.py ($Python) ..."
    & $Python (Join-Path $Root "python\make_seed.py") --out $seedOut
    if ($LASTEXITCODE -ne 0) { Write-Warning "make_seed.py failed; bundle has no model. Pass -Model <onnx> or -NoModel." }
  }
}

# --- 3. Python training stack (always: needed to TRAIN on Colab) -----------
Copy-Item (Join-Path $Root "python\*.py") (Join-Path $OutDir "python")
Copy-Item (Join-Path $Root "python\requirements.txt") (Join-Path $OutDir "python")

# --- 4. Engine source + colab scripts (colab/both: rebuild a GPU binary) ---
if ($wantColab) {
  Copy-Item -Recurse (Join-Path $Root "src") (Join-Path $OutDir "engine_src\src")
  Copy-Item (Join-Path $Root "meson.build") (Join-Path $OutDir "engine_src")
  Copy-Item (Join-Path $Root "meson_options.txt") (Join-Path $OutDir "engine_src")
  Copy-Item (Join-Path $Root "scripts\colab_setup.sh") (Join-Path $OutDir "scripts")
  Copy-Item (Join-Path $Root "scripts\colab_prebuilt.sh") (Join-Path $OutDir "scripts")
} else {
  Write-Host "[package] target '$Target': skipping engine_src/ + colab scripts."
}

# --- 5. Manual (always) ----------------------------------------------------
$manual = Join-Path $Root "HUONG_DAN.md"
if (Test-Path $manual) { Copy-Item $manual $OutDir }

# --- 6. VERSION.txt --------------------------------------------------------
$githash = (& git -C $Root rev-parse --short HEAD 2>$null)
$platformLine = switch ($Target) {
  'colab'   { "Colab GPU, source-only. Build once: bash scripts/colab_setup.sh ; later sessions: bash scripts/colab_prebuilt.sh wrap." }
  'windows' { "Windows x64 ($(if ($Dml) {'CPU+DirectML'} else {'CPU'}))." }
  default   { "Windows x64 ($(if ($Dml) {'CPU+DirectML'} else {'CPU'})) + Colab GPU source (scripts/colab_setup.sh)." }
}
$modelLine = if ($NoModel) { "model: (none - supply your own weights)" } else { "model: models/seed.onnx" }
$ver = @(
  "FairyZero portable bundle",
  "target: $Target",
  "built: $(Get-Date -Format 'yyyy-MM-dd HH:mm')",
  "git:   $githash",
  $modelLine,
  "platform: $platformLine"
) -join "`r`n"
Set-Content -Path (Join-Path $OutDir "VERSION.txt") -Value $ver -Encoding utf8

# --- 7. Summary + optional zip --------------------------------------------
$size = (Get-ChildItem -Recurse $OutDir | Measure-Object -Property Length -Sum).Sum / 1MB
Write-Host ("[package] {0} bundle ready: {1}  ({2:N1} MB)" -f $Target, $OutDir, $size)
if ($Zip) {
  $zipPath = "$OutDir.zip"
  if (Test-Path $zipPath) { Remove-Item -Force $zipPath }
  Compress-Archive -Path "$OutDir\*" -DestinationPath $zipPath
  Write-Host "[package] zipped: $zipPath"
}
