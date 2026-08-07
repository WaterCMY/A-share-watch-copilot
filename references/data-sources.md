# 数据源选型与踩坑经验

盯盘 agent 的数据链路，实测踩过的坑都记这里，照着用能少走弯路。

## 一、westock-mcp（腾讯自选股连接器）

**能力**：实时行情、资金流、K线、技术指标、持仓管理、`portfolio_tips_set` 到价提醒。
**调用**：通过 MCP 工具 `mcp__westock-mcp__*` 直接调用（无需命令行）。

**⚠️ 致命痛点：频繁断连**
- 现象：交易日多次 `disconnected`，依赖它的自动化（盘前/竞价/价格监控/午间/盘后/区间监控）在断连时段全部失败。
- 原因：桥接自选股会话 + 服务端不稳 + 无自动重连。
- 应对：
  1. **原生 App 提醒 = 可靠实时层**：`portfolio_tips_set` 设的 low/high 到价提醒由腾讯自选股 App 独立推送，断连也不受影响 → 这是底线兜底。
  2. **WorkBuddy 自动化 = best-effort 提前预警层**：断连即失效，需"断线哨兵"补位。
  3. 用户需在连接器页面点"信任"重连；无自动重连机制时，断线哨兵负责及时告警。

**设置原生提醒示例**：
```
portfolio_tips_set(code="sh510300", high="", low="3.80")   # 取消压力位提醒、改设支撑位提醒
portfolio_tips_set(code="sh159915", high="", low="1.86")   # 长持：取消压力位提醒、保留支撑位提醒
```

## 二、westock-data CLI（命令行数据）

独立 CLI，不依赖 MCP 会话，适合批量拉历史数据。

```bash
npx -y westock-data-skillhub@1.0.5 <subcommand> <args>
# 子命令：kline / technical / fund flow / chip / score / market-overview / report
```

常用：
- `kline sh510300,sz159915 --period day --limit 60` 批量日K（多代码逗号分隔）
- `technical sh510300 --indicator macd,boll,kdj,rsi`
- `fund flow sh510300` 资金流向
- `score sh510300` 综合评分
- `market-overview` 大盘画像
- `report list sh510300 --limit 5` 研报资讯

**坑**：
- **批量 kline 单股报错**：如 `sh510300` 在批量接口返回"单股数据"错误 → 单独用 `kline sh510300` 拉即可。
- **限频**：连续多命令易 502/ENOTFOUND，单发重试、降低并发。
- **LOF 类不支持**：如招商中证白酒LOF `161725` 在 westock 模拟盘/部分接口无返回 → 走本地 positions.json 跟踪。

## 三、market_overview（聚合接口）

- 返回 28 字段市场评分（情绪/估值/趋势/风格等），适合盘后总评。
- **⚠️ 关键限制：date 滞后一天**。所有 type 返回的 date 都是上一交易日，当日数据需等次日。判断"今天"必须用 `kline`/`quote` 的 `time` 字段，不能用 overview 的 date。
- **两融表**（`market_statis_margin_chg`）行内数值常空，全市场两融余额/周增拿不到 → 换 Wind/东财/iFinD 等专业源。
- **北向资金表**：仅覆盖沪深股通**个股**，ETF 持仓查不到（`data_north_holding` 对 ETF 返回 null，属已知限制）。盘后报告如实注明，勿据此下结论。

## 四、通用原则

1. **距支撑/压力位**：除按现价算空间，还必须检查当日 `high`/`low` 是否已盘中触及关键位，否则漏报。
2. **涨红跌绿**：A股约定，所有图表/报告遵守。
3. **催化剂核验**：研报/新闻里的"买入"评级常发在高位，需结合技术位与资金面交叉验证（例：券商 15 元发"买入"后跌 25%）。
4. **数据交叉**：单一源失败时换源（westock-mcp ↔ westock-data CLI ↔ 腾讯/东财直连）。
