$ErrorActionPreference = "Stop"

param(
  [string]$Owner = "AUDia",
  [string]$Repo = "AUDiaLLMGateway",
  [string]$InstallDir = "$HOME\AUDiaLLMGateway",
  [string]$Version = "latest",
  [string[]]$Component = @()
)

$TmpRoot = Join-Path $env:TEMP ("audia-bootstrap-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force $TmpRoot | Out-Null

try {
  if (Get-Command py -ErrorAction SilentlyContinue) {
    $Python = "py -3"
  } elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $Python = "python"
  } else {
    throw "Python was not found in PATH."
  }

  $Archive = Join-Path $TmpRoot "release.zip"
  $ApiUrl = if ($Version -eq "latest") { "https://api.github.com/repos/$Owner/$Repo/releases/latest" } else { "https://api.github.com/repos/$Owner/$Repo/releases/tags/$Version" }
  $Release = Invoke-RestMethod -Headers @{ Accept = "application/vnd.github+json" } -Uri $ApiUrl
  Invoke-WebRequest -Uri $Release.zipball_url -OutFile $Archive

  $ExtractRoot = Join-Path $TmpRoot "bundle"
  Expand-Archive -Path $Archive -DestinationPath $ExtractRoot
  $BundleDir = Get-ChildItem $ExtractRoot | Select-Object -First 1

  $ComponentArgs = @()
  foreach ($Item in $Component) {
    $ComponentArgs += "--component"
    $ComponentArgs += $Item
  }

  Push-Location $BundleDir.FullName
  try {
    Invoke-Expression "& $Python -m src.installer.release_installer install-bundle --bundle-root `"$($BundleDir.FullName)`" --install-dir `"$InstallDir`" --version `"$Version`" $($ComponentArgs -join ' ')"
  } finally {
    Pop-Location
  }
} finally {
  Remove-Item -Recurse -Force $TmpRoot -ErrorAction SilentlyContinue
}
