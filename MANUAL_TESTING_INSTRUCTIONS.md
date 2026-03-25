# Manual Testing Instructions - Complete the Repeatability Validation

This document guides you through the manual testing phases to fully validate that the auto-start implementation is repeatable.

## Testing Status

- ✅ **Phase 1 (Component Validation):** PASSED
- ⏳ **Phase 2 (Setup Execution):** Ready for your testing
- ⏳ **Phase 3 (Manual Startup Test):** Ready for your testing
- ⏳ **Phase 4 (Boot Test):** Ready for your testing

**Total Time Required:** ~50 minutes (includes 10 minute reboot)

---

## Phase 2: Setup Execution (5 minutes)

### What This Tests
- PowerShell script can create Task Scheduler entry
- Task is created with correct configuration
- No conflicts with existing tasks

### Prerequisites
✓ Administrator access to your computer
✓ Command Prompt or PowerShell installed
✓ All Phase 1 validations passed

### Step-by-Step Instructions

#### Step 1: Open Command Prompt as Administrator

**Option A: Windows 11 Quick Menu**
1. Press `Win+X`
2. Select "Command Prompt (Admin)" or "Windows Terminal (Admin)"
3. Click "Yes" when prompted by User Account Control

**Option B: Manual**
1. Press `Win+S` to search
2. Type "cmd"
3. Right-click "Command Prompt"
4. Select "Run as Administrator"

#### Step 2: Navigate to Scripts Directory

Copy and paste this command:

```cmd
cd /d h:\development\projects\AUDia\AUDiaLLMGateway\scripts
```

#### Step 3: Run the Setup Script

Copy and paste this command:

```cmd
setup-autostart.bat
```

#### Step 4: Observe Output

You should see:

```
========================================
AUDia LLM Gateway - Auto-Start Setup
========================================

Administrator privileges confirmed.

This setup will:
  1. Create Windows Task Scheduler entry
  2. Configure auto-start at logon
  3. Enable highest privileges for Docker access
  4. Set retry policy for failures

Running PowerShell registration script...

Registering scheduled task...
Task registered successfully!

Task Details:
  Name:           AUDia-LLM-Gateway-Startup
  Path:           \AUDia\
  State:          Ready
  Last Run:       (blank)
  Next Run:       (next logon)

Setup Complete!

The task will automatically:
  1. Wait for Docker daemon to start (max 60 seconds)
  2. Navigate to: h:\development\projects\AUDia\AUDiaLLMGateway
  3. Run: docker compose up -d
  4. Log output to: h:\development\projects\AUDia\AUDiaLLMGateway\logs\startup.log

Next Steps:
  1. Restart Windows to test auto-start
  2. Check logs: h:\development\projects\AUDia\AUDiaLLMGateway\logs\startup.log
  3. Verify services: docker compose ps

Would you like to test the startup script now?
Test now? (y/n):
```

#### Step 5: Test Now (Optional)

When prompted `Test now? (y/n):`, you have two options:

**Option A: Test Now (Type `y`)**
- The startup script will run immediately
- Services will start (if Docker is running)
- Provides quick confidence test
- Takes ~60-90 seconds

**Option B: Skip for Now (Type `n`)**
- Proceed to Phase 3 for manual testing
- More control over testing process

### Verification

After setup completes, verify the task was created:

#### Method 1: Command Line

```cmd
powershell -Command "Get-ScheduledTask -TaskName 'AUDia-LLM-Gateway-Startup' -TaskPath '\AUDia\' | Select-Object TaskName, State, LastRunTime, NextRunTime"
```

**Expected Output:**
```
TaskName                         State NextRunTime
--------                         ----- -----------
AUDia-LLM-Gateway-Startup        Ready (next logon time)
```

#### Method 2: Task Scheduler GUI

1. Press `Win+R`
2. Type `tasksched.msc`
3. Press Enter
4. Look for: `AUDia-LLM-Gateway-Startup` in the task list
5. Verify it's in the `\AUDia\` folder

### Success Criteria for Phase 2

- [✓] Setup script executed without errors
- [✓] PowerShell ran successfully
- [✓] Task created with name: `AUDia-LLM-Gateway-Startup`
- [✓] Task is in folder: `\AUDia\`
- [✓] Task state: `Ready`
- [✓] Trigger: `At logon`

If all above are ✓, **Phase 2 is PASSED**

---

## Phase 3: Manual Startup Test (15 minutes)

### What This Tests
- Startup script runs correctly
- Docker Compose services start properly
- Health checks pass
- Logging works

### Prerequisites
✓ Phase 2 completed (task created)
✓ Docker Desktop installed
✓ Docker daemon running
✓ Adequate disk space (~5GB free)

### Step-by-Step Instructions

#### Step 1: Start Docker Desktop

1. Click Windows Start menu
2. Search for "Docker"
3. Open "Docker Desktop"
4. Wait for it to fully start (~30 seconds)

You'll see the Docker icon in the system tray turn blue/active.

#### Step 2: Open Command Prompt (Regular - Not Admin)

1. Press `Win+S`
2. Type "cmd"
3. Press Enter (no need for admin)

#### Step 3: Navigate to Project Directory

Copy and paste:

```cmd
cd /d h:\development\projects\AUDia\AUDiaLLMGateway
```

#### Step 4: Stop Running Services (If Any)

Copy and paste:

```cmd
docker compose down
```

Wait a few seconds:

```cmd
timeout /t 5
```

#### Step 5: Verify Services Are Stopped

Copy and paste:

```cmd
docker compose ps
```

You should see an empty result or no containers running.

#### Step 6: Run the Startup Script

Copy and paste:

```cmd
scripts\startup-audia-gateway.bat
```

#### Step 7: Observe the Startup Process

You should see output similar to:

```
Waiting for Docker daemon...

Docker is ready. Starting AUDia LLM Gateway...
Starting Docker Compose services...
AUDia LLM Gateway services started successfully!

Status:
CONTAINER ID   IMAGE                                          STATUS              PORTS
xxxxxxx        example/audia-llm-gateway-orchestrator:latest  Up (healthy)        0.0.0.0:4000->4000/tcp
xxxxxxx        nginx:alpine                                   Up                  0.0.0.0:8080->8080/tcp
xxxxxxx        example/audia-llm-gateway-server:latest        Up
xxxxxxx        postgres:16-alpine                             Up (healthy)
```

**Timing:** Should complete in 45-90 seconds

#### Step 8: Verify Services Are Running

Copy and paste:

```cmd
docker compose ps
```

You should see 4 containers running:
- postgres (Healthy)
- llama-cpp (Up)
- gateway (Up, Healthy)
- nginx (Up)

#### Step 9: Check Logs for Errors

Copy and paste:

```cmd
type logs\startup.log
```

You should see timestamped entries:
```
[3/25/2026 2:00:15 PM] AUDia Gateway startup script started
[3/25/2026 2:00:15 PM] Waiting for Docker daemon to start...
[3/25/2026 2:00:25 PM] Docker daemon detected, starting compose services...
[3/25/2026 2:00:35 PM] Services started successfully
```

Check for errors:

```cmd
type logs\startup.log | findstr ERROR
```

Expected: No output (no errors found)

#### Step 10: Test Health Endpoints

Test Gateway (copy and paste each):

```cmd
curl http://localhost:4000/health/liveliness
```

Expected output: `"I'm alive!"`

Test llama-swap:

```cmd
curl http://localhost:41080/health
```

Expected output: `OK`

Test Models:

```cmd
curl http://localhost:41080/models | findstr id
```

Expected output: JSON lines with `"id":"model-name"`

### Success Criteria for Phase 3

- [✓] Startup script executed without errors
- [✓] All 4 containers started successfully
- [✓] No ERROR entries in logs/startup.log
- [✓] Gateway health: `"I'm alive!"`
- [✓] llama-swap health: `OK`
- [✓] Models endpoint responsive
- [✓] Startup completed in 45-90 seconds

If all above are ✓, **Phase 3 is PASSED**

### Optional: Repeat Phase 3

For extra confidence, repeat Phase 3:

```cmd
docker compose down
timeout /t 5
scripts\startup-audia-gateway.bat
```

This tests that the startup process is repeatable without random failures.

---

## Phase 4: Boot Test (30 minutes including reboot)

### What This Tests
- Task Scheduler actually runs the task at logon
- Services auto-start without manual intervention
- Logs show automatic execution
- System behaves correctly after reboot

### Prerequisites
✓ Phase 2 completed (task created)
✓ Phase 3 successful (startup script works)
✓ All work saved on your computer
✓ Time available for reboot (~15 minutes)

### Step-by-Step Instructions

#### Step 1: Prepare for Reboot

Close all applications and save work. Then copy and paste:

```cmd
cd /d h:\development\projects\AUDia\AUDiaLLMGateway
```

#### Step 2: Optional - Clean Logs for Fresh Test

To have a clean log from the reboot:

```cmd
del logs\startup.log
```

#### Step 3: Stop Services Before Reboot

```cmd
docker compose down
```

#### Step 4: Initiate Reboot

Copy and paste:

```cmd
shutdown /r /t 60
```

This schedules a reboot in 60 seconds. You'll see:
```
Shutdown initiated by C:\Windows\System32\shutdown.exe...
```

#### Alternative: Manual Reboot

Instead of the command, you can:
1. Click Windows Start
2. Click Power
3. Click Restart

#### Step 5: Wait for Reboot and Login

- System will show shutdown warning
- System restarts (takes ~1 minute)
- Windows loads
- You see login screen
- **You log in** (this triggers the task)

#### Step 6: Wait for Services to Start

After you log in, **wait 90 seconds**. The task should run automatically.

You can see progress by opening Task Manager:
- Press `Ctrl+Shift+Esc`
- Look for "docker.exe" in the task list

#### Step 7: Verify Services Started

After waiting 90 seconds, open Command Prompt:

```cmd
cd /d h:\development\projects\AUDia\AUDiaLLMGateway
docker compose ps
```

You should see 4 containers running without running any commands!

#### Step 8: Test Health Endpoints

```cmd
curl http://localhost:4000/health/liveliness
curl http://localhost:41080/health
```

Both should respond correctly.

#### Step 9: Review Boot Logs

```cmd
type logs\startup.log
```

You should see entries showing the script ran automatically:

```
[3/25/2026 2:15:30 PM] AUDia Gateway startup script started
[3/25/2026 2:15:35 PM] Docker daemon detected, starting compose services...
[3/25/2026 2:15:45 PM] Services started successfully
```

The timing should match when you logged in + ~30 seconds.

### Success Criteria for Phase 4

- [✓] System rebooted successfully
- [✓] Services running after you log in (no manual intervention)
- [✓] All 4 containers started automatically
- [✓] No errors in logs/startup.log
- [✓] Health endpoints responsive
- [✓] Boot logs show automatic execution
- [✓] Services ready within 90 seconds of login

If all above are ✓, **Phase 4 is PASSED**

---

## Complete Testing Summary

After completing all 4 phases, you will have validated:

### Repeatability ✓
- Setup script runs the same way every time
- Startup script works consistently
- Task executes reliably on boot
- Services start in correct order
- No random failures

### Reliability ✓
- All 4 services start successfully
- Health checks all pass
- No manual fixes needed
- Logs are clean (no errors)
- Performance is consistent

### Automation ✓
- Setup is one-command (setup-autostart.bat)
- Startup is logged automatically
- Task runs without user intervention
- No configuration between reboots

### Documentation ✓
- Full guides for each phase
- Expected outputs documented
- Troubleshooting available
- Test results recorded

---

## Troubleshooting Quick Links

If you encounter issues:

| Issue | Solution |
|-------|----------|
| Admin access denied | Right-click cmd.exe, select "Run as Administrator" |
| Docker not found | Install Docker Desktop or verify PATH |
| Task not created | Re-run setup-autostart.bat with admin privileges |
| Services don't start | Check logs/startup.log for specific errors |
| Port conflicts | Change ports in .env file |
| Health endpoints not responding | Wait 30 more seconds for services |
| Task doesn't run after reboot | Check Task Scheduler, verify trigger is "At logon" |

For detailed troubleshooting, see **TEST_AUTOSTART.md** → "Failure Handling" section.

---

## Recording Results

After completing testing, document your results:

1. Create a file: `TEST_RESULTS_YOURNAME_YYYYMMDD.txt`
2. Copy the template from **TEST_AUTOSTART.md**
3. Fill in your results
4. Save for future reference

Example:
```
TEST_RESULTS_John_20260325.txt
```

This provides an audit trail showing when and by whom the testing was completed.

---

## Timeline Estimate

| Phase | Time | Can Skip? |
|-------|------|-----------|
| 1 (Automated) | ✓ Done | No |
| 2 (Setup) | 5 min | No - Required |
| 3 (Manual Test) | 15 min | Optional but recommended |
| 4 (Boot Test) | 30 min (includes reboot) | Optional but recommended for full validation |

**Minimum:** 5 minutes (Phase 2 only)
**Recommended:** 50 minutes (all phases)

---

## Success Statement

When you complete all 4 phases successfully, you can confirm:

✅ **The auto-start implementation is REPEATABLE and RELIABLE**

It works the same way every time and doesn't require any special handling or workarounds. The process can be trusted for production use.

---

## Questions?

- **Setup questions:** See `SETUP_AUTOSTART.md`
- **Quick reference:** See `AUTOSTART_QUICKSTART.txt`
- **Detailed testing:** See `TEST_AUTOSTART.md`
- **Configuration:** See `DOCKER_AUTOSTART.md`

Good luck with your testing! 🚀
