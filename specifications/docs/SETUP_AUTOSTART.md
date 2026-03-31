# AUDia LLM Gateway - Auto-Start Setup Guide

This guide walks you through setting up automatic Docker Compose startup for AUDia LLM Gateway on Windows reboot.

## Quick Start (Recommended)

### Step 1: Open Command Prompt as Administrator

1. Press `Win+X` to open Quick Link menu
2. Select **"Command Prompt (Admin)"** or **"Windows PowerShell (Admin)"**
3. If prompted by User Account Control, click **"Yes"**

### Step 2: Run the Setup Script

Copy and paste this command:

```cmd
cd /d h:\development\projects\AUDia\AUDiaLLMGateway\scripts
setup-autostart.bat
```

The script will:
- Verify you have admin privileges
- Run the PowerShell registration script
- Create the scheduled task
- Optionally test the startup script immediately

### Step 3: Verify Setup

```cmd
REM Check that the task was created
tasklist /v | find "AUDia"

REM Or view it in Task Scheduler:
tasksched.msc
```

**Done!** The task is now registered and will run at next logon.

---

## Manual Setup (Alternative)

If you prefer to set up the task manually, follow these steps:

### 1. Enable Docker Desktop Auto-Start

1. Open **Docker Desktop**
2. Click **Settings** (gear icon)
3. Go to **General** tab
4. Check: **"Start Docker Desktop when you log in"**
5. Click **Apply & Restart**

### 2. Create Startup Batch Script

The batch script has already been created at:
```
h:\development\projects\AUDia\AUDiaLLMGateway\scripts\startup-audia-gateway.bat
```

This script:
- Waits up to 60 seconds for Docker daemon
- Navigates to the project directory
- Runs `docker compose up -d`
- Logs all output to `logs/startup.log`

### 3. Register Windows Task Scheduler Entry

Open Windows Task Scheduler:

**Option A: GUI (Easy)**
1. Press `Win+R` → type `taskschd.msc` → Enter
2. Right-click **Task Scheduler Library** → **Create Task**

**General Tab:**
- Name: `AUDia-LLM-Gateway-Startup`
- Check: **"Run with highest privileges"**
- Select: **"Run whether user is logged in or not"** (optional)

**Triggers Tab:**
- Click **New**
- Begin the task: **"At logon"**
- Click **OK**

**Actions Tab:**
- Click **New**
- Action: **"Start a program"**
- Program/script:
  ```
  h:\development\projects\AUDia\AUDiaLLMGateway\scripts\startup-audia-gateway.bat
  ```
- Start in:
  ```
  h:\development\projects\AUDia\AUDiaLLMGateway
  ```
- Click **OK**

**Settings Tab:**
- Check: **"Allow task to be run on demand"**
- Check: **"If the task fails, restart every: 1 minute"**
- Set **"Repeat task every"**: `5 minutes` (optional, for resilience)
- Set **"for a duration of"**: `1 hour` (optional)

**Click OK** and provide admin password.

**Option B: PowerShell (Automated)**

Open PowerShell as Administrator and run:

```powershell
cd h:\development\projects\AUDia\AUDiaLLMGateway\scripts
powershell -ExecutionPolicy Bypass -File register-startup-task.ps1
```

---

## Testing

### Manual Test (Before Reboot)

```bash
# Navigate to project directory
cd h:\development\projects\AUDia\AUDiaLLMGateway

# Run startup script directly
scripts\startup-audia-gateway.bat

# Watch services start
docker compose ps
```

### Boot Test (After Reboot)

1. Restart your computer
2. After logging in, wait 60-90 seconds
3. Verify services are running:
   ```bash
   docker compose ps
   ```
4. Check logs:
   ```bash
   type logs\startup.log
   ```

### Health Check After Boot

```bash
# Gateway health
curl http://localhost:4000/health/liveliness

# llama-swap health
curl http://localhost:41080/health

# Check models
curl http://localhost:41080/models | findstr /C:"id"
```

---

## Troubleshooting

### Task doesn't run automatically

**Check 1: Verify task exists**
```cmd
tasksched.msc
```
Look in "Task Scheduler Library" for "AUDia-LLM-Gateway-Startup"

**Check 2: Verify task is enabled**
- Right-click task → **Properties**
- Check: **"Enabled"**

**Check 3: Check last run result**
- View task in Task Scheduler
- Look at "Last Run Time" and "Last Run Result"
- Code `0` = success, non-zero = error

**Check 4: Review logs**
```bash
type logs\startup.log
```

### Docker doesn't start automatically

**Docker Desktop Settings:**
1. Open Docker Desktop
2. **Settings** → **General**
3. Check: **"Start Docker Desktop when you log in"**
4. Click **Apply & Restart**

**Alternative: Windows Services**
1. Press `Win+R` → `services.msc`
2. Find "Docker Desktop Service"
3. Right-click → **Properties**
4. Startup type: **Automatic**
5. Click **OK**

### Services start but with errors

Check the full log:
```bash
docker compose logs --tail 100
```

Common issues:
- **Database connection failing**: Check `logs/startup.log` for PostgreSQL errors
- **Gateway health failing**: Check `docker compose logs audia-gateway`
- **llama-cpp not ready**: Check `docker compose logs audia-llama-cpp`

### Startup script hangs

The script waits up to 60 seconds for Docker. If Docker is slow:

1. Check if Docker is running: `tasklist | find "docker"`
2. Open Docker Desktop and wait for it to fully start
3. Re-run the task or reboot

---

## Environment Variables

The startup script uses these variables (from `.env`):

| Variable | Default | Purpose |
|----------|---------|---------|
| `PROJECT_DIR` | `h:\development\projects\AUDia\AUDiaLLMGateway` | Where the project is located |
| `LOG_FILE` | `logs/startup.log` | Where startup logs are written |

To customize, edit `scripts/startup-audia-gateway.bat`:

```batch
set PROJECT_DIR=your-path-here
set LOG_FILE=your-log-path-here
```

---

## Logs

All startup events are logged to:
```
h:\development\projects\AUDia\AUDiaLLMGateway\logs\startup.log
```

Log entries include:
- When script started
- When Docker was detected
- When docker compose executed
- Service status
- Any errors

Example:
```
[3/25/2026 9:15:32 AM] AUDia Gateway startup script started
[3/25/2026 9:15:32 AM] Waiting for Docker daemon to start...
[3/25/2026 9:15:43 AM] Docker daemon detected, starting compose services...
[3/25/2026 9:15:45 AM] Services started successfully
```

View logs:
```cmd
type logs\startup.log                    REM Show all logs
type logs\startup.log | findstr ERROR    REM Show only errors
tail -f logs\startup.log                 REM Follow logs in real-time (if using Git Bash)
```

---

## Uninstall / Remove Auto-Start

### Via Task Scheduler GUI

1. Press `Win+R` → `taskschd.msc`
2. Find "AUDia-LLM-Gateway-Startup"
3. Right-click → **Delete**
4. Confirm deletion

### Via PowerShell

```powershell
# Remove the task
Unregister-ScheduledTask -TaskName "AUDia-LLM-Gateway-Startup" -TaskPath "\AUDia\" -Confirm:$false
```

---

## Advanced Configuration

### Run with Different User

To run the task as a specific user instead of SYSTEM:

1. Open Task Scheduler
2. Find "AUDia-LLM-Gateway-Startup"
3. Right-click → **Properties**
4. **General** tab
5. Under "Security options", select:
   - **"Change User or Group"**
   - Select your user account
6. Click **OK**

### Add Retry Policy

To auto-retry if startup fails:

1. Open Task Scheduler
2. Find "AUDia-LLM-Gateway-Startup"
3. Right-click → **Properties**
4. **Settings** tab
5. Check: **"If the task fails, restart every:"**
6. Set interval (e.g., 5 minutes) and duration (e.g., 1 hour)

### Schedule Multiple Triggers

You can trigger startup at:
- User logon (current setting)
- System startup (before user logs in)
- Specific time of day
- Network connection

1. Open Task Scheduler
2. Find task → **Properties**
3. **Triggers** tab
4. Click **New** to add additional triggers

---

## Performance Tips

### Reduce Startup Time

1. **Pre-load models**: Add to `docker/compose/docker-compose.yml`:
   ```yaml
   environment:
     - PRELOAD_MODELS=true
   ```

2. **Use faster backend**: Ensure Vulkan is selected in `.env`:
   ```
   LLAMA_BACKEND=vulkan
   ```

3. **Disable unnecessary services**: Comment out vLLM or watcher if not needed

### Monitor Startup Performance

```bash
# Check startup duration
Get-EventLog -LogName System -Source "Task Scheduler" -Newest 10 |
  Where-Object {$_.Message -like "*AUDia*"}
```

---

## Next Steps

1. ✅ Run `scripts/setup-autostart.bat` with admin privileges
2. ✅ Test with `scripts/startup-audia-gateway.bat`
3. ✅ Reboot and verify services start automatically
4. ✅ Check `logs/startup.log` for any issues
5. ✅ Monitor health endpoints after each reboot

**Congratulations!** Your AUDia LLM Gateway is now configured for automatic startup. 🎉
