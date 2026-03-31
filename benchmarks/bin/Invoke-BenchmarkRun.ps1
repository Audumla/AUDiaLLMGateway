param(
  [Parameter(Mandatory = $true)]
  [string]$BackendName,

  [Parameter(Mandatory = $true)]
  [string]$ContainerName,

  [Parameter(Mandatory = $true)]
  [string]$HealthUrl,

  [Parameter(Mandatory = $true)]
  [string[]]$StartCommand,

  [string]$KillTarget = $ContainerName,

  [switch]$ResetRocm,

  [int]$TimeoutSeconds = 600,

  [string]$MetricsBackend,

  [string]$MetricsModel,

  [string]$Elapsed,

  [string]$PromptTokens,

  [string]$CompletionTokens,

  [string]$EvalTokS,

  [string]$GpuMap,

  [string]$Status = 'ok'
)

$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

& "$scriptDir/preflight.ps1" $BackendName $ContainerName $HealthUrl
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}

& "$scriptDir/kill_backend.ps1" $KillTarget
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}

if ($ResetRocm) {
  & "$scriptDir/reset_rocm_state.ps1" $ContainerName
  if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
  }
}

$startArgs = @()
if ($StartCommand.Length -gt 1) {
  $startArgs = $StartCommand[1..($StartCommand.Length - 1)]
}

& $StartCommand[0] @startArgs
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}

& "$scriptDir/wait_ready.ps1" $BackendName $HealthUrl $ContainerName $TimeoutSeconds
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}

if ($MetricsBackend -or $MetricsModel) {
  if ([string]::IsNullOrWhiteSpace($MetricsBackend)) {
    $MetricsBackend = $BackendName
  }
  if ([string]::IsNullOrWhiteSpace($MetricsModel)) {
    $MetricsModel = $BackendName
  }

  & "$scriptDir/collect_metrics.ps1" $MetricsBackend $MetricsModel $Elapsed $PromptTokens $CompletionTokens $EvalTokS $GpuMap $Status
  if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
  }
}

Write-Output "benchmark run ready: $BackendName"
