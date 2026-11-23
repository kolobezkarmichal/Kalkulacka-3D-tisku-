# Spusť na Windows 10/11 v PowerShellu: powershell -ExecutionPolicy Bypass -File windows\SESTAVIT_WINDOWS.ps1
$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $root

Write-Host "Instaluji závislosti pro sestavení..."
python -m pip install -r "windows\requirements-build.txt"
if ($LASTEXITCODE -ne 0) { throw "Nepodařilo se nainstalovat potřebné balíčky." }

Write-Host "Testuji výpočty a práci s daty..."
Push-Location "windows"
try {
    python -m unittest discover -p "test_*.py" -v
    if ($LASTEXITCODE -ne 0) { throw "Automatické testy neprošly." }
} finally { Pop-Location }

Write-Host "Vytvářím Windows EXE včetně Pythonu a Qt..."
python -m PyInstaller --noconfirm --clean --onedir --windowed --name Kalkulacka3DTisku --add-data "windows/assets:assets" "windows/app.py"
if ($LASTEXITCODE -ne 0) { throw "Sestavení programu přes PyInstaller selhalo." }

$exe = Join-Path $root "dist\Kalkulacka3DTisku\Kalkulacka3DTisku.exe"
if (-not (Test-Path $exe)) { throw "Chybí vytvořený program: $exe" }

$compiler = (Get-Command ISCC.exe -ErrorAction SilentlyContinue).Source
if (-not $compiler) {
    foreach ($candidate in @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe")) {
        if (Test-Path $candidate) { $compiler = $candidate; break }
    }
}
if (-not $compiler) { throw "Chybí Inno Setup 6 (ISCC.exe). Nainstaluj jej z https://jrsoftware.org/isinfo.php ." }

Write-Host "Sestavuji český instalátor Inno Setup..."
& $compiler "windows\instalator.iss"
if ($LASTEXITCODE -ne 0) { throw "Sestavení instalátoru Inno Setup selhalo." }

$setup = Join-Path $root "output\Kalkulacka-3D-tisku-v0.8.1-Windows-Setup.exe"
if (-not (Test-Path $setup)) { throw "Výsledný instalátor nebyl vytvořen." }
Write-Host "Hotovo: $setup"
