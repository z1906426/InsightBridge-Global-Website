# InsightBridge Global — AI Agent 协作规则与搜索引擎推送 API 清单

> 本文件由 Devin 根据 Tong 指示创建（2026-09-07）。用于记录跨仓库工作流与已配置的搜索引擎/API 推送机制。

---

## 1. 每次任务结束后的固定动作

Tong 指示：每次完成工作后必须同时做两件事：

1. **本地保存** —— 所有源码修改写入磁盘；
2. **推送到 GitHub** —— `git add`、`git commit`、`git push origin main`。

不完成这两步不视为任务完成。

---

## 2. 搜索引擎与 URL 推送 API 清单

以下脚本已存在于仓库中，覆盖 Google、Bing/Yahoo、Baidu、Yandex、Naver、Seznam、Brave/DuckDuckGo/Yep 等主流引擎。

### 2.1 已配置的引擎

| 引擎 | 协议/API | 覆盖方式 | 关键文件 | 状态 |
|---|---|---|---|---|
| **Google** | Google Indexing API (`URL_UPDATED`) | 主动推送 | `global/backend/google_indexing.py`、`intel/backend/google_indexing.py`、`intel/backend/weekly_multisite_seo_push.py` | 已配置，需 Service Account JSON |
| **Bing / Yahoo** | IndexNow | 通过 `api.indexnow.org` 中继 + 直接 `bing.com/indexnow` | `intel/backend/indexnow.py`、`global/backend/seo_push.py` | 已配置，公钥文件已部署 |
| **Yandex（俄罗斯）** | IndexNow | 通过 `yandex.com/indexnow` | `intel/backend/indexnow.py` | 已配置 |
| **Naver（韩国）** | IndexNow | 通过 `searchadvisor.naver.com/indexnow` | `intel/backend/indexnow.py` | 已配置 |
| **Seznam（捷克）** | IndexNow + 直接 Webmaster Reindex API | `search.seznam.cz/indexnow` + `reporter.seznam.cz/wm-api/web/document/reindex` | `global/backend/seznam_push.py`、`intel/backend/indexnow.py` | IndexNow 已配置；直接 API 需 `SEZNAM_API_KEY` |
| **Brave / DuckDuckGo / Yep** | IndexNow | 通过 `api.indexnow.org` 中继 | `intel/backend/indexnow.py`、`intel/backend/google_indexing.py` 注释 | 已配置（IndexNow 成员） |
| **Baidu（百度）** | Baidu Zhanzhang 普通收录主动推送 | `data.zz.baidu.com/urls` | `intel/backend/baidu_push.py`、`global/backend/seo_push.py`、`intel/backend/push_baidu_daily.py` | 已配置，需 `BAIDU_PUSH_TOKEN` |

### 2.2 关键凭据与文件

| 凭据 | 用途 | 当前状态 |
|---|---|---|
| `BAIDU_PUSH_TOKEN` | 百度站长主动推送 | 已存在于 `~/ib-fix/InsightBridge-Intelligence/backend/.env` |
| `GOOGLE_INDEXING_SA_JSON` / `GOOGLE_INDEXING_CREDENTIALS` / `GOOGLE_INDEXING_SA_JSON_PATH` | Google Indexing API 服务账号 | 文件存在于 `~/.openclaw/credentials/google_indexing_sa.json`；`GOOGLE_INDEXING_CREDENTIALS` 已在 `.env` 中设置 |
| `SEZNAM_API_KEY` | Seznam 直接 Reindex API | **未确认**，IndexNow 已覆盖 Seznam；如需要直接 API，需提供 |
| `INDEXNOW_KEY` = `0b86b54984314544b1c91d6b32d71028` | IndexNow 公钥 | 硬编码于脚本；公钥文件已部署到四站点根目录 `/<key>.txt` |
| `SEZNAM_KEY` = `55c187c7e0ed386b5de69d22d4f6336d8bff86f4` | Seznam IndexNow key | 硬编码于脚本；公钥文件已部署到四站点根目录 `/<key>.txt` |

### 2.3 自动化脚本

| 脚本 | 作用 | 触发方式 |
|---|---|---|
| `intel/backend/indexnow.py` | 提交 URL 到 IndexNow（Bing/Yandex/Naver/Seznam/Brave/Yep） | 发布文章时调用 |
| `intel/backend/baidu_push.py` | 提交 URL 到百度 | 发布文章时调用；每日限额 10 条 |
| `intel/backend/google_indexing.py` | 提交 URL 到 Google Indexing API | 发布文章时调用 |
| `intel/backend/weekly_indexnow_sweep.py` | 每周日 02:05 北京时区全站 IndexNow 推送 | 后台定时任务 |
| `intel/backend/weekly_multisite_seo_push.py` | 四站统一 Google + IndexNow + Baidu 推送 | 每周手动/定时运行 |
| `global/backend/seo_push.py` | 主站 Baidu + IndexNow + Google + Seznam 推送 | APScheduler 每日/手动 |
| `global/backend/seznam_push.py` | Seznam 直接 Reindex API | 被 `seo_push.py` 调用 |
| `global/backend/google_indexing.py` | 主站 Google Indexing API | 被 `seo_push.py` 调用 |

### 2.4 说明

- **Google Search Console 没有通用的“推送 URL” API**。Google 官方推荐的主动方式是：
  1. `sitemap.xml`（已在各站部署）；
  2. **Google Indexing API**（本仓库已配置，但官方文档说明主要用于 JobPosting 和 BroadcastEvent，实际中很多发布者也用于一般 URL）。
- **Bing Webmaster** 的主动推送现代替代品是 **IndexNow**，本仓库已完整使用。
- **Brave、DuckDuckGo、Yep** 均为 IndexNow 成员，通过 IndexNow 自动覆盖。
- **Yandex、Naver、Seznam** 同样通过 IndexNow 覆盖；Seznam 额外有直接 Reindex API 作为冗余。

---

## 3. 待确认/待补充项

- [ ] `SEZNAM_API_KEY` 是否已配置？如需要 Seznam 直接 Reindex API（非 IndexNow 中继），请提供。
- [ ] 是否需要为 `global` 主站单独设置 `GOOGLE_INDEXING_SA_JSON_PATH` 环境变量（当前文件在 `~/.openclaw/credentials/google_indexing_sa.json`，生产路径可能为 `/app/backend/secrets/gsc-indexing-sa.json`）？
- [ ] 是否需要韩国、捷克、俄罗斯除 IndexNow 外的其他本地搜索引擎直接 API（如 Yandex Webmaster API、Naver Search Advisor 直接 API）？

---

## 4. 验证命令

检查四站 IndexNow 公钥文件是否可访问：

```bash
for site in insightbridge.global intelligence.insightbridge.global press.insightbridge.global lab.insightbridge.global; do
  echo "=== $site ==="
  curl -sL "https://$site/0b86b54984314544b1c91d6b32d71028.txt"
  curl -sL "https://$site/55c187c7e0ed386b5de69d22d4f6336d8bff86f4.txt"
done
```

---

*最后更新：2026-09-07*
