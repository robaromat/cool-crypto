#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Audit part 1 — analyses depuis les historiques PUBLIES (baseline exacte)."""
import csv, math, random, statistics as st

REPO = r"C:/Users/RobinMarandet/SynologyDrive/Drive/Documents/PATRIMOINE/Bourse - equity/Cryptos/cool-crypto"

def load(path, wcol, mult_s="mult_strategie", mult_h=None):
    rows = list(csv.DictReader(open(REPO + path, encoding="utf-8")))
    hcol = mult_h or ("mult_hodl" if "mult_hodl" in rows[0] else "mult_hodl_lqq")
    dates = [r["date"] for r in rows]
    w = [float(r[wcol]) for r in rows]
    ms = [float(r[mult_s]) for r in rows]
    mh = [float(r[hcol]) for r in rows]
    return dates, w, ms, mh

def cagr(mult, months): return mult ** (12 / months) - 1 if months > 0 else 0
def mdd(curve):
    pk, m = -1e18, 0
    for v in curve: pk = max(pk, v); m = min(m, v / pk - 1)
    return m

assets = {
    "BTC": load("/docs/history.csv", "cible_btc"),
    "ETH": load("/docs/eth/history.csv", "cible_eth"),
    "LQQ": load("/docs/lqq/history.csv", "cible_lqq"),
}

print("=== 1. TURNOVER & IMPACT DES COUTS (depuis history.csv publies) ===")
print("%-4s %6s %9s %10s | CAGR brut -> net a 10 / 25 / 50 bps (aller simple)" % ("", "mois", "arbitr.", "turnover"))
strat_rets = {}
for name, (dates, w, ms, mh) in assets.items():
    n = len(w)
    # rendements mensuels de la strategie et du hodl depuis les courbes publiees
    rs = [ms[i] / ms[i - 1] - 1 for i in range(1, n)]
    rh = [mh[i] / mh[i - 1] - 1 for i in range(1, n)]
    strat_rets[name] = (dates[1:], rs, rh, w)
    nreb = sum(1 for i in range(1, n) if abs(w[i] - w[i - 1]) > 1e-9)
    turn = sum(abs(w[i] - w[i - 1]) for i in range(1, n))   # aller simple, en multiples du portefeuille
    outs = []
    for c in (0.0010, 0.0025, 0.0050):
        net = 1.0
        for i in range(1, n):
            r = ms[i] / ms[i - 1] - 1
            net *= (1 + r) * (1 - c * abs(w[i] - w[i - 1]))
        outs.append(cagr(net, n - 1))
    g = cagr(ms[-1], n - 1)
    print("%-4s %6d %9d %9.1fx | %6.1f%% -> %5.1f%% / %5.1f%% / %5.1f%%  (drag max %.2f pt/an)"
          % (name, n, nreb, turn, g * 100, outs[0] * 100, outs[1] * 100, outs[2] * 100, (g - outs[2]) * 100))

print()
print("=== 2. CORRELATIONS (fenetre commune 2017-01 ->) ===")
# aligner sur dates communes approx: par (annee, mois)
def ym(d): return d[:7]
common = set(ym(d) for d in strat_rets["BTC"][0]) & set(ym(d) for d in strat_rets["ETH"][0]) & set(ym(d) for d in strat_rets["LQQ"][0])
common = sorted(m for m in common if m >= "2017-01")
def series(name, idx):
    dd, rs, rh, w = strat_rets[name]
    m2r = {ym(d): (rs[i] if idx == 0 else rh[i]) for i, d in enumerate(dd)}
    return [m2r[m] for m in common]
def corr(a, b):
    ma, mb = st.fmean(a), st.fmean(b)
    cov = st.fmean([(x - ma) * (y - mb) for x, y in zip(a, b)])
    return cov / (st.pstdev(a) * st.pstdev(b))
S = {n: series(n, 0) for n in assets}
H = {n: series(n, 1) for n in assets}
print("%d mois communs (%s -> %s)" % (len(common), common[0], common[-1]))
print("Correl. rendements ACTIFS  : BTC-ETH %.2f | BTC-LQQ %.2f | ETH-LQQ %.2f"
      % (corr(H["BTC"], H["ETH"]), corr(H["BTC"], H["LQQ"]), corr(H["ETH"], H["LQQ"])))
print("Correl. rendements STRATEG.: BTC-ETH %.2f | BTC-LQQ %.2f | ETH-LQQ %.2f"
      % (corr(S["BTC"], S["ETH"]), corr(S["BTC"], S["LQQ"]), corr(S["ETH"], S["LQQ"])))
# portefeuille 1/3 chacun, rebalance mensuel
pr = [(a + b + c) / 3 for a, b, c in zip(S["BTC"], S["ETH"], S["LQQ"])]
cur, curve = 1.0, []
for r in pr: cur *= (1 + r); curve.append(cur)
print("Portefeuille 1/3-1/3-1/3 (rebalance mensuel) : x%.1f (%.1f%%/an), MaxDD %.1f%%"
      % (cur, cagr(cur, len(pr)) * 100, mdd(curve) * 100))
for n in assets:
    cur2, curve2 = 1.0, []
    for r in S[n]: cur2 *= (1 + r); curve2.append(cur2)
    print("  %s seul sur la meme fenetre : x%.1f (%.1f%%/an), MaxDD %.1f%%" % (n, cur2, cagr(cur2, len(S[n])) * 100, mdd(curve2) * 100))

print()
print("=== 3. BOOTSTRAP PAR BLOCS (2000 tirages, blocs ~6 mois) — distribution du MaxDD ===")
random.seed(42)
def block_boot(rets, n_paths=2000, mean_block=6):
    n = len(rets); out = []
    for _ in range(n_paths):
        seq = []
        while len(seq) < n:
            start = random.randrange(n)
            blk = 1 + int(random.expovariate(1 / mean_block))
            seq.extend(rets[start:start + blk])
        seq = seq[:n]
        cur, curve = 1.0, []
        for r in seq: cur *= (1 + r); curve.append(cur)
        out.append((mdd(curve), cagr(cur, n)))
    return out
for name in assets:
    rs = strat_rets[name][1]
    res = block_boot(rs)
    dds = sorted(d for d, _ in res); cags = sorted(c for _, c in res)
    n = len(dds)
    print("%s : MaxDD median %.0f%% | 5%% pire %.0f%% | 1%% pire %.0f%%  (backtest observe: voir 1.) ; CAGR 5e pct %.1f%%"
          % (name, dds[n // 2] * 100, dds[int(n * 0.05)] * 100, dds[int(n * 0.01)] * 100, cags[int(n * 0.05)] * 100))
