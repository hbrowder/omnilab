# OmniLab transactional email templates

Sent by `backend/api/email.py` (CRE-13 / Module 8).

## Files

| File | Template name | Sent by |
| ---- | ------------- | ------- |
| `01_license_delivery.html` | `01_license_delivery` | Stripe `checkout.session.completed` webhook (`billing.py`) |
| `02_welcome.html`          | `02_welcome`          | First-run wizard finish (`system.py`) |
| `03_expiry_warning.html`   | `03_expiry_warning`   | Daily cron (planned) at 30/14/7/1 days before renewal |
| `04_payment_failed.html`   | `04_payment_failed`   | Stripe `invoice.payment_failed` webhook |
| `05_update_available.html` | `05_update_available` | Opt-in release announcements (planned) |

## Placeholders

Templates use plain `{placeholder}` syntax. Backed by Python `str.format` — no Jinja, no extra dependency. The set of valid placeholders per template comes from the matching `send_*` function in `api/email.py`:

- `01_license_delivery` — `{license_key}`, `{plan}`, `{year}`
- `02_welcome` — `{plan}`, `{year}`
- `03_expiry_warning` — `{days_left}`, `{plan}`, `{year}`
- `04_payment_failed` — `{customer_id}`, `{grace_period_days}`, `{year}`
- `05_update_available` — `{version}`, `{highlights}`, `{year}`

**Important:** any literal curly brace inside the HTML must be doubled (`{{` → `{`, `}}` → `}`). The current templates have no inline JS or CSS-in-style attributes that need this, but if you add one, escape the braces.

## Style conventions

- Light-themed (white background, dark text). Dark mode in email is hostile — Outlook will mangle inline dark backgrounds, gmail will sometimes invert them, and brand consistency loses to legibility.
- Inline CSS only (no `<style>` blocks). External CSS doesn't load in most email clients.
- Hero gradient `#7c5cff → #2cd4d9` matches the marketing site brand.
- 600px max width — the de facto email sweet spot for mobile + desktop.
- All CTAs are real `<a href>` styled like buttons — every email client renders them.

## Local testing without Postmark

Run the backend with `EMAIL_PROVIDER=log` (or just leave `POSTMARK_TOKEN` unset). Every send appends one JSON line per attempt to `~/.omnilab/email.log` with the rendered template path, subject, recipient, and full context. Tail it during dev to confirm the right template fires at the right trigger.

## Going live with Postmark

```bash
export EMAIL_PROVIDER=postmark
export POSTMARK_TOKEN=<server-token-from-postmark-dashboard>
export EMAIL_FROM='OmniLab <hello@omnilab.io>'   # must be a verified sender signature
```

That's it — no code change. The same `send_*` functions route via `httpx` to Postmark's REST API. Failures never raise; they log and return `False`, so a Postmark outage cannot break paid checkout.

## DNS / deliverability checklist (one-time)

These are operator tasks, out of scope for the backend code:

- [ ] Verify `hello@omnilab.io` as a Sender Signature in Postmark Dashboard
- [ ] Add Postmark's DKIM CNAME record to omnilab.io DNS
- [ ] Add SPF record: `v=spf1 include:spf.mtasv.net ~all`
- [ ] Add DMARC: `v=DMARC1; p=quarantine; rua=mailto:dmarc@omnilab.io`
- [ ] Send a test transactional via Postmark's Activity tab and check the spam score
