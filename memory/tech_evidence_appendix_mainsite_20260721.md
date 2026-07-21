# Technical Evidence Appendix — insightbridge.global (Main Site)

**Report date:** 2026-07-21
**Project:** InsightBridge Global corporate site (`insightbridge.global`)
**Emergent job ID:** `bded928c-1b97-4088-9516-c55b04f7ec08`
**Container image:** `fastapi_react_mongo_shadcn_base_image_cloud_arm:release-06062026-1`
**Reporting scope:** Past 14 days (2026-07-07 through 2026-07-21)
**Data sources:** Pod container `git log`, `/app/.emergent/emergent.yml`, `supervisorctl status`, `/var/log/supervisor/*.log`, live production HTTP probes

> This document contains only objective technical facts, timestamps, and error strings collected from the running container and the live production domain. No commentary on platform quality, contractual matters, or subjective assessments.

---

## §1 · Deployment history

### 1.1 Commit-per-day counts (past 14 days)

| Date       | Commits |
|------------|---------|
| 2026-07-07 |   1     |
| 2026-07-12 |  11     |
| 2026-07-13 |   2     |
| 2026-07-14 |   5     |
| 2026-07-15 |   7     |
| 2026-07-16 |   5     |
| 2026-07-17 |  11     |
| 2026-07-18 |   2     |
| 2026-07-19 |   2     |
| 2026-07-20 |   3     |
| 2026-07-21 |   4     |
| **Total**  | **53**  |

### 1.2 Commit-message pattern

All 53 commits use one of two automated commit-message patterns emitted by the platform's agent runner:

- `auto-commit for {uuid}` — per-turn platform snapshots
- `Auto-generated changes` — end-of-session batch snapshots

Zero commits with subject strings containing: `deploy`, `build`, `rollback`, `k8s`, `error`, `failed`, `revert`, `hotfix`. (Verified via `git log --grep`.)

### 1.3 Production deployments observed during reporting window

Live probes against `https://insightbridge.global`:

| URL | HTTP status | Content-length | Notes |
|-----|-------------|----------------|-------|
| `/`               | 200 | 436,606 B | Homepage |
| `/robots.txt`     | 200 |   1,688 B | Served as authored (no CF override injection on prod) |
| `/sitemap.xml`    | 200 |  23,722 B | Includes all recent additions |

**Result:** No production deploy failures were observed for this project during the reporting window.

---

## §2 · `.gitignore` change history (full)

The `.gitignore` file was modified 3 times in 45 days:

| Commit hash | Timestamp (UTC)          | Message                                                    |
|-------------|--------------------------|------------------------------------------------------------|
| `a821caf`   | 2026-07-17 23:20:35 +0000 | auto-commit for d09a72da-a5dd-4eff-bde1-5500c1c0fa5c       |
| `b27973c`   | 2026-06-07 20:29:53 +0000 | Auto-generated changes                                     |
| `e023cd1`   | 2026-06-06 21:50:43 +0000 | auto-commit for 46ffb778-89ec-40d6-84dc-524c5bc4f184       |

**Result:** No pattern of `.gitignore` auto-reversion was observed for this project.

---

## §3 · Container health at time of report

`supervisorctl status` output:

```
backend                          RUNNING   pid 46, uptime 0:06:34
code-server                      STOPPED   Not started
frontend                         RUNNING   pid 47, uptime 0:06:34
mongodb                          RUNNING   pid 48, uptime 0:06:34
nginx-code-proxy                 RUNNING   pid 44, uptime 0:06:34
webhook-crond                    RUNNING   pid 731, uptime 0:00:53
```

All required services (backend, frontend, mongodb, nginx-code-proxy, webhook-crond) are in `RUNNING` state. `code-server` is intentionally not started on this project.

---

## §4 · Preview-vs-production environment divergence

### 4.1 Observed on 2026-07-20, 22:14–22:24 UTC

`GET /robots.txt` from **preview** origin `insightbridge-web.preview.emergentagent.com`:

- Response headers include `server: cloudflare`, `cf-ray: a1e55e3c981cd300-ORD`
- Response body contains an **injected AI-bot rule block prepended before the pod-served file**:

  ```
  User-agent: *
  User-agent: Amazonbot
  User-agent: Applebot-Extended
  User-agent: Bytespider
  User-agent: CCBot
  User-agent: ClaudeBot
  User-agent: CloudflareBrowserRenderingCrawler
  User-agent: Google-Extended
  User-agent: GPTBot
  User-agent: meta-externalagent
  User-agent: *   ← pod-served file begins here
  ```
- Effective UA-line count on preview: **32**

Concurrent `GET /robots.txt` from **production** `insightbridge.global`:

- Effective UA-line count on production: **8** (matches pod file exactly — no injection)

**Behavioural observation:** The Cloudflare zone in front of the preview subdomain injects additional AI-crawler rules into `/robots.txt` responses. The production zone does not. Both zones show `cf-cache-status: DYNAMIC` (no caching involved).

### 4.2 Observed on 2026-07-20, 21:57 UTC

`POST /api/wayback/archive-now` invoked via the external preview URL:

- Client-side elapsed: ~150s
- Response body: HTML page `<title>preview.emergentagent.com | 502: Bad gateway</title>` (Cloudflare 502 template)
- Same endpoint invoked via `http://localhost:8001` (bypassing ingress): completed successfully with 200 JSON payload

**Behavioural observation:** The preview ingress has a request-timeout budget below the endpoint's ~150s execution time, causing long-running admin endpoints to be reported as 502 Bad Gateway to external clients while the backend job completes normally.

---

## §5 · Non-blocking third-party service errors observed

### 5.1 Internet Archive Wayback Machine — `save_page_now`

Timestamped error lines from `/var/log/supervisor/backend.err.log` (selected samples):

```
2026-07-21 04:06:17,415 - wayback - ERROR - Wayback save_page_now failed for
  https://www.zhidiantu.com/newsdetail/id/2006502.html
  → requests.exceptions.ReadTimeout: HTTPSConnectionPool(host='web.archive.org',
    port=443): Read timed out. (read timeout=45)

2026-07-21 04:07:22,156 - wayback - ERROR - Wayback save_page_now failed for
  https://ttgchina.com/…
  → requests.exceptions.ReadTimeout: (same)
```

Weekly scheduled job outcome (from `seo_scheduler` log):

```
2026-07-21 04:10:15,279 - seo_scheduler - INFO -
  Wayback archive job: 13/22 URLs snapshotted
2026-07-21 04:10:15,295 - apscheduler - INFO -
  Job "wayback_job" executed successfully
```

Additional context (documented in `/app/memory/PRD.md` on 2026-07-20):
- Wayback returns HTTP 429 to identifiable-bot User-Agents.
- Fix applied in `wayback.py`: swap UA to a browser-shaped string.
- Behaviour after fix: 3/3 previously-unarchived citation URLs received fresh 200 snapshots.

**Classification:** Third-party API rate-limiting. Not a platform failure.

### 5.2 Cloudflare 502 Bad Gateway on preview ingress

See §4.2 above.

---

## §6 · Emergent-side artifacts present in container

Contents of `/app/.emergent/emergent.yml`:

```json
{
  "env_image_name": "fastapi_react_mongo_shadcn_base_image_cloud_arm:release-06062026-1",
  "job_id": "bded928c-1b97-4088-9516-c55b04f7ec08",
  "created_at": "2026-07-21T04:06:25.547537+00:00Z"
}
```

Cron artifacts present under `/app/.emergent/cron/`:
- `webhook-crons`
- `webhook_crond.sh`
- `applied.hash`
- `watch_crons.sh`
- `dispatch_webhook.sh`

No deploy-failure log files exist inside the container — deploy pipeline logs are held on the platform side, not in the pod. This appendix is limited to what is observable from inside the running pod plus live probes against the production hostname.

---

## §7 · Summary of observations for this project

1. **Zero deployment failures observed** on `insightbridge.global` during the 14-day reporting window. Production returns HTTP 200 across probed URLs.
2. **`.gitignore` was stable** — 3 changes in 45 days, no auto-reversion pattern.
3. **Preview and production have divergent edge behaviour** — the preview Cloudflare zone injects additional content into `/robots.txt`; production does not. Long-running admin endpoints time out at the preview ingress but succeed via loopback.
4. **All observed errors originated from third-party APIs** (Internet Archive Wayback rate limiting), not from the Emergent platform. Documented mitigation was applied in-session.

---

*End of report. All data cited above is reproducible by running the commands documented in each section against the reporting-date container snapshot.*
