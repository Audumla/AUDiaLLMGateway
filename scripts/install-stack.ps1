$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$VenvPath = Join-Path $RepoRoot ".venv"

if (Get-Command py -ErrorAction SilentlyContinue) {
  $PythonBootstrap = "py -3"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
  $PythonBootstrap = "python"
} else {
  throw "Python was not found in PATH."
}

if (-not (Test-Path $VenvPath)) {
  Invoke-Expression "& $PythonBootstrap -m venv `"$VenvPath`""
}

$VenvPython = Join-Path $VenvPath "Scripts\\python.exe"

Push-Location $RepoRoot
try {
  & $VenvPython -m pip install --upgrade pip
  & $VenvPython -m pip install -r (Join-Path $RepoRoot "requirements.txt")

  if (-not (Get-Command llama-swap -ErrorAction SilentlyContinue) -and -not (Test-Path $env:LLAMA_SWAP_EXE)) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
      winget install llama-swap --accept-source-agreements --accept-package-agreements
    } else {
      Write-Warning "winget was not found. Install llama-swap manually or set LLAMA_SWAP_EXE."
    }
  }

  & $VenvPython -m src.launcher.process_manager --root $RepoRoot generate-configs
} finally {
  Pop-Location
}
