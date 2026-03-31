param(
  [Parameter(Position = 0)]
  [string]$Target
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($Target)) {
  Write-Error 'usage: kill_backend.ps1 <container_name_or_process_pattern>'
  exit 2
}

if (Get-Command docker -ErrorAction SilentlyContinue) {
  & docker inspect $Target 2>$null | Out-Null
  if ($LASTEXITCODE -eq 0) {
    & docker rm -f $Target | Out-Null
    Write-Output "killed: $Target"
    exit 0
  }
}

$matches = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -match [regex]::Escape($Target) }
foreach ($proc in $matches) {
  Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
}

Write-Output "killed: $Target"
