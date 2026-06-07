# SEO Auto-Push Configuration — InsightBridge Global

Setup date: 2026-01-07

## What this does
Every 72 hours, automatically submit all 6 site URLs to:
- 🇨🇳 Baidu Zhanzhang (data.zz.baidu.com)
- 🌐 IndexNow → Bing, Yandex, Naver, Seznam, Yep/DuckDuckGo

## Credentials (stored in /app/backend/.env)
- `BAIDU_PUSH_TOKEN=KytPztkoBprxHyKH`
- `INDEXNOW_KEY=b24a1ab5c04f483cace808846247e849`
- `SITE_DOMAIN=insightbridge.global`

## Files involved
- `/app/frontend/site/sitemap.xml`            — list of URLs (also served at /sitemap.xml)
- `/app/frontend/site/robots.txt`             — points crawlers to sitemap
- `/app/frontend/site/b24a1ab5c04f483cace808846247e849.txt` — IndexNow key proof
- `/app/backend/seo_push.py`                  — push logic
- `/app/backend/seo_scheduler.py`             — APScheduler interval job (72 h)
- `/app/backend/server.py`                    — startup hook + API endpoints

## API endpoints
| Method | Path                | Purpose                              |
|--------|---------------------|--------------------------------------|
| POST   | /api/seo/push       | Trigger a push to all engines now    |
| GET    | /api/seo/status     | Show last push result + total count  |

## Behaviour
- On every backend startup: check MongoDB → if last push > 72 h ago, run immediately ("catch-up")
- After startup: APScheduler triggers every 72 h
- Each push: 6 URLs × 6 engines = 36 indexing requests per cycle
- Baidu daily limit: 10 URLs/day. We use 6 → 4 remaining for any manual additions
- IndexNow: no limit. 202 = accepted; 200 = processed

## Updating the URL list
Edit `get_urls()` in `/app/backend/seo_push.py`.
Also update `/app/frontend/site/sitemap.xml` so crawlers see the new list.

## Manual push commands
```bash
# Trigger manual push (preview)
curl -X POST https://insightbridge-web.preview.emergentagent.com/api/seo/push

# Trigger manual push (production)
curl -X POST https://insightbridge.global/api/seo/push

# View last push status
curl https://insightbridge.global/api/seo/status
```

## Troubleshooting
- **Baidu returns 401**: token expired/revoked → regenerate in 百度搜索资源平台
- **Baidu returns `remain: 0`**: daily quota exhausted, will reset at midnight Beijing time
- **IndexNow returns 4xx**: key file at site root may be missing/wrong content → check `/{KEY}.txt`
- **Scheduled job not firing**: check `/var/log/supervisor/backend.err.log` for "SEO push" entries
- **Need to push more often than 72 h**: edit `PUSH_INTERVAL_HOURS` in `seo_scheduler.py`

## Manual rotation procedure
- **Baidu token**: get new from 百度搜索资源平台 → 资源提交 → API推送 → 修改准入密钥 → update `.env` → restart backend
- **IndexNow key**: generate `python3 -c "import uuid; print(uuid.uuid4().hex)"` → rename key file → update `.env` → restart backend
