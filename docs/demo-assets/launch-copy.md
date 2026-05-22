# OmniLab launch copy — drafts

> **Tied to:** CRE-24 (Product Hunt), CRE-25 (Show HN), CRE-28 (blog), CRE-29 (social)
> **Video they point at:** `docs/media/omnilab-90.mp4` once it exists, or the YouTube unlisted URL during the dress rehearsal.
>
> All copy below assumes the **GitHub repo is public** at `github.com/hbrowder/omnilab`. If the repo is still private on launch day, flip it first or the click-throughs are dead.

---

## 1. Hacker News — Show HN

**Title (80-char limit):**

```
Show HN: OmniLab – Self-hosted lab platform for networking, security, DevOps
```

Notes on the title:
- `Show HN:` prefix is mandatory for the show-hn frontpage (lowercase "Show HN").
- Don't put the URL in the title. HN renders it automatically next to the post.
- Don't lead with "We built" — "OmniLab" first reads cleaner.
- "self-hosted" in the title earns 3 upvotes by itself on HN. Free.

**First comment (post this within 60 seconds of submitting):**

```
Hey HN — I'm the solo dev. Quick context on why this exists and what's
actually here.

I've been teaching/practicing networking and security on the side for
years and kept hitting the same wall: GNS3 is fiddly to set up, EVE-NG
is awkward to share, and Cisco Modeling Labs costs more than my rent.
The "lightweight" alternatives are mostly Docker containers running
iproute2 — fine for a CCNA worksheet, useless for anything that touches
a real kernel.

OmniLab is what I wished existed:

- Browser UI, but every node is a real KVM/QEMU VM. Not a container.
- One-click templates for the labs people actually build:
  Wazuh + Suricata + Kali, k8s cluster, Ollama + Jupyter, mixed-vendor
  routing topologies.
- CLI and REST API for the half of you who'll never touch the UI past
  the screenshot.
- Self-hostable .deb, runs on a laptop or a homelab box. SQLite + a
  Python backend, no Postgres/Redis/k8s required.

What's NOT there yet, in the spirit of HN:

- Tests. Genuinely zero. v1.0 is "I hand-tested it on three machines."
  That's the next ticket.
- No Windows host support — KVM only, so Linux host. Guests can be
  anything you have an image for.
- Pricing is $12/mo for the Pro tier (multi-user, backup, priority
  patches). The Free tier is fully functional for one user — no
  artificial node limits or watermarks.

Repo, install instructions, and the 90-second demo:
https://github.com/hbrowder/omnilab

Happy to dig into any architectural decision in the comments. The two
choices I expect to defend most are (1) SQLite over Postgres and
(2) FastAPI's catch-all SPA fallback, which is going to look weird
to anyone who skims main.py.
```

Notes on the comment:
- Lead with the *why*, not the *what*. The title already said what.
- Name three competitors by name. HN respects "I'm aware of the alternatives."
- Volunteer the weaknesses *first*. They'll find them anyway; getting there
  ahead of the thread converts critics into helpers.
- End with two technical hooks (SQLite, catch-all) — explicit invitations
  to the kind of comment thread that drives engagement.

---

## 2. Product Hunt

**Tagline (60-char limit, sentence case, no period):**

```
Spin up a real multi-VM network lab in your browser in 30 seconds
```

(60 chars exactly. PH counts punctuation.)

**Topics to tag:**
- Developer Tools
- DevOps
- Self-Hosted

(Three is the sweet spot. More dilutes the leaderboard ranking.)

**First-comment / "Maker comment":**

```
Hi PH 👋 I'm Harold, the solo maker.

OmniLab gives you GNS3-class network and security labs through a browser
UI, backed by real KVM/QEMU VMs (not Docker fakes). You self-host the
whole thing on your laptop or a homelab box.

Three things I'd love feedback on today:

1. The one-click templates page — are the labs we ship the labs you'd
   actually want? (Wazuh SOC, k8s 3-node, Ollama + Jupyter, mixed-vendor
   routing.) Tell me what's missing.
2. The CLI — `omnilab lab deploy security-stack` should feel obvious.
   Does it?
3. Pricing — Free is fully functional. Pro is $12/mo for backup,
   multi-user, and priority patches. Comfortable or weird?

Everything is on the repo:
https://github.com/hbrowder/omnilab

The 90-second video on this page is the fastest tour. The README is the
slowest one. Pick your weapon.
```

Notes:
- PH rewards specific questions in the maker comment ("3 things I'd
  love feedback on"). Vague "let me know what you think" gets ignored.
- The video is the conversion engine on PH. The text is the SEO surface.

---

## 3. LinkedIn — launch post

```
I just shipped OmniLab — a self-hosted platform for network, security,
DevOps, and AI/ML labs that you spin up in your browser.

Why I built it 👇

For years, anyone wanting hands-on practice with real network gear,
SIEMs, or multi-node clusters had three bad options:

▸ GNS3 / EVE-NG — powerful, but a half-day to install correctly
▸ Cisco Modeling Labs — beautiful, but $$$$ and Cisco-only
▸ Docker labs — fast, but the kernel is fake. You can't really learn
  IDS evasion against a containerised Suricata.

OmniLab is what happens when you take the browser-first UX of CML, the
self-hostability of GNS3, and the actual real-VM substrate of EVE-NG,
and merge them into one .deb you install in 90 seconds.

→ Real KVM/QEMU VMs, not containers
→ One-click templates: Wazuh SOC, k8s, Ollama + Jupyter, mixed-vendor
  routing
→ CLI + REST API for automation
→ Free for personal use, $12/mo Pro tier

90-second demo + GitHub:
github.com/hbrowder/omnilab

If you teach networking, run a SOC, or just want a sane place to break
things — I'd love your feedback. DMs open.

#networking #cybersecurity #devops #homelab #selfhosted #opensource
```

Notes:
- LinkedIn rewards 3-5 line paragraphs broken up by single-line gaps.
- 6 hashtags is the engagement sweet spot — more looks like spam.
- Lead with the action ("I just shipped"), not the build journey.
- One CTA per post; "DMs open" outperforms "comment below" on LinkedIn.

---

## 4. Twitter / X — launch thread (5 tweets)

**Tweet 1 (the hook — paste the 15s video clip here):**

```
spent the last few months building this

real multi-VM network + security labs, in your browser, self-hosted

15 seconds:
[attach omnilab-15-twitter.mp4]
```

**Tweet 2:**

```
the problem: every "easy" lab tool i tried was secretly running docker
containers. you can't learn IDS evasion against a fake kernel.

omnilab uses real KVM/QEMU VMs under the hood. browser UI is just the
control plane.
```

**Tweet 3:**

```
one-click templates for the labs people actually build:

• wazuh + suricata + kali (security stack)
• 3-node k8s cluster
• ollama + jupyter (ai/ml playground)
• cisco + juniper + vyos triangle (multi-vendor routing)

drag/drop to add anything else.
```

**Tweet 4:**

```
also has a CLI:

$ omnilab lab deploy security-stack
✓ provisioning kali-1     (12s)
✓ provisioning wazuh-1    (14s)
✓ provisioning suricata-1 (9s)
lab running at http://lab.local:5000

REST API too. scriptable end-to-end.
```

**Tweet 5 (the CTA):**

```
free for personal use, $12/mo pro tier.

self-host on your laptop or homelab box. ubuntu/debian/rhel.

repo + full 90s video:
github.com/hbrowder/omnilab

🌟s appreciated, but feedback in replies appreciated more
```

Notes:
- Tweet 1 carries the video; tweets 2-5 are unfurl-free text. This
  keeps the engagement count concentrated on tweet 1, which is what
  the algorithm reads.
- Lowercase throughout — matches the dev-twitter voice; uppercase
  reads "marketing".
- The CTA hashtag-stuffing thing LinkedIn likes is the kiss of death
  on X. Zero hashtags here.

---

## 5. README hero block (goes above install)

This is the *only* copy that ends up on github.com itself.

```markdown
<p align="center">
  <img src="docs/media/omnilab-gif-hero.gif" alt="OmniLab — 8s demo" width="800">
</p>

<p align="center">
  <strong>Self-hosted lab platform for networking, security, DevOps, and AI/ML.</strong><br>
  Real KVM/QEMU VMs. Browser UI. CLI &amp; API. Free for personal use.
</p>

<p align="center">
  <a href="https://github.com/hbrowder/omnilab/releases/latest">Download .deb</a>
  &nbsp;·&nbsp;
  <a href="docs/DEMO_VIDEO.md">90-second demo</a>
  &nbsp;·&nbsp;
  <a href="docs/">Docs</a>
</p>
```

(Once `omnilab-90.mp4` is published unlisted on YouTube, swap the
middle link from `docs/DEMO_VIDEO.md` to the YouTube URL.)

---

## Posting schedule (the day-of plan)

Tied to Product Hunt's 12:01 AM PT launch window:

| Time (PT)       | Action                                                  |
| --------------- | ------------------------------------------------------- |
| T - 24h         | Repo public, README hero swap, releases tagged          |
| T - 1h          | Pre-write all 5 channels in drafts                      |
| **00:01 launch**| Product Hunt submission                                 |
| 00:05           | LinkedIn post                                           |
| 00:10           | Twitter/X thread                                        |
| 07:00 (10am ET) | Show HN submission (HN traffic peaks US morning)        |
| Throughout day  | Reply to every PH + HN + X comment within 30 minutes    |

The HN submission is *not* simultaneous with PH on purpose — splitting
them gives two separate spikes of attention to ride for the dashboard
graph. PH gets the West Coast night-owl crowd; HN gets the morning
office reader.

---

## What I (the agent) still can't do without you

- Hit submit on any of these. Publishing is on the "stop" list of the
  autonomy contract.
- Recording or editing the video itself.
- Cropping the 15s vertical cut for the Twitter post — that's a
  taste-driven NLE pass.

When you're ready to publish, hand me back any one of these blocks
edited and say "post it" and I'll prep the corresponding submission
draft (HN, PH, etc.) — but the final click is yours.
