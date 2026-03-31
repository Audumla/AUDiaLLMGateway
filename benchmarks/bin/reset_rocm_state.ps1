param(
  [Parameter(Position = 0)]
  [string]$GatewayContainer = 'audia-llama-cpp'
)

$ErrorActionPreference = 'Stop'

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  Write-Error 'docker not available'
  exit 1
}

& docker inspect $GatewayContainer 2>$null | Out-Null
if ($LASTEXITCODE -eq 0) {
  & docker restart $GatewayContainer | Out-Null
  Write-Output "restarted: $GatewayContainer"
  exit 0
}

Write-Error "gateway container not found: $GatewayContainer"
exit 1
