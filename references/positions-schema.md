# 持仓档案 Schema（positions.json）

持仓档案是盯盘 agent 的"单一事实源"。所有报告、监控、建议都从这里读取。用户手动维护，agent 辅助计算与更新。

## 顶层结构

```json
{
  "updated": "2026-08-06",
  "account": "600888****xx",
  "positions": [ { ... }, { ... } ],
  "watchlist": [ { ... } ]
}
```

- `positions`：实际持仓（ETF / 个股 / LOF）
- `watchlist`：自选股池（用于盘前/盘中异动观察，不参与持仓信息展示）

## 单标的字段规范

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `code` | str | ✓ | 6 位代码，如 `510300` |
| `name` | str | ✓ | 名称 |
| `market` | str | ✓ | `sh` / `sz` / `bj` |
| `shares` | int | ✓ | 持仓股数 |
| `cost_price` | float | ✓ | 真实成本价（非市价） |
| `current_price` | float | ✓ | 最新价（每日收盘后更新） |
| `market_value` | float | | shares × current_price |
| `pnl` | float | | 浮动盈亏金额 |
| `pnl_pct` | float | | 浮动盈亏比例 % |
| `category` | str | | 行业ETF / 宽基ETF / 个股 / LOF |
| `strategy` | str | ✓ | 见下方"策略标签" |
| `user_intent` | str | | 用户明确意图（长持/不卖/区间提醒等），agent 不得擅自推翻 |
| `strategy_note` | str | | 当前技术/基本面备注 |
| `stop_loss` | float | ✓ | 支撑位提醒价 |
| `stop_loss_pct` | float | | (stop_loss - cost)/cost |
| `stop_loss_basis` | str | | 支撑位依据（低点/BOLL下轨等） |
| `take_profit` | float | | 压力位提醒价（若已取消则留原值 + `take_profit_status`） |
| `take_profit_pct` | float | | 压力位比例 % |
| `take_profit_basis` | str | | 压力位依据 |
| `take_profit_status` | str | | `active` / `cancelled`（长持不设压力位时标 cancelled） |
| `replenish_plan` | list | | 价格提醒计划（见下），仅区间提醒标的用 |
| `tech` | obj | | 最近技术快照：boll/macd/kdj/rsi_6 |
| `suggestion` | str | | 当前给用户的行动建议 |

## 策略标签（strategy 取值）

| 标签 | 含义 | 报告中的处理方式 |
|------|------|------------------|
| `长期` / `长持` | 长期持有，不设压力位 | 仅监控支撑位；跌破支撑才重评，**不提示减仓** |
| `中长线` | 中期偏长 | 持有 + 关键位提示 |
| `中线` / `短线` | 按技术位设提醒 | 到压力/支撑位给动作 |
| `底仓观察` | 小额底仓，不主动操作 | 不列入"该减"清单；破成本才走 |
| `区间提醒` | 底仓 + 区间提醒计划 | 列出 replenish_plan，等价格进入预设区间触发 |
| `短期不卖` | 用户暂不离场 | 触及原压力位仅提示，不催卖 |
| `卫星仓` | 战术性小仓（如个股） | 按独立策略（反弹兑现/事件驱动） |

**`user_intent` 优先级高于一切规则**：用户明确说"长持不卖/短期不卖"，agent 后续所有报告都必须遵守，不得自行推翻（除非用户改口）。

## 价格提醒计划 replenish_plan

```json
"replenish_plan": [
  { "trigger": 2.80, "shares": 5000, "note": "前低支撑上沿，底仓翻倍" },
  { "trigger": 2.70, "shares": 5000, "note": "前期平台低点下方" },
  { "trigger": 2.60, "shares": 5000, "note": "BOLL下轨，深跌补" }
]
```
原则：**不追高，只等价格回落**；每档价位 + 股数提前定好，触发即执行。

## 价格提醒配置方法

1. 拉该标的 **60 日 K 线** + 技术指标（MACD / BOLL / KDJ / RSI）。
2. **支撑位**取：近期明显低点、BOLL 下轨、前低平台。
3. **压力位**取：近期明显高点、BOLL 中轨/上轨、前高。
4. **支撑位提醒** = 支撑下方 2~3%（或用户心理防线），确保"破位即趋势坏"。
5. **压力位提醒** = 压力位或用户目标收益位。
6. 写入 `stop_loss_basis` / `take_profit_basis` 写明依据，便于复盘。
7. 同步在 westock-mcp 设原生提醒：`portfolio_tips_set` 的 `low`=支撑位、`high`=压力位。长持不设压力位则 `high` 留空。

## 示例片段

```json
{
  "code": "510300",
  "name": "沪深300ETF",
  "market": "sh",
  "shares": 1000,
  "cost_price": 4.000,
  "current_price": 4.100,
  "strategy": "长期",
  "user_intent": "长持至少三个月，不主动减仓；3.80支撑位为硬边界，破位必须重评绝不硬扛",
  "stop_loss": 3.80,
  "stop_loss_basis": "前期低点下方，BOLL下轨上方",
  "take_profit": 4.30,
  "take_profit_status": "cancelled",
  "suggestion": "长持标的，已取消压力位提醒；仅跌破支撑3.80再评估"
}
```
