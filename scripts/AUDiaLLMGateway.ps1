param(
  [Parameter(Position = 0)]
  [string]$Action = "help",

  [Parameter(Position = 1)]
  [string]$Target = "",

  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$ExtraArgs = @()
)

$ErrorActionPreference = "Stop"

function Get-PythonCommand {
  if (Get-Command py -ErrorAction SilentlyContinue) {
    return @("py", "-3")
  }
  if (Get-Command python -ErrorAction SilentlyContinue) {
    return @("python")
  }
  throw "Python was not found in PATH."
}

function Invoke-PythonModule {
  param(
    [string[]]$PythonCommand,
    [string]$Module,
    [string[]]$ModuleArgs = @()
  )

  $PythonExe = $PythonCommand[0]
  $PythonArgs = @()
  if ($PythonCommand.Length -gt 1) {
    $PythonArgs = $PythonCommand[1..($PythonCommand.Length - 1)]
  }

  & $PythonExe @PythonArgs -m $Module @ModuleArgs
}

function Show-Usage {
  @"
Usage:
  .\scripts\AUDiaLLMGateway.ps1 <action> [target] [args...]

Examples:
  .\scripts\AUDiaLLMGateway.ps1 install
  .\scripts\AUDiaLLMGateway.ps1 install stack
  .\scripts\AUDiaLLMGateway.ps1 install llama_cpp
  .\scripts\AUDiaLLMGateway.ps1 update
  .\scripts\AUDiaLLMGateway.ps1 update stack
  .\scripts\AUDiaLLMGateway.ps1 start
  .\scripts\AUDiaLLMGateway.ps1 stop gateway
  .\scripts\AUDiaLLMGateway.ps1 check
  .\scripts\AUDiaLLMGateway.ps1 validate
  .\scripts\AUDiaLLMGateway.ps1 test

Actions:
  install [release|stack|<component>]
  update [release|stack|<component>]
  start [stack|gateway|llamaswap]
  stop [stack|gateway|llamaswap]
  check [updates|status|health]
  validate [configs]
  test [routing]
  generate [configs]
  help

Defaults:
  install   -> release
  update    -> release
  start     -> stack
  stop      -> stack
  check     -> updates
  validate  -> configs
  test      -> routing
  generate  -> configs
"@ | Write-Host
}

function Invoke-InstallStack {
  param([string]$RepoRoot)

  $Python = Get-PythonCommand
  $VenvPath = Join-Path $RepoRoot ".venv"

  if (-not (Test-Path $VenvPath)) {
    $PythonExe = $Python[0]
    $PythonArgs = @()
    if ($Python.Length -gt 1) {
      $PythonArgs = $Python[1..($Python.Length - 1)]
    }
    & $PythonExe @PythonArgs -m venv $VenvPath
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
}

function Invoke-UpdateStack {
  param([string]$RepoRoot)

  $VenvPython = Join-Path $RepoRoot ".venv\\Scripts\\python.exe"

  if (-not (Test-Path $VenvPython)) {
    throw "Virtual environment not found. Run .\\scripts\\AUDiaLLMGateway.ps1 install stack first."
  }

  Push-Location $RepoRoot
  try {
    & $VenvPython -m pip install --upgrade pip
    & $VenvPython -m pip install --upgrade -r (Join-Path $RepoRoot "requirements.txt")

    if (Get-Command winget -ErrorAction SilentlyContinue) {
      winget upgrade llama-swap --accept-source-agreements --accept-package-agreements
    }

    & $VenvPython -m src.launcher.process_manager --root $RepoRoot generate-configs
  } finally {
    Pop-Location
  }
}

function Invoke-ReleaseInstaller {
  param(
    [string]$RepoRoot,
    [string]$InstallerCommand,
    [string]$ComponentName = "",
    [string[]]$PassthroughArgs = @()
  )

  $Python = Get-PythonCommand
  $ArgsToPass = @($InstallerCommand)
  if ($InstallerCommand -eq "update-release" -or $InstallerCommand -eq "check-updates" -or $InstallerCommand -eq "validate-configs") {
    $ArgsToPass += @("--root", $RepoRoot)
  }
  if ($ComponentName) {
    $ArgsToPass += @("--component", $ComponentName)
  }
  $ArgsToPass += $PassthroughArgs

  Push-Location $RepoRoot
  try {
    Invoke-PythonModule -PythonCommand $Python -Module "src.installer.release_installer" -ModuleArgs $ArgsToPass
  } finally {
    Pop-Location
  }
}

function Invoke-ProcessManager {
  param(
    [string]$RepoRoot,
    [string]$ProcessCommand,
    [string[]]$PassthroughArgs = @()
  )

  $Python = Get-PythonCommand
  $ArgsToPass = @("--root", $RepoRoot, $ProcessCommand) + $PassthroughArgs
  Push-Location $RepoRoot
  try {
    Invoke-PythonModule -PythonCommand $Python -Module "src.launcher.process_manager" -ModuleArgs $ArgsToPass
  } finally {
    Pop-Location
  }
}

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$NormalizedAction = $Action.Trim().ToLowerInvariant()
$NormalizedTarget = $Target.Trim().ToLowerInvariant()

switch ($NormalizedAction) {
  "help" {
    Show-Usage
  }

  "install" {
    switch ($NormalizedTarget) {
      ""
      { Invoke-ReleaseInstaller -RepoRoot $RepoRoot -InstallerCommand "install-release" -PassthroughArgs $ExtraArgs }
      "release" { Invoke-ReleaseInstaller -RepoRoot $RepoRoot -InstallerCommand "install-release" -PassthroughArgs $ExtraArgs }
      "stack" { Invoke-InstallStack -RepoRoot $RepoRoot }
      default { Invoke-ReleaseInstaller -RepoRoot $RepoRoot -InstallerCommand "install-release" -ComponentName $Target -PassthroughArgs $ExtraArgs }
    }
  }

  "update" {
    switch ($NormalizedTarget) {
      ""
      { Invoke-ReleaseInstaller -RepoRoot $RepoRoot -InstallerCommand "update-release" -PassthroughArgs $ExtraArgs }
      "release" { Invoke-ReleaseInstaller -RepoRoot $RepoRoot -InstallerCommand "update-release" -PassthroughArgs $ExtraArgs }
      "stack" { Invoke-UpdateStack -RepoRoot $RepoRoot }
      default { Invoke-ReleaseInstaller -RepoRoot $RepoRoot -InstallerCommand "update-release" -ComponentName $Target -PassthroughArgs $ExtraArgs }
    }
  }

  "start" {
    switch ($NormalizedTarget) {
      ""
      { Invoke-ProcessManager -RepoRoot $RepoRoot -ProcessCommand "start-all" -PassthroughArgs $ExtraArgs }
      "stack" { Invoke-ProcessManager -RepoRoot $RepoRoot -ProcessCommand "start-all" -PassthroughArgs $ExtraArgs }
      "gateway" { Invoke-ProcessManager -RepoRoot $RepoRoot -ProcessCommand "start-gateway" -PassthroughArgs $ExtraArgs }
      "llamaswap" { Invoke-ProcessManager -RepoRoot $RepoRoot -ProcessCommand "start-llama-swap" -PassthroughArgs $ExtraArgs }
      default { throw "Unsupported start target '$Target'." }
    }
  }

  "stop" {
    switch ($NormalizedTarget) {
      ""
      { Invoke-ProcessManager -RepoRoot $RepoRoot -ProcessCommand "stop-all" -PassthroughArgs $ExtraArgs }
      "stack" { Invoke-ProcessManager -RepoRoot $RepoRoot -ProcessCommand "stop-all" -PassthroughArgs $ExtraArgs }
      "gateway" { Invoke-ProcessManager -RepoRoot $RepoRoot -ProcessCommand "stop-gateway" -PassthroughArgs $ExtraArgs }
      "llamaswap" { Invoke-ProcessManager -RepoRoot $RepoRoot -ProcessCommand "stop-llama-swap" -PassthroughArgs $ExtraArgs }
      default { throw "Unsupported stop target '$Target'." }
    }
  }

  "check" {
    switch ($NormalizedTarget) {
      ""
      { Invoke-ReleaseInstaller -RepoRoot $RepoRoot -InstallerCommand "check-updates" -PassthroughArgs $ExtraArgs }
      "updates" { Invoke-ReleaseInstaller -RepoRoot $RepoRoot -InstallerCommand "check-updates" -PassthroughArgs $ExtraArgs }
      "status" { Invoke-ProcessManager -RepoRoot $RepoRoot -ProcessCommand "status" -PassthroughArgs $ExtraArgs }
      "health" {
        $Python = Get-PythonCommand
        $ArgsToPass = @("--root", $RepoRoot) + $ExtraArgs
        Push-Location $RepoRoot
        try {
          Invoke-PythonModule -PythonCommand $Python -Module "src.launcher.health" -ModuleArgs $ArgsToPass
        } finally {
          Pop-Location
        }
      }
      default { throw "Unsupported check target '$Target'." }
    }
  }

  "validate" {
    switch ($NormalizedTarget) {
      ""
      { Invoke-ReleaseInstaller -RepoRoot $RepoRoot -InstallerCommand "validate-configs" -PassthroughArgs $ExtraArgs }
      "configs" { Invoke-ReleaseInstaller -RepoRoot $RepoRoot -InstallerCommand "validate-configs" -PassthroughArgs $ExtraArgs }
      default { throw "Unsupported validate target '$Target'." }
    }
  }

  "generate" {
    switch ($NormalizedTarget) {
      ""
      { Invoke-ProcessManager -RepoRoot $RepoRoot -ProcessCommand "generate-configs" -PassthroughArgs $ExtraArgs }
      "configs" { Invoke-ProcessManager -RepoRoot $RepoRoot -ProcessCommand "generate-configs" -PassthroughArgs $ExtraArgs }
      default { throw "Unsupported generate target '$Target'." }
    }
  }

  "test" {
    switch ($NormalizedTarget) {
      ""
      {
        $Python = Get-PythonCommand
        $ArgsToPass = @("--root", $RepoRoot)
        if (-not ($ExtraArgs -contains "--all-models")) {
          $ArgsToPass += "--all-models"
        }
        $ArgsToPass += $ExtraArgs
        Push-Location $RepoRoot
        try {
          Invoke-PythonModule -PythonCommand $Python -Module "src.launcher.router_test" -ModuleArgs $ArgsToPass
        } finally {
          Pop-Location
        }
      }
      "routing" {
        $Python = Get-PythonCommand
        $ArgsToPass = @("--root", $RepoRoot)
        if (-not ($ExtraArgs -contains "--all-models")) {
          $ArgsToPass += "--all-models"
        }
        $ArgsToPass += $ExtraArgs
        Push-Location $RepoRoot
        try {
          Invoke-PythonModule -PythonCommand $Python -Module "src.launcher.router_test" -ModuleArgs $ArgsToPass
        } finally {
          Pop-Location
        }
      }
      default { throw "Unsupported test target '$Target'." }
    }
  }

  default {
    throw "Unknown action '$Action'. Run .\\scripts\\AUDiaLLMGateway.ps1 help for usage."
  }
}
