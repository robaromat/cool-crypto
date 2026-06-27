#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cool-crypto — signal mensuel LQQ (ETF Amundi ×2 quotidien sur le Nasdaq-100).

Une seule décision par mois (le 1er), MÊME ESPRIT que les signaux crypto, mais
adapté à un produit à LEVIER. Sur un ×2, ne pas timer = ruine (le buy & hold a
fait −98 % au krach dot-com 2000-02). Le signal protège du levier en bear et
capte les hausses.

Méthode retenue après étude comparative (cf. README) : ENSEMBLE DE MOMENTUM
ABSOLU multi-fenêtres sur le Nasdaq-100. C'est la méthode de momentum de Floran,
« robustifiée » : au lieu de parier sur UNE fenêtre (8 mois — fragile : ses
voisins 4 et 11 mois s'effondrent), on vote sur QUATRE fenêtres.

  - Pour chaque fenêtre w ∈ {6, 8, 10, 12} mois : le Nasdaq-100 a-t-il progressé
    sur les w derniers mois (rendement glissant > 0) ?
  - Exposition cible au LQQ = fraction des fenêtres positives → 0 / 25 / 50 / 75 / 100 %.
  - Le reste en cash (fonds monétaire / USDC).

Le LQQ est simulé à partir du Nasdaq-100 (^NDX) en ×2 quotidien (sans dividendes,
donc conservateur) ; simulation validée sur le vrai LQQ.PA depuis 2008 (drawdowns
COVID/2022 reproduits à ~1 point près, corrélation mensuelle 0,94).

Backtest 1999→2026 (signal mensuel) : ENSEMBLE ~×201, ~21 %/an, pire baisse −59 %
vs buy & hold LQQ ×32, ~14 %/an, pire baisse −98 %.

Génère : docs/lqq/history.csv, docs/lqq/data.json, docs/lqq/index.html
"""
import json, math, csv, io, os, sys, datetime as dt
from collections import OrderedDict
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs", "lqq")
WINDOWS = [6, 8, 10, 12]        # fenêtres de momentum (mois) — vote d'ensemble
START = dt.date(1999, 1, 1)     # début de l'historique publié (rodage momentum dès 1986)
LEVERAGE = 2.0                  # ×2 quotidien

UA = {"User-Agent": "cool-crypto/1.0 (+https://github.com/robaromat/cool-crypto)"}


def _get(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def fetch_ndx_daily():
    """Nasdaq-100 (^NDX) quotidien via Yahoo Finance (query1 puis query2 en secours)."""
    last_err = None
    for host in ("query1", "query2"):
        try:
            url = ("https://%s.finance.yahoo.com/v8/finance/chart/%%5ENDX"
                   "?period1=0&period2=9999999999&interval=1d" % host)
            j = json.loads(_get(url, 60))
            r = j["chart"]["result"][0]
            ts = r["timestamp"]
            close = r["indicators"]["quote"][0]["close"]
            out = {}
            for t, c in zip(ts, close):
                if c:
                    d = dt.datetime.fromtimestamp(t, dt.timezone.utc).date()
                    out[d] = float(c)
            if len(out) > 1000:
                return out
        except Exception as e:
            last_err = e
            print("WARN Yahoo %s: %s" % (host, e), file=sys.stderr)
    raise RuntimeError("Nasdaq-100 introuvable (Yahoo KO): %s" % last_err)


def build():
    ndx = fetch_ndx_daily()
    days = sorted(ndx)
    print("Données ^NDX:", days[0], "->", days[-1], "(%d jours)" % len(days))

    # LQQ simulé : ×2 du rendement QUOTIDIEN (capture la décote de volatilité)
    lqqd = {}
    prev = None
    lvl = 100.0
    for d in days:
        if prev is not None:
            r = ndx[d] / ndx[prev] - 1
            lvl *= (1 + LEVERAGE * r)
        lqqd[d] = lvl
        prev = d

    # séries mensuelles (dernier jour coté de chaque mois = clôture de fin de mois)
    me = OrderedDict()
    for d in days:
        me[(d.year, d.month)] = d
    mk = list(me.keys())
    mend = [me[k] for k in mk]
    nclose = [ndx[x] for x in mend]
    lclose = [lqqd[x] for x in mend]
    n = len(mk)

    def mom_positive(i, win):
        """Le Nasdaq a-t-il progressé sur les `win` derniers mois (jusqu'à la clôture i) ?"""
        if i - win < 0:
            return None
        return nclose[i] / nclose[i - win] - 1 > 0

    def exposure_at(i):
        """Exposition décidée à la clôture du mois i (votes des fenêtres)."""
        votes = [mom_positive(i, w) for w in WINDOWS]
        valid = [v for v in votes if v is not None]
        if not valid:
            return None, votes
        return sum(1 for v in valid if v) / len(valid), votes

    rows = []
    strat, hodl = 1.0, 1.0
    prev_w = None
    for i in range(n):
        d = mend[i]
        # exposition appliquée DURANT le mois i = décidée à la clôture du mois i-1
        w, votes_prev = exposure_at(i - 1) if i > 0 else (None, [None] * len(WINDOWS))
        if d < START or w is None:
            continue
        # rendement du LQQ pendant le mois i
        r_lqq = lclose[i] / lclose[i - 1] - 1
        strat *= (1 + w * r_lqq)
        hodl *= (1 + r_lqq)
        # action vs mois précédent
        if prev_w is None:
            action = "INIT"
        elif w > prev_w + 1e-9:
            action = "ACHETER"
        elif w < prev_w - 1e-9:
            action = "VENDRE"
        else:
            action = "CONSERVER"
        prev_w = w
        rows.append(dict(
            date=str(d), ndx=round(nclose[i], 2),
            mom6="HAUSSE" if mom_positive(i - 1, 6) else "BAISSE",
            mom8="HAUSSE" if mom_positive(i - 1, 8) else "BAISSE",
            mom10="HAUSSE" if mom_positive(i - 1, 10) else "BAISSE",
            mom12="HAUSSE" if mom_positive(i - 1, 12) else "BAISSE",
            votes=sum(1 for v in [mom_positive(i - 1, w) for w in WINDOWS] if v),
            target=round(w, 2), action=action,
            strat=round(strat, 4), hodl=round(hodl, 4),
        ))
    return rows


def equity_stats(rows):
    sc = [r["strat"] for r in rows]
    hc = [r["hodl"] for r in rows]
    nn = len(rows) - 1
    def cagr(m): return m ** (12 / nn) - 1 if nn > 0 else 0
    def mdd(c):
        pk = -1; m = 0
        for v in c:
            pk = max(pk, v); m = min(m, v / pk - 1)
        return m
    return dict(
        months=nn,
        strat_mult=sc[-1], hodl_mult=hc[-1],
        strat_cagr=cagr(sc[-1]), hodl_cagr=cagr(hc[-1]),
        strat_mdd=mdd(sc), hodl_mdd=mdd(hc),
    )


if __name__ == "__main__":
    rows = build()
    stats = equity_stats(rows)
    os.makedirs(DOCS, exist_ok=True)

    with open(os.path.join(DOCS, "history.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "nasdaq100", "mom_6m", "mom_8m", "mom_10m", "mom_12m",
                    "fenetres_positives", "cible_lqq", "action", "mult_strategie", "mult_hodl_lqq"])
        for r in rows:
            w.writerow([r["date"], r["ndx"], r["mom6"], r["mom8"], r["mom10"], r["mom12"],
                        r["votes"], r["target"], r["action"], r["strat"], r["hodl"]])

    payload = dict(
        generated_utc=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        params=dict(windows=WINDOWS, leverage=LEVERAGE),
        stats=stats, current=rows[-1], history=rows,
    )
    with open(os.path.join(DOCS, "data.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from build_site import render_lqq
        html = render_lqq(payload)
        with open(os.path.join(DOCS, "index.html"), "w", encoding="utf-8") as f:
            f.write(html)
        print("lqq/index.html écrit.")
    except Exception as e:
        print("WARN rendu HTML:", e, file=sys.stderr)

    c = rows[-1]
    print("\n=== SIGNAL COURANT LQQ (%s) ===" % c["date"])
    print("Nasdaq-100 %.0f | fenêtres positives %d/4" % (c["ndx"], c["votes"]))
    print("CIBLE: %.0f%% LQQ -> %s" % (c["target"] * 100, c["action"]))
    print("Strat x%.0f (%.1f%%/an, DD %.1f%%) | HODL LQQ x%.0f (%.1f%%/an, DD %.1f%%)" % (
        stats["strat_mult"], stats["strat_cagr"] * 100, stats["strat_mdd"] * 100,
        stats["hodl_mult"], stats["hodl_cagr"] * 100, stats["hodl_mdd"] * 100))
