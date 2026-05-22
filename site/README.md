# Marketing site (omnilab.io)

Tracked under **CRE-20**. Single-file, vanilla HTML/CSS, zero runtime dependencies, zero third-party scripts.

## Layout

```
site/
├── index.html       # Single-page marketing site (all sections inline)
├── favicon.svg      # Triangle-of-nodes mark, gradient matches the wordmark
├── privacy.md       # Privacy notes (no cookies, no telemetry, no third parties)
└── README.md        # This file
```

`index.html` is intentionally one self-contained file. CSS lives in `<style>`, the one micro-script (copy-button) is inline. No build step, no bundler.

## Local preview

```bash
cd site
python3 -m http.server 8000
# open http://localhost:8000
```

## Deploy: Cloudflare Pages (recommended)

Cloudflare Pages is free, has the best DX of the static hosts, and gives you
a free wildcard certificate + global CDN. Procedure (do this when ready to
launch — these steps require *your* account and *your* domain payment):

1. **Register `omnilab.io`** at a registrar (Cloudflare Registrar is fine — price ≈ wholesale, no markup; alternatively Namecheap or Porkbun).
2. **Create a Cloudflare Pages project**:
   - Sign in to Cloudflare → Pages → Create a project → Connect to Git
   - Repo: `hbrowder/omnilab`
   - Build settings:
     - Framework preset: **None**
     - Build command: *leave blank*
     - Build output directory: `site`
     - Root directory: *leave blank*
3. **Custom domain**:
   - Pages project → Custom domains → Set up a custom domain → `omnilab.io` (and `www.omnilab.io`)
   - Cloudflare auto-provisions the cert and creates the DNS records if your domain is on Cloudflare DNS.
4. **Recommended Cloudflare settings**:
   - SSL/TLS encryption mode: **Full (strict)**
   - Always Use HTTPS: **On**
   - Automatic HTTPS Rewrites: **On**
   - Brotli compression: **On**
5. **Test**: every link, mobile + desktop, dark mode (the site is dark by default, so this is automatic).

### Headers (CSP + security)

Cloudflare Pages serves `site/_headers` automatically. Drop this in when ready:

```
/*
  Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; connect-src 'self' https://api.stripe.com; frame-ancestors 'none'; base-uri 'self'; form-action 'self'
  Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
  X-Frame-Options: DENY
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=(), interest-cohort=()
```

Note: `'unsafe-inline'` for script/style is only needed because the one
small copy-button script and all CSS live inline. If you ever extract them
to external files, tighten the CSP to remove `'unsafe-inline'`.

The `_headers` file is not currently committed because the site has no
external resources yet — adding it now is harmless but cosmetic. Add it
in the same PR that flips DNS live.

## Deploy: alternatives

| Host                    | Why pick                                          | Why not                                      |
| ----------------------- | ------------------------------------------------- | -------------------------------------------- |
| **Cloudflare Pages**    | Free, fast CDN, free cert, no build needed        | Their analytics is opt-in (which we want)    |
| Netlify                 | Generous free tier, easy forms                    | Edge slower than Cloudflare                  |
| Vercel                  | Best DX if you ever add Next.js                   | Bandwidth limits hit small launches faster   |
| GitHub Pages            | Already where the repo lives                      | No custom headers (so no CSP/HSTS control)   |
| AWS S3 + CloudFront     | Most control                                      | Most setup; not worth it for a 1-page site   |

## Analytics

**Not installed.** This is deliberate — the privacy page asserts zero
trackers. If we want metrics post-launch, the right options are:

- **Plausible Community Edition** — self-hostable, cookieless, GDPR-clean. Costs nothing if we host it on the same box as OmniLab.
- **Cloudflare Web Analytics** — free, no cookies, only counts page-views and referrers. Lower fidelity than Plausible but enables in one click and stays consistent with the privacy claim.

Either is a small follow-up ticket; do **not** add Google Analytics — it
contradicts the "no third-party scripts" promise on the page.

## Image assets still TODO

- `og-cover.png` — 1200×630, referenced in OpenGraph meta. Generate from a screenshot of the topology canvas + the wordmark; commit at `site/og-cover.png`. The page already references the path.
- `apple-touch-icon.png` — optional; 180×180 derived from `favicon.svg`.

These are cosmetic — the page works fine without them, the OG embed just falls back to a generic preview on Twitter/LinkedIn until the cover is committed.

## Content-correctness pre-launch checklist

- [x] Lab-template counts match `backend/api/templates.py` (Security 4, DevOps 3, AI/ML 2, Networking 1 — total 10 as of v1.0)
- [ ] Pricing matches Stripe Dashboard ($12/mo Pro is the source of truth — see CRE-21)
- [ ] All `github.com/hbrowder/omnilab` links resolve once the repo is public
- [ ] `mailto:harold@omnilab.io` mailbox is real before we point the domain (or change it to a working address)
- [ ] OmniLab CLI command shown in the install card matches the actual `omnilab start` entrypoint shipped in the `.deb`
