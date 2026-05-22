# Claude AI Tooling Setup — WeTTY + Cowork Workflow

> **Tracking issue:** [CRE-31](https://linear.app/harold-browder/issue/CRE-31)
>
> **Why this exists.** On 2026-05-19, significant time was wasted trying to get
> claude.ai (the web chat interface) to drive WeTTY and control the server
> terminal. It cannot do this. This document captures the correct setup so
> future sessions start in under 2 minutes.

---

## The Two Claude Products — Know Which One You Need

|                          | **claude.ai** (web/desktop chat)                   | **Claude Desktop — Cowork**                                                 |
| ------------------------ | -------------------------------------------------- | --------------------------------------------------------------------------- |
| What it is               | Conversational AI in a browser tab or desktop app  | Desktop automation tool built into the Claude Desktop app                   |
| Can drive WeTTY?         | ❌ NO                                              | ✅ YES                                                                      |
| Can type into terminals? | ❌ NO                                              | ✅ YES                                                                      |
| Can read files on server?| ❌ NO (paste/upload only)                          | ✅ YES                                                                      |
| Can use Linear?          | ✅ YES (with connector enabled)                    | ✅ YES                                                                      |
| Can write/run code?      | ✅ YES (sandboxed Linux container)                 | ✅ YES                                                                      |
| Best for                 | Planning, code generation, Linear updates, review  | Actually deploying to the server, running commands, editing files in place  |

**Rule of thumb:** if you need to touch the server, use Cowork. If you need to
generate files or update Linear, the Chat tab is fine.

---

## Correct Session Setup (< 2 minutes)

### Step 1 — Open WeTTY

Navigate to `http://192.168.174.132:3000` in Chrome. WeTTY password lives in
the team password manager (see `.env` / 1Password — **never commit it**).

WeTTY runs as a Docker container (`wettyoss/wetty`, restart policy
`unless-stopped`). It does not need to be started manually.

### Step 2 — Open Claude Desktop → Cowork tab

Open the Claude Desktop app on Windows. Click the **Cowork** tab at the top.
Type your task and press **Ctrl+Enter** to start.

Cowork will open Chrome, navigate to WeTTY, and start typing commands directly.

### Step 3 — Give Cowork context

Paste a brief handoff note covering:

- What was done last session
- Current server state
- Today's priority issue (CRE-XX)

### Step 4 — Keep the Chat tab open for Linear + file generation

The Chat tab is better for generating large files, updating Linear issues, and
reviewing code. Run both side by side.

---

## ⚠️ Cowork Virtualization Requirements (2026-05-19 incident)

Cowork requires hardware virtualization. On 2026-05-19 it stopped working
because virtualization was disabled. Fix:

1. **BIOS:** Intel Virtualization Technology → Enabled (ASUS laptop, Aptio
   Setup Utility).
2. **Windows features (PowerShell as Admin):**
   ```powershell
   dism.exe /Online /Enable-Feature /FeatureName:Microsoft-Windows-Subsystem-Linux /All /NoRestart
   dism.exe /Online /Enable-Feature /FeatureName:VirtualMachinePlatform /All /NoRestart
   wsl --set-default-version 2
   ```
3. Full Windows restart after both steps.

**Note:** this machine runs **Windows 10 Home** — Hyper-V is NOT available.
WSL2 + Virtual Machine Platform is the correct path.

**If Cowork shows "Virtualization is not available" again:**

- Check BIOS first (Advanced → Intel Virtualization Technology → Enabled)
- Run the PowerShell commands above
- Full restart
- If still failing: uninstall and reinstall Claude Desktop (a clean install
  picks up WSL2 properly)

---

## WeTTY — Current State

WeTTY is healthy. Nothing needs to be installed or configured.

| Field          | Value                                  |
| -------------- | -------------------------------------- |
| Container      | `wettyoss/wetty`                       |
| Name           | `wetty`                                |
| Status         | Up continuously                        |
| Port           | `0.0.0.0:3000->3000/tcp`               |
| Restart policy | `unless-stopped` (survives reboots)    |
| URL            | `http://192.168.174.132:3000`          |
| Password       | *see password manager / `.env`*        |

SSH keepalive configured 2026-05-19 to prevent session drops:

```
# /etc/ssh/sshd_config
ClientAliveInterval 60
ClientAliveCountMax 10
```

---

## OmniLab Backend — Start / Restart

The backend does NOT run under systemd. It runs as a plain Python process,
supervised by `~/start-omnilab.sh` (a `while true` loop).

```bash
# Check if running
ps -ef | grep 'python.*main.py' | grep -v grep

# Find what's on port 5000
sudo ss -ltnp | grep ':5000'

# Start (if stopped)
cd ~/netlab/backend && nohup ~/netlab-env/bin/python main.py > /tmp/omnilab.log 2>&1 &

# Watch logs
tail -f /tmp/omnilab.log

# Verify
curl -s http://localhost:5000/api/system/health
```

> **Note:** the backend auto-respawns via `start-omnilab.sh` — killing the PID
> sometimes results in "address already in use" because the loop relaunches it.
> Just verify the health endpoint and move on.

---

## Key Gotchas — Don't Repeat These

### 1. FastAPI catch-all swallows new static routes

`main.py` has `@app.get("/{full_path:path}")` as a SPA fallback. Any new route
added AFTER this line is silently swallowed. Always insert new routes ABOVE
it:

```python
@app.get("/checkout", include_in_schema=False)   # ← NEW ROUTES HERE
def serve_checkout(): ...

@app.get("/{full_path:path}")                    # ← catch-all MUST BE LAST
def serve_spa_fallback(): ...
```

### 2. Heredocs through WeTTY break on curly braces

The shell evaluates `{}` inside heredocs. Use WinSCP for files > ~5 KB or
files containing `{`.

### 3. `LabCanvas.jsx` is too complex to patch via terminal

845 lines of complex single-line JSX. Use Python string replacement only —
NOT `sed`/`awk`/heredoc.

### 4. `pkill -f 'uvicorn.*main:app'` misses the backend

Use `pkill -f 'python.*main.py'` instead.

### 5. claude.ai Chat cannot access the server — ever

No SSH, no browser control, no WeTTY. Use Cowork for server access.

### 6. Cowork needs Ctrl+Enter to start a task

Regular Enter just adds a new line. Ctrl+Enter starts execution.

---

## Context File Convention

At the end of each session, update the **OmniLab Master Context** document in
Linear (Documents section of the OmniLab v1.0 project). It should include:

- Infrastructure table
- What was deployed (with live test results)
- Files created/modified
- Open bugs or gotchas
- Next session priorities in order
