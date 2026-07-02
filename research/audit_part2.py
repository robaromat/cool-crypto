#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Audit part 2 — replication BTC + sensibilite + hysteresis + OOS ; LQQ timing T+1."""
import urllib.request, csv, io, math, datetime as dt
from collections import OrderedDict

# ---------- BTC ----------
req = urllib.request.Request('https://raw.githubusercontent.com/coinmetrics/data/master/csv/btc.csv',
                             headers={'User-Agent': 'audit/1.0'})
raw = urllib.request.urlopen(req, timeout=120).read().decode('utf-8')
daily = {}
for x in csv.DictReader(io.StringIO(raw)):
    p = x.get('PriceUSD', '')
    if p and float(p) > 0:
        daily[x['time'][:10]] = float(p)
items = sorted(daily.items())
dates = [dt.date.fromisoformat(d) for d, _ in items]
prices = [p for _, p in items]
GENESIS = dt.date(2009, 1, 3)
def ds(d): return (d - GENESIS).days

monthly = OrderedDict()
for d, p in zip(dates, prices):
    k = (d.year, d.month)
    if k not in monthly: monthly[k] = (d, p)
mk = list(monthly.keys()); md = [monthly[k][0] for k in mk]; mp = [monthly[k][1] for k in mk]; N = len(mk)

def make_A(slope):
    cache = {}
    def A(y):
        if y not in cache:
            up = dt.date(y, 1, 1)
            res = [math.log(p) - slope * math.log(ds(d)) for d, p in zip(dates, prices) if d < up]
            cache[y] = sum(res) / len(res) if res else None
        return cache[y]
    return A

def bt_btc(slope=5.8, bh=2.5, bl=0.6, sma_w=10, buf=0.75, sticky=True,
           start=dt.date(2015, 1, 1), end=None):
    A = make_A(slope)
    val = 'CASH'; strat = 1.0; hodl = 1.0; cur = []; hc = []; nmo = 0
    for i in range(N):
        d, p = md[i], mp[i]
        a = A(d.year)
        ratio = p / math.exp(a + slope * math.log(ds(d))) if (a is not None and d.year >= 2013) else None
        if sticky and ratio is not None:
            if ratio > bh: val = 'CASH'
            elif ratio < bl: val = 'BUY'
        if d < start: continue
        if end and d > end: break
        if i - sma_w >= 0:
            s = sum(mp[i - sma_w + 1:i + 1]) / sma_w; up = p > s
        else: up = False
        if sticky:
            w = 0.0 if val == 'CASH' else (1.0 if up else buf)
        else:
            expensive = ratio is not None and ratio > bh
            w = 0.0 if expensive else (1.0 if up else buf)
        if i + 1 < N:
            r = mp[i + 1] / p - 1
            strat *= (1 + w * r); hodl *= (1 + r); nmo += 1
        cur.append(strat); hc.append(hodl)
    def cagr(m): return m ** (12 / nmo) - 1
    def mdd(c):
        pk, m = -1e18, 0
        for v in c: pk = max(pk, v); m = min(m, v / pk - 1)
        return m
    return dict(mult=strat, cagr=cagr(strat), mdd=mdd(cur), hmult=hodl, hcagr=cagr(hodl), hmdd=mdd(hc), months=nmo)

r = bt_btc()
print("=== VALIDATION replication BTC (attendu publie 01/07 : strat x1588, DD -44%%, 138 mois) ===")
print("replique : x%.0f (%.1f%%/an, DD %.1f%%), %d mois | HODL x%.0f (DD %.1f%%)" %
      (r['mult'], r['cagr'] * 100, r['mdd'] * 100, r['months'], r['hmult'], r['hmdd'] * 100))

print("\n=== SENSIBILITE BTC (base slope5.8 bh2.5 sma10 buf.75 sticky) ===")
def row(lab, **kw):
    x = bt_btc(**kw)
    print("%-34s x%7.0f %6.1f%%/an DD %6.1f%%" % (lab, x['mult'], x['cagr'] * 100, x['mdd'] * 100))
for bh in (2.0, 2.5, 3.0): row("band_high=%.1f" % bh, bh=bh)
for sw in (8, 10, 12): row("sma=%dm" % sw, sma_w=sw)
for bf in (0.5, 0.75, 1.0): row("buffer=%.0f%%" % (bf * 100), buf=bf)
for sl in (5.4, 5.8, 6.2): row("slope=%.1f" % sl, slope=sl)
row("INSTANTANE (sans hysteresis)", sticky=False)

print("\n=== OOS BTC (moities) ===")
for lab, a, b in [("2015-2020", dt.date(2015, 1, 1), dt.date(2020, 12, 31)),
                  ("2021-2026", dt.date(2021, 1, 1), None)]:
    x = bt_btc(start=a, end=b)
    print("%-10s strat x%6.1f %6.1f%%/an DD %6.1f%% | HODL x%5.1f %6.1f%%/an DD %6.1f%%" %
          (lab, x['mult'], x['cagr'] * 100, x['mdd'] * 100, x['hmult'], x['hcagr'] * 100, x['hmdd'] * 100))

# ---------- LQQ timing T+1 ----------
print("\n=== LQQ : execution au close de fin de mois (backtest) vs T+1 (realiste) ===")
ndx = {}
for line in open(r"C:/Users/RobinMarandet/SynologyDrive/Drive/Documents/PATRIMOINE/Bourse - equity/Cryptos/cool-crypto/engine/ndx_cache.csv", encoding='utf-8').read().splitlines()[1:]:
    p = line.split(',')
    if len(p) >= 2: ndx[dt.date.fromisoformat(p[0])] = float(p[1])
days = sorted(ndx)
lqq = {}; prev = None; lvl = 100.0
for d in days:
    if prev is not None: lvl *= (1 + 2 * (ndx[d] / ndx[prev] - 1))
    lqq[d] = lvl; prev = d
me = OrderedDict()
for d in days: me[(d.year, d.month)] = d
mk2 = list(me.keys()); mend = [me[k] for k in mk2]
nclose = [ndx[x] for x in mend]
def mom_pos(i, w): return nclose[i] / nclose[i - w] - 1 > 0 if i - w >= 0 else None
def expo(i):
    v = [mom_pos(i, w) for w in (6, 8, 10, 12)]
    vv = [x for x in v if x is not None]
    return sum(1 for x in vv if x) / len(vv) if vv else None
START = dt.date(1999, 1, 1)
def run_lqq(delay_days):
    strat = 1.0; cur = []; nmo = 0
    for i in range(1, len(mend)):
        if mend[i] < START: continue
        w = expo(i - 1)
        if w is None: continue
        # fenetre d'application : du (close fin de mois i-1 + delay) au (close fin de mois i + delay)
        i0 = days.index(mend[i - 1]) + delay_days
        i1 = days.index(mend[i]) + delay_days
        if i1 >= len(days): break
        r = lqq[days[i1]] / lqq[days[i0]] - 1
        strat *= (1 + w * r); nmo += 1; cur.append(strat)
    def mdd(c):
        pk, m = -1e18, 0
        for v in c: pk = max(pk, v); m = min(m, v / pk - 1)
        return m
    return strat, strat ** (12 / nmo) - 1, mdd(cur), nmo
for lab, dl in [("T+0 (comme le backtest publie)", 0), ("T+1 jour de bourse", 1), ("T+2", 2)]:
    m, c, d_, n = run_lqq(dl)
    print("%-32s x%6.1f  %5.1f%%/an  DD %6.1f%%  (%d mois)" % (lab, m, c * 100, d_ * 100, n))
