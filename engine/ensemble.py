# -*- coding: utf-8 -*-
"""Ensembles de parametres pour les signaux G75 (P2 de l'audit du 02/07/2026).

Constat (findings B1/B3) : le resultat des strategies BTC/ETH est tres sensible a
la pente power-law choisie a la main (BTC : pente 5,4 -> x108 vs 5,8 -> x1945).
Correctif : au lieu d'UNE config, on vote sur une GRILLE pente x bande — l'exposition
ensemble = moyenne des allocations des membres, arrondie a 5 %.

Statut par actif (recherche du 02/07/2026, protocole audit §5-P2, net 25 bps) :
- ETH : ACCEPTE (Calmar 1,26 vs baseline 1,27 ; CAGR +4,6 pts ; leave-one-out 1,9 pt)
        -> publie en SHADOW 3 mois avant toute bascule de la consigne affichee.
- BTC : REJETE (Calmar 2,05 < 0,9 x 2,35) -> reste en SHADOW (observation), la
        consigne affichee reste la config historique ; sensibilite documentee.

Le champ `target_ens` publie dans data.json/history.csv N'EST PAS la consigne :
c'est le signal d'observation (shadow run).
"""
import math
import datetime as dt

# Grilles validees par la recherche du 02/07/2026 (ne pas modifier sans re-run
# du protocole : research/ ou AUDIT_MODELISATION_2026-07-02.md §5-P2).
GRID_BTC = [(sl, bh) for sl in (5.4, 5.6, 5.8, 6.0, 6.2) for bh in (2.0, 2.5, 3.0)]
GRID_ETH = [(sl, bh) for sl in (2.0, 2.2, 2.4, 2.6) for bh in (2.0, 2.5, 3.0)]


def member_weights(dates, prices, md, mp, genesis, slope, band_high, sticky,
                   start, warm_year, band_low=0.6, sma_win=10, buffer=0.75):
    """Cibles mensuelles d'UN membre (meme logique walk-forward que les moteurs)."""
    def ds(d):
        return max((d - genesis).days, 1)
    acache = {}

    def A(year):
        if year not in acache:
            upto = dt.date(year, 1, 1)
            res = [math.log(p) - slope * math.log(ds(d))
                   for d, p in zip(dates, prices) if d < upto]
            acache[year] = sum(res) / len(res) if res else None
        return acache[year]

    out = []
    val = "CASH"
    for i, d in enumerate(md):
        p = mp[i]
        a = A(d.year)
        ratio = (p / math.exp(a + slope * math.log(ds(d)))
                 if (a is not None and d.year >= warm_year) else None)
        if sticky and ratio is not None:
            if ratio > band_high:
                val = "CASH"
            elif ratio < band_low:
                val = "BUY"
        if d < start:
            continue
        trend_up = i - sma_win >= 0 and p > sum(mp[i - sma_win + 1:i + 1]) / sma_win
        if sticky:
            w = 0.0 if val == "CASH" else (1.0 if trend_up else buffer)
        else:
            w = 0.0 if (ratio is not None and ratio > band_high) else (1.0 if trend_up else buffer)
        out.append((d, w))
    return out


def ensemble_series(dates, prices, md, mp, genesis, grid, sticky, start, warm_year, **kw):
    """Cible ensemble par mois = moyenne des membres, arrondie a 5 %. Renvoie {date: w}."""
    members = [member_weights(dates, prices, md, mp, genesis, sl, bh, sticky,
                              start, warm_year, **kw) for sl, bh in grid]
    out = {}
    for j, (d, _) in enumerate(members[0]):
        w = sum(m[j][1] for m in members) / len(members)
        out[d] = round(w * 20) / 20
    return out


def shadow_stats(ens_map, md, mp, cost_oneway=0.0025):
    """Backtest du signal shadow (brut + net) pour observabilite dans data.json."""
    idx = {d: i for i, d in enumerate(md)}
    s = sn = 1.0
    cur = []
    prev_w = None
    nmo = 0
    for d in sorted(ens_map):
        w = ens_map[d]
        i = idx[d]
        dw = abs(w - prev_w) if prev_w is not None else 0.0
        prev_w = w
        sn *= (1 - cost_oneway * dw)
        if i + 1 < len(md):
            r = mp[i + 1] / mp[i] - 1
            s *= (1 + w * r)
            sn *= (1 + w * r)
            nmo += 1
        cur.append(s)
    pk, m = -1e18, 0.0
    for v in cur:
        pk = max(pk, v)
        m = min(m, v / pk - 1)
    cagr = (lambda x: x ** (12 / nmo) - 1 if nmo else 0.0)
    return dict(months=nmo, mult=round(s, 4), cagr=cagr(s), mult_net=round(sn, 4),
                cagr_net=cagr(sn), mdd=m)
