# AUDia LLM Gateway - Windows Task Scheduler Registration
# This script registers the auto-start task in Windows Task Scheduler
# Must be run as Administrator
# Usage: powershell -ExecutionPolicy Bypass -File register-startup-task.ps1

param(
    [switch]$Force
)

# Check if running as Administrator
$isAdmin = [Security.Principal.WindowsIdentity]::GetCurrent().Groups -contains [Security.Principal.SecurityIdentifier]::new("S-1-5-32-544")
if (-not $isAdmin) {
    Write-Host "ERROR: This script requires Administrator privileges." -ForegroundColor Red
    Write-Host "Please run PowerShell as Administrator and try again." -ForegroundColor Yellow
    exit 1
}

Write-Host "AUDia LLM Gateway - Startup Task Registration" -ForegroundColor Cyan
Write-Host ("=" * 50)

# Define paths
$projectDir = "h:\development\projects\AUDia\AUDiaLLMGateway"
$scriptPath = "$projectDir\scripts\startup-audia-gateway.bat"
$taskName = "AUDia-LLM-Gateway-Startup"
$taskPath = "\AUDia\"

# Verify script exists
if (-not (Test-Path $scriptPath)) {
    Write-Host "ERROR: Startup script not found at: $scriptPath" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Configuration:" -ForegroundColor Green
Write-Host "  Project Dir:    $projectDir"
Write-Host "  Script Path:    $scriptPath"
Write-Host "  Task Name:      $taskName"
Write-Host "  Task Folder:    $taskPath"

# Check if task already exists
$existingTask = Get-ScheduledTask -TaskName $taskName -TaskPath $taskPath -ErrorAction SilentlyContinue

if ($existingTask -and -not $Force) {
    Write-Host ""
    Write-Host "WARNING: Task '$taskName' already exists!" -ForegroundColor Yellow
    Write-Host "Use -Force flag to overwrite"
    exit 0
}

if ($existingTask) {
    Write-Host ""
    Write-Host "Removing existing task '$taskName'..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $taskName -TaskPath $taskPath -Confirm:$false
    Start-Sleep -Seconds 1
}

# Create task principal (run with highest privileges)
$principal = New-ScheduledTaskPrincipal `
    -UserID "SYSTEM" `
    -LogonType ServiceAccount `
    -RunLevel Highest

# Create task trigger (run at user logon)
$trigger = New-ScheduledTaskTrigger -AtLogOn

# Create task action
$action = New-ScheduledTaskAction `
    -Execute $scriptPath `
    -WorkingDirectory $projectDir

# Create task settings
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)

# Create and register the task
Write-Host ""
Write-Host "Registering scheduled task..." -ForegroundColor Cyan

try {
    Register-ScheduledTask `
        -TaskName $taskName `
        -TaskPath $taskPath `
        -Principal $principal `
        -Trigger $trigger `
        -Action $action `
        -Settings $settings `
        -Description "Automatically starts AUDia LLM Gateway Docker Compose stack after Windows boot." `
        -Force | Out-Null

    Write-Host "Task registered successfully!" -ForegroundColor Green

    # Verify task was created
    $newTask = Get-ScheduledTask -TaskName $taskName -TaskPath $taskPath -ErrorAction SilentlyContinue
    if ($newTask) {
        Write-Host ""
        Write-Host "Task Details:" -ForegroundColor Green
        Write-Host "  Name:           $($newTask.TaskName)"
        Write-Host "  Path:           $($newTask.TaskPath)"
        Write-Host "  State:          $($newTask.State)"
        Write-Host "  Last Run:       $($newTask.LastRunTime)"
        Write-Host "  Next Run:       $($newTask.NextRunTime)"
    }
} catch {
    Write-Host "ERROR: Failed to register task" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host ("=" * 50) -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "The task will automatically:" -ForegroundColor Yellow
Write-Host "  1. Wait for Docker daemon to start (max 60 seconds)"
Write-Host "  2. Navigate to: $projectDir"
Write-Host "  3. Run: docker compose up -d"
Write-Host "  4. Log output to: $projectDir\logs\startup.log"
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Restart Windows to test auto-start"
Write-Host "  2. Check logs: $projectDir\logs\startup.log"
Write-Host "  3. Verify services: docker compose ps"

# Test the script manually
Write-Host ""
Write-Host "Would you like to test the startup script now?" -ForegroundColor Cyan
$response = Read-Host "Test now? (y/n)"
if ($response.ToLower() -eq 'y') {
    Write-Host ""
    Write-Host "Running startup script - this will take several seconds..." -ForegroundColor Yellow
    & $scriptPath
}

exit 0
