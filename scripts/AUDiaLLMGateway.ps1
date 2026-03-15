param(
  [Parameter(Position = 0)]
  [string]$Action = "help",

  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$CommandArgs = @()
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
  .\scripts\AUDiaLLMGateway.ps1 <command> [args...]

Commands:
  install-release  Install from a GitHub release archive
  update-release   Update this installation from GitHub releases
  check-updates    Check upstream release availability
  validate-configs Validate layered project/local config
  install-stack    Create .venv, install Python deps, and generate configs
  update-stack     Upgrade Python deps and refresh generated configs
  generate-configs Generate llama-swap, LiteLLM, and MCP client configs
  start-stack      Start llama-swap and LiteLLM
  stop-stack       Stop llama-swap and LiteLLM
  start-gateway    Start LiteLLM only
  stop-gateway     Stop LiteLLM only
  start-llamaswap  Start llama-swap only
  stop-llamaswap   Stop llama-swap only
  status           Show runtime process status
  healthcheck      Run health checks
  test-routing     Run end-to-end routing tests
  help             Show this message
"@ | Write-Host
}

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$NormalizedCommand = $Action.Trim().ToLowerInvariant()

switch ($NormalizedCommand) {
  "help" {
    Show-Usage
  }

  "install-release" {
    $Python = Get-PythonCommand
    Push-Location $RepoRoot
    try {
      $ArgsToPass = @("install-release") + $CommandArgs
      Invoke-PythonModule -PythonCommand $Python -Module "src.installer.release_installer" -ModuleArgs $ArgsToPass
    } finally {
      Pop-Location
    }
  }

  "update-release" {
    $Python = Get-PythonCommand
    Push-Location $RepoRoot
    try {
      $ArgsToPass = @("update-release", "--root", $RepoRoot) + $CommandArgs
      Invoke-PythonModule -PythonCommand $Python -Module "src.installer.release_installer" -ModuleArgs $ArgsToPass
    } finally {
      Pop-Location
    }
  }

  "check-updates" {
    $Python = Get-PythonCommand
    Push-Location $RepoRoot
    try {
      $ArgsToPass = @("check-updates", "--root", $RepoRoot) + $CommandArgs
      Invoke-PythonModule -PythonCommand $Python -Module "src.installer.release_installer" -ModuleArgs $ArgsToPass
    } finally {
      Pop-Location
    }
  }

  "validate-configs" {
    $Python = Get-PythonCommand
    Push-Location $RepoRoot
    try {
      $ArgsToPass = @("validate-configs", "--root", $RepoRoot) + $CommandArgs
      Invoke-PythonModule -PythonCommand $Python -Module "src.installer.release_installer" -ModuleArgs $ArgsToPass
    } finally {
      Pop-Location
    }
  }

  "install-stack" {
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

  "update-stack" {
    $VenvPython = Join-Path $RepoRoot ".venv\\Scripts\\python.exe"

    if (-not (Test-Path $VenvPython)) {
      throw "Virtual environment not found. Run .\\scripts\\AUDiaLLMGateway.ps1 install-stack first."
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

  "generate-configs" {
    $Python = Get-PythonCommand
    Push-Location $RepoRoot
    try {
      $ArgsToPass = @("--root", $RepoRoot, "generate-configs") + $CommandArgs
      Invoke-PythonModule -PythonCommand $Python -Module "src.launcher.process_manager" -ModuleArgs $ArgsToPass
    } finally {
      Pop-Location
    }
  }

  "start-stack" {
    $Python = Get-PythonCommand
    Push-Location $RepoRoot
    try {
      $ArgsToPass = @("--root", $RepoRoot, "start-all") + $CommandArgs
      Invoke-PythonModule -PythonCommand $Python -Module "src.launcher.process_manager" -ModuleArgs $ArgsToPass
    } finally {
      Pop-Location
    }
  }

  "stop-stack" {
    $Python = Get-PythonCommand
    Push-Location $RepoRoot
    try {
      $ArgsToPass = @("--root", $RepoRoot, "stop-all") + $CommandArgs
      Invoke-PythonModule -PythonCommand $Python -Module "src.launcher.process_manager" -ModuleArgs $ArgsToPass
    } finally {
      Pop-Location
    }
  }

  "start-gateway" {
    $Python = Get-PythonCommand
    Push-Location $RepoRoot
    try {
      $ArgsToPass = @("--root", $RepoRoot, "start-gateway") + $CommandArgs
      Invoke-PythonModule -PythonCommand $Python -Module "src.launcher.process_manager" -ModuleArgs $ArgsToPass
    } finally {
      Pop-Location
    }
  }

  "stop-gateway" {
    $Python = Get-PythonCommand
    Push-Location $RepoRoot
    try {
      $ArgsToPass = @("--root", $RepoRoot, "stop-gateway") + $CommandArgs
      Invoke-PythonModule -PythonCommand $Python -Module "src.launcher.process_manager" -ModuleArgs $ArgsToPass
    } finally {
      Pop-Location
    }
  }

  "start-llamaswap" {
    $Python = Get-PythonCommand
    Push-Location $RepoRoot
    try {
      $ArgsToPass = @("--root", $RepoRoot, "start-llama-swap") + $CommandArgs
      Invoke-PythonModule -PythonCommand $Python -Module "src.launcher.process_manager" -ModuleArgs $ArgsToPass
    } finally {
      Pop-Location
    }
  }

  "stop-llamaswap" {
    $Python = Get-PythonCommand
    Push-Location $RepoRoot
    try {
      $ArgsToPass = @("--root", $RepoRoot, "stop-llama-swap") + $CommandArgs
      Invoke-PythonModule -PythonCommand $Python -Module "src.launcher.process_manager" -ModuleArgs $ArgsToPass
    } finally {
      Pop-Location
    }
  }

  "status" {
    $Python = Get-PythonCommand
    Push-Location $RepoRoot
    try {
      $ArgsToPass = @("--root", $RepoRoot, "status") + $CommandArgs
      Invoke-PythonModule -PythonCommand $Python -Module "src.launcher.process_manager" -ModuleArgs $ArgsToPass
    } finally {
      Pop-Location
    }
  }

  "healthcheck" {
    $Python = Get-PythonCommand
    Push-Location $RepoRoot
    try {
      $ArgsToPass = @("--root", $RepoRoot) + $CommandArgs
      Invoke-PythonModule -PythonCommand $Python -Module "src.launcher.health" -ModuleArgs $ArgsToPass
    } finally {
      Pop-Location
    }
  }

  "test-routing" {
    $Python = Get-PythonCommand
    $ArgsToPass = @("--root", $RepoRoot)
    if (-not ($CommandArgs -contains "--all-models")) {
      $ArgsToPass += "--all-models"
    }
    $ArgsToPass += $CommandArgs
    Push-Location $RepoRoot
    try {
      Invoke-PythonModule -PythonCommand $Python -Module "src.launcher.router_test" -ModuleArgs $ArgsToPass
    } finally {
      Pop-Location
    }
  }

  default {
    throw "Unknown command '$Action'. Run .\\scripts\\AUDiaLLMGateway.ps1 help for usage."
  }
}
