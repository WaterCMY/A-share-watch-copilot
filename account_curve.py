# -*- coding: utf-8 -*-
"""
account_curve.py — 账户每日资金曲线生成器（盯盘工作台配套）

功能：
  1. 回补各 A股/ETF 持仓的每日收盘价（东财历史K线，不复权 fqt=0，取实际成交价）
  2. 按 trades 还原每只持仓的「每日持股数」（baseline + 累计法，兼容"建仓(确切日不详)"）
  3. 叠加场外基金每日单位净值（东财 lsjz）
  4. 用「移动平均成本池」还原每只标的逐日真实成本均价（修复旧版"当前均价×历史股数"失真）
  5. 计算每日总市值 / 成本基数 / 浮盈 / 日涨跌%
  6. 单只抓取失败时不再整只丢弃：退回快照价(positions.current_price / funds.snap)作兜底，
     并在 gaps 字段显式记录缺口，供前端红字标注。
  7. 输出 portfolio_history.json，供 workbench.html 的「资金曲线」Tab 渲染

用法：
  python account_curve.py            # 全量重算并写盘（盘后自动化每日调用此命令即可续接）
  python account_curve.py --days 90  # 指定回补交易日数（默认 90）

注意：
  - 环境代理 127.0.0.1:7892 已关闭，故一律走 ProxyHandler({}) 直连。
  - 东财 push2his / api.fund.eastmoney 经 Bash 网络可达（独立 python 进程出口 Reset 的是 push2 另一主机）。
  - 单只失败不影响整体，最终必产出合法 JSON（缺口记入 gaps）。
"""
import json
import os
import sys
import time
import urllib.request
import urllib.parse
import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
POS = os.path.join(ROOT, 'positions.json')
FUND = os.path.join(ROOT, 'funds.json')
OUT = os.path.join(ROOT, 'portfolio_history.json')

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'
OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def http_get(url, referer='https://quote.eastmoney.com/', retries=4, delay=0.4):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Referer': referer})
            with OP.open(req, timeout=25) as r:
                return r.read().decode('utf-8')
        except Exception as e:
            last = e
            if attempt < retries - 1:
                time.sleep(delay * (attempt + 1))
    raise last


def em_kline(secid, days):
    """返回 {date: close}  不复权收盘价（最近约 days 个交易日）。
    主源：东财 push2his 历史K线；该接口偶发被网络 Reset 时自动回退新浪日K（更稳）。"""
    out = _em_kline_push2his(secid, days)
    if out:
        return out
    return _em_kline_sina(secid, days)


def _em_kline_push2his(secid, days):
    try:
        end_dt = datetime.date.today()
        beg_dt = end_dt - datetime.timedelta(days=int(days * 1.7) + 14)
        beg = beg_dt.strftime('%Y%m%d')
        url = ('https://push2his.eastmoney.com/api/qt/stock/kline/get'
               '?fields1=f1,f2,f3,f4,f5,f6'
               '&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61'
               '&ut=fa5fd194cee8f6f5a3cdefb5b7f3b1a9&pi=0&klt=101&fqt=0'
               f'&secid={secid}&beg={beg}&end=20500101&lmt={days * 2}')
        d = json.loads(http_get(url))
        kl = (d.get('data') or {}).get('klines') or []
        out = {}
        for s in kl:
            p = s.split(',')
            if len(p) >= 3:
                out[p[0]] = float(p[2])
        return out
    except Exception as e:
        return None


def _em_kline_sina(secid, days):
    """新浪日K兜底源：返回 {date: close}，date 格式 YYYY-MM-DD，约 days 个交易日。"""
    try:
        prefix = 'sh' if secid.startswith('1.') else 'sz'
        code = secid.split('.')[1]
        symbol = prefix + code
        url = ('https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/'
               f'CN_MarketData.getKLineData?symbol={symbol}&scale=240&ma=no&datalen={days}')
        txt = http_get(url, referer='https://finance.sina.com.cn/')
        rows = json.loads(txt)
        out = {}
        for r in rows:
            d = r.get('day')
            c = r.get('close')
            if d and c:
                out[d] = float(c)
        return out
    except Exception:
        return None


def fund_nav(code, lmt):
    """返回 {date: 单位净值}"""
    url = ('https://api.fund.eastmoney.com/f10/lsjz'
           f'?fundCode={code}&pageIndex=1&pageSize={min(lmt, 100)}')
    d = json.loads(http_get(url, referer='https://fundf10.eastmoney.com/'))
    rows = (d.get('Data') or {}).get('LSJZList') or []
    out = {}
    for r in rows:
        fsrq = r.get('FSRQ')
        dwjz = r.get('DWJZ')
        if fsrq and dwjz:
            try:
                out[fsrq] = float(dwjz)
            except ValueError:
                pass
    return out


def fetch_with_retry(fn, *a, attempts=5, pause=0.8):
    last = None
    for _ in range(attempts):
        try:
            r = fn(*a)
            if r:
                return r, None
        except Exception as e:
            last = e
        time.sleep(pause)
    return None, last


def parse_date(s):
    if not s:
        return None
    s = s.strip()
    for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S'):
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def build_shares_events(trades, current_shares, current_cost):
    """返回 (baseline, events)。
    events = [(date, delta_shares, kind, price, fee), ...] 按日期升序。
    baseline = 当前股数 - 所有"可解析日期"交易的累计变动。
    shares_on(date) = baseline + Σ(delta for dt<=date)。
    cost_per_share 由 build_cost_pool 用移动平均法还原。
    """
    events = []
    dated_delta = 0.0
    for t in (trades or []):
        d = parse_date(t.get('date', ''))
        if d is None:
            continue
        sh = float(t.get('shares', 0) or 0)
        price = float(t.get('price', 0) or 0)
        fee = float(t.get('fee', 0) or 0)
        side = str(t.get('side', '')).lower()
        if side in ('open', 'buy'):
            mult, kind = 1, 'buy'
        elif side == 'sell':
            mult, kind = -1, 'sell'
        else:
            continue
        delta = mult * sh
        events.append((d, delta, kind, price, fee))
        dated_delta += delta
    baseline = float(current_shares) - dated_delta
    if baseline < 0:
        baseline = 0.0
    events.sort(key=lambda x: x[0])
    return baseline, events


def shares_on(baseline, events, date):
    s = baseline
    for dt, delta, _, _, _ in events:
        if dt <= date:
            s += delta
        else:
            break
    return s


def build_cost_pool(baseline, events, current_cost, axis):
    """返回与 axis 对齐的逐日成本均价列表（移动平均成本法）。
    基线持仓按 current_cost 初始化成本池，逐笔交易滚动：
      buy  : 成本池 += 数量×价格 + 手续费
      sell : 成本池 -= (成本池/股数)×卖出数量（移除对应成本）
    最终 avg = 成本池/股数。基线成本未知的误差很小（<1%），属可接受近似。
    """
    cps = []
    sh = baseline
    pl = baseline * current_cost
    ti = 0
    for ds in axis:
        d = datetime.datetime.strptime(ds, '%Y-%m-%d').date()
        while ti < len(events) and events[ti][0] <= d:
            _, delta, kind, price, fee = events[ti]
            if kind == 'buy':
                sh += delta
                pl += delta * price + fee
            else:  # sell
                if sh > 0:
                    removed = pl / sh * abs(delta)
                    pl -= removed
                    sh += delta  # delta 为负
            ti += 1
        cps.append(pl / sh if sh > 0 else 0.0)
    return cps


def ff(m, axis):
    """对 axis 日期序列做前向填充，返回对齐的 value 列表"""
    vals = [m.get(d) for d in axis]
    first = next((v for v in vals if v is not None), None)
    out, last = [], first
    for v in vals:
        if v is not None:
            last = v
        out.append(last if last is not None else 0.0)
    return out


def main():
    days = 90
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == '--days' and i + 1 < len(args):
            try:
                days = int(args[i + 1])
            except ValueError:
                pass

    pos = json.load(open(POS, encoding='utf-8'))
    fund = json.load(open(FUND, encoding='utf-8'))

    warnings = []
    gaps = []  # 缺口：抓取失败退回快照兜底的标的

    # ---- 持仓（A股/ETF）----
    instruments = []  # {kind, name, code, baseline, events, cmap/flat, cost, missing}
    for p in pos.get('positions', []):
        code = p['code']
        market = p.get('market', 'sh')
        secid = ('1' if market == 'sh' else '0') + '.' + code
        cur = float(p['shares'])
        cur_cost = float(p.get('cost_price', 0) or 0)
        cmap, err = fetch_with_retry(em_kline, secid, days)
        baseline, events = build_shares_events(p.get('trades'), cur, cur_cost)
        if not cmap:
            snap = float(p.get('current_price', 0) or cur_cost or 0)
            warnings.append(f'持仓 {code} K线失败(退回快照价 {snap}): {err}')
            gaps.append({'code': code, 'name': p.get('name', code), 'kind': 'stock',
                         'proxy': 'current_price', 'value': snap})
            instruments.append({
                'kind': 'stock', 'name': p.get('name', code), 'code': code,
                'baseline': baseline, 'events': events, 'cmap': None,
                'flat': snap, 'cost': cur_cost, 'missing': True,
            })
        else:
            instruments.append({
                'kind': 'stock', 'name': p.get('name', code), 'code': code,
                'baseline': baseline, 'events': events, 'cmap': cmap,
                'cost': cur_cost, 'missing': False,
            })
        time.sleep(0.15)

    # ---- 场外基金 ----
    for f in fund.get('funds', []):
        code = f['code']
        cur = float(f.get('shares', 0) or 0)
        cur_cost = float(f.get('cost', 0) or 0)
        nmap, err = fetch_with_retry(fund_nav, code, days)
        baseline, events = build_shares_events(f.get('trades'), cur, cur_cost)
        if not nmap:
            snap = float(f.get('snap', 0) or cur_cost or 0)
            warnings.append(f'基金 {code} 净值失败(退回快照净值 {snap}): {err}')
            gaps.append({'code': code, 'name': f.get('name', code), 'kind': 'fund',
                         'proxy': 'snap', 'value': snap})
            instruments.append({
                'kind': 'fund', 'name': f.get('name', code), 'code': code,
                'baseline': baseline, 'events': events, 'cmap': None,
                'flat': snap, 'cost': cur_cost, 'missing': True,
            })
        else:
            instruments.append({
                'kind': 'fund', 'name': f.get('name', code), 'code': code,
                'baseline': baseline, 'events': events, 'cmap': nmap,
                'cost': cur_cost, 'missing': False,
            })

    # ---- 统一日期轴（并集，仅来自成功抓取的标的历史），裁剪到最近 days 个交易日 ----
    all_dates = set()
    for it in instruments:
        if it['cmap']:
            all_dates |= set(it['cmap'].keys())
    axis = sorted(all_dates)
    if len(axis) > days:
        axis = axis[-days:]

    # 对齐每个 instrument 的价格序列 + 成本池序列
    for it in instruments:
        if it['missing']:
            it['series'] = [it['flat']] * len(axis)
            it['cps'] = [it['cost']] * len(axis)
        else:
            it['series'] = ff(it['cmap'], axis)
            it['cps'] = build_cost_pool(it['baseline'], it['events'], it['cost'], axis)

    # ---- 逐日计算 ----
    series = []
    prev_value = None
    for i, d in enumerate(axis):
        v = 0.0
        cb = 0.0
        dd = datetime.datetime.strptime(d, '%Y-%m-%d').date()
        for it in instruments:
            sh = shares_on(it['baseline'], it['events'], dd)
            price = it['series'][i]
            cost_ps = it['cps'][i]
            v += price * sh
            cb += cost_ps * sh
        pnl = v - cb
        chg = None
        if prev_value not in (None, 0):
            chg = (v - prev_value) / prev_value * 100
        series.append({
            'date': d,
            'value': round(v, 2),
            'cost': round(cb, 2),
            'pnl': round(pnl, 2),
            'pnl_pct': round(pnl / cb * 100, 2) if cb else 0.0,
            'chg_pct': round(chg, 2) if chg is not None else None,
        })
        prev_value = v

    out = {
        'generated_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
        'source': 'positions.json + funds.json + 东财历史K线(新浪日K兜底)/基金净值回补(不复权)',
        'days': days,
        'instruments': len(instruments),
        'points': len(series),
        'warnings': warnings,
        'gaps': gaps,
        'series': series,
    }
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)

    # ---- 控制台摘要 ----
    if series:
        first, last = series[0], series[-1]
        peak = max(s['value'] for s in series)
        max_dd = 0.0
        seen_peak = False
        for s in series:
            if s['value'] >= peak * 0.9999:
                seen_peak = True
            if seen_peak:
                dd = (peak - s['value']) / peak * 100
                if dd > max_dd:
                    max_dd = dd
        print(f'✅ 已生成 portfolio_history.json')
        print(f'   数据区间: {first["date"]} ~ {last["date"]}  ({len(series)} 个交易日)')
        print(f'   覆盖标的数: {len(instruments)}  (警告 {len(warnings)} 条, 缺口 {len(gaps)} 只)')
        print(f'   起始市值: ¥{first["value"]:,.0f}  最新市值: ¥{last["value"]:,.0f}')
        print(f'   区间收益: {sign(last["pnl"])}¥{abs(last["pnl"]):,.0f} ({last["pnl_pct"]:+.2f}% 成本口径)')
        print(f'   最大回撤(峰后): {max_dd:.2f}%')
        if warnings:
            print('   警告:')
            for w in warnings[:10]:
                print('     -', w)
        if gaps:
            print('   缺口(已用快照兜底, 市值可能低估):')
            for g in gaps:
                print(f'     - {g["name"]}({g["code"]}) -> {g["proxy"]}={g["value"]}')
    else:
        print('⚠️ 未生成任何数据点（检查网络/接口）')


def sign(n):
    return '+' if n >= 0 else '-'


if __name__ == '__main__':
    main()
