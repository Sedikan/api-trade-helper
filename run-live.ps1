$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Nie znaleziono .venv. Najpierw uruchom: python -m venv .venv oraz pip install -e '.[dev]'"
}

$secureKey = Read-Host "Wklej nowy klucz Marketstack (nie zostanie zapisany)" -AsSecureString
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
try {
    $env:MARKETSTACK_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    & $python -m uvicorn app.main:app --reload
}
finally {
    if ($pointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    }
    Remove-Item Env:\MARKETSTACK_API_KEY -ErrorAction SilentlyContinue
}
