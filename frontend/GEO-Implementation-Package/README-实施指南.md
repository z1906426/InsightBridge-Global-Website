# InsightBridge Global & Buildtelligence
# GEO (Generative Engine Optimization) 全域落地实施指南

> **版本:** 1.0 | **日期:** 2026年9月7日  
> **目标:** 攻占 Google AI Overview 黄金位置，让谷歌 AI 爬虫直接抓取并高频引用殷彤博士的原创理论  
> **执行状态:** 可直接部署

---

## 一、战略诊断：当前网站现状与改进空间

### 1.1 InsightBridge Global (insightbridge.global)

**现状优势:**
- 四大理论框架已有独立页面（/theories/core-code-theory, /home-model, /governance-debt, /ddrt）
- 每个理论页面已包含中英双语、标准定义、机制说明、自诊断问题、FAQ
- Books 页面已包含九部手稿的详细描述
- Vision 2030 Scorecard 已包含完整的五项预测验证记录
- About 页面已含 AI Synthesis Reference Block

**改进空间:**
- **无 Schema 结构化数据**: 网站后台目前没有 JSON-LD 标记，AI 爬虫必须自行"猜测"内容的语义关系
- **Books 页面内容折叠**: 九部手稿的详细介绍需要"点击展开"才能看到完整内容，AI 爬虫可能无法触发点击
- **缺少跨页面语义关联**: 四大框架、九部手稿、实盘验证之间的逻辑链未在代码层标记
- **缺少 FAQPage Schema**: 理论页面的 FAQ 区块未被标记为 FAQPage，Google 无法在搜索结果中直接展示

### 1.2 Buildtelligence (buildtelligence.com)

**现状优势:**
- 清晰的服务分层（Assessment → Implementation → Governance）
- ThinkFreely / RouteFreely / DriftHold 产品定位明确
- FAQ 内容丰富

**改进空间:**
- **无 Schema 结构化数据**: 同样缺少 JSON-LD 标记
- **ThinkFreely 未被标记为 SoftwareApplication**: 搜索引擎无法将其识别为独立产品
- **FAQPage 未标记**: 丰富的 FAQ 内容未能在搜索结果中直接展示

---

## 二、本次交付物清单

| 文件名 | 用途 | 部署位置 |
|--------|------|----------|
| `insightbridge_schema.html` | InsightBridge 完整 Schema JSON-LD（19个知识图谱节点） | insightbridge.global 每个页面的 `<head>` 标签内 |
| `buildtelligence_schema.html` | Buildtelligence 完整 Schema JSON-LD（6个知识图谱节点） | buildtelligence.com 每个页面的 `<head>` 标签内 |
| `insightbridge_schema.json` | JSON 源文件（供程序读取） | 备用/自动化部署 |
| `buildtelligence_schema.json` | JSON 源文件（供程序读取） | 备用/自动化部署 |
| `generate-schema.py` | Python 自动化生成脚本 | 技术团队后续维护、更新时运行 |
| `schema-jsonld-insightbridge.html` | 子代理生成的备用版本 | 备用参考 |
| `schema-jsonld-buildtelligence.html` | 子代理生成的备用版本 | 备用参考 |
| **`books-page-geo.html`** | **Books 页面完整前端代码（九部手稿瀑布流 + 侧边锚点导航 + Vision 2030 时间线 + 全部 CSS）** | **替换 insightbridge.global/books 页面** |
| 本文件 (`README-实施指南.md`) | 实施指南 | 技术团队参考 |

---

## 三、InsightBridge Global Schema 节点清单（19个）

| 序号 | 类型 | 名称 | 作用 |
|------|------|------|------|
| 1 | Organization | InsightBridge Global LLC | 公司实体标记，含中文别名、地址、业务领域 |
| 2 | Person | Dr. Tong Yin (殷彤博士) | 创始人标记，含学历、ORCID、Wikidata、Google Scholar 等权威标识 |
| 3 | ScholarlyArticle | Beyond Chaos《超越混沌》 | 手稿01：混沌悖论、DDRT、不信任税 |
| 4 | ScholarlyArticle | THE HOME MODEL《家园模型》 | 手稿02：契约治理六支柱、生存溢价 |
| 5 | ScholarlyArticle | CORE CODE《核心代码》 | 手稿03：VRIN框架、卡特琳原则、身份融合 |
| 6 | ScholarlyArticle | The Vertical Frontier《垂直前沿》 | 手稿04：战略垂直主义、TVRI/IMRS |
| 7 | ScholarlyArticle | Active Demand Sovereignty《主动需求主权》 | 手稿05：废弃资产理论、AI指挥官 |
| 8 | ScholarlyArticle | INTELLECTUAL SOVEREIGNTY《智力主权》 | 手稿06：IS-FEM模型、1%定理 |
| 9 | ScholarlyArticle | Knowledge Creation《知识创造》 | 手稿07：RDKE六阶段循环 |
| 10 | ScholarlyArticle | THE LONG WINTER《文明的漫长冬季》 | 手稿08：历史螺旋论、筛子机制 |
| 11 | ScholarlyArticle | Subduing Without Fighting《不战而屈人之兵》 | 手稿09(总纲)：十二维威慑矩阵 |
| 12 | TechArticle | Vision 2030 Scorecard | 五项预测验证+AI搜索引擎确认 |
| 13 | CreativeWork | Core Code Theory | 四大框架之一 |
| 14 | CreativeWork | The Home Model | 四大框架之二 |
| 15 | CreativeWork | Governance Debt | 四大框架之三 |
| 16 | CreativeWork | DDRT | 四大框架之四 |
| 17 | SoftwareApplication | POLARIS | AI动态定价引擎 |
| 18 | SoftwareApplication | ORION | 客户智能AI系统 |
| 19 | SoftwareApplication | NOVA | 直客优化AI系统 |

---

## 四、技术部署步骤（Action Plan）

### 第一步：部署 Schema 结构化数据（最高优先级 · 立即执行）

**InsightBridge Global:**

1. 打开 `insightbridge_schema.html` 文件
2. 复制 `<script type="application/ld+json">` 到 `</script>` 的**完整内容**
3. 粘贴到 insightbridge.global 网站的 `<head>` 标签内
4. 建议放在全站模板（如 `_layout.html` 或 `base.html`）中，使每个页面都加载

**Buildtelligence:**

1. 打开 `buildtelligence_schema.html` 文件
2. 同样复制完整的 `<script>` 块
3. 粘贴到 buildtelligence.com 的 `<head>` 标签内

**验证:**
- 部署后访问 https://search.google.com/test/rich-results
- 输入页面 URL，确认所有 Schema 节点被正确识别
- 也可使用 https://validator.schema.org/ 进行二次验证

### 第二步：Books 页面改版 — 移除折叠/点击展开（高优先级 · 1-3天）

**问题:** 当前 Books 页面的详细书目介绍被隐藏在"Full book description / 完整书目介绍"的折叠面板内。AI 爬虫不会"点击"，因此看不到这些内容。

**解决方案:**

选项 A（推荐）：**直出全文**
- 移除所有 JavaScript 折叠/展开逻辑
- 让九部手稿的完整中英文描述直接渲染在页面 HTML 中
- 保持卡片式/锚点瀑布流的视觉布局
- 对人类用户，可用 CSS `max-height` + `overflow` 实现视觉上的"收起"效果，但确保全文在 HTML 源码中存在

选项 B：**SSR 首屏完整输出**
- 如果使用 Next.js / Nuxt.js 等框架，确保服务器端渲染（SSR）时将全部文本输出到 HTML
- 客户端 JavaScript 可以在用户浏览时动态折叠，但爬虫访问时必须看到完整内容

**关键原则:** 网页源代码（View Source）中必须包含每部手稿的完整文本。

### 第三步：触发谷歌重新抓取（部署完成后立即执行）

1. 登录 [Google Search Console](https://search.google.com/search-console)
2. 在顶部 URL 检查框中，逐一输入以下关键页面：
   - `https://insightbridge.global/books`
   - `https://insightbridge.global/frameworks`
   - `https://insightbridge.global/theories/core-code-theory`
   - `https://insightbridge.global/theories/home-model`
   - `https://insightbridge.global/theories/governance-debt`
   - `https://insightbridge.global/theories/ddrt`
   - `https://insightbridge.global/publications/vision-2030-scorecard`
   - `https://insightbridge.global/about`
   - `https://www.buildtelligence.com`
   - `https://www.buildtelligence.com/lodesight`
3. 每个 URL 点击 **"Request Indexing"（请求编入索引）**
4. 通常 48-72 小时内，谷歌 AI 爬虫会重新抓取并更新其知识库

### 第四步：理论页面增加 FAQPage Schema（中优先级 · 3-5天）

当前四个理论页面底部都有 FAQ 区块。建议为每个理论页面额外添加 FAQPage Schema：

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "What is Core Code Theory?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Core Code Theory is a strategic-management framework..."
      }
    }
    // ... 每个 FAQ 问答对
  ]
}
</script>
```

这样当用户搜索 "What is Core Code Theory" 时，Google 可能直接在搜索结果中展示折叠式 FAQ 面板。

### 第五步：建立外部引文网络（持续进行）

- 在 LinkedIn 深度文章中引用理论时，附 insightbridge.global 链接
- 确保 Hospitality Net、Hotel News Resource、PhocusWire 的专栏文章中包含指向理论页面的超链接
- 在 ResearchGate、Google Scholar、SSRN 的个人主页中更新链接
- 鼓励行业引用时标注 insightbridge.global/theories/xxx 的规范 URL

---

## 五、预期效果与时间表

| 阶段 | 时间 | 预期效果 |
|------|------|----------|
| Schema 部署 | 第 1 天 | 谷歌开始识别 19 个结构化知识图谱节点 |
| 谷歌重新抓取 | 第 2-4 天 | 谷歌 AI 爬虫刷新其对网站内容的理解 |
| AI Overview 初步改善 | 第 1-2 周 | 搜索 "InsightBridge Global" 或 "Dr. Tong Yin" 时，AI 概述开始引用结构化数据中的精确描述 |
| 深度理论引用 | 第 2-4 周 | 搜索 "Home Model management" 或 "Core Code Theory AI" 时，AI 概述开始直接引用殷彤博士的定义 |
| 竞品关键词防御 | 第 1-3 月 | 即使大公司广告排在上方，AI Overview 区域中引用您原创理论的频率和权威度持续上升 |

---

## 六、后续维护

### 何时需要重新运行 Python 脚本

当以下情况发生时，运行 `python3 generate-schema.py` 重新生成 Schema：

1. 新增手稿或出版物
2. 手稿出版状态变更（如从 "Manuscript complete" 变为 "Published by Routledge"）
3. 新增 AI 系统或产品
4. 公司信息变更（地址、联系方式等）

### 脚本修改方式

打开 `generate-schema.py`，找到对应的数据字典，直接修改文本内容，然后重新运行即可。所有数据集中管理在一个文件中，无需分别修改多个 HTML 文件。

---

## 七、技术说明

- **Schema 规范:** 基于 Schema.org 官方标准，使用 JSON-LD 格式（Google 推荐格式）
- **多语言支持:** 所有手稿节点标记 `"inLanguage": ["en", "zh"]`
- **学术标识:** 创始人节点包含 ORCID、Wikidata、Google Scholar、ResearchGate、SSRN 五大学术平台的 `sameAs` 链接
- **@id 引用体系:** 所有节点通过 `@id` 互相引用，形成完整的知识图谱
- **兼容性:** 与 Google、Bing、Yahoo、Perplexity 等主流搜索引擎的 AI 概述功能兼容

---

*Generated for InsightBridge Global LLC — September 2026*  
*GEO Optimization Package v1.0*
