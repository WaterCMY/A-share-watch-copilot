# -*- coding: utf-8 -*-
"""
盯盘工作台本地代理服务 v2
- 托管静态 HTML（单页工作台）
- /api/quotes  代理腾讯 qt.gtimg.cn（GBK 解码为 UTF-8 返回）
- /api/em      代理东方财富 push2delay.eastmoney.com 行情列表
- 使用 urllib 替代 curl，无外部依赖
- 支持 OPTIONS 预检请求
"""
import http.server
import urllib.parse
import urllib.request
import os
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8801
ROOT = os.path.dirname(os.path.abspath(__file__))
EM_BASE = 'https://push2delay.eastmoney.com/api/qt/clist/get'
QT_BASE = 'https://qt.gtimg.cn/q='
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
# 沪深京A股：沪市主板+深市主板+创业板+科创板+北交所
EM_BREADTH_FS = 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81'


class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype='text/plain; charset=utf-8'):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        if isinstance(body, str):
            body = body.encode('utf-8')
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send(200, '')

    def _proxy(self, url, decode):
        if 'sina' in url:
            referer = 'https://finance.sina.com.cn/'
        elif 'qt.gtimg' in url:
            referer = 'https://gu.qq.com/'
        else:
            referer = 'https://quote.eastmoney.com/'
        req = urllib.request.Request(url, headers={
            'User-Agent': UA,
            'Referer': referer,
            'Accept': '*/*',
        })
        with urllib.request.urlopen(req, timeout=12) as resp:
            raw = resp.read()
            return raw.decode(decode, 'ignore')

    def _fetch_em_page(self, pn, pz, fields):
        params = urllib.parse.urlencode({
            'pn': pn, 'pz': pz, 'po': 1, 'np': 1,
            'fltt': 2, 'invt': 2, 'fid': 'f3',
            'fs': EM_BREADTH_FS, 'fields': fields,
            '_': str(int(__import__('time').time() * 1000))
        })
        url = EM_BASE + '?' + params
        data = self._proxy(url, 'utf-8')
        return __import__('json').loads(data)

    def fetch_breadth(self):
        """分页拉取沪深京A股，计算市场宽度。东财接口 pz 超过100会被截断，必须循环。"""
        fields = 'f2,f3,f6'
        pz = 100
        up = down = flat = zt = dt = 0
        amt = 0.0
        total = None
        pn = 1
        while True:
            try:
                r = self._fetch_em_page(pn, pz, fields)
            except Exception:
                break
            data = r.get('data', {}) or {}
            if total is None:
                total = data.get('total', 0)
            diff = data.get('diff', [])
            if not diff:
                break
            def _f(v):
                try:
                    return float(v)
                except (TypeError, ValueError):
                    return 0.0
            for d in diff:
                pct = _f(d.get('f3'))
                price = _f(d.get('f2'))
                vol = _f(d.get('f6'))
                if pct > 0:
                    up += 1
                elif pct < 0:
                    down += 1
                else:
                    flat += 1
                # 过滤新股/复牌首日极端涨跌幅（>50%）后再统计涨停跌停
                if 9.9 <= pct <= 50:
                    zt += 1
                if -50 <= pct <= -9.9:
                    dt += 1
                amt += vol
            if len(diff) < pz or (total is not None and pn * pz >= total):
                break
            pn += 1
        ratio = round(up / (down or 1), 2)
        return {'up': up, 'down': down, 'flat': flat,
                'zt': zt, 'dt': dt, 'amount': round(amt / 1e8, 2),
                'ratio': ratio, 'total': total or (up + down + flat)}

    def fetch_kline(self, market, code, klt, lmt):
        """代理新浪K线(money.finance.sina.com.cn)。market: sh/sz；返回结构化 {name,code,klines:[{date,o,c,h,l,v}]}。
        注：东财 push2his 在当前环境不可达，故改用新浪源（ETF/股票均支持，symbol=market+code）。"""
        scale_map = {'d': 240, 'w': 1200, 'm': 10200, '101': 240, '102': 1200}
        scale = scale_map.get(klt, 240)
        symbol = market + code
        params = urllib.parse.urlencode({
            'symbol': symbol, 'scale': scale, 'ma': '5', 'datalen': lmt,
        })
        url = 'https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?' + params
        raw = self._proxy(url, 'utf-8')
        arr = __import__('json').loads(raw)
        out = []
        for d in arr:
            out.append({
                'date': str(d.get('day', '')).split(' ')[0],
                'o': float(d.get('open', 0)),
                'c': float(d.get('close', 0)),
                'h': float(d.get('high', 0)),
                'l': float(d.get('low', 0)),
                'v': float(d.get('volume', 0)),
            })
        return {'name': symbol, 'code': code, 'symbol': symbol, 'klines': out}

    def fetch_intraday(self, market, code):
        """代理东方财富分时(push2delay trends2)。返回 {name,code,points:[{t,price,avg,v}]}。"""
        sec = ('1' if market == 'sh' else '0') + '.' + code
        params = urllib.parse.urlencode({
            'secid': sec, 'fields1': 'f1,f2,f3,f7,f8',
            'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58',
            'iscr': '0', 'ndays': '1', 'forcect': '1',
        })
        url = 'https://push2delay.eastmoney.com/api/qt/stock/trends2/get?' + params
        raw = self._proxy(url, 'utf-8')
        d = __import__('json').loads(raw)
        dd = d.get('data') or {}
        tr = dd.get('trends') or []
        pts = []
        for row in tr:
            f = row.split(',')
            if len(f) < 8:
                continue
            pts.append({
                't': f[0], 'price': float(f[2]), 'avg': float(f[7]), 'v': float(f[6]),
            })
        return {'name': dd.get('name') or (market + code), 'code': code, 'points': pts}

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)

        if u.path == '/api/quotes':
            qs = urllib.parse.parse_qs(u.query)
            codes = qs.get('codes', [''])[0]
            if not codes:
                self._send(400, 'missing codes')
                return
            try:
                url = QT_BASE + codes + '&_=' + str(int(__import__('time').time()))
                data = self._proxy(url, 'gbk')
                self._send(200, data, 'text/plain; charset=utf-8')
            except Exception as e:
                self._send(502, 'proxy error: ' + str(e))
            return

        if u.path == '/api/em':
            url = EM_BASE + '?' + u.query
            try:
                data = self._proxy(url, 'utf-8')
                self._send(200, data, 'application/json; charset=utf-8')
            except Exception as e:
                self._send(502, '{"error":"%s"}' % str(e), 'application/json')
            return

        if u.path == '/api/breadth':
            try:
                data = self.fetch_breadth()
                self._send(200, __import__('json').dumps(data), 'application/json; charset=utf-8')
            except Exception as e:
                self._send(502, '{"error":"%s"}' % str(e), 'application/json')
            return

        if u.path == '/api/kline':
            qs = urllib.parse.parse_qs(u.query)
            market = qs.get('market', ['sh'])[0]
            code = qs.get('code', [''])[0]
            klt = qs.get('klt', ['101'])[0]
            lmt = qs.get('lmt', ['60'])[0]
            if not code:
                self._send(400, 'missing code')
                return
            try:
                data = self.fetch_kline(market, code, klt, lmt)
                self._send(200, __import__('json').dumps(data, ensure_ascii=False),
                           'application/json; charset=utf-8')
            except Exception as e:
                self._send(502, '{"error":"%s"}' % str(e), 'application/json')
            return

        if u.path == '/api/intraday':
            qs = urllib.parse.parse_qs(u.query)
            market = qs.get('market', ['sh'])[0]
            code = qs.get('code', [''])[0]
            if not code:
                self._send(400, 'missing code')
                return
            try:
                data = self.fetch_intraday(market, code)
                self._send(200, __import__('json').dumps(data, ensure_ascii=False),
                           'application/json; charset=utf-8')
            except Exception as e:
                self._send(502, '{"error":"%s"}' % str(e), 'application/json')
            return

        # 静态文件
        path = u.path
        if path in ('/', ''):
            path = '/workbench.html'
        fp = os.path.normpath(os.path.join(ROOT, path.lstrip('/')))
        if not fp.startswith(ROOT):
            self._send(403, 'forbidden')
            return
        if os.path.isfile(fp):
            ext = os.path.splitext(fp)[1].lower().lstrip('.')
            ctype = {
                'html': 'text/html; charset=utf-8',
                'js': 'application/javascript',
                'css': 'text/css',
                'json': 'application/json',
                'png': 'image/png',
            }.get(ext, 'application/octet-stream')
            with open(fp, 'rb') as f:
                self._send(200, f.read(), ctype)
        else:
            self._send(404, 'not found')

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        if u.path == '/api/sync':
            try:
                length = int(self.headers.get('Content-Length', 0) or 0)
                raw = self.rfile.read(length) if length else b''
                payload = json.loads(raw.decode('utf-8') or '{}')
                pj = os.path.join(ROOT, 'positions.json')
                with open(pj, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                now = time.strftime('%Y-%m-%d %H:%M:%S')
                base = data.get('positions', [])
                basemap = {(p.get('market'), p.get('code')): p for p in base}

                def manual_entry(m):
                    return {
                        'code': m.get('code'),
                        'name': m.get('name'),
                        'market': m.get('market'),
                        'shares': m.get('shares'),
                        'cost_price': m.get('cost'),
                        'current_price': None,
                        'market_value': None,
                        'pnl': None,
                        'pnl_pct': None,
                        'category': m.get('intent') or '手动录入',
                        'strategy': m.get('intent') or '手动录入',
                        'stop_loss': m.get('sl'),
                        'take_profit': m.get('tp'),
                        'manual': True,
                        'synced_at': now,
                        'realized_pnl': m.get('realized') or 0,
                    }

                if 'positions' in payload:
                    # 新契约：完整持仓列表（含手动+基仓，带 manual 标记与 realized）
                    # 匹配到 base 的仅更新 shares / realized_pnl，保留全部原始元数据（tech/boll/策略等）
                    # incoming 中不存在的 base 持仓视为清仓/移除，直接丢弃
                    result = []
                    for it in payload.get('positions', []):
                        key = (it.get('market'), it.get('code'))
                        b = basemap.get(key)
                        if b is not None:
                            b = dict(b)
                            b['shares'] = it.get('shares')
                            if it.get('cost') is not None:
                                b['cost_price'] = it.get('cost')
                            r = it.get('realized')
                            if r:
                                b['realized_pnl'] = r
                            elif 'realized_pnl' in b:
                                del b['realized_pnl']
                            result.append(b)
                        else:
                            result.append(manual_entry(it))
                    data['positions'] = result
                    count = len(result)
                else:
                    # 兼容旧契约：仅 manual 列表（替换所有 manual:true 项）
                    manual = payload.get('manual', [])
                    if not isinstance(manual, list):
                        manual = []
                    kept = [p for p in base if not p.get('manual')]
                    out = [manual_entry(m) for m in manual]
                    data['positions'] = kept + out
                    count = len(out)
                with open(pj, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                self._send(200, json.dumps({'ok': True, 'count': count}, ensure_ascii=False),
                           'application/json; charset=utf-8')
            except Exception as e:
                self._send(500, json.dumps({'ok': False, 'error': str(e)}, ensure_ascii=False),
                           'application/json; charset=utf-8')
            return
        self._send(405, json.dumps({'ok': False, 'error': 'method not allowed'}), 'application/json')

    def log_message(self, *a):
        pass


if __name__ == '__main__':
    srv = ThreadingHTTPServer(('127.0.0.1', PORT), H)
    print('serving on http://localhost:%d' % PORT)
    srv.serve_forever()
