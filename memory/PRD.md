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


### 2026-02-08 — Replaced legacy calculators with Three-Model Live Dashboard iframe
- **Home page (`#page-home`):** Removed the legacy POLARIS `tools.html` iframe + OTA True Cost Calculator section (+ its JS handler block). Replaced with a single embedded iframe of `https://intelligence.insightbridge.global/dashboard` titled "POLARIS · ORION · NOVA — Three-Model Dashboard".
- **AI Model page (`#page-ai-model`):** Removed the three "Live AI Model" cards (ORION → app.*, POLARIS → mare.*, NOVA → director.* subdomains) and replaced with the same dashboard iframe. LinkedIn profile card preserved.
- **Tools / Intelligence sections kept untouched** per user request (they still use the dedicated `tools.html` iframe + OTA True Cost Calculator).
- **Sister-site CSP check:** `frame-ancestors 'self' https://insightbridge.global https://www.insightbridge.global` confirmed on `https://intelligence.insightbridge.global/dashboard` (HTTP 200) — iframe will render in production. Preview environment shows blank iframe (expected: preview domain not in whitelist).
- **HTML hygiene after edit:** 1× `<main>` / 1× `</main>`, 0× legacy `otach-` IDs, 4× references to `intelligence.insightbridge.global/dashboard` (2 iframes + 2 "Open full screen" links).

### 2026-02-08 — Headline ordering fix (RSS-first)
- **Root cause:** `sister_articles.py` sorted candidates by sitemap `<lastmod>`, but a bulk republish on the sister site assigned 48+ articles near-identical lastmod timestamps in a tight window, burying the genuinely-new "Why AI Pricing Still Fails Hotels" article (published 2026-06-24) at rank 48 by lastmod.
- **Fix:** Rewrote `sister_articles.py` to use the sister site's RSS feed (`/api/rss.xml?lang=en`) as primary source — already ordered by true `pubDate`. Sitemap + per-article HTML meta parsing retained as fallback only.
- **Verification:** target now appears at rank #5; external e2e through Kubernetes ingress confirmed.
- **Regression test:** `/app/backend/tests/test_sister_articles.py` asserts headlines are sorted newest-first by publish date.

### 2026-07-12 — "Cited & Syndicated Worldwide" trust signal strip
- Added per sister-site update request: trust strip showing 9 verified citations / 5 countries / 3 languages (Muck Rack, TTG China, HotelX Tech, Canadian Reviews, AI Hospitality Alliance, AI for Tourism & Hospitality, Let's Data Science).
- **index.html:** inserted after Stats/Company-Registration section, before 2027 Whitepaper card. Uses site palette (#F5EFE6/#7A1F2B/#0A192F) + lang-en/lang-cn toggle spans. data-testid: cited-worldwide-strip / cited-worldwide-cta.
- **zh.html:** inserted after 发表媒体与平台 section, restyled to zh.html navy/gold theme (#1a3a5c/#c8913a). data-testid: cited-worldwide-strip-zh / cited-worldwide-cta-zh.
- All CTAs link to https://intelligence.insightbridge.global/press#press-citations-section (target=_blank).
- Verified via screenshots on preview (EN + ZH both render correctly).

### 2026-07-12 — Weekly auto-sync of citation counters
- New `/app/backend/press_stats.py`: scrapes sister-site `/press` SSR HTML (`press-citations-stats` element), extracts citations/countries/languages, caches in Mongo `press_stats_snapshot`.
- Endpoints: `GET /api/press/stats` (cached, static fallback 9/5/3), `POST /api/press/stats/refresh` (manual).
- APScheduler job `press_stats_job` every 168h (weekly) + warm-up 2 min after boot.
- Frontend: strip numbers wrapped in `[data-ib-stat]` spans (index.html EN+CN, zh.html); tiny fetch script updates them on load, silent fallback to static values. Headline wording corrected to "verified citations / 已验证引用" (matches sister-site source of truth).
- Tests: `/app/backend/tests/test_press_stats.py` (parser regression + live-page parseability), all 3 backend tests pass.


### 2026-07-12 — Main-site RSS feed for crawler self-discovery
- **User ask (zh):** "创建一个 RSS,把这个链接推给各主要搜索引擎。各搜索引擎自己可以抓取了。" (sister-site articles already covered by sister-site RSS — main-site feed should only include our own sections).
- **Follow-up ask:** "把发表物和研究栏目里面所有文章的链接都加进去,不让大家看都可惜了。" → expanded scope to include Intelligence Coverage press articles + the 2027 whitepaper.
- **New backend module:** `/app/backend/rss_feed.py` — generates RSS 2.0 XML with 43 items total:
  - 6 canonical sections (`/`, `/zh.html`, `/tools.html`, `/intelligence-market-report.html`, `/intelligence-vol01.html`, `/privacy.html`)
  - 25 publications from `#page-publications`
  - 11 press-coverage PDFs from `#page-intelligence` (media/IB_*.pdf)
  - 1 featured 2027 whitepaper from `#cited-worldwide-strip`
  - Real human titles are auto-lifted from the nearest preceding `<h1>-<h6>` heading (with HTML-entity unescape before XML escape); slug-derived fallback if no heading is found.
- **Endpoints:** `GET /api/rss/status` (metadata), `POST /api/rss/refresh` (manual regen).
- **APScheduler:** new `rss_feed_job` runs `write_rss()` every 24 h (starts ~3 min after boot).
- **Startup guard:** `ensure_rss_exists()` writes the file on backend boot if missing.
- **Crawler discovery paths (multi-layer):**
  1. `<link rel="alternate" type="application/rss+xml" href=".../rss.xml">` in `<head>` of both `index.html` and `zh.html` — browser & crawler auto-discovery.
  2. `robots.txt` — RSS URL noted alongside the sitemap.
  3. `seo_push.get_urls()` — `/rss.xml` now included in every IndexNow + Baidu + Google push, so search engines are actively notified whenever the feed URL changes.
- **Public verification:** `curl https://insightbridge.global/rss.xml` → 200 `application/xml; charset=utf-8`; 43 items with real editorial titles; XML validates with ElementTree.
- **Tests:** `/app/backend/tests/test_rss_feed.py` — 5 tests (well-formedness, section coverage, channel metadata, disk write, production-file guard) — all pass.

### 2026-07-12 — Seznam.cz integration (Czech search engine)
- **Context:** User verified `insightbridge.global` in Seznam Webmaster (meta tag `seznam-wmt` added to `index.html` line 27) and generated a Seznam Webmaster API key.
- **Env:** `SEZNAM_API_KEY=<40-char hex>` in `/app/backend/.env`.
- **New module:** `/app/backend/seznam_push.py` — POSTs to `https://reporter.seznam.cz/wm-api/web/document/reindex?key=<KEY>&url=<URL>` per-URL. Returns per-URL statuses so we see exactly which URLs Seznam accepted (unlike IndexNow's aggregate 200).
- **API contract discovery:** GitHub docs said `GET` with `Authorization: key <KEY>` header — actually returns 405/400. Correct call is **POST with `?key=` and `?url=` query params, no auth header**. Verified via probe returning `{"status": 200}`.
- **Integrated into** both `run_push_and_save()` (scheduled 24h push) and `run_push_urls()` (publications push). Cap per push: 10 URLs (mirrors Baidu safety cap).
- **Verification:** manual `POST /api/seo/push` → all 4 engines return `ok=True`: Baidu 200, IndexNow 200, Google 200, **Seznam 7/7 accepted**.
- **Coverage note:** Seznam is already an IndexNow member so IndexNow was already reaching it; the direct API adds (a) per-URL confirmation and (b) redundancy if IndexNow ever de-registers our key.


### 2026-07-12 — Fix: broken URL snowballing (Clarity investigation)
- **Symptom (from Clarity analytics):** real visitors were landing on pathological URLs like `/media/media/assets/publications/assets/media/publications/Kinship_...pdf` and `/publications/publications/media/assets/zh.html`. These URLs returned 200 (with full index.html content) instead of 404 → users saw wrong page → immediate bounce; Google sees dozens of "duplicate content" URLs → dilutes homepage ranking.
- **Root cause identified:**
  1. Production Cloudflare edge returns `index.html` (SPA fallback) for any 404 path, instead of a real 404 (preview node server does the right thing).
  2. `index.html` contained 42 **relative** hrefs (`href="publications/xxx.pdf"`, `href="media/yyy.pdf"`, `href="assets/lab-articles-of-organization.pdf"`).
  3. When a user hits a bad URL (e.g. via a bad backlink), CDN serves index.html at wrong path → browser resolves the 42 relative links against wrong path → clicking produces `/publications/publications/xxx.pdf` → also 404 → CDN serves index.html again → snowball into deeper duplications.
- **Fix layer 1 — absolutise 42+ relative links:**
  - `href="publications/…"` → `href="/publications/…"` × 26
  - `href="media/…"` → `href="/media/…"` × 14
  - `href="assets/{lab-articles,lab-cert,2027-whitepaper}.…"` → `href="/assets/…"` × 2
  - Same fix in `tools.html` for `<img src="assets/logo-en.jpg">`.
- **Fix layer 2 — SPA-fallback client-side guard** (added to `index.html` and `zh.html` `<head>` before all other scripts):
  - If `location.pathname` is not the file's canonical path (`/` or `/index.html` for index; `/zh.html` for ZH), `history.replaceState(null, '', '/')` (or `/zh.html`) — corrects the address bar so relative links (should any remain) resolve correctly AND search engines that follow such URLs see a clean canonical location.
- **Verification:**
  - Preview: `/` HTTP 200; hero links now absolute (`/publications/HBS_Case_Study_PUBLICATION_GRADE.pdf`, `/assets/lab-articles-of-organization.pdf`).
  - Preview: `/foo/bar` HTTP 404 (node server correct).
  - Production diagnostic: `curl https://insightbridge.global/foo/bar.pdf` returns HTTP 200 + full 364 KB index.html — confirmed CDN SPA fallback.
  - Playwright simulation: injected `/publications/publications/media/assets/zh.html` → guard rewrote to `/` — PASS.
- **Follow-up item:** contact Emergent Support to request disabling SPA fallback at the Cloudflare edge for this deployment (proper 404 pages are the ideal root-cause fix; layers 1 and 2 above are belt-and-braces defence).

