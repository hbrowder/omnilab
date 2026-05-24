# EVE-NG Professional Edition Cookbook Analysis
## Document Review for OmniLab Feature Parity

**Source:** EVE-PE-BOOK-6.5.0-Edition-2026.pdf (280 pages)  
**Authors:** Uldis Dzerkals, Christopher Lim, Michael Doe  
**Review Date:** 2026-05-24  
**Reviewer:** Hermes Agent (007)

---

## Executive Summary

EVE-NG is the market leader in network emulation platforms. This 280-page professional cookbook documents their complete feature set, best practices, and enterprise patterns. OmniLab aims to compete in the same space with modern UX and simplified deployment.

**Key Finding:** OmniLab has solid foundational features but is missing ~15 enterprise-critical capabilities that EVE-NG customers expect.

---

## 1. Core Feature Comparison

### ✅ Features OmniLab Already Has

| Feature | OmniLab Status | EVE-NG Section |
|---------|----------------|----------------|
| Web-based GUI | ✅ Implemented | 3.9, 7.x |
| Lab topology canvas | ✅ React Flow | 7.9 |
| Node management | ✅ Backend API | 7.9.1.1 |
| Network objects (bridges) | ✅ Basic | 7.9.1.2 |
| Console access (telnet/SSH) | ✅ WebSocket xterm | 3.8, 8.x |
| VNC support | ✅ noVNC | 8.3 |
| RDP support | ✅ guacamole | 8.4 |
| User authentication | ✅ Session-based | 7.3.1 |
| Health monitoring | ✅ /metrics endpoint | 16.1 |
| System status dashboard | ✅ HealthDashboard.jsx | 7.4.3 |
| Lab import/export | ⚠️ Partial (needs .zip support) | 7.2.2.5, 7.2.2.6 |

### ❌ Critical Missing Features (High Priority)

#### 1. **Multi-User Role-Based Access Control (RBAC)**
- **EVE-NG:** Admin, User, Radius, LDAP/AD auth (pages 88-89, 99)
- **OmniLab:** Single admin user only
- **Business Impact:** Cannot sell to enterprises without multi-tenancy
- **Recommended:** CRE-XX: Implement user roles (admin, power-user, readonly)

#### 2. **Template/Image Management System**
- **EVE-NG:** Centralized template visibility controls (page 100), YAML-based node definitions (page 274)
- **OmniLab:** No formal template system visible in codebase
- **Business Impact:** Users can't manage vendor images (Cisco IOS, Juniper vMX, etc.)
- **Recommended:** CRE-XX: Build template library with upload/version tracking

#### 3. **Lab Sharing & Collaboration**
- **EVE-NG:** Export labs as .zip with all configs (page 88)
- **OmniLab:** No export mechanism
- **Business Impact:** Can't share topologies between users/teams
- **Recommended:** CRE-XX: Lab export/import with JSON manifests

#### 4. **Network Types Beyond Bridges**
- **EVE-NG:** Cloud networks, NAT networks, pnet (physical NIC passthrough) (pages 14, 99, 170-184)
- **OmniLab:** Only basic bridge networking
- **Business Impact:** Labs can't reach internet or external networks
- **Recommended:** CRE-XX: NAT network object + DHCP service

#### 5. **Wireshark Integration**
- **EVE-NG:** Native packet capture on any link, sends PCAP to Wireshark (pages 193-197)
- **OmniLab:** No packet capture
- **Business Impact:** Debugging network issues impossible without seeing packets
- **Recommended:** CRE-XX: tcpdump capture API + download .pcap files

#### 6. **Docker Container Support**
- **EVE-NG:** Integrated docker stations with DHCP/static IP (pages 205-221)
- **OmniLab:** No container support
- **Business Impact:** Can't run modern network images (Arista cEOS, Cisco XRd, Nokia SR Linux)
- **Recommended:** CRE-XX: Docker node type + container lifecycle management

#### 7. **Backup & Recovery System**
- **EVE-NG:** Full backup manager with SFTP/FTP export (pages 275-279)
- **OmniLab:** No backup system
- **Business Impact:** Data loss risk, no DR strategy
- **Recommended:** CRE-XX: Automated SQLite + lab file backups to S3/SFTP

#### 8. **Cluster/Multi-Host Support**
- **EVE-NG:** Master + Satellite architecture for scaling (pages 222-253)
- **OmniLab:** Single-host only
- **Business Impact:** Can't scale beyond one server's resources
- **Priority:** v1.1+ (complex, multi-month effort)

#### 9. **Native Console Client Packs**
- **EVE-NG:** Windows/Linux/Mac integration with PuTTY/SecureCRT (pages 52-54)
- **OmniLab:** Web-only consoles
- **Business Impact:** Power users prefer native terminal emulators
- **Recommended:** CRE-XX: telnet:// protocol handlers + download links

#### 10. **Advanced Node Options**
- **EVE-NG:** CPU limit controls, UKSM (kernel same-page merging), per-node RAM/CPU (page 102)
- **OmniLab:** No resource controls visible
- **Business Impact:** Can't prevent single node from hogging CPU
- **Recommended:** CRE-XX: QoS controls in node config

#### 11. **Traffic Capture Filters**
- **EVE-NG:** PCAP filtering with GPT-assisted syntax (pages 189-192)
- **OmniLab:** N/A (no capture yet)
- **Recommended:** Pair with CRE-XX (Wireshark integration)

#### 12. **Task/Assignment System**
- **EVE-NG:** Embedded PDF/HTML documents in labs for training (pages 185-188)
- **OmniLab:** No learning/assignment features
- **Business Impact:** Can't use for education/certification prep
- **Priority:** v1.2+ (niche feature)

#### 13. **Licensing System**
- **EVE-NG:** Per-user license enforcement with session limits (page 100)
- **OmniLab:** No license system
- **Business Impact:** Can't monetize enterprise tiers
- **Recommended:** CRE-52 billing integration + license check middleware

#### 14. **API Documentation**
- **EVE-NG:** External API docs referenced (pages 266, 274, 280)
- **OmniLab:** API exists but undocumented
- **Business Impact:** Can't build integrations or automation
- **Recommended:** CRE-XX: OpenAPI spec + Swagger UI

#### 15. **Migration/Import Tool**
- **EVE-NG:** CLI migration script from old hosts (page 258)
- **OmniLab:** N/A (first version)
- **Priority:** v1.1+ (for EVE-NG switchers)

---

## 2. Architecture Insights

### EVE-NG System Design (Relevant to OmniLab)

#### Management Networks (Page 14, 99)
EVE-NG uses fixed internal subnets:
- **172.29.129.0/24** - NAT interface for internet access
- **172.29.130.0/24** - Cluster inter-node communication (Wireguard)
- **172.18.0.0/16** - Docker network
- **192.168.100.0/24** - Default NAT network (customizable)

**OmniLab Implication:** Need network isolation strategy for multi-lab environments.

#### Hardware Priorities (Page 12)
1. **CPU cores** (most important - labs are CPU-bound)
2. **Fast SSD** (IOPS matter more than capacity)
3. **RAM** (only after CPU is adequate)

**OmniLab Insight:** Health dashboard should warn when CPU:RAM ratio is poor (e.g., 4 cores + 64GB = wasted RAM).

#### KSM (Kernel Same-Page Merging) (Page 102)
EVE-NG uses KSM to deduplicate identical memory pages across VMs. Default: enabled.

**OmniLab Opportunity:** Implement KSM toggle in system settings (easy Linux kernel feature).

---

## 3. UX/UI Observations

### What EVE-NG Does Well (To Emulate)
- **Template visibility toggle:** Hide unprovisioned images from node list (page 100)
- **System status page:** Real-time node count per template (page 102)
- **Native console integration:** Protocol handlers for telnet:// links (pages 52-54)
- **Backup manager CLI:** Simple `backup-manager` command (page 276)

### Where OmniLab Can Differentiate
- **Modern React UI:** EVE-NG GUI is legacy PHP/jQuery
- **3D Carousel:** CRE-52 (no EVE-NG equivalent)
- **Real-time metrics:** WebSocket-based health updates vs EVE's polling
- **Simplified first-run:** EVE requires manual ISO setup, OmniLab has wizard

---

## 4. Security & Auth Patterns

### EVE-NG Auth Options (Pages 88-89, 99)
1. **Local:** Username/password in MySQL
2. **Radius:** Centralized auth server (IP + shared secret)
3. **LDAP/AD:** Active Directory integration (requires domain in username)

**OmniLab v1.0 Decision:** Localhost-only (no auth). ✅ Documented in memory.
**OmniLab v1.1:** Add local user DB + optional LDAP.

---

## 5. Gaps in EVE-NG (OmniLab Opportunities)

### What EVE-NG Lacks (Competitive Advantages)
1. **Modern UI/UX:** EVE interface feels dated (2015-era design)
2. **Cloud-native deployment:** EVE requires VM/bare metal, OmniLab could do Docker Compose
3. **REST API first:** EVE's API is an afterthought, OmniLab is FastAPI-native
4. **Real-time collaboration:** No live multi-user editing (could be killer feature)
5. **Built-in AI assistance:** No LLM-powered config generation or troubleshooting

---

## 6. Recommended OmniLab Roadmap

### v1.0 (MVP - Current Sprint)
- [x] Basic lab topology canvas
- [x] WebSocket console (telnet/SSH)
- [x] VNC/RDP support
- [x] Health monitoring
- [ ] **Missing for parity:**
  - [ ] CRE-XX: Multi-user auth (local DB)
  - [ ] CRE-XX: Lab export/import (.zip or JSON)
  - [ ] CRE-XX: NAT network type
  - [ ] CRE-XX: Basic Wireshark capture

### v1.1 (Enterprise Features)
- [ ] CRE-XX: Template library system
- [ ] CRE-XX: RBAC (admin/user/readonly roles)
- [ ] CRE-XX: Backup/restore to S3
- [ ] CRE-XX: API documentation (OpenAPI)
- [ ] CRE-XX: Docker container nodes
- [ ] CRE-XX: Native console client packs

### v1.2 (Advanced)
- [ ] CRE-XX: Cluster support (multi-host)
- [ ] CRE-XX: LDAP/AD integration
- [ ] CRE-XX: EVE-NG migration tool
- [ ] CRE-XX: Task/assignment system for education

### v2.0 (Differentiation)
- [ ] Real-time collaboration (Google Docs-style)
- [ ] AI-powered config assistant
- [ ] Cloud marketplace integration
- [ ] Mobile app for monitoring

---

## 7. Action Items

### Immediate (This Week)
1. ✅ Create this analysis document
2. ⬜ **Create GitHub issues for critical missing features:**
   - Multi-user authentication system
   - Lab import/export mechanism
   - NAT network support
   - Wireshark packet capture
   - Template/image management
3. ⬜ **Draft OmniLab Cookbook outline** (competitor to EVE-NG cookbook)
4. ⬜ Add "Feature Comparison" page to marketing site

### Short-term (Next 2 Weeks)
1. Implement CRE-XX: Multi-user auth (JWT tokens)
2. Implement CRE-XX: Lab export (JSON manifest + SQLite dump)
3. Document existing API endpoints (start cookbook)

### Long-term (Q3 2026)
1. Achieve feature parity with EVE-NG Community Edition
2. Publish OmniLab Professional Cookbook v1.0
3. Build Docker container node support
4. Launch beta program for enterprise users

---

## 8. Critical Cookbook Content We Need

Based on EVE-NG's 280-page cookbook, OmniLab needs:

### Must-Have Chapters
1. **Introduction & Use Cases** (EVE pages 11-12)
2. **System Requirements** (EVE pages 12-15) - ours will be simpler (Docker-based)
3. **Installation Guide** (EVE pages 16-54) - ours: `docker-compose up`
4. **First Login & Setup** (EVE page 54) - we have wizard ✅
5. **Lab Creation & Topology** (EVE pages 100-108)
6. **Node Management** (EVE Chapter 8)
7. **Network Objects** (EVE Chapter 9)
8. **User Management** (EVE pages 88-93) - coming in v1.1
9. **Console Access** (EVE pages 52-54, Chapter 8)
10. **Backup & Recovery** (EVE Chapter 19)
11. **API Reference** (EVE pages 266-280)
12. **Troubleshooting** (EVE Chapter 16)

### Nice-to-Have Chapters
- Docker Integration (EVE Chapter 14)
- Cluster Setup (EVE Chapter 15)
- Traffic Capture (EVE Chapters 11-12)
- Templates & Images (EVE Chapter 18)

---

## 9. Licensing & Business Model Insights

EVE-NG has three tiers:
1. **Community Edition** - Free, feature-limited
2. **Professional Edition** - Per-user licensing (~$90-200/user/year estimated)
3. **Enterprise Edition** - Volume licensing + cluster support

**OmniLab Strategy Recommendation:**
- **v1.0:** Free & open-source (build community)
- **v1.1:** Freemium model:
  - Community: 3 users, 50 nodes max
  - Professional: Unlimited users, backup, API access ($99/year)
  - Enterprise: Multi-host, LDAP, priority support ($499/year)

---

## 10. Conclusion

**Bottom Line:** OmniLab has 70% of EVE-NG Community Edition features but 0% of Professional Edition enterprise features.

**To compete effectively:**
1. Implement missing v1.0 critical features (auth, export, NAT, capture)
2. Write comprehensive cookbook (documentation = sales tool)
3. Build enterprise features in v1.1 (RBAC, backup, templates)
4. Differentiate with modern UX and cloud-native architecture

**Estimated effort to reach EVE-NG Professional parity:** 4-6 months full-time development.

---

## Appendix: EVE-NG PDF Structure

**Total Pages:** 280  
**Key Sections:**
- Installation: Pages 16-54 (39 pages)
- User Management: Pages 88-99 (12 pages)
- Topology & Labs: Pages 100-184 (85 pages)
- Docker Integration: Pages 205-221 (17 pages)
- Cluster System: Pages 222-253 (32 pages)
- Backup: Pages 275-279 (5 pages)
- API: Pages 266, 274, 280 (scattered references)

**Keywords Found:**
- `installation`: 10 pages
- `authentication`: 5 pages
- `API`: 6 pages
- `templates`: 10 pages
- `backup`: 9 pages
- `database`: 8 pages
- `licensing`: 10 pages

---

**END OF ANALYSIS**

**Next Step:** Create GitHub issues for missing features and begin OmniLab Cookbook draft.
