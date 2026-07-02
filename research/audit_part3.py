#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Audit part 3 — spot-check replication BTC vs CSV publie ; harnais ETH complet."""
import urllib.request, csv, io, math, datetime as dt
from collections import OrderedDict
REPO = r"C:/Users/RobinMarandet/SynologyDrive/Drive/Documents/PATRIMOINE/Bourse - equity/Cryptos/cool-crypto"

def fetch(sym):
    req = urllib.request.Request('https://raw.githubusercontent.com/coinmetrics/data/master/csv/%s.csv' % sym,
                                 headers={'User-Agent': 'audit/1.0'})
    raw = urllib.request.urlopen(req, timeout=120).read().decode('utf-8')
    out = {}
    for x in csv.DictReader(io.StringIO(raw)):
        p = x.get('PriceUSD', '')
        if p and float(p) > 0: out[x['time'][:10]] = float(p)
    return out

def harness(daily, genesis, slope, bh, bl, sma_w, buf, sticky, start, warm_year, end=None):
    items = sorted(daily.items())
    dates = [dt.date.fromisoformat(d) for d, _ in items]; prices = [p for _, p in items]
    def ds(d): return max((d - genesis).days, 1)
    monthly = OrderedDict()
    for d, p in zip(dates, prices):
        k = (d.year, d.month)
        if k not in monthly: monthly[k] = (d, p)
    mk = list(monthly.keys()); md = [monthly[k][0] for k in mk]; mp = [monthly[k][1] for k in mk]; N = len(mk)
    Ac = {}
    def A(y):
        if y not in Ac:
            up = dt.date(y, 1, 1)
            res = [math.log(p) - slope * math.log(ds(d)) for d, p in zip(dates, prices) if d < up]
            Ac[y] = sum(res) / len(res) if res else None
        return Ac[y]
    val = 'CASH'; strat = hodl = 1.0; cur = []; hc = []; nmo = 0; series = []
    for i in range(N):
        d, p = md[i], mp[i]
        a = A(d.year)
        ratio = p / math.exp(a + slope * math.log(ds(d))) if (a is not None and d.year >= warm_year) else None
        if sticky and ratio is not None:
            if ratio > bh: val = 'CASH'
            elif ratio < bl: val = 'BUY'
        if d < start: continue
        if end and d > end: break
        if i - sma_w >= 0:
            s = sum(mp[i - sma_w + 1:i + 1]) / sma_w; up = p > s
        else: up = False
        if sticky: w = 0.0 if val == 'CASH' else (1.0 if up else buf)
        else:
            w = 0.0 if (ratio is not None and ratio > bh) else (1.0 if up else buf)
        if i + 1 < N:
            r = mp[i + 1] / p - 1
            strat *= (1 + w * r); hodl *= (1 + r); nmo += 1
        cur.append(strat); hc.append(hodl); series.append((str(d), strat))
    def cagr(m): return m ** (12 / nmo) - 1 if nmo else 0
    def mdd(c):
        pk, m = -1e18, 0
        for v in c: pk = max(pk, v); m = min(m, v / pk - 1)
        return m
    return dict(mult=strat, cagr=cagr(strat), mdd=mdd(cur), hmult=hodl, hcagr=cagr(hodl), hmdd=mdd(hc),
                months=nmo, series=series)

# --- spot-check BTC vs CSV publie, meme date ---
btc = fetch('btc')
rb = harness(btc, dt.date(2009, 1, 3), 5.8, 2.5, 0.6, 10, 0.75, True, dt.date(2015, 1, 1), 2013)
pub = list(csv.DictReader(open(REPO + '/docs/history.csv', encoding='utf-8')))
pubmap = {r['date']: float(r['mult_strategie']) for r in pub}
print("=== SPOT-CHECK BTC : mult replique vs publie, memes dates ===")
for dstr, v in rb['series'][::24] + rb['series'][-3:]:
    if dstr in pubmap:
        print("  %s : replique %10.2f | publie %10.2f | ecart %+.1f%%" % (dstr, v, pubmap[dstr], (v / pubmap[dstr] - 1) * 100))

# --- harnais ETH complet (donnees du jour) ---
eth = fetch('eth')
G = dt.date(2015, 7, 30); S = dt.date(2017, 1, 1)
base = dict(daily=eth, genesis=G, slope=2.3, bh=2.5, bl=0.6, sma_w=10, buf=0.75, sticky=False, start=S, warm_year=2016)
r0 = harness(**base)
print("\n=== VALIDATION ETH (publie 01/07 : x204, DD -64%%, 114 mois) ===")
print("replique : x%.0f (%.1f%%/an, DD %.1f%%), %d mois" % (r0['mult'], r0['cagr'] * 100, r0['mdd'] * 100, r0['months']))
print("\n=== SENSIBILITE ETH (base slope2.3 bh2.5 sma10 buf.75 INSTANTANE) ===")
def row(lab, **kw):
    d = dict(base); d.update(kw); x = harness(**d)
    print("%-30s x%7.1f %6.1f%%/an DD %6.1f%%" % (lab, x['mult'], x['cagr'] * 100, x['mdd'] * 100))
for sl in (2.0, 2.3, 2.6): row("slope=%.1f" % sl, slope=sl)
for bh in (2.0, 2.5, 3.0): row("band_high=%.1f" % bh, bh=bh)
for sw in (8, 10, 12): row("sma=%dm" % sw, sma_w=sw)
for bf in (0.5, 0.75, 1.0): row("buffer=%.0f%%" % (bf * 100), buf=bf)
row("STICKY (hysteresis, comme BTC)", sticky=True)
print("\n=== OOS ETH (moities) ===")
for lab, a, b in [("2017-2021", dt.date(2017, 1, 1), dt.date(2021, 12, 31)),
                  ("2022-2026", dt.date(2022, 1, 1), None)]:
    d = dict(base); d.update(start=a, end=b); x = harness(**d)
    print("%-10s strat x%6.1f %6.1f%%/an DD %6.1f%% | HODL x%5.1f %6.1f%%/an DD %6.1f%%" %
          (lab, x['mult'], x['cagr'] * 100, x['mdd'] * 100, x['hmult'], x['hcagr'] * 100, x['hmdd'] * 100))
