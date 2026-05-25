# Website Deployment Guide

## Current Setup: GitHub Pages + Custom Domain

**Live Site:** https://getomnilab.com  
**Source:** `gh-pages` branch  
**File:** `index.html` (marketing landing page)

---

## ✅ Already Done

1. ✅ Created `gh-pages` branch
2. ✅ Deployed marketing page as `index.html`
3. ✅ Added `CNAME` file with `getomnilab.com`
4. ✅ Pushed to GitHub

**Commit:** 9a41603

---

## 🔧 Steps YOU Need to Complete

### Step 1: Enable GitHub Pages (One-Time Setup)

1. Go to: https://github.com/hbrowder/omnilab/settings/pages
2. Under **"Source"**:
   - Branch: `gh-pages`
   - Folder: `/ (root)`
3. Click **Save**
4. Wait 2-3 minutes for deployment

GitHub will show: `Your site is live at https://hbrowder.github.io/omnilab/`

---

### Step 2: Configure Custom Domain in GitHub

1. Still on the Pages settings page
2. Under **"Custom domain"**:
   - Enter: `getomnilab.com`
3. Click **Save**
4. Check **"Enforce HTTPS"** (wait 5 min after DNS propagates)

---

### Step 3: Update DNS at GoDaddy

1. Go to: https://dcc.godaddy.com/control/getomnilab.com/dns
2. Delete any existing A/CNAME records for `@` (root domain)
3. Add these **4 A records** (all pointing to `@`):

```
Type: A    Name: @    Value: 185.199.108.153
Type: A    Name: @    Value: 185.199.109.153
Type: A    Name: @    Value: 185.199.110.153
Type: A    Name: @    Value: 185.199.111.153
```

4. Add **1 CNAME record** for www:

```
Type: CNAME    Name: www    Value: hbrowder.github.io
```

5. Click **Save**

**DNS propagation takes 5-60 minutes.** Test with:
```bash
dig +short getomnilab.com A
# Should show: 185.199.108.153, 185.199.109.153, etc.
```

---

## 🧪 Verification

After DNS propagates:

```bash
# Test HTTP → HTTPS redirect
curl -I http://getomnilab.com

# Test page loads
curl -s https://getomnilab.com | grep "Say Goodbye"
# Should show: <title>Say Goodbye to fixpermissions | OmniLab</title>
```

---

## 🔄 Updating the Site

To update content:

```bash
cd ~/omnilab
git checkout gh-pages

# Edit index.html
nano index.html

# Commit and push
git add index.html
git commit -m "update: [describe changes]"
git push origin gh-pages

# GitHub Pages auto-deploys in ~2 minutes
```

---

## 📊 Current Status

| Component | Status | Action Required |
|-----------|--------|-----------------|
| gh-pages branch | ✅ Created | None |
| index.html | ✅ Deployed | None |
| CNAME file | ✅ Added | None |
| GitHub Pages enabled | ⏸️ Pending | Enable in repo settings |
| Custom domain configured | ⏸️ Pending | Add in Pages settings |
| DNS A records | ⏸️ Pending | Update at GoDaddy |
| HTTPS enabled | ⏸️ Pending | Enable after DNS propagates |

---

## 🆘 Troubleshooting

### "Domain not verified" error in GitHub
- Wait 10 minutes after adding DNS records
- Check DNS with: `dig getomnilab.com`
- Clear GitHub's DNS cache by removing and re-adding the domain

### Site shows 404
- Verify `gh-pages` branch exists: `git branch -a | grep gh-pages`
- Check GitHub Pages build log: repo Settings → Pages → view build logs

### HTTPS not working
- DNS must propagate first (15-60 min)
- "Enforce HTTPS" checkbox grayed out? Wait longer
- Try visiting without www: `https://getomnilab.com`

---

## 📝 Related

- **Linear Issue:** CRE-62 (Marketing Landing Page)
- **Commit:** 9a41603 (gh-pages deployment)
- **Source File:** `marketing/fixpermissions-landing.html`
