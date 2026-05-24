# OmniLab Professional Cookbook
## The Complete Guide to Network Emulation with OmniLab

**Version:** 1.0.0-DRAFT  
**Target Release:** Q3 2026  
**Last Updated:** 2026-05-24

---

## Document Status

**DRAFT IN PROGRESS** — This is the outline/skeleton for OmniLab's comprehensive documentation. Each chapter will be expanded as features are implemented and validated.

**Inspiration:** EVE-NG Professional Edition Cookbook (280 pages) — the gold standard for network emulation documentation.

**OmniLab's Differentiation:**
- Modern web-first architecture (no thick client required)
- Simplified installation (Docker Compose vs manual ISO setup)
- Real-time collaboration features (coming v2.0)
- AI-powered assistance (config generation, troubleshooting)
- Cloud-native design (Kubernetes-ready)

---

## Table of Contents

### Part I: Getting Started

#### Chapter 1: Introduction to OmniLab
**Status:** ⬜ Not Started | **Pages:** ~10 | **Priority:** Must-Have

**Sections:**
- 1.1 What is OmniLab?
- 1.2 Use Cases
  - Network certification labs (CCNA, CCNP, CCIE)
  - Pre-production testing
  - Customer demos
  - Training and education
  - Security research
- 1.3 OmniLab vs EVE-NG vs GNS3
  - Feature comparison matrix
  - Performance benchmarks
  - Pricing models
- 1.4 Architecture Overview
  - Frontend (React 18 + Vite)
  - Backend (FastAPI + async/await)
  - Database (SQLite for labs, PostgreSQL for production)
  - Network layer (Linux bridges, Open vSwitch)
- 1.5 Licensing Models
  - Community Edition (free, 3 users, 50 nodes max)
  - Professional Edition ($99/year, unlimited users, API access)
  - Enterprise Edition ($499/year, multi-host clusters, LDAP, support)

#### Chapter 2: System Requirements
**Status:** ⬜ Not Started | **Pages:** ~8 | **Priority:** Must-Have

**Sections:**
- 2.1 Hardware Requirements
  - Minimum specs (4 cores, 16GB RAM, 100GB SSD)
  - Recommended specs (16 cores, 64GB RAM, 500GB NVMe)
  - Enterprise specs (32+ cores, 128GB+ RAM, 1TB+ NVMe)
  - CPU requirements (VT-x/EPT for Intel, AMD-V for AMD)
  - Storage IOPS guidelines
- 2.2 Software Requirements
  - OS support (Ubuntu 22.04 LTS recommended, Debian 12)
  - Docker 24.0+
  - Docker Compose 2.20+
  - Kernel modules (KVM, vhost_net, tun/tap)
- 2.3 Network Requirements
  - Management port (HTTPS 443, SSH 22)
  - Console ports (WebSocket 5000)
  - Internet access for image downloads
  - Firewall rules
- 2.4 Browser Requirements
  - Chrome/Edge 90+ (recommended)
  - Firefox 88+
  - Safari 14+
- 2.5 Capacity Planning
  - Nodes per CPU core guideline (2-4 routers per core)
  - RAM per node estimates (Cisco: 1-2GB, Juniper: 4GB, Linux: 512MB)
  - Storage per lab estimates (10-50GB typical)

#### Chapter 3: Installation & Setup
**Status:** ⬜ Not Started | **Pages:** ~15 | **Priority:** Must-Have

**Sections:**
- 3.1 Pre-Installation Checklist
- 3.2 Docker Compose Installation (Recommended)
  - Clone repository
  - Configure .env file
  - docker-compose up -d
  - Initial startup validation
- 3.3 Manual Installation (Advanced)
  - Backend installation (Python venv)
  - Frontend build (npm/vite)
  - Reverse proxy setup (Nginx)
  - Systemd service configuration
- 3.4 First Login & Admin Setup
  - Default credentials (change immediately!)
  - First Run Wizard walkthrough
  - SSL certificate installation
  - Email/notification configuration
- 3.5 Post-Installation Hardening
  - Change default passwords
  - Enable firewall
  - Configure backups
  - Set up monitoring

---

### Part II: Core Concepts

#### Chapter 4: Labs & Topologies
**Status:** ⬜ Not Started | **Pages:** ~20 | **Priority:** Must-Have

**Sections:**
- 4.1 Understanding Labs
  - Lab lifecycle (create, start, stop, delete)
  - Lab metadata (name, description, tags)
  - Lab templates vs instances
- 4.2 Creating Your First Lab
  - New lab wizard
  - Naming conventions
  - Lab settings (resource limits, network mode)
- 4.3 Topology Canvas Basics
  - Drag-and-drop interface
  - Node placement
  - Link drawing
  - Zoom/pan controls
  - Grid snap
- 4.4 Canvas Tools
  - Select/move tool
  - Link tool
  - Delete tool
  - Annotation tool (text labels, shapes)
- 4.5 Saving & Versioning Labs
  - Auto-save behavior
  - Manual save checkpoints
  - Version history (coming v1.1)

#### Chapter 5: Nodes
**Status:** ⬜ Not Started | **Pages:** ~25 | **Priority:** Must-Have

**Sections:**
- 5.1 Node Types
  - Routers (Cisco, Juniper, Arista, Mikrotik)
  - Switches (Cisco, Aruba, Cumulus)
  - Firewalls (pfSense, Fortinet, Palo Alto)
  - Servers (Linux, Windows, FreeBSD)
  - Docker containers (coming v1.1)
- 5.2 Adding Nodes to Labs
  - Node palette
  - Template selection
  - Node configuration wizard
- 5.3 Node Configuration
  - CPU allocation (cores, pinning)
  - RAM allocation (MB/GB)
  - Disk size and type (qcow2, raw)
  - Network interfaces (count, type)
  - Console type (telnet, SSH, VNC, RDP)
  - Boot order
  - Startup delay
- 5.4 Node Lifecycle
  - Start/stop individual nodes
  - Suspend/resume (save RAM state)
  - Clone nodes
  - Delete nodes
- 5.5 Resource Limits
  - Per-node CPU throttling
  - QoS controls (coming v1.1)
  - Preventing resource starvation

#### Chapter 6: Network Objects
**Status:** ⬜ Not Started | **Pages:** ~18 | **Priority:** Must-Have

**Sections:**
- 6.1 Network Types Overview
  - Bridge networks (isolated L2)
  - NAT networks (internet access) [CRE-56]
  - Cloud networks (multi-lab connectivity) [v1.2]
  - Physical NIC passthrough (pnet) [v1.2]
- 6.2 Bridge Networks
  - Creating bridges
  - Connecting nodes to bridges
  - Bridge naming conventions
  - VLANs on bridges (coming v1.1)
- 6.3 NAT Networks [CRE-56]
  - NAT network wizard
  - DHCP configuration
  - DNS servers
  - Port forwarding rules
  - Subnet isolation
- 6.4 Link Configuration
  - Link bandwidth limits (Mbps)
  - Link latency simulation (ms delay)
  - Packet loss injection (%)
  - Link labels and annotations
- 6.5 Advanced Networking
  - Open vSwitch integration [v1.2]
  - Network namespaces [v1.2]
  - SR-IOV passthrough [Enterprise]

---

### Part III: Operations

#### Chapter 7: Console Access
**Status:** ⬜ Not Started | **Pages:** ~12 | **Priority:** Must-Have

**Sections:**
- 7.1 Console Types
  - Telnet (text-based CLI)
  - SSH (encrypted CLI)
  - VNC (graphical desktop)
  - RDP (Windows Remote Desktop)
- 7.2 Web Console (xterm.js)
  - Opening consoles
  - Multiple console tabs
  - Copy/paste handling
  - Terminal settings (font, colors)
- 7.3 Native Console Clients [v1.1]
  - telnet:// protocol handlers
  - PuTTY integration (Windows)
  - Terminal.app integration (macOS)
  - GNOME Terminal integration (Linux)
- 7.4 Console Tips & Tricks
  - Shared clipboard
  - Console history
  - Console logging to file

#### Chapter 8: Lab Management
**Status:** ⬜ Not Started | **Pages:** ~15 | **Priority:** Must-Have

**Sections:**
- 8.1 Starting & Stopping Labs
  - Start all nodes
  - Start nodes in order (dependency chains)
  - Stop gracefully vs force stop
  - Startup scripts (coming v1.1)
- 8.2 Lab Import/Export [CRE-54]
  - Export lab as JSON
  - Export lab as ZIP (with images)
  - Import lab from file
  - Handling duplicate names
- 8.3 Lab Templates
  - Saving labs as templates
  - Template library
  - Instantiating from templates
- 8.4 Lab Collaboration [v2.0]
  - Sharing labs with users
  - Read-only vs edit permissions
  - Real-time multi-user editing

#### Chapter 9: Templates & Images [CRE-55]
**Status:** ⬜ Not Started | **Pages:** ~20 | **Priority:** Must-Have

**Sections:**
- 9.1 Understanding Templates
  - Template metadata (vendor, category, version)
  - Default resource settings
  - Console configuration
  - Icon/logo
- 9.2 Built-in Templates
  - Cisco IOSv / IOSvL2 / IOS-XE / IOS-XR
  - Juniper vMX / vQFX / vSRX
  - Arista vEOS / cEOS
  - Mikrotik CHR
  - Linux (Ubuntu, CentOS, Alpine)
- 9.3 Uploading Custom Images
  - Image upload wizard
  - Supported formats (qcow2, vmdk, ova)
  - Image conversion (qemu-img)
  - Image optimization (compression, thin provisioning)
- 9.4 Template Versioning
  - Multiple versions per vendor/model
  - Default version selection
  - Version comparison
- 9.5 Template Visibility
  - Hiding unprovisioned templates
  - Per-user template access (Enterprise)

---

### Part IV: Advanced Features

#### Chapter 10: Packet Capture & Analysis [CRE-57]
**Status:** ⬜ Not Started | **Pages:** ~10 | **Priority:** Must-Have

**Sections:**
- 10.1 Starting a Capture
  - Right-click link menu
  - Capture filters (BPF syntax)
  - Capture duration limits
- 10.2 Viewing Captures
  - Download PCAP files
  - Opening in Wireshark
  - Built-in packet viewer [v1.2]
- 10.3 Advanced Capture Features [v1.2]
  - Live streaming (WebSocket)
  - Ring buffer mode (last N MB)
  - Scheduled captures (cron)

#### Chapter 11: User Management [CRE-53]
**Status:** ⬜ Not Started | **Pages:** ~15 | **Priority:** Must-Have v1.1

**Sections:**
- 11.1 User Roles
  - Admin (full system access)
  - Power User (create/edit own labs)
  - Read-Only (view labs, no changes)
- 11.2 Creating Users
  - User creation wizard
  - Password policies
  - Email verification
- 11.3 Authentication Methods
  - Local (username/password) [v1.1]
  - LDAP/Active Directory [v1.2]
  - RADIUS [v1.2]
  - OAuth/SAML SSO [v2.0]
- 11.4 User Sessions
  - Session timeout
  - Concurrent session limits
  - Force logout

#### Chapter 12: Backup & Recovery
**Status:** ⬜ Not Started | **Pages:** ~12 | **Priority:** Should-Have v1.1

**Sections:**
- 12.1 Backup Strategies
  - Full system backup (Docker volumes)
  - Lab-only backup (SQLite + configs)
  - Template/image backup
- 12.2 Automated Backups
  - Schedule configuration (daily, weekly)
  - Backup retention policies (keep last N)
  - Backup destinations (local, S3, SFTP)
- 12.3 Restore Procedures
  - Restore single lab
  - Restore entire system
  - Disaster recovery testing

#### Chapter 13: Monitoring & Health
**Status:** ⬜ Not Started | **Pages:** ~10 | **Priority:** Should-Have v1.1

**Sections:**
- 13.1 Health Dashboard
  - System status overview
  - CPU/RAM/disk usage
  - Active nodes count
  - WebSocket connections
  - API latency metrics
- 13.2 Network Health
  - Bridge status
  - Interface statistics (up/down)
  - Active links count
- 13.3 Alerting [v1.2]
  - Email notifications
  - Slack/Discord webhooks
  - Alert thresholds (CPU > 90%, disk < 10GB)

#### Chapter 14: API Reference
**Status:** ⬜ Not Started | **Pages:** ~30 | **Priority:** Should-Have v1.1

**Sections:**
- 14.1 Authentication
  - API key generation
  - JWT token authentication
  - Rate limits
- 14.2 Labs API
  - GET /api/labs (list)
  - POST /api/labs (create)
  - GET /api/labs/{id} (detail)
  - PUT /api/labs/{id} (update)
  - DELETE /api/labs/{id} (delete)
  - POST /api/labs/{id}/start (start lab)
  - POST /api/labs/{id}/stop (stop lab)
- 14.3 Nodes API
  - POST /api/labs/{id}/nodes (add node)
  - PUT /api/nodes/{id} (update node)
  - DELETE /api/nodes/{id} (delete node)
  - POST /api/nodes/{id}/start (start node)
  - POST /api/nodes/{id}/stop (stop node)
- 14.4 Networks API
  - POST /api/networks (create network)
  - GET /api/networks (list networks)
  - DELETE /api/networks/{id} (delete network)
- 14.5 Templates API
  - GET /api/templates (list templates)
  - POST /api/templates (upload template)
- 14.6 Health API
  - GET /api/health (system status)
  - GET /api/health/metrics (Prometheus metrics)

---

### Part V: Enterprise Features [v1.1+]

#### Chapter 15: Cluster Architecture [v1.2]
**Status:** ⬜ Not Started | **Pages:** ~25 | **Priority:** Nice-to-Have v1.2+

**Sections:**
- 15.1 Master + Satellite Design
- 15.2 Cluster Setup
- 15.3 Node Placement Policies
- 15.4 Load Balancing
- 15.5 Failover & HA

#### Chapter 16: Docker Container Support [v1.1]
**Status:** ⬜ Not Started | **Pages:** ~15 | **Priority:** Should-Have v1.1

**Sections:**
- 16.1 Docker Node Type
- 16.2 Container Images
  - Arista cEOS
  - Cisco XRd (IOS-XR Docker)
  - Nokia SR Linux
  - Custom Dockerfiles
- 16.3 Container Networking
- 16.4 Resource Limits (cgroups)

#### Chapter 17: Licensing & Billing [CRE-52]
**Status:** ⬜ Not Started | **Pages:** ~8 | **Priority:** Should-Have v1.1

**Sections:**
- 17.1 License Types
- 17.2 License Enforcement
- 17.3 Billing Integration (Stripe)
- 17.4 Usage Reporting

---

### Part VI: Tutorials & Examples

#### Chapter 18: Hands-On Labs
**Status:** ⬜ Not Started | **Pages:** ~40 | **Priority:** Nice-to-Have v1.0+

**Sections:**
- 18.1 Lab 1: Basic Router Configuration (Cisco)
  - Topology diagram
  - Step-by-step commands
  - Verification steps
- 18.2 Lab 2: OSPF Routing (Multi-Vendor)
  - Cisco + Juniper + Arista
  - Interoperability testing
- 18.3 Lab 3: BGP Internet Edge
  - Dual-homed ISP setup
  - BGP route filtering
  - Failover scenarios
- 18.4 Lab 4: VLAN Trunking & Switching
  - 802.1Q trunks
  - VTP (if applicable)
  - Spanning tree
- 18.5 Lab 5: MPLS VPN (Service Provider)
  - PE-CE routing
  - Label distribution
  - VRF configuration
- 18.6 Lab 6: Firewall & NAT (pfSense)
  - Internet gateway
  - Port forwarding
  - IDS/IPS
- 18.7 Lab 7: Linux Server Automation (Ansible)
  - Docker container nodes
  - Ansible playbooks
  - Configuration management

#### Chapter 19: Certification Prep Topologies
**Status:** ⬜ Not Started | **Pages:** ~20 | **Priority:** Nice-to-Have v1.0+

**Sections:**
- 19.1 CCNA Lab Topologies (10 examples)
- 19.2 CCNP Enterprise Lab Topologies (5 examples)
- 19.3 CCNP Security Lab Topologies (5 examples)
- 19.4 CCIE Lab Topologies (3 examples)
- 19.5 Juniper JNCIA/JNCIP Lab Topologies

---

### Part VII: Troubleshooting & FAQ

#### Chapter 20: Troubleshooting
**Status:** ⬜ Not Started | **Pages:** ~20 | **Priority:** Should-Have v1.0

**Sections:**
- 20.1 Common Issues
  - Nodes won't start (VT-x not enabled)
  - Console won't connect (port conflicts)
  - Network not working (bridge issues)
  - Low performance (insufficient resources)
- 20.2 Log Files
  - Backend logs (backend/logs/)
  - Frontend logs (browser console)
  - Docker logs (docker logs omnilab-backend)
  - System logs (dmesg, journalctl)
- 20.3 Debug Mode
  - Enabling debug logging
  - Verbose API output
  - Network diagnostics
- 20.4 Support Channels
  - GitHub Issues
  - Discord community
  - Email support (Enterprise)

#### Chapter 21: FAQ
**Status:** ⬜ Not Started | **Pages:** ~10 | **Priority:** Should-Have v1.0

**Sections:**
- 21.1 General Questions
- 21.2 Performance Questions
- 21.3 Licensing Questions
- 21.4 Compatibility Questions
- 21.5 Feature Requests

---

### Part VIII: Appendices

#### Appendix A: Supported Vendors & Images
**Status:** ⬜ Not Started | **Pages:** ~15 | **Priority:** Should-Have v1.0

- A.1 Cisco (IOSv, IOSvL2, IOS-XE, IOS-XR, ASA, FTD)
- A.2 Juniper (vMX, vQFX, vSRX, vEX)
- A.3 Arista (vEOS, cEOS)
- A.4 Mikrotik (CHR)
- A.5 Palo Alto (VM-Series)
- A.6 Fortinet (FortiGate VM)
- A.7 pfSense / OPNsense
- A.8 Linux Distributions (Ubuntu, CentOS, Alpine, Debian)
- A.9 Windows Server
- A.10 FreeBSD

#### Appendix B: Keyboard Shortcuts
**Status:** ⬜ Not Started | **Pages:** ~2 | **Priority:** Nice-to-Have

- Canvas shortcuts (Ctrl+D duplicate, Del delete, etc.)
- Console shortcuts (Ctrl+Shift+C copy, Ctrl+Shift+V paste)

#### Appendix C: Configuration File Reference
**Status:** ⬜ Not Started | **Pages:** ~5 | **Priority:** Should-Have v1.1

- .env file options
- docker-compose.yml customization
- config/backend.yaml (coming v1.1)

#### Appendix D: Security Best Practices
**Status:** ⬜ Not Started | **Pages:** ~8 | **Priority:** Should-Have v1.0

- Firewall rules
- SSL/TLS configuration
- Password policies
- Network segmentation

#### Appendix E: Contributing to OmniLab
**Status:** ⬜ Not Started | **Pages:** ~5 | **Priority:** Nice-to-Have

- GitHub workflow
- Code standards
- Pull request process
- Issue reporting

---

## Glossary
**Status:** ⬜ Not Started | **Pages:** ~5 | **Priority:** Should-Have v1.0

- Terms (Bridge, NAT, Template, Node, Lab, Console, etc.)

---

## Index
**Status:** ⬜ Not Started | **Pages:** ~10 | **Priority:** Must-Have v1.0 (final)

---

## Estimated Page Counts by Priority

| Priority | Pages | Chapters |
|----------|-------|----------|
| **Must-Have v1.0** | ~150 | Chapters 1-9, 18 (1 lab), 20-21, Appendix A, D |
| **Should-Have v1.1** | ~80 | Chapters 10-14, 16-17, Appendix C |
| **Nice-to-Have v1.2+** | ~50 | Chapters 15, 19, Appendix B, E |
| **Total** | **~280** | 21 chapters + 5 appendices |

---

## Writing Roadmap

### Phase 1: MVP Chapters (v1.0 Launch)
**Target:** 100 pages by v1.0 release

**Immediate (Week 1-2):**
1. Chapter 1 (Introduction)
2. Chapter 2 (System Requirements)
3. Chapter 3 (Installation)
4. Chapter 4 (Labs & Topologies)

**Short-term (Week 3-4):**
5. Chapter 5 (Nodes)
6. Chapter 6 (Network Objects - Bridge only)
7. Chapter 7 (Console Access)
8. Chapter 20 (Troubleshooting basics)

**Before v1.0 Launch:**
9. Chapter 18.1 (One complete hands-on lab)
10. Appendix A (Supported images list)
11. Glossary
12. Index

### Phase 2: Enterprise Chapters (v1.1)
**Target:** +80 pages

1. Chapter 8 (Lab Management + Import/Export)
2. Chapter 9 (Templates & Images)
3. Chapter 10 (Packet Capture)
4. Chapter 11 (User Management)
5. Chapter 12 (Backup & Recovery)
6. Chapter 14 (API Reference)
7. Chapter 16 (Docker Support)

### Phase 3: Advanced Chapters (v1.2+)
**Target:** +50 pages

1. Chapter 13 (Monitoring)
2. Chapter 15 (Cluster Architecture)
3. Chapter 17 (Licensing & Billing)
4. Chapter 18.2-18.7 (Additional labs)
5. Chapter 19 (Certification topologies)

---

## Content Style Guide

### Voice & Tone
- **Professional but approachable** — not dry academic, not chatty startup
- **Clear and direct** — assume networking knowledge, don't over-explain basics
- **Action-oriented** — use imperative mood ("Click Save", not "You should click Save")

### Conventions
- **Code/commands** — Use monospace `like this` inline, code blocks for multi-line
- **UI elements** — Bold for buttons/menus: **Click Save**
- **File paths** — Monospace: `~/omnilab/backend/main.py`
- **Screenshots** — Annotate with red arrows/boxes, include descriptive captions
- **Notes/Warnings** — Use callout boxes:
  ```
  ⚠️ **Warning:** This will delete all labs permanently.
  ```
  ```
  💡 **Tip:** Use Ctrl+D to duplicate a selected node.
  ```

### Technical Standards
- **OS references** — Default to Ubuntu 22.04 LTS (mention Debian/RHEL alternatives in footnotes)
- **Browser references** — Default to Chrome (mention Firefox/Safari support)
- **Version numbers** — Always specify versions (Docker 24.0+, not "recent Docker")
- **Command examples** — Include full commands with expected output

---

## Contributing to the Cookbook

**Current Status:** DRAFT OUTLINE (2026-05-24)

As features are implemented, corresponding cookbook chapters should be written by:
1. Feature developer (initial draft)
2. Technical writer (polish & screenshots)
3. QA/Beta tester (validation)

**Issue Tracking:** Each cookbook chapter should have a Linear issue (e.g., CRE-XX: Write Chapter 3 - Installation)

**Storage:** Markdown source in `~/omnilab/docs/cookbook/` directory, PDF/HTML export via Pandoc or mdBook

---

**END OF OUTLINE**

**Next Steps:**
1. ✅ Create this outline
2. ⬜ Create Linear issue for "Write OmniLab Cookbook - Phase 1 MVP Chapters"
3. ⬜ Set up docs/ directory structure in repo
4. ⬜ Choose documentation toolchain (mdBook, Docusaurus, or Pandoc)
5. ⬜ Write Chapter 1 (Introduction) as proof of concept
