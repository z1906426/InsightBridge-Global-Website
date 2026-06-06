# InsightBridge Global — Corporate Site (Static Deployment)

## Original problem statement
Deploy the static InsightBridge Global corporate site (`insightbridge-corporate-site.zip`, 8.6 MB, 25 files) as-is per the `HANDOFF_corporate_site.md` rules:
- No styling, font, or palette changes
- Editorial Brief section must remain
- Pure static, no backend
- Provide Cloudflare DNS targets so the user can point `insightbridge.global` and `www.insightbridge.global` at the new deployment
- Do NOT touch `intelligence.insightbridge.global` (separate Emergent project)

## Architecture
- **Type:** Static multi-page site (HTML/CSS/JS only, no backend, no DB)
- **Serving:** Tiny zero-dep Node static server at `/app/frontend/static-server.js` listens on `0.0.0.0:3000`, serves `/app/frontend/site/` (k8s ingress routes all non-`/api` traffic here)
- **Supervisor:** unchanged; `yarn start` script now runs `node static-server.js`
- **Backend (FastAPI):** still running on :8001 but unused by this site

## Files served (under /app/frontend/site/)
- `index.html` — homepage with Hero + Editorial Brief + Stats + Quote + Framework + Calculators + News + Publications + Contact
- `tools.html` — Interactive Hotel Pricing Calculator (MARE v2.0)
- `intelligence-market-report.html` — bilingual long-form report
- `intelligence-vol01.html` — first issue archive
- `zh.html` — Chinese landing variant
- `privacy.html` — privacy policy
- `style.css`, `base.css`, `app.js`, `wecom-track.js`
- `assets/` (9 images), `cdn-cgi/scripts/`

## Design tokens (preserved verbatim)
Playfair Display / IBM Plex Sans, cream `#F5EFE6`, surface `#FBF7F0`, primary `#0A192F`, accent `#7A1F2B`, gold `#C9A961`.

## Status — 2026-01-06
- ✅ Zip extracted (25 files, 9.3 MB unpacked)
- ✅ Static server live; all 6 HTML pages return 200; CSS/JS/images return 200 with correct MIME
- ✅ Editorial Brief section verified intact (2 occurrences in HTML, dark Spotlight card links to intelligence.insightbridge.global)
- ✅ Sister-site CNAME left untouched
- ✅ deployment_agent: PASS

## Next action items (user-side)
1. Click **Deploy** in the Emergent platform to publish to production
2. After deploy, copy the production hostname Emergent provides
3. In Cloudflare DNS for `insightbridge.global`:
   - `insightbridge.global` (apex) → CNAME-flatten (or A) to the Emergent production hostname
   - `www.insightbridge.global` → CNAME to the Emergent production hostname
   - Leave `intelligence.insightbridge.global` CNAME untouched
4. Set both new records to "Proxied" (orange cloud) in Cloudflare for TLS + caching
