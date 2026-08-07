# 自动化任务模板（8 个）

所有任务 `scheduleType=recurring`，`status=ACTIVE`。rrule 仅覆盖交易日（周一至五），自动跳过周末与法定假日。午休 11:50–13:00 不在 BYHOUR 列表内，天然不触发。

> 创建方式：用 `automation_update` 工具，`mode=create`，填 `name` / `prompt` / `rrule` / `scheduleType=recurring` / `status=ACTIVE`。依赖 westock 的任务填 `connectorIds=["westock-mcp"]`，断线哨兵**不填**。

---

## 1. 盘前摘要（08:50）

- **rrule**：`FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYHOUR=8;BYMINUTE=50`
- **prompt**：
```
生成今日盘前摘要：① 拉取隔夜要闻/外围市场（美股/港股/大宗）与今日重大事件；
② 读取 positions.json，列持仓速览（代码/成本/现价/盈亏/距止损止盈空间）；
③ 标注今日需重点关注的止损/止盈预警标的；
④ 给出今日态度（持有/观察/可操作）。报告用中文，涨红跌绿，控制在 300 字内。
```

## 2. 盘前竞价速览（09:27）

- **rrule**：`FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYHOUR=9;BYMINUTE=27`
- **prompt**：
```
生成竞价速览：拉取持仓与自选股集合竞价表现（高开/低开/量能），对照昨日收盘判断强弱；
对持仓中开盘异动（±2%以上）做一句话解读。中文，涨红跌绿，200 字内。
```

## 3. 止损止盈盘中监控（每 10 分钟）

- **rrule**：`FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYHOUR=9,10,11,13,14;BYMINUTE=0,10,20,30,40,50`
- **connectorIds**：`["westock-mcp"]`
- **prompt**：
```
盘中监控（每10分钟）：读取 positions.json，对每标的计算现价距止损/止盈比例。
仅当满足以下任一条件才推送：① 逼近止损≤2% 或 跌破；② 逼近止盈≤3% 或 突破；
③ 用户标记短期不卖的标的，触及原止盈仅提示不催卖；④ 长持标的仅报止损触发。
其余情况静默。推送用中文，涨红跌绿，列出代码/现价/触发类型/建议动作。
```

## 4. 午间总结（11:30）

- **rrule**：`FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYHOUR=11;BYMINUTE=30`
- **connectorIds**：`["westock-mcp"]`
- **prompt**：
```
生成午间总结：① 上午大盘（上证/深成/创业/科创50）涨跌与形态；
② 持仓上午盈亏与异动；③ 下午风险提示与关注点。中文，涨红跌绿，250 字内。
对长持/短期不卖标的按 positions.json 的 user_intent 处理，不催卖。
```

## 5. 科创50 回踩补仓监控（每 10 分钟）

- **rrule**：同 #3（`BYHOUR=9,10,11,13,14;BYMINUTE=0,10,20,30,40,50`）
- **connectorIds**：`["westock-mcp"]`
- **prompt**：
```
监控示例ETF(510300)回踩补仓区间：① 价格 ∈ [3.80, 3.95] → 推送 🔵 可补仓；
② 价格 < 3.80 → 推送 ⚠️ 深跌预警；③ 区间上方 → 静默。中文，简洁。
```

## 6. 盘后总结（15:30）

- **rrule**：`FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYHOUR=15;BYMINUTE=30`
- **connectorIds**：`["westock-mcp"]`
- **prompt**：
```
生成盘后总结：① 今日大盘与热门板块；② 持仓当日盈亏、风险点；③ 资金面要点（主力净流入/流出靠前标的）；
④ 明日关注。中文，涨红跌绿。对长持/短期不卖标的依 user_intent 仅提示不催卖。
北向资金 ETF 查不到时注明"ETF 非沪深股通标的，无法纳入"。
```

## 7. 断线哨兵（每 15 分钟）

- **rrule**：`FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYHOUR=9,10,11,13,14;BYMINUTE=0,15,30,45`
- **connectorIds**：**不填**（关键：自身不能依赖 westock）
- **prompt**：
```
断线哨兵：用 ToolSearch 探测 `mcp__westock-mcp__*` 工具是否仍在索引中。
- 搜到 → 静默；
- 搜不到（返回 No matching tools） → 判定 westock-mcp 已断连，立即推送 ⚠️ 提醒，
  内容含：受影响自动化清单（止损监控/科创50回踩/午间/盘后）+ 重连指引（连接器页点"信任"）。
```

## 8. （可选）交易计划 / 次日策略

- 非固定时刻，由用户在盘后触发；或设一次性 `scheduleType=once`。
- 结构见 `report-templates.md` 的"交易计划"模板。

---

### 依赖与失效兜底

- 任务 #2/#3/#4/#5/#6 依赖 westock-mcp。连接器断连时这些任务失败，但**腾讯自选股 App 原生到价提醒仍独立推送**，靠这一层兜底。
- 任务 #7 不依赖任何连接器，专门负责"断连早发现"。
- 创建后建议用户在 WorkBuddy 连接器页面对 westock-mcp 点一次"信任"以确保激活。
