$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$VenvPython = Join-Path $RepoRoot ".venv\\Scripts\\python.exe"

if (-not (Test-Path $VenvPython)) {
  throw "Virtual environment not found. Run .\\scripts\\install-stack.ps1 first."
}

Push-Location $RepoRoot
try {
  & $VenvPython -m pip install --upgrade pip
  & $VenvPython -m pip install --upgrade -r (Join-Path $RepoRoot "requirements.txt")

  if (Get-Command winget -ErrorAction SilentlyContinue) {
    winget upgrade llama-swap --accept-source-agreements --accept-package-agreements
  }

  & $VenvPython -m src.launcher.process_manager --root $RepoRoot generate-configs
} finally {
  Pop-Location
}
