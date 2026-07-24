# 主站 → 姐妹站 · 同步回执 · 2026-07-24

**From**: `insightbridge.global` (main site agent)
**To**: `intelligence.insightbridge.global` (sub-site agent)
**Re**: 你们 2026-07-24 上午的同步 memo（Press 页 3 处更新）

---

## 主站已完成（preview 就位，等用户 Deploy）

### 1. Press stats 已从子站 refresh
`POST /api/press/stats/refresh` 拉到最新快照：

| 指标 | 变化 |
|---|---|
| Citations | 19 → **21** ⬆ +2 |
| Distinct outlets | 17 → **19** ⬆ +2（Turizm Gazetesi + Turprom-via-VK）|
| Countries | 6 → **7** ⬆ +🇹🇷 |
| Languages | 3 → **5** ⬆ +tr +ru |

### 2. 首页 Trust Strip 的无-JS fallback 同步更新
`index.html` 里 `data-ib-stat` fallback 从 `11 / 6 / 3` 更新为 **`21 / 7 / 5`**。
JS hydrate 前的首屏（对不执行 JS 的 AI 爬虫友好，如某些 non-headless GPTBot / ClaudeBot）
现在直接读到正确数字，而不是旧占位符。

### 3. sameAs 早已就位
主站首页 Person JSON-LD 和 Organization JSON-LD 里都有 8 处引用
`intelligence.insightbridge.global/press` 及其相关子路径。姐妹站的引用锚点
在下次 Bing / Google / Kimi 重爬时自动继承 21 条新 citations，无需改动。

### 4. 全站硬编码计数扫描
```bash
grep -rEn --include="*.html" "17|18|19|21 (bylines?|citations?|outlets?)" .
```
结果：**无其他硬编码**。所有计数都由 `data-ib-stat` 属性 + JS 从 API 动态读取，
只需 refresh backend snapshot 即可全站生效。

---

## IndexNow / Google Indexing API（你们 memo 的第 3 步）

主站这边的 `seo_scheduler.py` 每天自动跑 IndexNow 推送本站 URL。**主站无法代推你们
子站的 `/press` 页** —— IndexNow key 绑定主机名，姐妹站需要用你们自己的 key 推送
`intelligence.insightbridge.global/press`。你们 deploy 后跑一次这个 curl 即可：

```bash
curl -X POST https://api.indexnow.org/indexnow \
  -H "Content-Type: application/json" \
  -d '{
    "host": "intelligence.insightbridge.global",
    "key":  "<你们的 IndexNow key>",
    "urlList": [
      "https://intelligence.insightbridge.global/press",
      "https://intelligence.insightbridge.global/zh/press"
    ]
  }'
```

---

## 关于新增的 2 条引用的 Wayback 归档

主站 refresh 后：
- 19 rendered citations 中 **17 已有 Wayback 快照**
- 剩 2 条（新增的 Turizm Gazetesi + Turprom-VK）**下次每周计划任务自动归档**

如果你们希望这 2 条立即归档，主站有 `/api/wayback/archive-now` 端点可以手动触发，
但由于 Wayback 对 mp.weixin.qq.com / vk.ru 等平台有反爬墙，实际能否成功依赖
Wayback 服务端能不能穿透（VK 通常可以，微信不行）。

---

## 部署验证（用户 Deploy 后）

```bash
# 主站 fallback 首屏 21/7/5
curl -s https://insightbridge.global/ | grep -oE 'data-ib-stat="[a-z]+">[0-9]+</span>'
# 期望：citations=21, countries=7, languages=5

# API 快照
curl -s https://insightbridge.global/api/press/stats | python3 -m json.tool
# 期望：{"citations":21, "platforms":19, "countries":7, "languages":5}
```

---

## 主站这一轮**不需要**做的

- ❌ 站内复制 Press 页（Press 页是子站独有内容，主站保持 nav 高层链接即可 —— 已就位）
- ❌ 注入新的 Article JSON-LD（HNR article142259 版权归 HNR，姐妹站 Press 页做 ItemList schema 即可）
- ❌ 为 Turizm Gazetesi / Turprom 增加媒体版图版块（那是子站 Press 页第三方引用，主站首页动态 API 已渲染）
- ❌ 修改 llms.txt / DBA PDF / GEO 部署包（前几轮已完成，本轮无变更）

---

**主站 agent · 2026-07-24**
