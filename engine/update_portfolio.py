#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cool-crypto — portefeuille consolidé BTC + ETH + LQQ (P3 de l'audit du 02/07/2026).

Constat de l'audit (finding D2) : les rendements mensuels des trois stratégies sont
faiblement corrélés (BTC-ETH ≈ 0,44 ; BTC-LQQ ≈ 0,20 ; ETH-LQQ ≈ 0,22, fenêtre
2017→2026). Un portefeuille 1/3-1/3-1/3 rebalancé chaque mois a historiquement un
drawdown MEILLEUR que chacune des trois jambes, pour un rendement proche de la
meilleure. Cette page rend cette diversification actionnable : une seule consigne
consolidée par mois.

Méthode (v1, volontairement sans paramètre) :
  - chaque poche pèse 1/3 du portefeuille, rebalancée le 1er du mois ;
  - à l'intérieur de chaque poche, on applique la cible de la stratégie de l'actif
    (ex. poche BTC à 75 % -> 25 % du total en BTC, 8,3 % du total en cash) ;
  - le backtest compose les rendements mensuels des trois stratégies publiées
    (docs/*/data.json), bruts et nets de coûts (les coûts sont comptés DANS chaque
    jambe à 25 bps par arbitrage ; le rebalancement inter-poches mensuel est supposé
    sans friction — hypothèse documentée sur la page).

Ce script lit les data.json produits par update.py / update_eth.py / update_lqq.py :
il doit tourner APRÈS eux (ordre du workflow). Fenêtre = mois communs aux trois
historiques (le plus jeune, l'ETH, démarre en 2017 ; son premier mois de rendement
exploitable est 2017-02).

Génère : docs/portfolio/history.csv, docs/portfolio/data.json, docs/portfolio/index.html
"""
import json, csv, os, sys, datetime as dt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stats_common import cagr as _cagr, mdd as _mdd, bootstrap_mdd

DOCS = os.path.join(ROOT, "docs", "portfolio")
LEGS = [("BTC", "docs/data.json"), ("ETH", "docs/eth/data.json"), ("LQQ", "docs/lqq/data.json")]
W_LEG = 1.0 / len(LEGS)   # 1/3 par poche, rebalance mensuel


def load_leg(relpath):
    """Extrait du data.json d'une jambe : rendements mensuels (bruts, nets, hodl)
    et cible, indexés par mois 'YYYY-MM'. Le rendement du mois M = ratio des
    multiples publiés entre la ligne du mois M et la précédente (le premier mois
    de chaque série, sans prédécesseur, est ignoré)."""
    payload = json.load(open(os.path.join(ROOT, relpath), encoding="utf-8"))
    hist = payload["history"]
    out = {}
    for i in range(1, len(hist)):
        a, b = hist[i - 1], hist[i]
        month = b["date"][:7]
        out[month] = dict(
            r=b["strat"] / a["strat"] - 1,
            r_net=b["strat_net"] / a["strat_net"] - 1,
            r_hodl=b["hodl"] / a["hodl"] - 1,
            target=b["target"],
        )
    return out, payload["current"], payload["generated_utc"]


def build():
    legs, currents = {}, {}
    gen = None
    for name, path in LEGS:
        legs[name], currents[name], gen = load_leg(path)
    common = sorted(set.intersection(*(set(l.keys()) for l in legs.values())))
    # contiguite : aucun mois manquant au milieu de la fenetre commune
    def next_month(m):
        y, mo = int(m[:4]), int(m[5:7])
        return "%04d-%02d" % (y + mo // 12, mo % 12 + 1)
    holes = [m for i, m in enumerate(common[:-1]) if next_month(m) != common[i + 1]]
    if holes:
        raise RuntimeError("Trous dans la fenetre commune apres %s" % holes[:3])

    rows = []
    mult = mult_net = mult_hodl = 1.0
    for m in common:
        r = sum(legs[n][m]["r"] for n in legs) * W_LEG
        rn = sum(legs[n][m]["r_net"] for n in legs) * W_LEG
        rh = sum(legs[n][m]["r_hodl"] for n in legs) * W_LEG
        mult *= (1 + r); mult_net *= (1 + rn); mult_hodl *= (1 + rh)
        riskon = sum(legs[n][m]["target"] for n in legs) * W_LEG
        rows.append(dict(
            date=m,
            r_btc=round(legs["BTC"][m]["r"], 5), r_eth=round(legs["ETH"][m]["r"], 5),
            r_lqq=round(legs["LQQ"][m]["r"], 5), r_pf=round(r, 5),
            t_btc=legs["BTC"][m]["target"], t_eth=legs["ETH"][m]["target"],
            t_lqq=legs["LQQ"][m]["target"], riskon=round(riskon, 4),
            strat=round(mult, 4), strat_net=round(mult_net, 4), hodl=round(mult_hodl, 4),
        ))
    return rows, currents, gen


def equity_stats(rows):
    n = len(rows)   # chaque ligne porte exactement un rendement mensuel
    sc = [r["strat"] for r in rows]
    sn = [r["strat_net"] for r in rows]
    hc = [r["hodl"] for r in rows]
    rets = [r["r_pf"] for r in rows]
    boot_med, boot_p5, boot_p1 = bootstrap_mdd(rets)
    g = _cagr(sc[-1], n)
    dd = _mdd(sc)
    return dict(
        months=n, first_month=rows[0]["date"], last_month=rows[-1]["date"],
        strat_mult=sc[-1], strat_cagr=g, strat_mdd=dd,
        strat_mult_net=sn[-1], strat_cagr_net=_cagr(sn[-1], n), strat_mdd_net=_mdd(sn),
        hodl_mult=hc[-1], hodl_cagr=_cagr(hc[-1], n), hodl_mdd=_mdd(hc),
        calmar=g / abs(dd) if dd else None,
        avg_riskon=sum(r["riskon"] for r in rows) / n,
        boot_mdd_median=boot_med, boot_mdd_p5=boot_p5, boot_mdd_p1=boot_p1,
        cost_bps=25,
    )


if __name__ == "__main__":
    rows, currents, gen = build()
    stats = equity_stats(rows)
    os.makedirs(DOCS, exist_ok=True)

    with open(os.path.join(DOCS, "history.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["mois", "rdt_strat_btc", "rdt_strat_eth", "rdt_strat_lqq", "rdt_portefeuille",
                    "cible_btc", "cible_eth", "cible_lqq", "part_investie",
                    "mult_portefeuille", "mult_portefeuille_net", "mult_hodl_1_3"])
        for r in rows:
            w.writerow([r["date"], r["r_btc"], r["r_eth"], r["r_lqq"], r["r_pf"],
                        r["t_btc"], r["t_eth"], r["t_lqq"], r["riskon"],
                        r["strat"], r["strat_net"], r["hodl"]])

    payload = dict(
        generated_utc=gen or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        params=dict(weights={n: round(W_LEG, 4) for n, _ in LEGS}, rebalance="mensuel"),
        stats=stats, currents=currents, history=rows,
    )
    with open(os.path.join(DOCS, "data.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    try:
        from build_site import render_portfolio
        html = render_portfolio(payload)
        with open(os.path.join(DOCS, "index.html"), "w", encoding="utf-8") as f:
            f.write(html)
        print("portfolio/index.html écrit.")
    except Exception as e:
        print("WARN rendu HTML:", e, file=sys.stderr)

    print("\n=== PORTEFEUILLE CONSOLIDÉ (%s -> %s, %d mois) ===" % (
        stats["first_month"], stats["last_month"], stats["months"]))
    for n, _ in LEGS:
        print("  %s : cible %d%% de la poche -> %.1f%% du total" % (
            n, currents[n]["target"] * 100, currents[n]["target"] * W_LEG * 100))
    total_inv = sum(currents[n]["target"] for n, _ in LEGS) * W_LEG
    print("  CASH : %.1f%% du total" % ((1 - total_inv) * 100))
    print("Backtest : x%.0f (%.1f%%/an, DD %.1f%%) | net x%.0f (%.1f%%/an) | 1/3-HODL x%.0f (DD %.1f%%)" % (
        stats["strat_mult"], stats["strat_cagr"] * 100, stats["strat_mdd"] * 100,
        stats["strat_mult_net"], stats["strat_cagr_net"] * 100,
        stats["hodl_mult"], stats["hodl_mdd"] * 100))
