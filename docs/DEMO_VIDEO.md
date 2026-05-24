# OmniLab Demo Video — Script & Production Plan

> **Tracking:** [CRE-26](https://linear.app/harold-browder/issue/CRE-26)
> **Target length:** 90 seconds (the HN/Product Hunt sweet spot — long enough to show value, short enough that people finish it)
> **Target audience:** technical buyers — network engineers, sec analysts, DevOps practitioners, instructors. They've seen GNS3/EVE-NG/Cisco Modeling Labs and want to know why they should care.
> **One-line pitch:** *"Spin up real, multi-node network and security labs in your browser in 30 seconds — self-hosted, free for personal use."*
> **Distribution targets:** GitHub README hero, Product Hunt video field, landing page hero, embedded in HN comment, looped silently on the social-media post (CRE-29).

---

## Strategic decisions baked into this script

1. **Cold-open on a working topology, not a logo.** The first 3 seconds decide whether someone finishes. We show product value before saying our name.
2. **Skip the install.** Do NOT spend 15 seconds on `sudo dpkg -i`. Cut to "already installed" — install pain is a *feature in writing*, not a *feature in video*. Mention it as a 1-second on-screen text card later.
3. **One labwalk, not a tour.** Don't try to show all 4 lab types. Show one (security — most viral on HN/Reddit) end-to-end. The other types are name-dropped on screen for 1.5s.
4. **Hands stay off the keyboard for the cool moments.** Mouse-only operations look magical; typing looks like work. Reserve keystrokes for the one place we want viewers to *feel* the speed (deploy command in the embedded terminal).
5. **No voiceover.** Subtitles + ambient lo-fi. Reasons: (a) ships faster, no studio, (b) plays anywhere autoplay-muted (Twitter, LinkedIn, HN preview), (c) avoids the "AI voice or bad-mic founder voice" tradeoff, (d) re-records are free (just re-edit captions).
6. **End on a single call to action.** "github.com/hbrowder/omnilab" on screen for the last 3 seconds. Not "star us, follow us, join Discord, sign up for the newsletter."

---

## Pre-production checklist

### Environment to record from
- [ ] **Clean Chrome profile** — no extensions, no bookmarks bar, no third-party tab favicons. People notice.
- [ ] **1920×1080 window**, browser zoomed to 100%, dev tools closed, OS notifications silenced (`Do Not Disturb`)
- [ ] **OmniLab built from `v1.0.0-rc.1` tag** (the one we just released) so the version badge in the corner matches the release URL we point at
- [ ] **Seed lab created and saved** in `~/.omnilab/labs/`: 1 Kali node, 1 Wazuh node, 1 Suricata IDS sensor, on a single OVS bridge. Pre-position the nodes on the canvas in an aesthetically pleasing triangle (Kali top-left, Wazuh top-right, Suricata bottom-center, lines drawn).
- [ ] **A second "empty" lab** also pre-created, for the drag-drop demo segment
- [ ] **Backend version stamp visible**: `/api/system/health` returns `{"version":"1.0.0-rc.1"}`

### Capture tools
- **OBS Studio** (free, cross-platform). Settings: 1080p60, CBR 8 Mbps, mp4 container.
- Or **macOS QuickTime + Cleanshot X** if you prefer; either is fine.
- Mouse cursor highlight enabled (yellow dot, ~30px) — viewers track the cursor much faster than the cursor itself
- Keyboard event overlay on for the terminal segment (Cleanshot has this built in; OBS uses an external plugin)

### Editing tools
- **DaVinci Resolve** (free) or **Final Cut** or **Premiere** — any NLE that supports keyframes
- **Music:** royalty-free lo-fi from Uppbeat.io or YouTube Audio Library. Suggested track: anything BPM 80-100, no vocals, mellow synth. *Specifically* avoid "epic dramatic build" tracks — they feel like a 2017 startup pitch.

---

## The script — 8 beats, 90 seconds total

Each beat below: timing, what's on screen, what the cursor does, what text overlays say. Captions appear as crisp white-on-black-bar at the bottom (not floating — bars are easier to read on noisy backgrounds).

---

### Beat 1 — Cold open (0:00 → 0:06)

**On screen:** OmniLab dashboard. The pre-saved 3-node security lab is rendered in the topology canvas, status indicators all green, faint animated traffic lines pulsing between nodes.

**Cursor:** stationary, off-canvas. Don't move it yet.

**Caption (appears at 0:01):** `A real network lab. Running in your browser. Right now.`

**Why this works:** No logo, no intro. The viewer is asking "what am I looking at?" — that question is the only thing that keeps them past 3 seconds. We answer it on beat 2.

---

### Beat 2 — Name + frame (0:06 → 0:12)

**On screen:** Same topology canvas. OmniLab wordmark animates in at the top-center (small, subtle — not a slide).

**Caption (replaces previous):** `OmniLab — self-hosted lab platform for networking, security, DevOps, and AI/ML.`

**Cursor:** still stationary.

---

### Beat 3 — The first interaction: open a node console (0:12 → 0:24)

**On screen:** Cursor moves to the Kali node, right-clicks → context menu appears → click "Open console."

A web-terminal slides in from the right side of the screen, occupying ~40% of the viewport. Topology stays visible on the left.

In the terminal, an `ip a` command auto-types at ~5 chars/sec (`pyautogui` or the editor — NOT real typing; we want a steady rhythm). The cursor stays still during this — viewer's eye is on the new content.

**Caption:** `Every node is a real VM. SSH, root, kernel, the works — directly in your browser.`

**Why this works:** This is the moment a competing tool like CML or EVE-NG charges $thousands for. Showing it for free, in-browser, in beat 3 is the entire pitch.

---

### Beat 4 — Drag-and-drop a new node (0:24 → 0:38)

**On screen:** Cut (hard cut, no transition) to the second pre-prepared lab — the empty one. Cursor drags a "Suricata" node from the left palette onto the canvas, then drags a connection line from the new Suricata node to the existing Kali. The node briefly pulses, then turns green ("Running").

**Caption (split across the beat):**
- 0:25 → 0:31: `Drag, drop, deploy.`
- 0:32 → 0:38: `Backed by real KVM/QEMU. No Docker shortcuts, no toys.`

**Why "no Docker shortcuts" matters:** Half our serious-engineer audience has been burned by tools that *say* they emulate a Cisco router and actually just run a Docker container with `iproute2`. State that we don't, on screen, with no equivocation.

---

### Beat 5 — Show the CLI for the keyboard-people (0:38 → 0:50)

**On screen:** Picture-in-picture: topology stays in the main view; a smaller terminal pane appears bottom-right. In that terminal, type (real keystrokes — *this* is the segment where typing sells the speed):

```
$ omnilab lab deploy security-stack
✓ provisioning kali-1     (12s)
✓ provisioning wazuh-1    (14s)
✓ provisioning suricata-1 (9s)
✓ wiring lab-net-0        (1s)
lab "security-stack" running at http://lab.local:5000/labs/3
```

Times appear with a slight stagger (~0.6s between lines) to imply parallelism but not too fast to read.

**Caption:** `Or skip the UI entirely. Full CLI. Full API. Your call.`

**Why this works:** Network/sec engineers will not adopt a tool that's GUI-only — it can't slot into their automation. Showing the CLI for 12 seconds reassures them without us saying "scriptable" (which everyone says).

---

### Beat 6 — The "what else" reel (0:50 → 1:06)

**On screen:** Fast cut sequence, ~2 seconds each, no captions on the visuals — just a single sticky caption.

- 2s — Network lab: Cisco + Juniper + VyOS routers in a triangle, OSPF adjacency animation
- 2s — DevOps lab: a Kubernetes 3-node cluster icon with `kubectl get nodes` ghosting in the corner
- 2s — AI/ML lab: an Ollama node + Jupyter node, a `curl` to the Ollama endpoint streaming a token-by-token reply
- 2s — Templates page: scroll through the "one-click lab templates" grid (10+ visible)

**Sticky caption (whole sequence):** `Networking. Security. DevOps. AI/ML. Real workloads. Real protocols.`

---

### Beat 7 — The install one-liner card (1:06 → 1:14)

**On screen:** Black card. Centered, monospace text appears one segment at a time:

```
$ wget https://github.com/hbrowder/omnilab/releases/latest/omnilab.deb
$ sudo dpkg -i omnilab.deb
$ omnilab start
→ http://your-server:5000
```

**Caption:** `Self-hosted. Ubuntu, Debian, RHEL. 90 seconds to running.`

**Why a card and not a screen-recording:** Recording an apt install is boring and slow. A typed card communicates "easy" in 8 seconds. The viewer who wants proof clicks through to the GitHub README.

---

### Beat 8 — Call to action (1:14 → 1:24)

**On screen:** Hero shot. OmniLab logo, the same security lab from beat 1 faintly in the background (low opacity), and at the bottom in large clean type:

```
github.com/hbrowder/omnilab
```

**Caption:** `Free for personal use. Pro tier $12/mo. Star the repo.`

Hold for 8 seconds. Yes, 8 seconds is "too long" for a CTA — but autoplay loops, social embeds, and people who paused to look at the URL all benefit. The music fades over the last 3 seconds.

---

## Production timeline (realistic)

| Phase                                  | Time     | Owner |
| -------------------------------------- | -------- | ----- |
| Pre-prep environment + seed labs       | 30 min   | you   |
| Record raw clips (1-3 takes per beat)  | 60 min   | you   |
| Rough cut in NLE                       | 90 min   | you   |
| Music + captions + color pass          | 60 min   | you   |
| Review + tweaks                        | 30 min   | you   |
| Export 1080p mp4 + 720p mp4 (Twitter)  | 10 min   | you   |
| **Total**                              | **~5 h** |       |

If you want me to: I can scaffold the seed-lab JSON files (`~/.omnilab/labs/security-stack.json` etc.) so step 1 of pre-prep is zero work for you. Just say "seed the labs."

---

## Common ways this video can fail (and how to avoid them)

1. **Recording at 30fps.** Modern viewers can tell. Lock OBS to 60fps.
2. **Doing the topology drag at human speed.** Looks sluggish on playback. Either record at normal speed and 1.5x in post, or use the editor's clip speed.
3. **The cursor disappears on the white canvas.** Mandatory: enable cursor highlight.
4. **Captions written like documentation.** ("OmniLab allows users to deploy multi-node topologies via a drag-and-drop interface.") Re-read every caption — would you screenshot and post it as a tweet? If not, rewrite shorter.
5. **The terminal output scrolls too fast to read.** Aim for ~1s per line minimum. Slow it down.
6. **Music with a vocal hook.** Viewer's brain processes the vocal instead of the visual. Strictly instrumental.
7. **Recording before tagging a release.** If the on-screen version says `1.0.0-rc.1` but the README install command says `1.0.0`, that's the comment everyone leaves. Tag, *then* record.

---

## Variants to export from the same master cut

| Variant       | Format    | Length | Purpose                                 |
| ------------- | --------- | ------ | --------------------------------------- |
| `omnilab-90.mp4`       | 1920×1080, 60fps | 1:24 | Master / landing / PH / GitHub README |
| `omnilab-90-720.mp4`   | 1280×720, 60fps  | 1:24 | Twitter / LinkedIn (file-size friendly) |
| `omnilab-30-loop.mp4`  | 1080×1080, no audio, loops | 0:30 | Embedded silent loop on landing hero |
| `omnilab-15-twitter.mp4` | 1280×720, 30fps | 0:15 | Cut down to beats 1+3+8 for tweet replies |
| `omnilab-gif-hero.gif` | 800×450, 12fps | 0:08 | GitHub README hero (under 5 MB) |

The 0:15 cut is the highest-leverage variant — it's what you'll post in every HN/Reddit/Twitter reply where the full video is too long for the medium.

---

## Prep status (updated 2026-05-24)

✅ **PREP COMPLETE — READY FOR RECORDING**

Agent-delivered assets (all committed to main):
- [x] Script (this file) — 230 lines, 8 beats, 90 seconds
- [x] Seed lab JSONs at `docs/demo-assets/seed-labs/{security-stack,empty,networking-triangle}.json`
- [x] SRT caption track at `docs/demo-assets/captions/omnilab-90.srt` (35 cues)
- [x] Launch copy drafts at `docs/demo-assets/launch-copy.md` (HN, PH, LinkedIn, X thread)
- [x] **Recording checklist** at `docs/CRE-26-RECORDING-CHECKLIST.md` (9,188 bytes)
  - Tag command (v1.0.0-rc.1, copy-paste ready)
  - Seed lab import commands (3 curl commands)
  - OBS Studio settings (1080p60, 8 Mbps CBR)
  - Complete 4-hour production timeline
  - Post-production workflow
  - Upload instructions

Current commit: `1e1f02d` (checklist pushed to main)  
Linear: CRE-26 updated with recording-ready comment

## What needs Harold (manual work)

**Estimated time: 4 hours (single-session workflow)**

1. **Tag v1.0.0-rc.1** (2 min) — git tag + push
2. **Import seed labs** (5 min) — 3 curl commands in checklist
3. **OBS setup** (10 min) — configure capture settings
4. **Record raw clips** (60 min) — 8 beats × 3-5 takes
5. **Edit in NLE** (2.5 hours) — cut, captions, music, color, export
6. **Upload to YouTube** (15 min) — unlisted, grab embed URL
7. **Post URL to Linear CRE-26** (2 min)

See `docs/CRE-26-RECORDING-CHECKLIST.md` for step-by-step commands.

---

## When recording is complete

Once the master cut exists and is uploaded to YouTube:

1. Harold posts YouTube URL to Linear CRE-26
2. Agent updates README.md with hero embed
3. Agent closes CRE-26 → Done
4. **Unblocked:** CRE-27 (beta recruitment), CRE-24 (Product Hunt), CRE-25 (Show HN)

Then launch tasks can proceed with demo video in hand.
