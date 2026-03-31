param(
  [Parameter(Position = 0)]
  [string]$Name,
  [Parameter(Position = 1)]
  [string]$HealthUrl,
  [Parameter(Position = 2)]
  [string]$ContainerName,
  [Parameter(Position = 3)]
  [int]$TimeoutSeconds = 600
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($Name) -or [string]::IsNullOrWhiteSpace($HealthUrl) -or [string]::IsNullOrWhiteSpace($ContainerName)) {
  Write-Error 'usage: wait_ready.ps1 <name> <health_url> <container_name> [timeout_seconds]'
  exit 2
}

$start = Get-Date
while ($true) {
  try {
    if (Get-Command curl.exe -ErrorAction SilentlyContinue) {
      & curl.exe -sf $HealthUrl | Out-Null
      if ($LASTEXITCODE -eq 0) {
        Write-Output "ready: $Name"
        exit 0
      }
    } else {
      Invoke-WebRequest -Uri $HealthUrl -UseBasicParsing -TimeoutSec 5 | Out-Null
      Write-Output "ready: $Name"
      exit 0
    }
  } catch {
    # keep polling
  }

  $state = 'missing'
  if (Get-Command docker -ErrorAction SilentlyContinue) {
    & docker inspect -f '{{.State.Status}}' $ContainerName 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
      $state = (& docker inspect -f '{{.State.Status}}' $ContainerName 2>$null).Trim()
    }
  }

  if ($state -eq 'exited' -or $state -eq 'dead' -or $state -eq 'missing') {
    Write-Error "stopped-before-ready: $Name ($state)"
    exit 1
  }

  if (((Get-Date) - $start).TotalSeconds -gt $TimeoutSeconds) {
    Write-Error "timeout waiting for $Name"
    exit 1
  }

  Start-Sleep -Seconds 5
}
