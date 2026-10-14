# Construit dist\Tramage.exe (un seul fichier, sans console).
# Usage : powershell -ExecutionPolicy Bypass -File build.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path venv)) { py -3.12 -m venv venv }
.\venv\Scripts\python.exe -m pip install -q --disable-pip-version-check pillow tkinterdnd2 pyinstaller

.\venv\Scripts\pyinstaller.exe --noconfirm Tramage.spec

Write-Host "OK : $PSScriptRoot\dist\Tramage.exe"
