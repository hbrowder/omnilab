# AI Lab Builder — 90-Second Demo Script (CRE-48 / AILB-8)

A recordable, shot-by-shot script for the AI Lab Builder launch video. Total
target: **90 seconds**. Prompts are written to be typed *verbatim* — they are the
same prompts validated in `tests/agent_scenarios.json`.

## Before you record

- [ ] Backend running (`~/start-omnilab.sh`) and frontend bundle built
      (`cd frontend && npm run build`).
- [ ] An AI provider is configured in **Settings → AI Lab Builder** (OpenRouter
      key works; the demo uses `anthropic/claude-sonnet-4.5`).
- [ ] Pre-pull the headline image so node start is instant on camera:
      `docker pull frrouting/frr:latest` (already local in dev).
- [ ] Start from an empty `/labs` view (delete demo clutter first).
- [ ] Window at 1280×720+; browser zoom 100%; hide bookmarks bar.

---

## Shot list

### 0:00–0:10 — Hook
**On screen:** `/labs`, empty. Cursor moves to the **✨ Build with AI** button.
**VO:** "Building a network lab usually means dragging nodes, wiring links, and
hand-writing configs. In OmniLab, you just describe it."

### 0:10–0:20 — The prompt
**Action:** Click **✨ Build with AI**. In the prompt box, type **verbatim**:

> Build me an OSPF lab with 4 FRR routers. Put r1 and r2 in area 0 (the
> backbone) and r3 and r4 in area 1. Chain them r1-r2-r3-r4, push a basic OSPF
> startup config to each, and start them so the hellos can come up.

Press **Send**.
**VO:** "Tell it what you want — here, a four-router OSPF lab split across two
areas."

### 0:20–0:55 — Watch it build (the money shot)
**On screen:** The streaming activity log fills in live:
`🔧 create_lab` → `🔧 create_node r1 (frrouting/frr)` ×4 → `🔧 link_nodes`
r1-r2-r3-r4 → `🔧 push_config` (OSPF) ×4 → `🔧 start_node` ×4, each flipping to a
green ✅.
**Highlight:** Hover the collapsible **"thinking"** section once to show the
agent's reasoning. Point out the running token/▢ counters.
**VO:** "Behind the scenes the agent calls the exact same tools the UI does —
create the lab, add the routers, link them, push the OSPF config, and boot them.
You see every step as it happens."

### 0:55–1:05 — Cancel control (trust)
**Action:** On the *next* example, start typing a second prompt and click the red
**⏹ Stop** button mid-build to show graceful cancel.
**VO:** "Anything looks wrong? One click stops it — and cleans up so nothing is
left running."

### 1:05–1:20 — Land on the canvas
**On screen:** The **done** event navigates to `/lab/<id>`; the ReactFlow canvas
shows r1–r4 wired in a chain, all green/running. Optionally open a console on r1
and run `show ip ospf neighbor` to show adjacencies forming.
**VO:** "When it's done, you're dropped right onto the canvas — a real, running
lab. OSPF neighbors are already coming up."

### 1:20–1:30 — Close
**On screen:** Settings → AI Lab Builder run history (last runs listed).
**VO:** "Bring your own key, every run is tracked, and you can re-run any build
in a click. That's the OmniLab AI Lab Builder."

---

## Alternate prompts (B-roll / variety)

Each is a validated scenario from `tests/agent_scenarios.json`:

| Scenario | Prompt to type |
|---|---|
| eBGP | "Create a BGP lab with two FRR routers, one in AS65001 and one in AS65002, connected by a single link. Configure an eBGP peering between them and start both routers." |
| Pentest | "Set up a pentest lab with a Kali Linux attacker connected to a DVWA vulnerable web target on the same network. Add a second DVWA box as an additional target. Start everything." |
| 3-tier campus | "Build a 3-tier campus topology: 2 core nodes, 2 distribution nodes, and 4 access nodes, wired core-to-distribution-to-access. No routing protocol needed, just the topology. Use ubuntu nodes." |
| k3s | "Build a 3-node Kubernetes cluster using k3s: one server node and two agent nodes, all on the same network. Start them." |
| Wazuh SOC | "Create a small SOC lab: one Wazuh manager and one Ubuntu Linux endpoint that will report to it, connected on the same network. Start both." |

## Recording tips

- The OSPF build (pre-pulled FRR) takes ~20–35s end to end — good real-time
  pacing. If pulls are cold, record with images pre-pulled or speed-ramp the
  pull segment.
- Capture the **green ✅ cascade** on the `start_node` calls; it reads as
  "it's really running," not a mockup.
- Keep the activity log visible the whole build — it *is* the product.
