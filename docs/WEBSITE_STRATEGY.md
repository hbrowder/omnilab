# Website Strategy - May 25, 2026

## Current Status: Phase 1 - Technical Preview Landing Page

**Live:** http://getomnilab.com (HTTPS pending auto-provision)
**Purpose:** Technical validation with EVE-NG community
**Deployment:** May 25, 2026

---

## Phase 1 Analysis (Current State)

### ✅ Strengths
- **Clear value proposition:** "Say Goodbye to fixpermissions"
- **Target audience focused:** Direct EVE-NG comparison
- **Technical credibility:** Real code examples and commands
- **Quantified benefits:** "50 min saved per 20-image lab"
- **Simple structure:** Single-page, fast loading, no dependencies
- **Professional design:** Purple gradient, clean layout, responsive

### 🔄 Intentional Limitations
- **No navigation:** Single focused message
- **No product screenshots:** Still in early development
- **No social proof:** No testimonials yet (too early)
- **Minimal branding:** No logo (not needed for validation)
- **No extensive docs:** One clear use case (fixpermissions)
- **No CTAs beyond awareness:** No "Download" yet (pre-release)

### 🎯 Phase 1 Goals
1. **Validate the message:** Does "fixpermissions" resonate?
2. **Identify questions:** What do people ask when they see this?
3. **Gauge interest:** How much traffic/engagement?
4. **Learn priorities:** Which features matter most to users?

### 📊 Success Metrics (Next 2 Weeks)
- Share on Reddit r/networking, r/ccna
- Share in EVE-NG communities/forums
- Track which sections get the most attention
- Collect feedback on what's missing
- Identify top 3 "where's the X?" questions

---

## Phase 2 Plan - Full Professional Site

### When to Upgrade
**Trigger any of:**
- 2 weeks of feedback collected
- 100+ unique visitors
- 5+ people ask "how do I try it?"
- Clear signal: people want more info/features

### What to Add

#### 1. Site Structure (Multi-Page)
```
/              → Homepage (current landing + overview)
/features      → Full feature comparison
/docs          → Getting Started, API docs, deployment guides
/download      → Installation instructions, Docker images
/about         → Story, team, roadmap
/contact       → Support, community links
```

#### 2. Visual Enhancements
- **Logo/branding:** OmniLab logomark + wordmark
- **Product screenshots:** UI, lab topology view, template library
- **Architecture diagrams:** How it works under the hood
- **Video demo:** 60-second "fixpermissions eliminated" walkthrough

#### 3. Navigation & Structure
- **Header:** Logo + Nav menu (Features, Docs, Download, About)
- **Footer:** Links (GitHub, Docs, Contact), copyright, social
- **Sticky CTA:** "Try OmniLab" or "View Docs" button

#### 4. Content Expansion
- **Use case library:** Multiple pain points beyond fixpermissions
  - Migration from EVE-NG/GNS3
  - Packet capture integration
  - NAT networks (CRE-56)
  - Batch lab deployment
- **Documentation hub:** Installation, API reference, troubleshooting
- **Comparison table:** Feature-by-feature vs EVE-NG/GNS3
- **Testimonials:** Early adopter quotes (after Phase 1 feedback)
- **Roadmap:** What's coming next

#### 5. Professional Polish
- **Search functionality:** Docs search
- **Dark mode toggle:** User preference
- **Code snippet copy buttons:** One-click copy for curl commands
- **Interactive demos:** Try API calls in browser
- **Analytics:** Google Analytics or Plausible

### Estimated Effort
- **Design & planning:** 4 hours
- **Multi-page site structure:** 6 hours
- **Content writing:** 8 hours
- **Visual assets (logo, diagrams, screenshots):** 6 hours
- **Polish & testing:** 4 hours
- **Total:** ~28 hours (~1.5 weeks casual pace, 3 days focused)

---

## Phase 3 (Future) - Product Marketing Site

### When to Consider
- Product reaches v1.0
- 100+ active users
- Ready for wider adoption beyond early adopters

### Additional Elements
- **Case studies:** "How Company X migrated 50 labs in 1 day"
- **Pricing page:** (if commercial model)
- **Enterprise features:** SSO, multi-tenancy, auditing
- **Community showcase:** User-shared labs, templates
- **Blog:** Technical deep dives, release notes, best practices
- **Newsletter signup:** Product updates, tips
- **Live chat/support widget**
- **SEO optimization:** Rank for "EVE-NG alternative", "network emulation"

---

## Decision: Phase 1 First ✅

### Rationale (May 25, 2026)
1. **Validate before building:** No point in 6 pages if the core message is wrong
2. **Feedback shapes design:** Users will tell us what they need
3. **Faster iteration:** Single page = quick updates based on feedback
4. **Resource efficient:** Don't spend 3 days on a site that might need different content
5. **Early stage:** Product is still being built; docs would be incomplete anyway

### Action Plan
1. ✅ **Deploy Phase 1 site** (DONE - May 25, 2026)
2. ⏳ **Collect feedback** (Next 2 weeks)
   - Share in communities
   - Monitor analytics
   - Track questions/comments
3. 📋 **Review & decide** (Early June 2026)
   - Analyze feedback
   - Prioritize Phase 2 features
   - Decide: enhance or rebuild

---

## Tracking
- **Linear Issue:** CRE-63 (Website Enhancement - Phase 2)
- **Current deployment:** CRE-62 (Phase 1 - Done)
- **Review date:** June 8, 2026

---

## Notes
- Current site is intentionally minimal - this is a feature, not a limitation
- "Professional" ≠ complex; it means appropriate for current stage
- Technical audience (network engineers) values clarity over flashiness
- Single-page marketing site is standard for early-stage technical products
- Examples: Stripe v1, Slack v1, Tailwind CSS v1 - all started simple

**Decision made by:** Harold + 007  
**Date:** May 25, 2026  
**Status:** Monitoring Phase 1, Phase 2 spec ready to execute
