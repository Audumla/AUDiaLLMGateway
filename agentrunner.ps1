# agentrunner.ps1 - Universal AI agent orchestration CLI for PowerShell
param (
    [Parameter(Position=0)]
    [ValidateSet("install", "update", "start", "auth", "detect", "permissions", "local-llm", "help")]
    [string]$Command = "help",

    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$CommandArgs
)

$RepoUrl = 'https://github.com/ExampleOrg/AgentRunner.git'
# Use Join-Path or single quotes to avoid \r (carriage return) interpretation
$RuntimeDir = Join-Path $HOME '.agent-system\runtime'
$Installer = Join-Path $RuntimeDir 'agent_system\install.py'
$WorkspaceSelector = Join-Path $RuntimeDir 'agent_system\core\tools\workspace_install_selector.py'

function Show-Help {
    Write-Host "`nAgentRunner CLI" -ForegroundColor Cyan
    Write-Host "Usage: agentrunner <command> [args]"
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  install [name]  Bootstrap a new project in a new directory"
    Write-Host "  update          Update the global AgentRunner core and current project"
    Write-Host "  start           Launch the monitoring dashboard for the current project"
    Write-Host "  auth [--fix]    Check or fix AI provider authentication"
    Write-Host "  detect          Detect installed AI providers and update config"
    Write-Host "  permissions     Configure provider permission prompts"
    Write-Host "  local-llm       Manage local LLM (status|start|stop|configure|configure-project)"
    Write-Host "  help            Show this help message"
}

function Ensure-Runtime {
    $runtimeExists = Test-Path $RuntimeDir
    $runtimeEmpty = $true
    if ($runtimeExists) {
        $files = Get-ChildItem -Path $RuntimeDir -ErrorAction SilentlyContinue
        if ($files) { $runtimeEmpty = $false }
    }

    if ($runtimeEmpty) {
        Write-Host "[agentrunner] Downloading core runtime to $RuntimeDir..." -ForegroundColor Cyan
        if (-not $runtimeExists) {
            $parent = Split-Path $RuntimeDir
            if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
        } else {
            Remove-Item -Path $RuntimeDir -Recurse -Force -ErrorAction SilentlyContinue | Out-Null
        }
        git clone $RepoUrl $RuntimeDir
    }
}

function Refresh-LocalLaunchers {
    $latestPs1 = Join-Path $RuntimeDir "agent_system\scripts\agentrunner.ps1"
    $latestCmd = Join-Path $RuntimeDir "agent_system\scripts\agentrunner.cmd"
    $latestSh = Join-Path $RuntimeDir "agent_system\scripts\agentrunner.sh"
    if (Test-Path $latestPs1) {
        Copy-Item $latestPs1 -Destination "." -Force -ErrorAction SilentlyContinue
    }
    if (Test-Path $latestCmd) {
        Copy-Item $latestCmd -Destination "." -Force -ErrorAction SilentlyContinue
    }
    if (Test-Path $latestSh) {
        Copy-Item $latestSh -Destination "." -Force -ErrorAction SilentlyContinue
    }
}

function Repair-Runtime {
    $stamp = Get-Date -Format 'yyyyMMddHHmmss'
    $brokenDir = "$RuntimeDir.broken-$stamp"

    if (Test-Path $RuntimeDir) {
        Write-Warning "[agentrunner] Runtime repo is conflicted. Moving it to: $brokenDir"
        Move-Item -Path $RuntimeDir -Destination $brokenDir -Force -ErrorAction Stop
    }

    $parent = Split-Path $RuntimeDir
    if (-not (Test-Path $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }

    Write-Host "[agentrunner] Cloning a clean runtime to $RuntimeDir ..." -ForegroundColor Cyan
    git clone $RepoUrl $RuntimeDir
    if ($LASTEXITCODE -ne 0) {
        Write-Error "[agentrunner] Failed to clone clean runtime."
        return $false
    }

    $script:Installer = Join-Path $RuntimeDir 'agent_system\install.py'
    return $true
}

function Update-RuntimeCore {
    param([string]$PythonCmd)

    # Keep runtime current so install seeds latest workspace policy files.
    & $PythonCmd $Installer update --workspace . --no-workspace-refresh --autostash
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "[agentrunner] Runtime update failed; attempting runtime self-repair..."
        if (-not (Repair-Runtime)) {
            return $false
        }
        & $PythonCmd $Installer update --workspace . --no-workspace-refresh --autostash
        if ($LASTEXITCODE -ne 0) {
            Write-Error "[agentrunner] Runtime update still failed after self-repair."
            return $false
        }
    }
    return $true
}

function Get-Python {
    $py = Get-Command python3, python | Select-Object -First 1 -ExpandProperty Name
    if (-not $py) { Write-Error "Python 3.9+ is required."; exit 1 }
    return $py
}

function Get-RepoRoot {
    param([string]$Workspace = ".")

    $resolved = Resolve-Path -Path $Workspace -ErrorAction SilentlyContinue
    if (-not $resolved) { return $null }
    $workspacePath = [System.IO.Path]::GetFullPath($resolved.Path)
    $gitRootRaw = git -C $workspacePath rev-parse --show-toplevel 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $gitRootRaw) { return $null }
    return [System.IO.Path]::GetFullPath($gitRootRaw.Trim())
}

function Assert-ProjectRoot {
    param(
        [string]$Workspace = ".",
        [string]$CommandName = "command"
    )

    $resolved = Resolve-Path -Path $Workspace -ErrorAction SilentlyContinue
    if (-not $resolved) {
        Write-Error "[agentrunner] Workspace path not found for '$CommandName': $Workspace"
        exit 1
    }

    $workspacePath = [System.IO.Path]::GetFullPath($resolved.Path)
    $gitRootRaw = git -C $workspacePath rev-parse --show-toplevel 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $gitRootRaw) {
        Write-Error "[agentrunner] '$CommandName' must run from the git repository root. Run this command from the project root."
        exit 1
    }

    $gitRoot = [System.IO.Path]::GetFullPath($gitRootRaw.Trim())
    if ($gitRoot -ne $workspacePath) {
        Write-Error "[agentrunner] '$CommandName' must run from repository root.`n  current: $workspacePath`n  root:    $gitRoot"
        exit 1
    }
}

function Invoke-WorkspaceSelector {
    param(
        [string]$SubCommand,
        [string[]]$ForwardArgs = @()
    )

    $selectorArgs = @(
        "--workspace", ".",
        "--runtime-dir", $RuntimeDir,
        "--installer", $Installer,
        "--command", $SubCommand
    )
    if ($ForwardArgs.Count -gt 0) {
        $selectorArgs += "--"
        $selectorArgs += $ForwardArgs
    }
    & $script:py $WorkspaceSelector @selectorArgs
    return $LASTEXITCODE
}

$script:py = Get-Python
$py = $script:py

switch ($Command) {
    "install" {
        Ensure-Runtime
        if (-not (Update-RuntimeCore -PythonCmd $py)) { exit 1 }
        Refresh-LocalLaunchers
        $projectName = ""
        $installExtraArgs = @()
        if ($CommandArgs.Count -gt 0) {
            if ($CommandArgs[0].StartsWith("-")) {
                $installExtraArgs = @($CommandArgs)
            } else {
                $projectName = $CommandArgs[0]
                if ($CommandArgs.Count -gt 1) {
                    $installExtraArgs = @($CommandArgs[1..($CommandArgs.Count - 1)])
                }
            }
        }

        if (-not $projectName) {
            $selectorRc = Invoke-WorkspaceSelector -SubCommand "install" -ForwardArgs $installExtraArgs
            if ($selectorRc -eq 0) { break }
            if ($selectorRc -ne 2) { exit $selectorRc }

            $cwd = [System.IO.Path]::GetFullPath((Resolve-Path ".").Path)
            $repoRoot = Get-RepoRoot -Workspace "."
            if ($repoRoot -and $repoRoot -eq $cwd) {
                $confirm = Read-Host "Detected git project root '$cwd'. Enable AgentRunner for this project? [Y/n]"
                if (-not $confirm -or $confirm -match '^(y|yes)$') {
                    $projectName = "."
                }
            }
        }
        if (-not $projectName) { $projectName = Read-Host "Enter name for your new project" }
        if (-not (Test-Path $projectName)) {
            New-Item -ItemType Directory -Path $projectName -Force | Out-Null
        }
        Set-Location $projectName
        if (-not (Test-Path ".git")) {
            git init | Out-Null
            if ($LASTEXITCODE -ne 0) {
                Write-Error "[agentrunner] Failed to initialize git repository in $projectName"
                exit 1
            }
        }
        Assert-ProjectRoot -Workspace "." -CommandName "install"
        # ALWAYS run the installer from the shared runtime to ensure path consistency
        & $py $Installer install --workspace . @installExtraArgs
    }
    "update" { 
        Ensure-Runtime
        Refresh-LocalLaunchers
        $selectorRc = Invoke-WorkspaceSelector -SubCommand "update" -ForwardArgs @("--autostash")
        if ($selectorRc -eq 0) { break }
        if ($selectorRc -ne 2) { exit $selectorRc }
        Assert-ProjectRoot -Workspace "." -CommandName "update"
        & $py $Installer update --workspace . --autostash
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "[agentrunner] Workspace update failed; repairing runtime clone and retrying..."
            if (-not (Repair-Runtime)) { exit 1 }
            & $py $Installer update --workspace . --autostash
            if ($LASTEXITCODE -ne 0) { exit 1 }
        }
        Refresh-LocalLaunchers
    }
    "start" {
        Ensure-Runtime; Refresh-LocalLaunchers
        $selectorRc = Invoke-WorkspaceSelector -SubCommand "start" -ForwardArgs $CommandArgs
        if ($selectorRc -eq 0) { break }
        if ($selectorRc -ne 2) { exit $selectorRc }
        Assert-ProjectRoot -Workspace "." -CommandName "start"
        & $py $Installer start --workspace . @CommandArgs
    }
    "auth" {
        Ensure-Runtime; Refresh-LocalLaunchers
        $authArgs = if ($CommandArgs.Count -gt 0) { @($CommandArgs) } else { @("--fix") }
        $selectorRc = Invoke-WorkspaceSelector -SubCommand "auth" -ForwardArgs $authArgs
        if ($selectorRc -eq 0) { break }
        if ($selectorRc -ne 2) { exit $selectorRc }
        Assert-ProjectRoot -Workspace "." -CommandName "auth"
        & $py $Installer auth --workspace . @authArgs
    }
    "detect" {
        Ensure-Runtime; Refresh-LocalLaunchers
        $selectorRc = Invoke-WorkspaceSelector -SubCommand "detect" -ForwardArgs $CommandArgs
        if ($selectorRc -eq 0) { break }
        if ($selectorRc -ne 2) { exit $selectorRc }
        Assert-ProjectRoot -Workspace "." -CommandName "detect"
        & $py $Installer detect --workspace . @CommandArgs
    }
    "permissions" {
        Ensure-Runtime; Refresh-LocalLaunchers
        $permArgs = if ($CommandArgs.Count -gt 0) { @($CommandArgs) } else { @("--mode", "prompt") }
        $selectorRc = Invoke-WorkspaceSelector -SubCommand "permissions" -ForwardArgs $permArgs
        if ($selectorRc -eq 0) { break }
        if ($selectorRc -ne 2) { exit $selectorRc }
        Assert-ProjectRoot -Workspace "." -CommandName "permissions"
        & $py $Installer permissions --workspace . @permArgs
    }
    "local-llm" {
        Ensure-Runtime; Refresh-LocalLaunchers
        $subCmd = if ($CommandArgs.Count -gt 0) { $CommandArgs[0] } else { "status" }
        $runner = if ($CommandArgs.Count -gt 1) { $CommandArgs[1] } else { $null }

        $selectorArgs = @()
        switch ($subCmd) {
            "status" { $selectorArgs = @("status") }
            "configure" { $selectorArgs = @("configure") }
            "configure-project" { $selectorArgs = @("configure", "--project-only") }
            "start" {
                if ($runner) { $selectorArgs = @("start", "--runner", $runner) }
                else { $selectorArgs = @("start") }
            }
            "stop" {
                if ($runner) { $selectorArgs = @("stop", "--runner", $runner) }
                else { $selectorArgs = @("stop") }
            }
            default {
                Write-Error "[agentrunner] Unknown local-llm command '$subCmd'. Use status|start|stop|configure|configure-project."
                exit 1
            }
        }

        $selectorRc = Invoke-WorkspaceSelector -SubCommand "local-llm" -ForwardArgs $selectorArgs
        if ($selectorRc -eq 0) { break }
        if ($selectorRc -ne 2) { exit $selectorRc }
        Assert-ProjectRoot -Workspace "." -CommandName "local-llm"

        switch ($subCmd) {
            "status" { & $py $Installer local-llm --workspace . status }
            "configure" { & $py $Installer local-llm --workspace . configure }
            "configure-project" { & $py $Installer local-llm --workspace . configure --project-only }
            "start" {
                if ($runner) { & $py $Installer local-llm --workspace . start --runner $runner }
                else { & $py $Installer local-llm --workspace . start }
            }
            "stop" {
                if ($runner) { & $py $Installer local-llm --workspace . stop --runner $runner }
                else { & $py $Installer local-llm --workspace . stop }
            }
            default {
                Write-Error "[agentrunner] Unknown local-llm command '$subCmd'. Use status|start|stop|configure|configure-project."
                exit 1
            }
        }
    }
    "help" { Show-Help }
    Default { Write-Host "Unknown command: $Command"; Show-Help }
}
