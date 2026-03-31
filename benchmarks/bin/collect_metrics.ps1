param(
  [Parameter(Position = 0)]
  [string]$Backend,
  [Parameter(Position = 1)]
  [string]$Model,
  [Parameter(Position = 2)]
  [string]$Elapsed,
  [Parameter(Position = 3)]
  [string]$PromptTokens,
  [Parameter(Position = 4)]
  [string]$CompletionTokens,
  [Parameter(Position = 5)]
  [string]$EvalTokS,
  [Parameter(Position = 6)]
  [string]$GpuMap,
  [Parameter(Position = 7)]
  [string]$Status = 'ok'
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($Backend) -or [string]::IsNullOrWhiteSpace($Model)) {
  Write-Error 'usage: collect_metrics.ps1 <backend> <model> [elapsed] [prompt_tokens] [completion_tokens] [eval_tok_s] [gpu_map] [status]'
  exit 2
}

$record = [ordered]@{
  backend = $Backend
  model = $Model
  elapsed_s = if ($Elapsed) { [double]$Elapsed } else { $null }
  prompt_tokens = if ($PromptTokens) { [int]$PromptTokens } else { $null }
  completion_tokens = if ($CompletionTokens) { [int]$CompletionTokens } else { $null }
  eval_tok_s = if ($EvalTokS) { [double]$EvalTokS } else { $null }
  gpu_map = if ($GpuMap) { $GpuMap } else { $null }
  status = $Status
}

$record | ConvertTo-Json -Compress
