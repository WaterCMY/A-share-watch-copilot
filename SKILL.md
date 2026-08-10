---
name: a-share-watch-copilot
slug: a-share-watch-copilot
description: 个人 A股/港股盯盘智能副驾（信息驱动、人在回路、非量化、非自动下单）。当用户要搭建/运营一个盯盘 agent、设计持仓管理体系、写 positions.json、跟踪场外开放式基金、设置价格提醒、配置盘前/盘后/盘中监控自动化、生成信息整理模板或盘后总结时使用。覆盖五层架构、持仓与基金 JSON schema、数据源选型（westock-mcp / westock-data CLI / 东财净值）、8 个自动化任务模板、本地看盘工作台、报告结构与踩坑经验。
version: 1.2.1
agent_created: true
displayName: "盯盘副驾"
---

# 盯盘副驾（A股 / 港股）

信息驱动、人在回路的个人盯盘智能助手。**非量化交易系统、不自动下单、只做信息聚合与决策辅助。**

## 角色定位

- **形态**：定时推送（盘前 / 盘后 / 盘中监控）+ 交互问答
- **市场**：A股 + 港股（默认）
- **风格**：混合（短 / 中 / 长线切换，按单个标的单独设策略）
- **持仓**：用户手动维护 `positions.json`，价格提醒每标的单独设，agent 仅做信息展示
- **推送策略**：仅异动触发 + 主动查询，不做无差别定时刷屏
- **关键边界**：**不下单、不代客理财、不做自动喊单**（规避投顾合规风险）

## 五层架构

```
交互层  → 定时推送 + 对话问答
决策层  → 基于规则+数据的买卖/风控建议（人在回路最终拍板）
分析层  → 技术位 / 资金面 / 基本面 / 情绪研判
感知层  → 行情 / 资金 / K线 / 新闻 / 公告抓取
数据源  → westock-mcp / westock-data CLI / market_overview
```

## 触发条件（When to Use）

- 用户要"搭建一个盯盘 agent / 个人副驾 / 盯盘助手"
- 用户要设计持仓管理体系、写或维护 `positions.json`
- 用户要设置价格提醒（支撑/压力位通知），或问"某标的该怎么跟踪"
- 用户要配置盘前摘要、盘后总结、盘中监控等定时任务
- 用户要生成信息整理模板、盘后总结、午间总结、持仓信息展示
- 用户要跟踪**场外开放式基金**（净值、持有收益、分销售平台归集）
- 关键词：盯盘、持仓、价格提醒、支撑压力、盘中监控、盘前、盘后、信息整理、风控、A股、港股、ETF、场外基金、净值、仓位、副驾

## 核心工作流

### 1. 初始化持仓档案
- 读取用户持仓截图 / 文本，提取标的信息，写入 `positions.json`
- 字段规范与意图标签见 `references/positions-schema.md`
- 用 60 日 K 线 + MACD / BOLL / KDJ / RSI 计算支撑压力位，设定价格提醒（详见该文档）
- 在 westock-mcp 设置原生到价提醒（low=支撑位 / high=压力位）作为可靠实时兜底

### 2. 配置自动化任务
- 8 个任务模板见 `references/automation-templates.md`，直接复制 rrule + prompt 即可创建
- **必须包含「断线哨兵」**：不绑定 westock，用 ToolSearch 探测 `mcp__westock-mcp__*` 工具，搜不到即推 ⚠️（连接器频繁断连时的兜底）

### 3. 日常运营
- 盘前 8:50 / 盘后 15:30 / 午间 11:30 三节点自动出报告
- 盘中每 10 分钟价格提醒监控 + 特定标的价格区间监控（仅触发时推送，否则静默）
- 报告模板见 `references/report-templates.md`

### 4. 数据源与坑点
- 选型与限制见 `references/data-sources.md`（westock-mcp 断连、market_overview 滞后、北向/两融限制、批量 kline 单股报错等）

### 5. 本地工作台（可选）
- 一个纯前端的单页看盘工作台（`workbench.example.html`）+ 本地代理（`workbench-server.py`），用于实时看盘与持仓管理，**与 agent 对话互补**：agent 负责定时推送与深度分析，工作台负责实时行情与快捷操作。
- 三个 Tab：**📊 个人持仓**（场内）/ **🌐 大盘全景**（指数、市场宽度）/ **🐔 养鸡场**（场外基金）。
- 能力：实时行情（60s 刷新）、持仓表格（表头排序）、K线/分时/周K弹窗（MA5/10/20/120/250 + 量能）、手动录入仓位、卖出减仓（核算已实现盈亏）、调整成本价/股数、一键同步回 `positions.json`。
- 架构与搭建步骤见 `references/workbench-guide.md`；示例代码（脱敏）见 `assets/workbench.example.html` 与 `assets/workbench-server.py`。
- **合规**：工作台仅为个人信息整理工具，不含投顾逻辑、不自动下单；示例代码中所有持仓均为虚构数据。

### 6. 场外基金跟踪「养鸡场」（可选）
- 工作台第三个 Tab，跟踪**场外开放式基金**，数据独立存放于 `funds.json`（不与 `positions.json` 混用）。
- 与场内持仓的本质差异：场外基金**只有每个交易日公布的单位净值**，没有实时价、没有分时/K线、也没有盘中支撑压力位——因此该页不提供 K 线弹窗与价格提醒。
- 净值数据源：东方财富 `api.fund.eastmoney.com/f10/lsjz`（取最近两条记录，最新为现价、次条算日涨跌）。
  - ⚠️ 旧接口 `fundgz.1234567.com.cn` 的实时估值已失效，勿再使用。
- **分销售平台管理**：每只基金带 `source` 字段标记购买平台；页面顶部有平台筛选（全部 / 各平台）与**平台总览表**，分平台及合计展示总市值、持有收益、收益率、今日涨跌、基金数。
- 使用：`＋ 录入基金` → 填 6 位代码 / 份额 / 成本净值 / 平台 → `🔄 同步到后端` 写回 `funds.json`。
- 字段说明与模板见 `assets/funds.template.json`；使用细节见 `references/workbench-guide.md`。

## 风控与合规铁律

1. **人在回路**：所有信息展示仅供参考，agent 绝不自动下单
2. **红线即底线**：每标的可设价格提醒；触发才提示，平时不打扰
3. **A股配色**：涨=红、跌=绿（中国习惯），所有图表 / 报告遵守
4. **合规边界**：只做"信息驱动 + 人在回路"的辅助，不输出"保证收益 / 必买必卖"式喊单
5. **数据失效兜底**：westock-mcp 断连时，腾讯自选股 App 原生到价提醒仍独立推送，靠这一层兜底

## 资源索引

| 资源 | 用途 |
|------|------|
| `references/positions-schema.md` | 持仓 JSON schema、意图标签、价格提醒配置方法 |
| `references/automation-templates.md` | 8 个自动化任务 prompt + rrule |
| `references/data-sources.md` | 数据源选型与踩坑经验 |
| `references/report-templates.md` | 盘前/盘后/午间/信息整理报告结构 |
| `references/workbench-guide.md` | 本地工作台架构、能力与搭建步骤（含养鸡场） |
| `assets/positions.template.json` | 场内持仓文件模板（可直接复制改） |
| `assets/funds.template.json` | 场外基金（养鸡场）文件模板与字段说明 |
| `assets/workbench.example.html` | 本地工作台前端示例（脱敏，虚构持仓与基金） |
| `assets/workbench-server.py` | 本地工作台代理服务示例 |

## 数据安全提示

`positions.json` 与 `funds.json` 含个人真实持仓，**已在 `.gitignore` 中排除，切勿提交到任何公开仓库**。仓库内 `assets/` 下的模板与示例均为虚构数据。
