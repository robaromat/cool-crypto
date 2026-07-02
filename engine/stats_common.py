# -*- coding: utf-8 -*-
"""Statistiques communes aux trois moteurs (P1 de l'audit du 02/07/2026).

Ajoute aux stats publiées : performance nette de coûts de transaction, Calmar,
turnover, exposition moyenne, nombre d'arbitrages, et fourchette de MaxDD par
bootstrap de blocs (le MaxDD historique est un point unique sur un seul chemin ;
le bootstrap donne un ordre de grandeur de sa variance d'échantillonnage).

Conventions :
- coût appliqué à chaque changement de cible : facteur (1 - c·|Δw|), c aller simple ;
- bootstrap : blocs de longueur exponentielle (moyenne 6 mois), 2000 tirages, seed
  fixe (résultats reproductibles d'un run mensuel à l'autre à données égales).
"""
import math
import random

COST_ONEWAY = 0.0025   # 25 bps par aller — hypothèse par défaut (frais + spread)
BOOT_PATHS = 2000
BOOT_MEAN_BLOCK = 6
BOOT_SEED = 42


def cagr(mult, months):
    return mult ** (12 / months) - 1 if months > 0 else 0.0


def mdd(curve):
    pk, m = -1e18, 0.0
    for v in curve:
        pk = max(pk, v)
        m = min(m, v / pk - 1)
    return m


def bootstrap_mdd(monthly_rets, n_paths=BOOT_PATHS, mean_block=BOOT_MEAN_BLOCK, seed=BOOT_SEED):
    """Distribution du MaxDD par bootstrap de blocs stationnaire. Renvoie (médian, p5, p1)."""
    rng = random.Random(seed)
    n = len(monthly_rets)
    if n < 24:
        return None, None, None
    dds = []
    for _ in range(n_paths):
        seq = []
        while len(seq) < n:
            start = rng.randrange(n)
            blk = 1 + int(rng.expovariate(1.0 / mean_block))
            seq.extend(monthly_rets[start:start + blk])
        cur, pk, m = 1.0, 1.0, 0.0
        for r in seq[:n]:
            cur *= (1 + r)
            pk = max(pk, cur)
            m = min(m, cur / pk - 1)
        dds.append(m)
    dds.sort()
    return dds[len(dds) // 2], dds[int(len(dds) * 0.05)], dds[int(len(dds) * 0.01)]


def extra_stats(rows, months, cost_oneway=COST_ONEWAY):
    """Complète les stats à partir des rows du moteur (champs target, strat, strat_net)."""
    sc = [r["strat"] for r in rows]
    sn = [r["strat_net"] for r in rows]
    w = [r["target"] for r in rows]
    turnover = sum(abs(w[i] - w[i - 1]) for i in range(1, len(w)))
    n_trades = sum(1 for i in range(1, len(w)) if abs(w[i] - w[i - 1]) > 1e-9)
    rets = [sc[i] / sc[i - 1] - 1 for i in range(1, len(sc))]
    boot_med, boot_p5, boot_p1 = bootstrap_mdd(rets)
    g_cagr = cagr(sc[-1], months)
    n_cagr = cagr(sn[-1], months)
    g_mdd = mdd(sc)
    years = months / 12.0
    return dict(
        cost_bps=round(cost_oneway * 10000),
        strat_mult_net=sn[-1], strat_cagr_net=n_cagr, strat_mdd_net=mdd(sn),
        calmar=(g_cagr / abs(g_mdd)) if g_mdd else None,
        turnover=turnover, turnover_per_year=turnover / years if years else None,
        n_trades=n_trades,
        avg_exposure=sum(w) / len(w),
        boot_mdd_median=boot_med, boot_mdd_p5=boot_p5, boot_mdd_p1=boot_p1,
    )
