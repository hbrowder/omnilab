# CRE-26: DEMO VIDEO — RECORDING CHECKLIST

**Target:** 90-second demo video for v1.0 launch  
**Script:** docs/DEMO_VIDEO.md (230 lines, complete)  
**Status:** Ready to record  
**Date:** 2026-05-24  

---

## ✅ PRE-FLIGHT COMPLETE

**Assets verified:**
- ✅ Script: docs/DEMO_VIDEO.md (90-second, 8 beats)
- ✅ Seed labs: 3 JSON files in docs/demo-assets/seed-labs/
- ✅ Captions: docs/demo-assets/captions/omnilab-90.srt (35 cues)
- ✅ Launch copy: docs/demo-assets/launch-copy.md (PH/HN/Reddit variants)

**Current state:**
- Main branch: 1c15eb2 (CRE-51 complete)
- Backend healthy: http://localhost:5000/api/system/health
- Production DB: 1 lab (smoketest-v2), 2 nodes running

---

## 🎬 RECORDING SESSION PREP

### Step 1: Tag v1.0.0-rc.1

```bash
cd ~/omnilab
git tag -a v1.0.0-rc.1 -m "v1.0 Release Candidate 1

Production hardening complete (CRE-51):
- DEBUG mode environment-controlled
- Transaction rollbacks on all mutating endpoints
- Localhost-only security warnings
- Ready for demo video recording

Launch blockers cleared:
- CRE-39 (Docker provisioning) ✅
- CRE-49 (ENOSPC handling) ✅
- CRE-51 (production hardening) ✅

Next: CRE-26 (demo video recording)"

git push origin v1.0.0-rc.1
```

### Step 2: Import seed labs

The script uses 3 pre-configured labs:

```bash
# 1. Empty lab (for drag-drop demo)
curl -X POST http://localhost:5000/api/labs/import \
  -H "Content-Type: application/json" \
  -d @~/omnilab/docs/demo-assets/seed-labs/empty.json

# 2. Security stack (Kali + Wazuh + Suricata)
curl -X POST http://localhost:5000/api/labs/import \
  -H "Content-Type: application/json" \
  -d @~/omnilab/docs/demo-assets/seed-labs/security-stack.json

# 3. Networking triangle (3-router mesh)
curl -X POST http://localhost:5000/api/labs/import \
  -H "Content-Type: application/json" \
  -d @~/omnilab/docs/demo-assets/seed-labs/networking-triangle.json
```

### Step 3: Clean Chrome profile

**Before recording:**
- Open Chrome in clean profile mode:
  ```bash
  google-chrome --user-data-dir=/tmp/chrome-demo --disable-extensions
  ```
- No bookmarks bar
- No third-party extensions
- 1920×1080 window at 100% zoom
- Dev tools closed
- macOS: Enable "Do Not Disturb" (silence notifications)

### Step 4: OBS Studio setup

**Recording settings:**
- Resolution: 1920×1080 (1080p)
- Frame rate: 60 FPS
- Bitrate: 8 Mbps CBR
- Format: mp4
- Mouse cursor highlight: Yellow dot, 30px radius
- Keyboard overlay: Enabled (for terminal segment)

**Audio:**
- No voiceover (subtitles only)
- Background music: Lo-fi, 80-100 BPM, royalty-free
- Suggested sources: Uppbeat.io, YouTube Audio Library
- Volume: 20% (ambient, not intrusive)

---

## 📝 RECORDING SCRIPT (8 BEATS, 90 SECONDS)

### Beat 1: Cold open (0:00 → 0:06)
**On screen:** 3-node security lab, green status, traffic animation  
**Caption:** "A real network lab. Running in your browser. Right now."  
**Cursor:** Stationary

### Beat 2: Name + frame (0:06 → 0:12)
**On screen:** OmniLab wordmark animates in  
**Caption:** "OmniLab — self-hosted lab platform for networking, security, DevOps, and AI/ML."  
**Cursor:** Stationary

### Beat 3: Open console (0:12 → 0:24)
**Action:** Right-click Kali node → "Open console" → terminal slides in  
**Auto-type:** `ip a` command at 5 chars/sec  
**Caption:** "Every node is a real VM. SSH, root, kernel, the works — directly in your browser."

### Beat 4: Drag-drop node (0:24 → 0:38)
**Action:** Cut to empty lab → drag Suricata from palette → connect to Kali → node turns green  
**Caption 1 (0:25-0:31):** "Drag, drop, deploy."  
**Caption 2 (0:32-0:38):** "Backed by real KVM/QEMU. No Docker shortcuts, no toys."

### Beat 5: CLI demo (0:38 → 0:50)
**On screen:** PIP terminal bottom-right  
**Type (real keystrokes):** `omnilab deploy pentest-lab`  
**Caption:** "Or skip the GUI. Deploy from CLI. Ansible-ready."

### Beat 6: Template gallery (0:50 → 1:06)
**On screen:** Template gallery page, scroll through 10 templates  
**Hover:** Pentest Lab, Wazuh SOC, Threat Hunting, K8s, VyOS Routing  
**Caption 1 (0:50-0:58):** "10 ready-to-go labs: pen-testing, threat hunting, SOC simulation, K8s, routing, ML pipelines."  
**Caption 2 (0:59-1:06):** "Or build your own. Import from Terraform, EVE-NG, GNS3."

### Beat 7: Fast-forward (1:06 → 1:18)
**On screen:** Time-lapse of 3 labs being deployed in parallel (2x speed)  
**Overlay:** Animated progress bars, node statuses flipping to green  
**Caption:** "Multi-lab environments. One command. 30 seconds from idea to running topology."

### Beat 8: CTA (1:18 → 1:30)
**On screen:** Black screen, white text fades in  
**Text:**
```
OmniLab
github.com/hbrowder/omnilab

Free for personal use. Self-hosted. No cloud lock-in.
```
**Music:** Fade out over last 3 seconds

---

## 🎞️ POST-PRODUCTION WORKFLOW

### Editing timeline (DaVinci Resolve / Final Cut / Premiere)

1. **Import raw clips** (8 beats, ~5-10 min total footage)
2. **Cut to 90 seconds** (trim pauses, speed up slow parts to 1.5-2x)
3. **Add captions** from docs/demo-assets/captions/omnilab-90.srt
   - Font: Inter or SF Pro Display, 24pt
   - Color: White text on 70% opacity black bar
   - Position: Bottom center, 60px from edge
4. **Add background music** (lo-fi track, 20% volume)
5. **Color grade** (optional): slight contrast boost, saturation +5%
6. **Export settings:**
   - Format: H.264 (mp4)
   - Resolution: 1920×1080
   - Frame rate: 60 FPS
   - Bitrate: 10 Mbps (higher for upload, platforms re-encode anyway)

### Upload checklist

**YouTube (unlisted for embedding):**
- Title: "OmniLab — Self-Hosted Network Lab Platform (90s Demo)"
- Description: Full feature list + link to GitHub
- Tags: networking, security, devops, self-hosted, open-source
- Thumbnail: Frame from Beat 3 (console open, topology visible)

**Direct hosting (for Product Hunt / landing page):**
- Upload to: Cloudflare R2 or S3
- CDN URL: https://cdn.getomnilab.com/demo-v1.0.mp4
- Fallback: GitHub Releases asset

---

## ⏱️ TIME ESTIMATES

| Task | Time | Notes |
|------|------|-------|
| Tag v1.0.0-rc.1 | 2 min | Git tag + push |
| Import seed labs | 5 min | 3 curl commands |
| Clean Chrome setup | 5 min | Profile + window config |
| OBS configuration | 10 min | Settings + test recording |
| **Recording session** | **60 min** | 8 beats × 3-5 takes each = 30 min raw, 30 min retakes |
| **Editing in NLE** | **2.5 hours** | Cut, captions, music, color, export |
| YouTube upload | 15 min | Metadata + thumbnail |
| Embed in README | 5 min | Markdown + commit |
| **TOTAL** | **~4 hours** | Single-session workflow |

---

## 📋 MANUAL STEPS (HAROLD'S WORK)

1. **Tag v1.0.0-rc.1** (2 min)
   - Run the git tag command above
   - Verify tag pushed to GitHub

2. **Import seed labs** (5 min)
   - Run 3 curl commands
   - Verify labs appear in dashboard

3. **Record raw clips** (60 min)
   - Follow 8-beat script
   - Multiple takes per beat
   - Save raw clips to ~/omnilab-demo-raw/

4. **Edit in NLE** (2.5 hours)
   - Cut to 90 seconds
   - Add captions from .srt file
   - Add background music
   - Export final mp4

5. **Upload to YouTube** (15 min)
   - Unlisted video
   - Copy embed URL

6. **Embed in README** (5 min)
   - Add YouTube embed at top of README
   - Commit + push

---

## 🚀 AFTER VIDEO IS LIVE

**Linear update:**
- Post comment with YouTube URL + verification
- Move CRE-26 to Done

**Unblock launch tasks:**
- CRE-27 (beta recruitment) — now has demo video to share
- CRE-24 (Product Hunt) — video field ready
- CRE-25 (Show HN) — embed in post

**GitHub README:**
- Hero section gets `[![Demo Video](thumbnail.jpg)](https://youtube.com/...)`
- Becomes the first thing visitors see

---

## 💡 PRODUCTION TIPS

**From the script (docs/DEMO_VIDEO.md):**

1. **Cold-open on working product, not logo**
   - First 3 seconds decide if they finish
   - Show value before saying your name

2. **Skip the install in video**
   - Install pain is feature in writing, not video
   - Start with "already installed"

3. **One lab walkthrough, not a tour**
   - Show security lab end-to-end
   - Name-drop other types on-screen (1.5s each)

4. **Mouse-only for cool moments**
   - Drag-drop looks magical
   - Typing looks like work
   - Reserve keystrokes for CLI speed demo

5. **No voiceover**
   - Ships faster (no studio, no script reading)
   - Plays anywhere (autoplay-muted Twitter/LinkedIn)
   - Re-edits are free (just change captions)

6. **End on single CTA**
   - "github.com/hbrowder/omnilab" for 3 seconds
   - Not "star us, follow us, join Discord..."

---

## ✅ READY STATE

**Harold, you're cleared for recording. The checklist above has:**
- Tag command (copy-paste ready)
- Seed lab imports (3 curl commands)
- OBS settings
- 8-beat script with exact timings
- Post-production workflow
- Upload instructions

**Next move after you finish:**
1. Upload video to YouTube (unlisted)
2. Grab embed URL
3. I'll update README + close CRE-26
4. Then we move to CRE-27 (beta) or launch tasks

**Estimated single-session time: 4 hours (record + edit + upload)**

Let me know when you're done or if you need me to adjust the script/checklist. 🎬
