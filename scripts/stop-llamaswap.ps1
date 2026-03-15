$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$Python = if (Get-Command py -ErrorAction SilentlyContinue) { "py -3" } elseif (Get-Command python -ErrorAction SilentlyContinue) { "python" } else { throw "Python was not found in PATH." }

Push-Location $RepoRoot
try {
  Invoke-Expression "& $Python -m src.launcher.process_manager --root `"$RepoRoot`" stop-llama-swap"
} finally {
  Pop-Location
}
