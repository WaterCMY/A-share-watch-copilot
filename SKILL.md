---
name: a-share-watch-copilot
description: 个人 A股/港股盯盘智能副驾（信息驱动、人在回路、非量化、非自动下单）。当用户要搭建/运营一个盯盘 agent、设计持仓管理体系、写 positions.json、设置止损止盈与补仓策略、配置盘前/盘后/盘中监控自动化、生成交易计划或盘后总结时使用。覆盖五层架构、持仓 JSON schema、数据源选型（westock-mcp / westock-data CLI）、8 个自动化任务模板、报告结构与踩坑经验。
version: 1.0.0
agent_created: true
display_name: "盯盘副驾"
---

# 盯盘副驾（A股 / 港股）

信息驱动、人在回路的个人盯盘智能助手。**非量化交易系统、不自动下单、只做信息聚合与决策辅助。**

## 角色定位

- **形态**：定时推送（盘前 / 盘后 / 盘中监控）+ 交互问答
- **市场**：A股 + 港股（默认）
- **风格**：混合（短 / 中 / 长线切换，按单个标的单独设策略）
- **持仓**：用户手动维护 `positions.json`，止损/止盈每标的单独设，agent 仅给建议
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
- 用户要设置止损 / 止盈 / 补仓线，或问"某标的该什么策略"
- 用户要配置盘前摘要、盘后总结、盘中监控等定时任务
- 用户要生成交易计划、盘后总结、午间总结、持仓建议
- 关键词：盯盘、持仓、止损、止盈、补仓、盘中监控、盘前、盘后、交易计划、风控、A股、港股、ETF、仓位、副驾

## 核心工作流

### 1. 初始化持仓档案
- 读取用户持仓截图 / 文本，提取标的信息，写入 `positions.json`
- 字段规范与意图标签见 `references/positions-schema.md`
- 用 60 日 K 线 + MACD / BOLL / KDJ / RSI 计算支撑压力位，设定止损 / 止盈（详见该文档）
- 在 westock-mcp 设置原生到价提醒（low=止损 / high=止盈）作为可靠实时兜底

### 2. 配置自动化任务
- 8 个任务模板见 `references/automation-templates.md`，直接复制 rrule + prompt 即可创建
- **必须包含「断线哨兵」**：不绑定 westock，用 ToolSearch 探测 `mcp__westock-mcp__*` 工具，搜不到即推 ⚠️（连接器频繁断连时的兜底）

### 3. 日常运营
- 盘前 8:50 / 盘后 15:30 / 午间 11:30 三节点自动出报告
- 盘中每 10 分钟止损止盈监控 + 特定标的回踩补仓监控（仅触发时推送，否则静默）
- 报告模板见 `references/report-templates.md`

### 4. 数据源与坑点
- 选型与限制见 `references/data-sources.md`（westock-mcp 断连、market_overview 滞后、北向/两融限制、批量 kline 单股报错等）

## 风控与合规铁律

1. **人在回路**：所有买卖建议最终由用户决策，agent 绝不自动下单
2. **红线即底线**：每标的必须设止损；止损线破位才动，平时不打扰
3. **A股配色**：涨=红、跌=绿（中国习惯），所有图表 / 报告遵守
4. **合规边界**：只做"信息驱动 + 人在回路"的辅助，不输出"保证收益 / 必买必卖"式喊单
5. **数据失效兜底**：westock-mcp 断连时，腾讯自选股 App 原生到价提醒仍独立推送，靠这一层兜底

## 资源索引

| 资源 | 用途 |
|------|------|
| `references/positions-schema.md` | 持仓 JSON schema、意图标签、止损止盈设定法 |
| `references/automation-templates.md` | 8 个自动化任务 prompt + rrule |
| `references/data-sources.md` | 数据源选型与踩坑经验 |
| `references/report-templates.md` | 盘前/盘后/午间/计划/建议报告结构 |
| `assets/positions.template.json` | 持仓文件模板（可直接复制改） |
