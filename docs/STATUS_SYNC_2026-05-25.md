# OmniLab Status Sync - May 25, 2026 17:30 UTC

**Harold's Request:** "Document in Linear what's completed vs what are open action items"

---

## ✅ SHIPPED BUT LINEAR SAYS "BACKLOG" (needs sync)

### CRE-66: Link Styling System
**Linear Status:** Backlog  
**Reality:** ✅ SHIPPED (commit `de05bb1`)  
**Delivered:**
- Database: 8 new columns (src_interface, dst_interface, color, style, linkstyle, label, labelpos, width)
- Frontend: 3 path algorithms (Straight/Bezier/Flowchart)
- Frontend: Custom label rendering with rotation at midpoint
- Frontend: Color + stroke-width support (RGBA colors)
- Docs: EVE_NG_CODEBASE_ANALYSIS.md (336 lines)
- Docs: IMPLEMENTATION_PHASE1.md (243 lines)
- **Files changed:** 4 files, +635/-6 lines

**Action:** ✅ DONE - Moved to Done + added verification comment

---

### CRE-67: Modal System (No More Popups)
**Linear Status:** Backlog  
**Reality:** ✅ SHIPPED (commit `cd66465`)  
**Delivered:**
- Modal.jsx (6.8KB): Reusable modal system with Base/Prompt/Confirm variants
- Dark mode GitHub-style theme
- ESC key + click-outside handlers
- TopBar.jsx: 2x prompt() replaced with PromptModal
- NodePanel.jsx: window.open() replaced with iframe modal (1200px x 70vh)
- Build: 626KB bundle (176KB gzipped, 12.09s)
- **3 browser popup violations eliminated**
- **Files changed:** 4 files, +428/-14 lines

**Action:** ✅ DONE - Moved to Done + added verification comment

---

## 🚧 IN PROGRESS (uncommitted work on disk)

### CRE-64: Visual Container Boxes (Drawing Tools)
**Linear Status:** Backlog  
**Reality:** 🚧 IN PROGRESS (75% done)  
**Current State:**
- ✅ DrawingToolbar.jsx exists (178 lines, 5.8KB)
- ✅ UI toolbar wired up (select/rectangle/circle/text tools)
- ✅ Color pickers (fill + stroke) wired up
- ✅ Drawing preview works (live rubber-band rectangle/ellipse)
- ✅ In-memory state (shapes stored in `texts` array)
- ❌ Database persistence NOT implemented
- ❌ Backend API for textobjects NOT created
- ❌ Load/save from DB NOT wired up

**What's Left:**
1. Add `textobjects` table to database.py (id, lab_id, type, x, y, width, height, fill, stroke, text, z_index)
2. Create backend API endpoint: GET/POST /api/labs/{lab_id}/textobjects
3. Wire up persistence in LabCanvas.jsx:
   - Load textobjects on lab open
   - POST new shapes on mouseUp
   - DELETE on shape delete
4. Test: draw box → refresh page → box still there
5. Commit with verification doc

**Estimated Time:** 2-3 hours (backend API + frontend persistence wiring)

---

### CRE-65: Network Visibility Enhancement
**Linear Status:** Backlog  
**Reality:** ✅ COMPLETE (verification doc exists!)  
**Delivered:**
- Network objects now render with labels, icons, connection badges
- Size scaling based on connection count (1.0x-1.67x)
- Hover & selection states
- Interface labels on network links (purple network names vs blue interfaces)
- Status indicators (green=active, gray=inactive)
- Dark/light mode support
- **Build:** 636KB bundle (178KB gzipped, 47.41s)
- **Docs:** CRE-65_VERIFICATION.md (235 lines)

**What's Left:**
- Commit the changes (LabCanvas.jsx modified)
- Update Linear to Done + add verification comment

**Note:** The verification doc says "Next: CRE-68 Phase 1" but I think this was actually done as part of earlier work. Need to verify commit status.

---

### CRE-68: Traffic Filter Backend API
**Linear Status:** Backlog (draft scope)  
**Reality:** 🚧 BACKEND API DONE, no frontend yet  
**Current State:**
- ✅ Database schema: `traffic_filters` table (id, lab_id, title, expr, color, timeout, enabled, priority, timestamps)
- ✅ Backend API: `backend/routes/traffic_filters.py` (172 lines, 5KB)
  - GET /api/labs/{lab_id}/filters (list all)
  - POST /api/labs/{lab_id}/filters (create)
  - GET /api/labs/{lab_id}/filters/{filter_id} (get one)
  - PATCH /api/labs/{lab_id}/filters/{filter_id} (update)
  - DELETE /api/labs/{lab_id}/filters/{filter_id} (delete)
- ✅ Router registered in main.py
- ❌ No frontend UI yet
- ❌ No capture engine yet (tcpdump integration)
- ❌ No WebSocket streaming yet
- ❌ No animation engine yet

**Research Completed:**
- docs/CRE-68_TRAFFIC_FILTER_ANALYSIS.md (EVE-NG feature analysis)
- docs/CRE-68_ARCHITECTURE_DEEP_DIVE.md (37KB technical architecture)
- docs/CRE-68_TRAFFIC_VISUALIZATION_MASTER_PLAN.md (51KB 10-week plan)
- docs/TRAFFIC_FILTER_FINDINGS.md (SSH dive findings)
- **Total research:** 88KB of documentation

**What's Next:**
Kit created a 10-week master plan that builds EVE-NG-level traffic visualization. Harold clarified he wants to execute CREs as scoped, not over-engineer. Need to:
1. Define realistic MVP scope for CRE-68 based on Linear ticket
2. Break into phases (Phase 1: API done ✅, Phase 2: UI panel, Phase 3: capture engine, Phase 4: animation)
3. Commit Phase 1 (backend API) separately
4. Build Phase 2 (frontend filter panel UI)

---

## 📋 OPEN IN LINEAR (not started yet)

### CRE-69: Enhanced Left Sidebar
**Status:** Backlog  
**Priority:** 0  
**Assignee:** None  
**Needs:** Requirements definition

### CRE-70: Layout Tools (Snap-to-Grid, Align, Distribute)
**Status:** Backlog  
**Priority:** 0  
**Assignee:** None  
**Needs:** Requirements definition

---

## 🎯 RECOMMENDED ACTION PLAN

### Immediate (next 2 hours):
1. ✅ **CRE-66 & CRE-67:** Synced Linear to Done (COMPLETE)
2. **CRE-65:** Verify if already committed, or commit now + update Linear to Done
3. **CRE-64:** Finish database persistence (2-3 hours) → commit + update Linear to Done
4. **Push all commits** to GitHub (currently 3 commits ahead of origin)

### Next Session (CRE-68):
1. Commit CRE-68 Phase 1 (backend API) separately with verification doc
2. Update Linear CRE-68 with comment: "Phase 1 (Backend API) ✅ DONE"
3. Build Phase 2: Frontend filter panel UI
4. Build Phase 3: Capture engine integration (tcpdump + Docker exec)
5. Build Phase 4: Animation engine (SVG flows on canvas)

### Backlog Grooming:
- CRE-69 and CRE-70 need requirements before starting
- Break CRE-68 into sub-tickets if phases take >1 day each

---

## 📊 CURRENT GIT STATUS

```
M  backend/core/database.py          (CRE-68: traffic_filters table)
M  backend/main.py                   (CRE-68: router registration)
M  frontend/src/pages/LabCanvas.jsx  (CRE-64 + CRE-65 + CRE-66 + CRE-67 all in this file)
?? backend/routes/                   (CRE-68: traffic_filters.py)
?? docs/CRE-65_VERIFICATION.md       (CRE-65: verification doc)
?? docs/CRE-68_*.md                  (CRE-68: research docs x4)
?? frontend/src/components/DrawingToolbar.jsx  (CRE-64: UI toolbar)
```

**Commits ahead of origin:** 3 (cd66465 CRE-67, de05bb1 CRE-66, 4cfb89b UI plan)

---

## 🔍 VERIFICATION NOTES

**Harold's Rule:** "Every commit updates relevant .md docs AND posts a Linear comment with verification numbers"

**Status:**
- CRE-66 ✅ Has commit message with details
- CRE-67 ✅ Has commit message with verification (build time, bundle size, popup count)
- CRE-64 ❌ Not committed yet
- CRE-65 ❌ Has verification doc but commit status unclear
- CRE-68 ❌ Not committed yet (backend API done, no frontend)

---

**Next Steps:**
1. Harold reviews this status doc
2. Kit executes the recommended action plan
3. All uncommitted work gets proper commits + docs + Linear updates
4. Push everything to GitHub
