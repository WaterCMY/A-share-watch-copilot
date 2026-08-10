# CN No.1盯盘副驾（A股 / 港股 个人投资效率助手）— Skill 模板

> 一个用于搭建**个人盯盘智能助手**的 WorkBuddy Skill（方法论 + 可复用模板）。
> 定位：**信息驱动、人在回路、非量化、非自动下单**。

---

## ⚠️ 重要免责声明 / DISCLAIMER

### 中文

1. **本项目仅供个人学习、研究与效率提升使用，不构成任何证券、投资、交易或财务建议。**
2. 作者及贡献者对任何依据本项目内容做出的投资决策、交易行为及其后果**不承担任何责任**。
3. **投资有风险，入市须谨慎。** 使用者须自行判断并承担全部风险与盈亏。
4. 本项目坚持**「人在回路」原则**：所有买卖决策由使用者本人做出；本项目**不自动下单、不保证收益、不进行喊单、不提供具体买卖点**。
5. 使用者须遵守所在地相关法律法规（包括但不限于中国证券监督管理委员会关于证券投资咨询业务的规定），**不得将本项目用于非法证券咨询、荐股、代客理财等用途**。
6. 本项目**不含任何真实个人持仓数据**；文档与模板中的代码、价格、仓位均为**虚构示例**，仅用于说明文件格式与配置方法。
7. 本项目涉及的市场数据、行情接口、商标等权利归各自所有者所有。

**如您不同意上述条款，请勿使用本项目。**

### English

1. This project is for **personal learning, research, and productivity only**. It does **NOT** constitute any securities, investment, trading, or financial advice.
2. The author and contributors accept **no liability** for any investment decisions, trades, or consequences derived from this project.
3. **Investing carries risk.** Users must make their own judgments and bear all risk and profit/loss.
4. This project follows a **"human-in-the-loop"** principle: all buy/sell decisions are made by the user. It **does NOT auto-trade, guarantee returns, send trading signals, or provide specific entry/exit points**.
5. Users must comply with all applicable laws and regulations in their jurisdiction (including, without limitation, rules of the China Securities Regulatory Commission regarding securities investment advisory services), and **must NOT use this project for unlawful securities advisory, stock tipping, or discretionary asset management**.
6. This project **contains no real personal holdings**. All codes, prices, and positions in the docs/templates are **fictional examples** for illustration only.
7. Market data, quoting APIs, and trademarks referenced belong to their respective owners.

**If you do not agree with the above, do not use this project.**

---

## 项目简介

本 Skill 把「如何搭建并运营一个个人盯盘助手」的方法论沉淀为可复用资产，覆盖：

- **五层架构**：交互层 → 决策层 → 分析层 → 感知层 → 数据源
- **持仓管理体系**：`positions.json` schema、意图标签（长持 / 中线 / 卫星仓 / 区间提醒…）、价格提醒配置方法
- **8 个自动化任务模板**：盘前摘要 / 竞价速览 / 盘中价格监控 / 午间总结 / 特定标的价格区间监控 / 盘后总结 / 断线哨兵（含 rrule + prompt）
- **数据源选型与踩坑经验**：westock-mcp 断连兜底、market_overview 滞后、批量 kline 单股报错等
- **报告模板**：盘前 / 盘后 / 午间 / 信息整理模板 / 持仓信息展示

## 功能特性

- 📊 盘前 / 盘后 / 午间自动生成市场与持仓报告
- 🔔 盘中异动监控（仅触发时推送，不刷屏）
- 📉 每标的独立设价格提醒（支撑/压力位通知）
- 🛡️ 断线哨兵：数据源连接器掉线时及时告警
- 📱 PC 端配置 + 移动端（小程序 / App）实时接收推送、随时问答、到价弹窗
- 🖥️ **本地工作台（可选）**：单页看盘 HTML + 本地代理，三个 Tab（个人持仓 / 大盘全景 / 养鸡场），支持实时行情、K线/分时弹窗、手动录入/卖出减仓/调整成本、一键同步回持仓档案
- 🐔 **养鸡场（场外基金）**：跟踪场外开放式基金每日净值与持有收益，支持按销售平台分组筛选与平台总览（分平台 + 合计）
- 🔒 人在回路：只辅助决策，不代你下单

## 快速开始

1. **安装 Skill**：将本目录解压 / 复制到 `~/.workbuddy/skills/a-share-watch-copilot/`（或在 WorkBuddy 客户端导入）。
2. **连接数据源**：启用 `westock-mcp`（腾讯自选股）连接器并信任；详见 `references/data-sources.md`。
3. **建立持仓**：复制 `assets/positions.template.json` 为你的 `positions.json`，**替换为你的真实持仓**（注意：此文件含个人数据，请勿提交到公开仓库，见 `.gitignore`）。
4. **创建自动化任务**：按 `references/automation-templates.md` 的 rrule + prompt 创建 8 个定时任务。
5. **设置原生提醒**：在 westock 设为 each 标的的到价提醒（low=支撑位 / high=压力位）作为实时兜底。
6. **（可选）搭建本地工作台**：将 `assets/workbench.example.html` 与 `assets/workbench-server.py` 复制到 `positions.json` 同目录，`python workbench-server.py` 启动后访问 `http://localhost:8801`。详见 `references/workbench-guide.md`。
7. **（可选）启用养鸡场**：若要跟踪场外开放式基金，再复制 `assets/funds.template.json` 为同目录下的 `funds.json` 并替换为你的基金持仓（同样含个人数据，已在 `.gitignore` 中排除）。

> 更详细的上手路径见 `references/` 下各文档。

## 目录结构

```
a-share-watch-copilot/
├── SKILL.md                       # Skill 核心说明（角色/架构/工作流/合规）
├── README.md                      # 本文件
├── LICENSE                        # MIT + 投资风险提示
├── .gitignore                     # 忽略个人持仓等敏感文件
├── assets/
│   ├── positions.template.json    # 场内持仓文件模板（示例数据）
│   ├── funds.template.json        # 场外基金（养鸡场）模板与字段说明
│   ├── workbench.example.html     # 本地工作台前端示例（脱敏）
│   └── workbench-server.py        # 本地工作台代理服务示例
└── references/
    ├── positions-schema.md        # 持仓 JSON schema 与意图标签
    ├── automation-templates.md     # 8 个自动化任务模板
    ├── data-sources.md            # 数据源选型与踩坑经验
    ├── report-templates.md        # 报告结构模板
    └── workbench-guide.md         # 本地工作台架构与搭建指南（含养鸡场）
```

## 合规与法律

使用本项目即表示您同意：

- 您将本项目及任何衍生内容**仅用于个人合法用途**；
- 您不会将其包装为「投资顾问」对外提供收费或免费的证券建议；
- 您理解并同意，任何投资决策的风险由您自行承担，与本项目作者无关。

如您所在地区对证券投资辅助工具另有监管要求，请以当地法规为准。

## License

[MIT](./LICENSE) — 详见 LICENSE 文件。本项目按「现状」提供，不提供任何明示或暗示担保，包括但不限于适用性、特定用途适用性及非侵权的担保；作者不对使用后果负责。
