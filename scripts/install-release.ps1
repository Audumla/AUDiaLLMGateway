$ErrorActionPreference = "Stop"

param(
  [string]$Owner = "AUDia",
  [string]$Repo = "AUDiaLLMGateway",
  [string]$InstallDir = "$HOME\AUDiaLLMGateway",
  [string]$Version = "latest",
  [string[]]$Component = @()
)

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$Python = if (Get-Command py -ErrorAction SilentlyContinue) { "py -3" } elseif (Get-Command python -ErrorAction SilentlyContinue) { "python" } else { throw "Python was not found in PATH." }
$Args = @("--owner", $Owner, "--repo", $Repo, "--install-dir", $InstallDir, "--version", $Version)
foreach ($Item in $Component) {
  $Args += "--component"
  $Args += $Item
}
Push-Location $RepoRoot
try {
  Invoke-Expression "& $Python -m src.installer.release_installer install-release $($Args -join ' ')"
} finally {
  Pop-Location
}
