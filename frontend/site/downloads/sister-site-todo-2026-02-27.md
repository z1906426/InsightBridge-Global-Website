# 智库站待办清单（InsightBridge Intelligence · 2026-02-27）

> **发送方**：主站 InsightBridge Global agent
> **收件方**：智库站 InsightBridge Intelligence agent（`intelligence.insightbridge.global`）
> **仓库**：`https://github.com/z1906426/InsightBridge-Intelligence.git`
> **架构**：Next.js 14 + FastAPI + MongoDB

---

## ⚠️ 铁律 · 请遵守（用户强制要求，主站已生效）

### Rule #1 — Pull-before-Save

在**任何** "Save to GitHub" / 部署 / Re-publish 之前，必须先从 GitHub 拉最新：

```bash
cd /app && git fetch origin main && git reset --hard origin/main
```

**原因**：Emergent 平台会用 stale pod snapshot 覆盖 GitHub，且若 pod ↔ main 不同步，"Save to GitHub" 会产生 `conflict_*` 分支需要用户手工合并（已多次发生）。

主站已经加了**两层防护**参考实现：
- `/app/scripts/pre-save-check.sh` —— 手动检查工具，自动 fast-forward pod
- `/app/.git/hooks/pre-push` —— 自动兜底 Git 钩子，push 前 fetch + 若 remote 领先自动 fast-forward，diverged 时中止 push

**建议**：您也可以在智库站部署同样的 pre-push hook 保护。

### Rule #2 — robots.txt 不要碰

**禁止创建 `frontend/public/robots.txt`**。智库站 robots 由 `frontend/src/app/robots.js` 动态生成（约 30 条含 AI/中文爬虫全套），静态文件会被 Next.js 遮蔽。已经发生过两次误创，请务必避免。

---

## 🎯 待办任务

### 任务 1 · 拉取并执行 Sovereign Q&A Rewrite 脚本（高优先级）

主站已经把脚本推送到您的 repo main 分支：

**Commit**: `624d474`
**File**: `backend/rewrite_top10_headings.py`（431 行）

**它做什么**：
- 复用您现有的 `data_density_check.py` 的 `priority_score` 算法取 top-10 文章
- 对每篇文章的每个 declarative `<h2>` `<h3>` 调用 Claude Sonnet 4.6
- 按 GEO SEO 作战手册的 **4 个问句模板**（Diagnostic / Comparative / Mechanism / Quantitative）改写
- 严格校验：必须问号结尾 + 含 framework 术语（Core Code Theory / Home Model / Management Debt / DDRT / Polaris / Orion / Nova / hospitality / pricing）+ 属于 4 模板之一 + 非 forbidden lead（Overview / Introduction / Conclusion / Reflections / Thoughts on）
- **保留 `<h2 id="...">` 属性** —— JSON-LD @id 三元组不破
- MongoDB `articles.content_en` / `content_zh` 直接更新
- 幂等（已是问句的 heading 会跳过）
- 审计 TSV 输出到 `backend/_audit/headings_rewritten_YYYYMMDD_HHMMSS.tsv` 供回滚

**执行命令**（在智库站 pod 里）：

```bash
# Step 1 · 遵守 Rule #1 拉最新
cd /app && git fetch origin main && git reset --hard origin/main

# Step 2 · 先 dry-run 看建议（不写 MongoDB）
cd /app/backend && python3 rewrite_top10_headings.py --dry-run

# Step 3 · 满意就正式跑
cd /app/backend && python3 rewrite_top10_headings.py

# 可选：只处理 3 篇先测
python3 rewrite_top10_headings.py --limit 3 --dry-run

# 可选：单篇点测
python3 rewrite_top10_headings.py --slug <article-slug>
```

**跑完后**：把 `_audit/headings_rewritten_*.tsv` 发一份到主站 agent 审阅。

---

### 任务 2 · Wayback Machine 归档（用户即将做）

主站遇到网络问题：pod 到 `web.archive.org:443` 持续 `ConnectTimeoutError`。已提供 Mac 本地脚本让用户自己归档主站 URL。

**建议智库站也自查**：
```bash
# 在智库站 pod 内测试
curl -sI --connect-timeout 10 https://web.archive.org/
```

若同样超时，请一并告知用户，可能是**整个 Emergent 平台**对 IA 出站有限制，需要工单一起解决。

主站已生成的 Mac 归档脚本模板可复用（详见主站 `/app/scripts/archive_to_wayback.py`），只需替换 URL 列表即可归档智库站的 82 篇文章。

---

### 任务 3 · 跨站实体图对齐（长期，可选）

主站已完成 GEO/SEO 升级，产物：
- `/api/articles/{slug}/ai-tldr` — 6 字段 JSON-LD 数据（Core Problem / Theoretical Solution / Empirical Metric × EN+ZH）
- `/api/articles/aliases/map` — canonical URL 映射
- 每篇 HTML 内嵌 `<script type="application/ld+json" data-geo-synthesis="true">` + 可见 AI Synthesis Reference Block 卡片
- 主站现有 GEO 覆盖：**38 slugs**（8 主要文章 + 30 publications landing pages）

**为了让两站的 AI Citation 实体图完全打通**：
1. 智库站请确保 `Person` @id 指向 `https://insightbridge.global/about.html#person`（主站规范 Person entity）
2. 智库站请确保 `Organization` @id 指向 `https://insightbridge.global/index.html#org`（主站规范 Org entity）
3. 双站互相 `sameAs` 引用应该在 JSON-LD 里保留

**验证工具**（主站已有）：
- `geo_verify.py` — 15 项 GEO entity 同步验证
- 23 项 acceptance checklist

若智库站尚未跑过 `geo_verify.py`，建议跑一次。

---

### 任务 4 · robots.txt 恢复完整版（如果被覆盖）

**如果**发现 `frontend/public/robots.txt` 又被自动创建了，请：
1. **删除**该静态文件（`rm frontend/public/robots.txt`）
2. 确认 `frontend/src/app/robots.js` 输出完整（约 30 条 rules）：
   - Allow: `Googlebot`, `Bingbot`, `Baiduspider`, `YandexBot`, `Sogou`, `360Spider`
   - Allow AI: `GPTBot`, `ClaudeBot`, `PerplexityBot`, `anthropic-ai`, `Google-Extended`, `CCBot`, `FacebookBot`, `Applebot-Extended`, `Bytespider`, `PetalBot`
   - Sitemap: `https://intelligence.insightbridge.global/sitemap.xml`

---

## 📚 主站 GEO 升级参考资料

如果智库站也需要给现存文章补充 AI Synthesis Reference Block 可见卡片，可参考主站脚本模板：

| 主站脚本 | 位置 | 用途 |
|---|---|---|
| `populate_geo_static.py` | `/app/backend/` | 静态站 8 篇文章 GEO 6 字段填充 |
| `build_publication_landings.py` | `/app/backend/` | PDF/DOCX 论文批量生成 HTML landing page |
| `rewrite_top10_headings.py` | 已推到智库站 repo | Q&A 问句改写（就是本任务 1） |

**注意**：主站是静态 HTML；智库站是 Next.js + MongoDB。脚本逻辑（Claude prompt、模板、校验）可复用，但 IO 层需要改成 Next.js/MongoDB 版本。

---

## ⏱️ 主站近期完成事项摘要（2026-02-26/27）

| 时间 | 事项 |
|---|---|
| 2026-02-26 | GEO 主站移植（8 篇 GEO 6 字段 + AI Synthesis 卡片 + `/api/articles/{slug}/ai-tldr`）|
| 2026-02-26 | 30 篇 publications landing pages 生成 + publications hub + sitemap patch |
| 2026-02-27 | 中文品牌名全站统一：`InsightBridge Global LLC` → `美国洞见桥全球公司`（32 处中文可见位置）|
| 2026-02-27 | 移动/平板中文首页顶部品牌显示修复（wordmark CSS）|
| 2026-02-27 | SEO 全量推送 49 URLs 到 IndexNow / Seznam（Baidu quota 明日续推）|
| 2026-02-27 | Mac 本地 Wayback 归档脚本交付（pod 到 IA 网络阻断）|

---

## 📞 联系与协调

若您需要主站配合任何跨站 SEO/GEO 联调，请告知用户并让他转达。主站 agent 会协助。

主站现在生产 URL：**https://insightbridge.global**  
主站 Preview URL：**https://insightbridge-web.preview.emergentagent.com**  
主站 API 端点已上线：
- `GET /api/articles/{slug}/ai-tldr`
- `GET /api/articles/aliases/map`
- `POST /api/seo/push-all-geo`
- `POST /api/wayback/archive-all-geo`（当前受 IA 网络阻断影响）

---

**祝工作顺利。**  
— 主站 Emergent Agent  
2026-02-27
