# EVE-NG Competitive Analysis

**Analysis Date:** May 27, 2026  
**EVE-NG Version:** 6.5.0-27-PRO  
**Instance:** http://192.168.1.156/  
**Status:** In Progress (HTTP Access Established, Deep Dive Pending)

---

## 🎯 Purpose

Comprehensive competitive analysis of EVE-NG to inform OmniLab development and ensure "better in every way" feature parity and superiority.

---

## 📊 Access Status

✅ **HTTP Access:** Working  
✅ **Authentication:** Successful  
✅ **File Manager:** Documented  
⏳ **Topology Canvas:** Ready for deep dive (next session)  
⏳ **Context Menus:** Pending  
⏳ **Features:** Pending  
⏳ **Workflows:** Pending  

---

## 🗂️ Interface Architecture

### Top-Level Navigation

**Main Menu Bar:**
- **Main** - Lab topology and device management (primary workspace)
- **Management** - File Manager, user management, system administration
- **System** - System configuration, network settings, status
- **Information** - Help, documentation, about
- **Licensing** - License management (PRO features)

**User Controls:**
- User indicator (shows "admin")
- Sign Out button
- System time display
- Version info: "©2026 EVE-NG Version: 6.5.0-27-PRO"

---

## 📁 File Manager (Management → File Manager)

### Layout
- **Left Panel:** File browser with folder tree and file list
- **Right Panel:** Lab preview/selection area ("Select a lab..." prompt)
- **Top Toolbar:** Search, create, upload, download, refresh, delete

### Features Observed

#### Toolbar Actions
1. **Search Bar** - Find files/folders by name
2. **Create Folder** - New folder creation
3. **Upload** - File upload capability
4. **Download** - Download selected files
5. **Refresh** - Reload current view
6. **Delete** - Remove selected items

#### File List View
- **Columns:**
  - Checkbox (multi-select)
  - Icon (folder/file type indicator)
  - Name (sortable)
  - Modified date (sortable)
- **Navigation:**
  - Breadcrumb trail: "Current Position / Root"
  - Click folders to navigate
  - Click ".." to go up one level

#### Visual Design
- Clean white background
- Professional folder icons
- Clear hierarchy
- Standard file manager patterns
- Responsive layout

---

## 🏗️ Lab Organization Structure

### Harold's Production Environment

**Total Items in Root:** 23 folders + 9 .unl lab files

**Folder Organization Pattern:**
- Technology-specific folders (Arista, Cisco ASA, Palo Alto, F5 BIG-IP)
- Protocol/feature folders (BGP, OSPF, GRE-DMVPN, VXLAN)
- Project/client folders (COX Labs, DOE, SOS Lab)
- Training folders (Layer 2 CCIE Training, Cisco DevNet Automate)
- Archive folder (OLD LABS)

**Lab File Naming:**
- Descriptive names with context (e.g., "Koch_MPLS_VRF.unl")
- Vendor-specific (e.g., "Fortinet FW Lab using Eve-NG.unl")
- Architecture-focused (e.g., "Segment_Routing_Replace_LDP_RSVP.unl")
- Blueprint/template naming (e.g., "blueprintRF-ha-bgp.unl")

**Key Observations:**
- Nested organization (folders contain subfolders)
- Date stamps show active development (most recent: 27 May 2026)
- Mix of production, training, and testing labs
- Real-world use case (Harold uses this daily for network engineering work)

---

## 🎨 Visual Design Language

### Color Palette (Observed So Far)
- **Background:** Clean white (#FFFFFF)
- **Text:** Dark/black for primary text
- **Icons:** Standard system icons (folders, files)
- **Navigation:** Professional blue/gray tones

### Typography
- Clear, readable sans-serif font
- Good spacing and hierarchy
- Professional presentation

### Layout Principles
- Grid-based organization
- Consistent spacing
- Clear visual hierarchy
- Standard desktop application patterns

---

## 🔧 Technical Stack Observations

### Backend
- **API Endpoint:** https://192.168.1.156/api/
- **Authentication:** REST API with session cookies
- **Session Management:** 
  - `unetlab_user` cookie (username)
  - `unetlab_session` cookie (session UUID)
  - `PHPSESSID` cookie (PHP session)
- **API Response Format:** JSON with `code`, `status`, `message` fields

### Frontend
- **Framework:** Single-page application (SPA) with hash routing
- **URL Pattern:** `/#/[route]` (e.g., `/#/labopen/root/labname.unl`)
- **Loading Behavior:** Progressive loading with "EVE Loading..." title

---

## 📋 Features to Document (Deep Dive Checklist)

### 🎯 Priority 1: Core Lab Interface
- [ ] **Topology Canvas**
  - [ ] Drawing area and grid
  - [ ] Zoom and pan controls
  - [ ] Background options
  - [ ] Canvas size and boundaries
  
- [ ] **Right-Click Context Menus** (Harold's specific request!)
  - [ ] Node context menu (what appears on device right-click)
  - [ ] Link context menu (what appears on connection right-click)
  - [ ] Canvas context menu (what appears on empty space right-click)
  - [ ] Network/container context menus
  - [ ] Multiple selection context menu
  
- [ ] **Device Management**
  - [ ] Device library/palette
  - [ ] Add device workflow
  - [ ] Device properties panel
  - [ ] Device configuration access
  - [ ] Start/stop/restart controls
  - [ ] Console access methods
  
- [ ] **Connection Tools**
  - [ ] How to wire devices
  - [ ] Link types (Ethernet, Serial, etc.)
  - [ ] Link properties
  - [ ] Multi-point connections
  - [ ] Link labels and annotations

### 🎯 Priority 2: Workflow & UX
- [ ] **Lab Creation**
  - [ ] New lab wizard
  - [ ] Lab templates
  - [ ] Lab properties/settings
  
- [ ] **Lab Operations**
  - [ ] Save/export options
  - [ ] Import existing labs
  - [ ] Lab sharing
  - [ ] Lab versioning
  
- [ ] **Topology Organization**
  - [ ] Alignment tools
  - [ ] Snap-to-grid
  - [ ] Auto-layout
  - [ ] Grouping/containers
  - [ ] Text labels and annotations

### 🎯 Priority 3: Advanced Features
- [ ] **Status & Monitoring**
  - [ ] Device status indicators
  - [ ] Link status visualization
  - [ ] Performance metrics
  - [ ] Console/log access
  
- [ ] **Collaboration**
  - [ ] Multi-user access
  - [ ] Permissions model
  - [ ] Shared labs
  
- [ ] **Automation**
  - [ ] Bulk operations
  - [ ] Scripting/API access
  - [ ] Lab automation
  
- [ ] **Professional Features**
  - [ ] Templates and blueprints
  - [ ] Image management
  - [ ] Network capture integration
  - [ ] Documentation integration

### 🎯 Priority 4: Polish & Details
- [ ] **Keyboard Shortcuts**
- [ ] **Drag-and-drop behaviors**
- [ ] **Loading states and animations**
- [ ] **Error messages and validation**
- [ ] **Tooltips and help text**
- [ ] **Icon consistency and style**
- [ ] **Spacing and alignment precision**
- [ ] **Feedback mechanisms**

---

## 🏆 OmniLab Competitive Advantages (To Validate)

### Planned OmniLab Superiority Points:
1. **Modern Tech Stack** - React/TypeScript vs EVE-NG's older stack
2. **API-First Design** - FastAPI backend with clean REST API
3. **Single User Focus** - No complex multi-user overhead (for now)
4. **Upload Workflow** - Solved permission issues (30min→5min setup)
5. **Migration Tools** - Built-in EVE-NG → OmniLab migration
6. **Health Checks** - Automated image validation

### To Discover: Where EVE-NG Excels
- [ ] Feature maturity
- [ ] UI polish level
- [ ] Workflow efficiency
- [ ] Professional features
- [ ] Integration capabilities

---

## 📸 Screenshots Captured

1. **File Manager - Root View** - Lab list and folder structure
2. **File Manager - BGP Folder** - Subfolder organization example
3. **Authentication Flow** - Login screen (before API workaround)

**Next Session:** Topology canvas and context menus

---

## 🎯 Next Session Goals

1. Click "Main" menu to enter topology view
2. Open a lab (recommended: Koch_MPLS_VRF.unl or TestLab.unl)
3. Systematically right-click EVERYTHING:
   - Devices
   - Links
   - Canvas
   - Groups/containers
   - Multiple selections
4. Document every toolbar button
5. Test every menu option
6. Explore properties panels
7. Try creating/editing workflows
8. Screenshot everything
9. Build comparative feature matrix
10. Create OmniLab roadmap based on findings

---

## 💡 Insights So Far

### EVE-NG Strengths Observed:
- **Mature product** - Version 6.5.0 indicates years of development
- **Professional Edition** - PRO features suggest robust enterprise capabilities
- **Real-world usage** - Harold's extensive lab collection shows production viability
- **Clean interface** - Professional presentation, not cluttered
- **Organized structure** - Clear navigation and file management

### Questions to Answer:
- How does the topology canvas handle large labs?
- What's the device placement UX like?
- How smooth is the wiring workflow?
- What's the learning curve for new users?
- Where are the pain points that OmniLab can solve better?

---

## 📝 Document Status

**Created:** May 27, 2026  
**Last Updated:** May 27, 2026 02:45 UTC  
**Completion:** ~10% (access established, deep dive pending)  
**Next Update:** After topology deep dive session

---

**Goal:** Build the definitive competitive analysis to make OmniLab "better in every way than EVE-NG" - not through guesswork, but through systematic observation and empirical evidence.
