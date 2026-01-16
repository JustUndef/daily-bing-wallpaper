param(
  # Pfade
  [string]$ProjectDir = (Resolve-Path ".").Path,
  [string]$EntryPy = "bing_wallpaper.py",
  [string]$BuildDir = "build",
  [string]$DistDir = "dist",
  [string]$ExeName = "BingWallpaperDownloader.exe",

  # Nuitka
  [switch]$Console = $false,
  [string]$IconIco = "",
  [switch]$UseMSVC = $true,
  [switch]$LTO = $true,
  [switch]$OneFile = $true,

  # Signieren
  [switch]$Sign = $true,
  [string]$SignToolPath = "C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\signtool.exe",
  [ValidateSet("store","pfx")]
  [string]$CertSource = "store",
  [string]$PfxPath = "",
  [string]$PfxPassword = "",
  [string]$TimeStampUrl = "http://timestamp.digicert.com?alg=sha256",

  # Python-Abhängigkeiten
  [string[]]$PipInstall = @("nuitka","requests","pillow","beautifulsoup4"),
  [switch]$UpgradePip = $true
)

$ErrorActionPreference = "Stop"
function Info($m){Write-Host "[INFO ] $m" -ForegroundColor Cyan}
function Warn($m){Write-Host "[WARN ] $m" -ForegroundColor Yellow}
function Err ($m){Write-Host "[ERROR] $m" -ForegroundColor Red}

# 1) Pfade
$ProjectDir = (Resolve-Path $ProjectDir).Path
Push-Location $ProjectDir
try {
  $EntryPath = Join-Path $ProjectDir $EntryPy
  if (!(Test-Path $EntryPath)) { throw "Entry file not found: $EntryPath" }

  $BuildDir = Join-Path $ProjectDir $BuildDir
  $DistDir  = Join-Path $ProjectDir $DistDir
  New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null
  New-Item -ItemType Directory -Force -Path $DistDir | Out-Null

  # 2) venv
  $VenvDir = Join-Path $BuildDir ".venv"
  if (!(Test-Path $VenvDir)) {
    Info "Erstelle venv: $VenvDir"
    python -m venv $VenvDir
  }
  $Py  = Join-Path $VenvDir "Scripts\python.exe"
  $Pip = Join-Path $VenvDir "Scripts\pip.exe"

  if ($UpgradePip) {
    & $Py -m pip install --upgrade pip setuptools wheel
  }
  if ($PipInstall.Count -gt 0) {
    Info "Installiere Dependencies: $($PipInstall -join ', ')"
    & $Py -m pip install $PipInstall
  }

  # 3) Nuitka Build (richtige Argumentliste)
  $nuitkaArgs = @()
  if ($OneFile) { $nuitkaArgs += "--onefile" }
  if ($Console) { $nuitkaArgs += "--windows-console" } else { $nuitkaArgs += "--windows-disable-console" }
  if ($IconIco) { $nuitkaArgs += "--windows-icon-from-ico=$IconIco" }
  if ($UseMSVC) { $nuitkaArgs += "--msvc=latest" }
  if ($LTO) { $nuitkaArgs += "--lto=yes" }
  $nuitkaArgs += @(
    "--output-dir=$DistDir",
    "--remove-output",
    "--disable-ccache",
    "--nofollow-imports"
  )
  $nuitkaArgs += "--output-filename=$ExeName"

  Info "Baue EXE mit Nuitka..."
  & $Py -m nuitka @nuitkaArgs $EntryPath

  $ExePath = Join-Path $DistDir $ExeName
  if (!(Test-Path $ExePath)) { throw "Build fehlgeschlagen: $ExePath nicht gefunden." }
  Info "EXE erstellt: $ExePath"

  if ($Sign) {
    if (!(Test-Path $SignToolPath)) { throw "signtool nicht gefunden: $SignToolPath" }

    Info "Signiere EXE..."
    $signArgs = @("sign","/fd","SHA256")
    switch ($CertSource) {
      "store" { $signArgs += "/a" }
      "pfx" {
        if (-not $PfxPath) { throw "PFX-Pfad nicht gesetzt." }
        $signArgs += @("/f",$PfxPath)
        if ($PfxPassword) { $signArgs += @("/p",$PfxPassword) }
      }
    }
    $signArgs += @("/td","SHA256","/tr",$TimeStampUrl,$ExePath)
    & $SignToolPath $signArgs

    Info "Verifiziere Signatur..."
    & $SignToolPath verify /pa /v $ExePath
    Info "Signatur OK."
  } else {
    Warn "Signieren übersprungen (--Sign:false)."
  }

  Write-Host ""
  Write-Host "FERTIG: $ExePath" -ForegroundColor Green
  if ($Sign) { Write-Host "Signiert und verifiziert." -ForegroundColor Green }

} catch {
  Err $_.Exception.Message
  exit 1
} finally {
  Pop-Location | Out-Null
}