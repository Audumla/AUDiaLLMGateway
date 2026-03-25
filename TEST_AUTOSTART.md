# Auto-Start Testing & Validation Guide

This document provides a repeatable testing process to verify the auto-start implementation works correctly.

## Test Plan Overview

```
┌─────────────────────────────────────────────────────────────┐
│ TEST PHASE 1: Component Validation (No Admin Required)     │
│ - Script syntax checks                                      │
│ - File existence verification                               │
│ - Dry-run simulations                                       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ TEST PHASE 2: Setup Execution (Admin Required)             │
│ - Run setup-autostart.bat                                   │
│ - Verify Task Scheduler entry created                       │
│ - Export task configuration                                 │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ TEST PHASE 3: Manual Startup Test (No Reboot)             │
│ - Stop all services                                         │
│ - Run startup script manually                               │
│ - Verify services start correctly                           │
│ - Check logs for errors                                     │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ TEST PHASE 4: Boot Test (Requires Reboot)                 │
│ - Reboot system                                             │
│ - Verify services auto-start                               │
│ - Check health endpoints                                    │
│ - Review startup logs                                       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ RESULT: Pass/Fail Summary                                  │
│ - All tests passed: Setup is repeatable                    │
│ - Document any failures and fixes                          │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Component Validation

### 1.1 Verify All Files Exist

```bash
# Check all required files
ls -lh scripts/startup-audia-gateway.bat
ls -lh scripts/setup-autostart.bat
ls -lh scripts/register-startup-task.ps1
ls -lh SETUP_AUTOSTART.md
ls -lh AUTOSTART_QUICKSTART.txt
ls -lh .env
ls -lh docker-compose.yml
```

**Expected:** All files present with reasonable sizes

### 1.2 Validate Script Syntax

```bash
# Batch script syntax check
cmd /c "scripts\startup-audia-gateway.bat /?" >nul 2>&1 && echo "Batch syntax: OK" || echo "Batch syntax: ERROR"

# PowerShell script syntax check
powershell -NoProfile -Command "[scriptblock]::Create((Get-Content 'scripts\register-startup-task.ps1' -Raw)) | Out-Null && Write-Host 'PowerShell syntax: OK' -ForegroundColor Green || Write-Host 'PowerShell syntax: ERROR' -ForegroundColor Red"
```

**Expected:** Both scripts syntax valid

### 1.3 Verify Environment

```bash
# Check Docker is installed
docker --version

# Check Docker Compose is installed
docker compose --version

# Check project directory structure
tree -L 2 config/

# Check Docker Compose file is valid
docker compose config > /dev/null 2>&1 && echo "Compose file: VALID" || echo "Compose file: INVALID"
```

**Expected:** Docker/Compose present, compose file valid

### 1.4 Verify .env Configuration

```bash
# Check .env contains required variables
echo "=== Required Variables ===" && \
grep -E "^(LLAMA_BACKEND|LLAMA_VERSION|ROCM_LLAMA_CPP_PREVIEW_REF|NGINX_PORT|GATEWAY_PORT)" .env && \
echo "" && \
echo "=== Expected Values ===" && \
echo "LLAMA_BACKEND=vulkan (or auto/cuda/rocm/cpu)" && \
echo "LLAMA_VERSION=latest" && \
echo "ROCM_LLAMA_CPP_PREVIEW_REF=rocm-7.11.0-preview" && \
echo "NGINX_PORT=8080" && \
echo "GATEWAY_PORT=4000"
```

**Expected:** All required variables present with valid values

---

## Phase 2: Setup Execution (Admin Required)

### 2.1 Run Setup Script

```bash
# Open Command Prompt as Administrator, then:
cd /d h:\development\projects\AUDia\AUDiaLLMGateway\scripts
setup-autostart.bat
```

**Expected Output:**
```
========================================
AUDia LLM Gateway - Auto-Start Setup
========================================

Administrator privileges confirmed.

This setup will:
  1. Create Windows Task Scheduler entry
  2. Configure auto-start at logon
  ...

Running PowerShell registration script...
[PowerShell output]

Successfully registered!
Task registered successfully!

Task Details:
  Name:           AUDia-LLM-Gateway-Startup
  Path:           \AUDia\
  State:          Ready
  Last Run:       (blank if first run)
  Next Run:       (next logon)

Setup Complete!
```

### 2.2 Verify Task Was Created

```bash
# Method 1: Command line
tasklist /v | find "AUDia"

# Method 2: Task Scheduler GUI
tasksched.msc

# Method 3: PowerShell query
powershell -Command "Get-ScheduledTask -TaskName 'AUDia-LLM-Gateway-Startup' | Select-Object TaskName, State, LastRunTime, NextRunTime"
```

**Expected:**
- Task name: `AUDia-LLM-Gateway-Startup`
- State: `Ready`
- Path: `\AUDia\AUDia-LLM-Gateway-Startup`

### 2.3 Export Task Configuration

```bash
# Backup the task definition
powershell -Command "Export-ScheduledTask -TaskName 'AUDia-LLM-Gateway-Startup' -TaskPath '\AUDia\' | Out-File 'scripts\task-backup.xml'"

# Verify export
ls -lh scripts/task-backup.xml
```

**Expected:** task-backup.xml created (for restoration if needed)

---

## Phase 3: Manual Startup Test (No Reboot)

### 3.1 Stop All Services

```bash
cd h:\development\projects\AUDia\AUDiaLLMGateway

# Stop all services gracefully
docker compose down

# Wait for services to stop
timeout /t 5

# Verify services are stopped
docker compose ps
```

**Expected:** No running containers

### 3.2 Run Startup Script Manually

```bash
# Record start time
echo Current time: %date% %time%

# Run the startup script
scripts\startup-audia-gateway.bat

# Record end time
echo Current time: %date% %time%
```

**Expected Output:**
```
Waiting for Docker daemon...
Docker is ready. Starting AUDia LLM Gateway...
Starting Docker Compose services...
AUDia LLM Gateway services started successfully!

Status:
CONTAINER ID   IMAGE                                          STATUS              PORTS
xxxxx          example/audia-llm-gateway-orchestrator:latest  Up (healthy)        0.0.0.0:4000->4000/tcp
xxxxx          nginx:alpine                                   Up                  0.0.0.0:8080->8080/tcp
xxxxx          example/audia-llm-gateway-server:latest        Up
xxxxx          postgres:16-alpine                             Up (healthy)
```

**Timing:** Should complete in 45-90 seconds

### 3.3 Verify Services Started Correctly

```bash
# Check all services are running
docker compose ps

# Check specific service health
docker compose logs audia-gateway | tail -20

# Verify each service
echo "=== PostgreSQL Health ===" && docker compose ps | grep postgres
echo "=== llama-cpp Health ===" && docker compose ps | grep llama-cpp
echo "=== Gateway Health ===" && docker compose logs audia-gateway | grep -i "alive\|error" | tail -5
echo "=== Nginx Health ===" && docker compose ps | grep nginx
```

**Expected:**
- All 4 containers running
- PostgreSQL: healthy
- Gateway: "I'm alive!" in logs
- No ERROR entries in logs

### 3.4 Check Startup Logs

```bash
# View startup log
echo "=== Startup Log ===" && type logs\startup.log

# Check for errors
echo "" && echo "=== Any Errors? ===" && type logs\startup.log | findstr /I "error\|failed\|warning" || echo "No errors found"
```

**Expected:**
```
[DATE TIME] AUDia Gateway startup script started
[DATE TIME] Waiting for Docker daemon to start...
[DATE TIME] Docker daemon detected, starting compose services...
[DATE TIME] Services started successfully
```

### 3.5 Test Health Endpoints

```bash
# Gateway health
echo "=== Gateway Health ===" && curl -s http://localhost:4000/health/liveliness

# llama-swap health
echo "" && echo "=== llama-swap Health ===" && curl -s http://localhost:41080/health

# Available models
echo "" && echo "=== Available Models ===" && curl -s http://localhost:41080/models | findstr /C:"id" | head -3

# Test inference (simple request)
echo "" && echo "=== Test Inference ===" && curl -s -X POST http://localhost:41080/v1/chat/completions -H "Content-Type: application/json" -d "{\"model\":\"qwen3.5-27b-(96k-Q6)\",\"messages\":[{\"role\":\"user\",\"content\":\"test\"}],\"max_tokens\":10}" | findstr /C:"content"
```

**Expected:**
- Gateway: `"I'm alive!"`
- llama-swap: `OK`
- Models: `id` entries visible
- Inference: Response with content

---

## Phase 4: Boot Test (Requires Reboot)

### 4.1 Prepare for Reboot

```bash
# Save current logs
copy logs\startup.log logs\startup-pre-reboot.log

# Note current time
echo Current time before reboot: %date% %time%

# Optional: Clean logs for fresh test
del logs\startup.log

# Verify services will start from scratch
docker compose down
```

### 4.2 Reboot System

```bash
# Option 1: Command line
shutdown /r /t 60 /c "AUDia Auto-Start Test"

# Option 2: GUI
# Start → Power → Restart
```

### 4.3 Post-Reboot Verification (30-90 seconds after login)

```bash
# Check if services auto-started
docker compose ps

# Check service health
docker compose logs audia-gateway | tail -20

# Verify via health endpoints
curl http://localhost:4000/health/liveliness
curl http://localhost:41080/health

# Review startup logs
type logs\startup.log
```

**Expected:**
- All services running
- No errors in logs
- Health endpoints responsive
- Services started within 90 seconds of login

### 4.4 Performance Analysis

```bash
# Extract timing from logs
echo "=== Boot Timeline ===" && type logs\startup.log

# Check Task Scheduler history
powershell -Command "Get-EventLog -LogName System -Source 'Task Scheduler' -Newest 5 | Where-Object {$_.Message -like '*AUDia*'} | Select-Object TimeGenerated, Message"

# Measure service startup time
docker compose ps --format "table {{.Names}}\t{{.Status}}"
```

---

## Test Results Template

Create a file: `TEST_RESULTS_YYYYMMDD.txt`

```
================================================================================
AUTO-START TESTING RESULTS
================================================================================

Test Date: [DATE]
Test Environment: Windows [VERSION]
Docker Version: [docker --version]
Docker Compose Version: [docker compose --version]

================================================================================
PHASE 1: COMPONENT VALIDATION
================================================================================

[x] All files exist
[x] Script syntax valid
[x] Docker/Compose installed
[x] docker-compose.yml valid
[x] .env configured correctly

Result: PASS

================================================================================
PHASE 2: SETUP EXECUTION
================================================================================

[x] Setup script ran successfully
[x] Task created in Task Scheduler
[x] Task name: AUDia-LLM-Gateway-Startup
[x] Task path: \AUDia\
[x] Task state: Ready
[x] Task backup exported

Result: PASS

================================================================================
PHASE 3: MANUAL STARTUP TEST
================================================================================

[x] Services stopped cleanly
[x] Startup script executed
[x] All 4 services started
[x] No errors in logs
[x] Health endpoints responsive
[x] Startup time: 45-90 seconds

Services Status:
  - PostgreSQL: UP (healthy)
  - llama-cpp: UP
  - Gateway: UP (alive)
  - Nginx: UP

Health Checks:
  - Gateway: "I'm alive!" ✓
  - llama-swap: OK ✓
  - Models: Available ✓
  - Inference: Working ✓

Result: PASS

================================================================================
PHASE 4: BOOT TEST
================================================================================

[x] Reboot completed
[x] Services auto-started
[x] All services healthy
[x] No errors in logs
[x] Health endpoints responsive
[x] Boot time: ~90 seconds from login

Services Status (after reboot):
  - PostgreSQL: UP (healthy)
  - llama-cpp: UP
  - Gateway: UP (alive)
  - Nginx: UP

Health Checks (after reboot):
  - Gateway: "I'm alive!" ✓
  - llama-swap: OK ✓
  - Models: Available ✓
  - Inference: Working ✓

Result: PASS

================================================================================
OVERALL RESULT: ALL TESTS PASSED ✓
================================================================================

The auto-start implementation is REPEATABLE and RELIABLE.

Timestamp: [DATE TIME]
Tested by: [NAME]
System: [HOSTNAME]

Notes:
- Services start consistently within 60-90 seconds
- No manual intervention required
- Logs provide clear audit trail
- Health checks all pass

Recommendation: APPROVED FOR PRODUCTION USE

================================================================================
```

---

## Repeatability Checklist

Use this checklist to verify the process is repeatable:

- [ ] Phase 1 tests pass on first attempt
- [ ] Phase 1 tests pass on second attempt (same day)
- [ ] Phase 2 setup works after task removal/reinstall
- [ ] Phase 3 manual startup works 5 times consecutively
- [ ] Phase 4 boot test works 2+ times
- [ ] Logs show no errors on any run
- [ ] Health endpoints all respond correctly
- [ ] Services start in consistent order and time
- [ ] No manual fixes needed between runs
- [ ] Test results can be reproduced on different days

---

## Failure Handling

### If Phase 1 Fails

1. Check file permissions
2. Verify .env file is properly formatted (no BOM, UTF-8)
3. Check docker-compose.yml syntax with: `docker compose config`
4. Verify Docker/Compose are in PATH

### If Phase 2 Fails

1. Verify running as Administrator
2. Check PowerShell execution policy: `Get-ExecutionPolicy`
3. Remove existing task first: `taskkill /F /IM powershell.exe`
4. Re-run setup-autostart.bat

### If Phase 3 Fails

1. Check Docker daemon is running
2. Review full logs: `docker compose logs`
3. Check resource availability: `docker stats`
4. Verify ports are not in use: `netstat -ano | findstr :4000`

### If Phase 4 Fails

1. Check Task Scheduler history: `tasksched.msc`
2. Review Windows Event Viewer for task execution
3. Check logs/startup.log for specific error
4. Verify Docker Desktop auto-start is enabled
5. Increase timeout in startup script if needed

---

## Documentation for Repeatability

✅ **Documented:** All steps in this file
✅ **Automated:** setup-autostart.bat handles 90% of setup
✅ **Logged:** All actions logged to logs/startup.log
✅ **Testable:** Can be verified without code changes
✅ **Recoverable:** Task can be removed and re-created
✅ **Auditable:** Clear log trail of all startup events

---

## Success Criteria

Process is **repeatable** when:

1. ✅ All 4 phases pass consistently (no random failures)
2. ✅ No manual troubleshooting required after setup
3. ✅ Services start in same order and time every boot
4. ✅ Health endpoints all respond correctly
5. ✅ Logs are clean (no warnings/errors)
6. ✅ Someone else can follow the guide and succeed
7. ✅ Process works the same way every time

---

## Next Steps

1. Follow Phase 1-3 (no reboot required): ~15 minutes
2. If all pass, you're safe to reboot
3. Follow Phase 4 (requires reboot): ~10 minutes + reboot time
4. Document results in TEST_RESULTS_YYYYMMDD.txt
5. Keep test results for future reference

**Estimated Total Time:** 30-45 minutes (including reboot)
