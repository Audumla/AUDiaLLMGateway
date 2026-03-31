param(
  [Parameter(Position = 0)]
  [string]$BackendName,
  [Parameter(Position = 1)]
  [string]$ContainerName,
  [Parameter(Position = 2)]
  [string]$HealthUrl
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($BackendName) -or [string]::IsNullOrWhiteSpace($ContainerName) -or [string]::IsNullOrWhiteSpace($HealthUrl)) {
  Write-Error 'usage: preflight.ps1 <backend_name> <container_name> <health_url>'
  exit 2
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  Write-Error 'docker not available'
  exit 1
}

$inspect = & docker inspect $ContainerName 2>$null
if ($LASTEXITCODE -eq 0) {
  $state = (& docker inspect -f '{{.State.Status}}' $ContainerName 2>$null).Trim()
  if ($state -ne 'exited' -and $state -ne 'dead' -and $state -ne 'missing') {
    Write-Error "backend $BackendName is already running in $ContainerName ($state)"
    exit 1
  }
}

if (-not (Get-Command curl.exe -ErrorAction SilentlyContinue) -and -not (Get-Command Invoke-WebRequest -ErrorAction SilentlyContinue)) {
  Write-Error 'curl.exe or Invoke-WebRequest not available'
  exit 1
}

Write-Output "preflight ok: $BackendName -> $ContainerName -> $HealthUrl"
