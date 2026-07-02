#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P2 — ensembles de parametres BTC/ETH : mesure vs criteres d'acceptation (audit §5-P2)."""
import urllib.request, csv, io, math, datetime as dt
from collections import OrderedDict

def fetch(sym):
    req = urllib.request.Request('https://raw.githubusercontent.com/coinmetrics/data/master/csv/%s.csv' % sym,
                                 headers={'User-Agent': 'audit/1.0'})
    raw = urllib.request.urlopen(req, timeout=120).read().decode('utf-8')
    out = {}
    for x in csv.DictReader(io.StringIO(raw)):
        p = x.get('PriceUSD', '')
        if p and float(p) > 0: out[x['time'][:10]] = float(p)
    return out

def prep(daily, genesis):
    items = sorted(daily.items())
    dates = [dt.date.fromisoformat(d) for d, _ in items]; prices = [p for _, p in items]
    monthly = OrderedDict()
    for d, p in zip(dates, prices):
        k = (d.year, d.month)
        if k not in monthly: monthly[k] = (d, p)
    mk = list(monthly.keys())
    return dates, prices, [monthly[k][0] for k in mk], [monthly[k][1] for k in mk]

def weights(dates, prices, md, mp, genesis, slope, bh, sticky, start, warm_year,
            bl=0.6, sma_w=10, buf=0.75):
    """Serie mensuelle des cibles pour UNE config (walk-forward)."""
    def ds(d): return max((d - genesis).days, 1)
    Ac = {}
    def A(y):
        if y not in Ac:
            up = dt.date(y, 1, 1)
            res = [math.log(p) - slope * math.log(ds(d)) for d, p in zip(dates, prices) if d < up]
            Ac[y] = sum(res) / len(res) if res else None
        return Ac[y]
    N = len(md); val = 'CASH'; out = []
    for i in range(N):
        d, p = md[i], mp[i]
        a = A(d.year)
        ratio = p / math.exp(a + slope * math.log(ds(d))) if (a is not None and d.year >= warm_year) else None
        if sticky and ratio is not None:
            if ratio > bh: val = 'CASH'
            elif ratio < bl: val = 'BUY'
        if d < start: continue
        up_t = i - sma_w >= 0 and p > sum(mp[i - sma_w + 1:i + 1]) / sma_w
        if sticky:
            w = 0.0 if val == 'CASH' else (1.0 if up_t else buf)
        else:
            w = 0.0 if (ratio is not None and ratio > bh) else (1.0 if up_t else buf)
        out.append((d, w))
    return out

def bt(wseries, md, mp, cost=0.0, start=None, end=None):
    """Backtest d'une serie de cibles (convention moteur : w du mois i -> rendement i->i+1)."""
    idx = {d: i for i, d in enumerate(md)}
    s = 1.0; cur = []; prev_w = None; nmo = 0
    for d, w in wseries:
        if (start and d < start) or (end and d > end): continue
        i = idx[d]
        dw = abs(w - prev_w) if prev_w is not None else 0.0
        prev_w = w
        s *= (1 - cost * dw)
        if i + 1 < len(md):
            s *= (1 + w * (mp[i + 1] / mp[i] - 1)); nmo += 1
        cur.append(s)
    pk, m = -1e18, 0.0
    for v in cur: pk = max(pk, v); m = min(m, v / pk - 1)
    return dict(mult=s, cagr=s ** (12 / nmo) - 1, mdd=m, months=nmo)

def ens(series_list):
    """Moyenne des cibles membre par membre, arrondie a 5%."""
    base = [d for d, _ in series_list[0]]
    out = []
    for j, d in enumerate(base):
        w = sum(sl[j][1] for sl in series_list) / len(series_list)
        out.append((d, round(w * 20) / 20))
    return out

def evaluate(name, daily, genesis, grid, sticky, base_cfg, start, warm_year, cagr_tol, sp=None):
    dates, prices, md, mp = prep(daily, genesis)
    A = dict(dates=dates, prices=prices, md=md, mp=mp, genesis=genesis, start=start, warm_year=warm_year)
    members = [weights(slope=sl, bh=bh, sticky=sticky, **A) for sl, bh in grid]
    e = ens(members)
    base_w = weights(slope=base_cfg[0], bh=base_cfg[1], sticky=sticky, **A)
    rb = bt(base_w, md, mp, cost=0.0025)
    re = bt(e, md, mp, cost=0.0025)
    cb, ce = rb['cagr'] / abs(rb['mdd']), re['cagr'] / abs(re['mdd'])
    print("\n=== %s : baseline vs ENSEMBLE (%d membres, net 25bps, %d mois) ===" % (name, len(grid), rb['months']))
    print("  baseline  : x%7.0f %6.1f%%/an DD %6.1f%% Calmar %.2f" % (rb['mult'], rb['cagr']*100, rb['mdd']*100, cb))
    print("  ensemble  : x%7.0f %6.1f%%/an DD %6.1f%% Calmar %.2f" % (re['mult'], re['cagr']*100, re['mdd']*100, ce))
    # criteres
    c1 = ce >= cb * 0.9
    c2 = (rb['cagr'] - re['cagr']) * 100 <= cagr_tol
    print("  crit.1 Calmar_ens >= 0.9x baseline : %.2f vs %.2f -> %s" % (ce, cb*0.9, "PASS" if c1 else "FAIL"))
    print("  crit.2 perte CAGR <= %d pts : %.1f pts -> %s" % (cagr_tol, (rb['cagr']-re['cagr'])*100, "PASS" if c2 else "FAIL"))
    # crit.3 leave-one-out : stabilite de l'ensemble
    worst = 0.0
    for k in range(len(members)):
        loo = ens(members[:k] + members[k+1:])
        rl = bt(loo, md, mp, cost=0.0025)
        worst = max(worst, abs(rl['cagr'] - re['cagr']) * 100)
    c3 = worst <= 3.0
    print("  crit.3 leave-one-out max |dCAGR| : %.2f pts -> %s" % (worst, "PASS" if c3 else "FAIL"))
    # OOS moities
    mid = start.replace(year=start.year + (2026 - start.year) // 2)
    for lab, a, b in [("1re moitie", start, mid), ("2e moitie", mid, None)]:
        rbh = bt(base_w, md, mp, 0.0025, a, b); reh = bt(e, md, mp, 0.0025, a, b)
        print("  OOS %-10s base %6.1f%%/an DD %5.1f%% | ens %6.1f%%/an DD %5.1f%%" % (
            lab, rbh['cagr']*100, rbh['mdd']*100, reh['cagr']*100, reh['mdd']*100))
    # turnover ensemble vs baseline
    tb = sum(abs(base_w[i][1]-base_w[i-1][1]) for i in range(1, len(base_w)))
    te = sum(abs(e[i][1]-e[i-1][1]) for i in range(1, len(e)))
    print("  turnover : baseline %.1fx -> ensemble %.1fx" % (tb, te))
    print("  VERDICT %s : %s" % (name, "ACCEPTE" if (c1 and c2 and c3) else "REJETE (reste en shadow)"))
    return c1 and c2 and c3

if __name__ == '__main__':
    btc = fetch('btc'); eth = fetch('eth')
    GRID_BTC = [(sl, bh) for sl in (5.4, 5.6, 5.8, 6.0, 6.2) for bh in (2.0, 2.5, 3.0)]
    GRID_ETH = [(sl, bh) for sl in (2.0, 2.2, 2.4, 2.6) for bh in (2.0, 2.5, 3.0)]
    ok_btc = evaluate("BTC", btc, dt.date(2009, 1, 3), GRID_BTC, True,  (5.8, 2.5), dt.date(2015, 1, 1), 2013, 15)
    ok_eth = evaluate("ETH", eth, dt.date(2015, 7, 30), GRID_ETH, False, (2.3, 2.5), dt.date(2017, 1, 1), 2016, 10)
