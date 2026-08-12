#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
北向/沪深港通资金流向快照
数据源: 东方财富 push2 接口 (Bash 工具网络可达；独立 python 进程出口被 Reset，故仅作本机/自动化内 Bash 调用)
单位: 接口返回 netBuyAmt 为「万元」，转「亿」需 /10000
注意: 该接口在本环境常只返回 沪股通(sh2hk) 与 港股通(hk2sh/hk2sz)，深股通(sz2hk) 多缺失、且无 total 合计。
      缺失时以沪股通为北向代理并明确标注。
"""
import json
import sys
import urllib.request

URL = ("https://push2.eastmoney.com/api/qt/kamt/get"
       "?fields1=f1,f2,f3"
       "&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65"
       "&ut=7eea3edcaed734bea9cbfc24409ed989")


def wan_to_yi(x):
    return (x or 0.0) / 10000.0


def main():
    # 规避系统代理导致的 WinError 10061（urllib 默认读注册表代理）
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    urllib.request.install_opener(opener)
    try:
        with urllib.request.urlopen(URL, timeout=20) as r:
            raw = r.read().decode("utf-8")
        data = json.loads(raw)
    except Exception as e:
        print("ERROR: 北向接口获取失败 - %s" % e)
        sys.exit(1)

    d = data.get("data") or {}
    legs = {k: v for k, v in d.items() if isinstance(v, dict)}

    def net(k):
        return wan_to_yi((legs.get(k) or {}).get("netBuyAmt"))

    sh = net("sh2hk")     # 沪股通（北向·沪）
    sz = net("sz2hk")     # 深股通（北向·深）
    hk_sh = net("hk2sh")  # 港股通(沪)
    hk_sz = net("hk2sz")  # 港股通(深)

    date = ((legs.get("sh2hk") or {}).get("date2")
            or (legs.get("hk2sh") or {}).get("date2")
            or "未知")
    has_sz = "sz2hk" in legs
    north = sh + (sz if has_sz else 0.0)

    print(u"北向资金快照 @ %s" % date)
    print(u"沪股通净买入 : %+.2f 亿" % sh)
    if has_sz:
        print(u"深股通净买入 : %+.2f 亿" % sz)
        print(u"北向合计净买入: %+.2f 亿" % north)
    else:
        print(u"深股通(sz2hk): 数据源未返回（缺失）")
        print(u"北向(沪股通口径)净买入: %+.2f 亿  [注：仅含沪股通，未含深股通]" % sh)
    print(u"港股通(沪)净买入: %+.2f 亿" % hk_sh)
    print(u"港股通(深)净买入: %+.2f 亿" % hk_sz)

    direction = u"净流入" if north >= 0 else u"净流出"
    scope = (u"沪股通+深股通") if has_sz else u"仅沪股通口径(缺深股通)"
    print(u"SUMMARY: 北向资金%s约 %.2f 亿（%s）" % (direction, abs(north), scope))


if __name__ == "__main__":
    main()
