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

## 2026-01-06 — Code review decision: REJECTED (kept as-is)

An automated code-quality scan flagged several issues. After review with the owner,
**all flagged items were intentionally not fixed**, decision **A** (keep as-is). Rationale recorded below for future reference:

| Flagged item | File | Decision | Reason |
|---|---|---|---|
| "XSS via innerHTML" | `site/app.js:27` | Not fixed | False positive: assignment is a hardcoded SVG icon literal for the theme toggle; no user input involved. |
| useEffect missing deps | `src/hooks/use-toast.js:138`, `src/App.js:20` | Not fixed | Dead code. CRA scaffold under `src/` is never loaded — `yarn start` runs `node static-server.js`, which serves `/app/frontend/site/`. |
| High cyclomatic complexity | `site/app.js`, `site/wecom-track.js` | Not fixed | HANDOFF_corporate_site.md explicitly states: "Preserve all existing JavaScript (app.js, wecom-track.js)". These files are user-curated and already running in production; refactor risk > benefit. |
| Complexity 11 in static server | `static-server.js:76` | Not fixed | ~100-line zero-dependency static server; splitting would add abstraction without functional benefit. |
| 4 console statements | mixed | Not fixed | 3 are inside Cloudflare's third-party `email-decode.min.js` (cannot touch). 1 is the startup banner in `static-server.js` (operational logging, kept intentionally). |

**Authoritative source of truth for this project: `HANDOFF_corporate_site.md`'s "What NOT to do" list.** Future automated reports that conflict with HANDOFF should be reviewed against this decision before action.

## 2026-01-07 (Jun 7) — Production migration COMPLETE ✅

### Final verification (body-level, not just HTTP status)
- `https://insightbridge.global/` → Title: "Dr. Tong Yin | InsightBridge Global..."
- All 6 HTML pages return correct titles & content
- All 8 verified assets (CSS/JS/JPGs) return 200 with correct byte counts
- `https://www.insightbridge.global/` → HTTP 308 redirect to apex (SEO best practice)
- `https://intelligence.insightbridge.global/` → unchanged, sister site healthy
- SSL: Let's Encrypt wildcard *.insightbridge.global, auto-renewed (89 days remaining)
- Cloudflare DNS verified clean: no Hostinger IPs remaining; only Cloudflare-for-SaaS 172.66.2.113 / 162.159.142.117

### Root cause of the "Building something incredible" issue
- `package.json` had `"build": "craco build"` (default CRA)
- Emergent production deployment runs `yarn build` and serves the resulting `build/` dir
- This produced the empty React template instead of the static site
- **Fix**: changed to `"build": "rm -rf build && cp -R site build"` 
- Original CRA preserved as `build:cra` fallback
- Verified locally: `yarn build` now produces correct 12-file output

### Architecture (final)
```
Namecheap (registrar)
   └─ NS → Cloudflare (daniella + duke .ns.cloudflare.com)
            ├─ A insightbridge.global   → 172.66.2.113 + 162.159.142.117 (Emergent SaaS edge)
            ├─ CNAME www                → insightbridge.global
            ├─ A intelligence            → 172.66.2.113 + 162.159.142.117 (sister project)
            ├─ MX × 5                    → Google Workspace
            ├─ MX send.                  → AWS SES
            └─ TXT DMARC/DKIM/SPF/Yandex/Baidu/Google verifications
                ↓
         Cloudflare edge (TLS termination, CDN, DDoS)
                ↓
         Emergent K8s ingress (Host-header routing)
                ↓
         Container running `node static-server.js` → /app/frontend/build/ → 12 static files
```

### Hostinger
- Still active as 7-14 day rollback insurance
- User to back up `public_html` then cancel subscription after observation period

## 2026-01-07 (afternoon) — Major feature wave deployed to production
### Site-wide redesign (sister-site visual alignment)
- New typographic system: Fraunces (variable serif, opsz auto, SOFT=30) + Hanken Grotesk
- Hero recomposed into editorial 8/4 grid: brand mark (2-line stack) + headline + dek + CTA + inline publication link  |  news brief sidebar
- Header gains text wordmark "InsightBridge Global / STRATEGY & AI RESEARCH" beside the compass logo (hidden under 1180px)
- Hero brief de-boxed: no panel, no top accent rule, no blur — naturalised into background
- Contact section rebuilt: emojis (🔑📅) → SVG icons, trust banner detuned, editorial CTA, all-uppercase form labels, sharp-corner inputs
- All 6 pages: Fraunces + Hanken Grotesk fonts loaded

### Brand naming sweep
- "MARE v2.0" → "MARE" everywhere (meta, OG, JSON-LD, body, footer)
- Standalone "InsightBridge" → "InsightBridge Global" (18 places in tools.html, index.html, intelligence-vol01.html)
- 🧮 emoji in calculator badges → SVG calculator icon

### Removed
- Duplicate MARE + OTA Cost calculators inside #page-intelligence (display:none, kept for rollback)
- "Live Market Rates" section in tools.html (display:none — Makcorps API decommissioned)

### Image protection extended
- Main `dr-tong-yin.jpg` portrait + 4 LinkedIn thumbnails now have full credential-wrap protection
- CSS adds -webkit-touch-callout: none for iOS long-press defence
- JS contextmenu + dragstart preventDefault listeners

### SEO automation
- Built sitemap.xml (6 URLs + image:image entries for hero/portrait/framework + hreflang)
- robots.txt fully open: 28 named bot user-agents incl. all AI/LLM crawlers (GPTBot, ClaudeBot, PerplexityBot, etc.)
- IndexNow key file: b24a1ab5c04f483cace808846247e849.txt at site root
- All 6 pages: absolute canonical URLs + robots meta (max-snippet:-1, max-image-preview:large) + googlebot/bingbot/Baiduspider/YandexBot meta
- intelligence-market-report.html: full SEO head pack added (was previously bare)
- intelligence-vol01.html: Article JSON-LD schema + hreflang
- static-server.js: X-Robots-Tag: all + Referrer-Policy response headers

### SEO auto-push (every 24h, backend cron)
- backend/seo_push.py — pushes to Baidu Zhanzhang + IndexNow (Bing/Yandex/Naver/Seznam/Yep)
- backend/seo_scheduler.py — APScheduler interval job + MongoDB-persisted catch-up logic
- POST /api/seo/push — manual trigger (main + sister URLs)
- POST /api/seo/push-publications — push the 24 Research & Publications URLs (auto-extracted from index.html)
- GET  /api/seo/publications — list extracted publication URLs (debug)
- GET  /api/seo/status — last push + total count
- ENV: SITE_DOMAIN, INDEXNOW_KEY, BAIDU_PUSH_TOKEN
- IndexNow covers Naver (solves Korea registration problem)

### 2026-06-10 — Research & Publications push to search engines
- New helper backend/publications.py auto-extracts publication URLs from index.html's #page-publications section
- New endpoint POST /api/seo/push-publications submits all 24 publication PDFs/DOCX to IndexNow (Baidu capped at 10 to respect daily quota)
- First run: 24/24 URLs accepted by IndexNow (HTTP 200) → Bing/Yandex/Naver/Seznam/Yep. Baidu over-quota (expected, will retry on next 24h cron tick)
- Scheduler interval reduced from 72h → 24h to keep up with the sister site's publishing cadence

### Calculator IP protection (server-side migration)
- backend/calculators.py — MAREInput/MAREResult, OTAInput/OTAResult Pydantic models
- POST /api/calc/mare — 5 driver weights [0.18, 0.16, 0.14, 0.12, 0.12] now SERVER-ONLY
- POST /api/calc/ota — 4-layer cost math now SERVER-ONLY
- tools.html: removed weight table column, removed `data-w` attributes from sliders, removed inline formula box, replaced compute()/rateForIndex with fetch() to /api/calc/mare, draw() now uses server-supplied trajectory
- index.html OTA calculator: replaced local calc() with debounced fetch() to /api/calc/ota
- HTML source contains 0 leaks: zero "0.18", zero "data-w", zero "demand_index = Σ", zero "rateForIndex"

### Strategic decisions (recorded for posterity)
- Code-review report (XSS/Hooks/complexity warnings): all REJECTED — flagged items were false positives, dead code, or violated HANDOFF
- "Allow all crawlers" → robots.txt fully open, all AI/LLM bots welcome
- Calculator IP protection requested AFTER initial transparent-marketing decision because user's actual customer base (small-mid hotel owners) doesn't read code; engineers who do aren't customers
